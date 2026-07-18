import logging
import threading
import time
from datetime import datetime
from backend.app.core.database import SessionLocal, Station
from backend.app.services.ingestion.cpcb import (
    fetch_cpcb_live_reading,
    fetch_nationwide_records,
)
from backend.app.services.ingestion.openmeteo import fetch_openmeteo_live_weather
from backend.app.services.ingestion.firms import fetch_upwind_fire_index
from backend.app.services.ingestion.cache import commit_normalized_observation

logger = logging.getLogger(__name__)

# Global lock and state to prevent duplicate concurrent sync jobs
_ingestion_lock = threading.Lock()
_ingestion_in_progress = False

def warm_city_cache() -> bool:
    """
    Pre-warm the government API nationwide cache with a single bulk fetch call.
    """
    logger.info("[Cache Warm-up] Fetching nationwide CPCB records...")
    success = fetch_nationwide_records()
    if success:
        logger.info("[Cache Warm-up] Nationwide cache pre-warmed successfully.")
    else:
        logger.warning("[Cache Warm-up] Nationwide cache pre-warm skipped or failed.")
    return success

def trigger_hourly_ingestion() -> dict:
    """
    Background scheduler ingestion process.
    """
    global _ingestion_in_progress

    with _ingestion_lock:
        if _ingestion_in_progress:
            logger.warning("[Ingestion Scheduler] Ingestion sync is already running. Skipping duplicate job.")
            return {"status": "skipped", "message": "Another ingestion job is currently running."}
        _ingestion_in_progress = True

    logger.info("[Ingestion Scheduler] Ingestion sync lock acquired.")
    db = SessionLocal()
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    try:
        stations = db.query(Station).all()
        logger.info(f"[Ingestion Scheduler] Running live sync for {len(stations)} stations at {now}...")

        # Pre-warm government cache in bulk first
        warm_city_cache()

        synced_count = 0
        failures = 0

        for st in stations:
            try:
                # 1. Fetch live observations using fallback chain (passes DB session for local query fallback)
                aq_data = fetch_cpcb_live_reading(
                    station_id=st.id,
                    latitude=st.latitude,
                    longitude=st.longitude,
                    city=st.city,
                    station_name=st.name,
                    db=db
                )

                # Skip if data is unavailable (avoid inserting null pollutant values)
                if aq_data["pm25"] is None or aq_data["no2"] is None:
                    logger.warning(f"[Ingestion Scheduler] Station {st.name} ({st.id}) returned null pollutant values. Skipping DB write.")
                    failures += 1
                    continue

                # 2. Fetch live meteorology
                weather = fetch_openmeteo_live_weather(st.latitude, st.longitude)

                # 3. Fetch satellite biomass index
                fire = fetch_upwind_fire_index(
                    st.latitude,
                    st.longitude,
                    weather["wind_speed"],
                    weather["wind_direction"]
                )

                # 4. Commit observations to SQLite cache
                commit_normalized_observation(
                    db=db,
                    station_id=st.id,
                    timestamp=now,
                    pm25=aq_data["pm25"],
                    no2=aq_data["no2"],
                    temp=weather["temperature"],
                    humidity=weather["humidity"],
                    wind_speed=weather["wind_speed"],
                    wind_deg=weather["wind_direction"],
                    fire_intensity=fire["upwind_fire_intensity"],
                    fire_count=fire["upwind_fire_count"],
                    source=aq_data["metadata"]["source"],
                    quality_flag=aq_data["metadata"]["quality_status"]
                )
                synced_count += 1

            except Exception as e:
                logger.error(f"[Ingestion Scheduler] Sync failed for station {st.name} ({st.id}): {e}")
                failures += 1

        db.commit()
        logger.info(f"[Ingestion Scheduler] Ingestion sync complete. Synced: {synced_count}, Failed: {failures}.")
        return {"status": "success", "synced": synced_count, "failures": failures}

    finally:
        db.close()
        with _ingestion_lock:
            _ingestion_in_progress = False
        logger.info("[Ingestion Scheduler] Ingestion sync lock released.")
