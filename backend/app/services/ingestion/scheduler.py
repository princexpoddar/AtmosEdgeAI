import logging
import time
from datetime import datetime
from backend.app.core.database import SessionLocal, Station
from backend.app.services.ingestion.cpcb import (
    fetch_cpcb_live_reading,
    fetch_city_records_cached,
    fetch_nationwide_records,
)
from backend.app.services.ingestion.openmeteo import fetch_openmeteo_live_weather
from backend.app.services.ingestion.firms import fetch_upwind_fire_index
from backend.app.services.ingestion.cache import commit_normalized_observation

logger = logging.getLogger(__name__)


def warm_city_cache(stations=None) -> bool:
    """
    Pre-warm the government API nationwide cache with a single API call.
    This loads all 4671+ India station records once, which are then served
    from in-memory cache for all 40 monitoring stations during sync.
    Returns True on success.
    """
    logger.info("[Cache Warm-up] Fetching nationwide CPCB records...")
    success = fetch_nationwide_records()
    if success:
        logger.info("[Cache Warm-up] Nationwide cache loaded successfully.")
    else:
        logger.warning("[Cache Warm-up] Nationwide fetch failed. Sync will use cached defaults.")
    return success


def trigger_hourly_ingestion() -> dict:
    """
    Background scheduler process. Executes every hour to refresh live observations
    across all active monitoring stations.
    """
    db = SessionLocal()
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    
    stations = db.query(Station).all()
    print(f"[Ingestion Scheduler] Triggering live sync for {len(stations)} stations at timestamp {now}...")
    
    # Pre-warm government API cache to avoid per-station concurrent API calls
    warm_city_cache(stations)

    synced_count = 0
    failures = 0
    
    for st in stations:
        try:
            # 1. Fetch live air quality (reads from warm cache, no new HTTP call)
            aq_data = fetch_cpcb_live_reading(st.id, st.latitude, st.longitude, st.city, st.name)
            
            # 2. Fetch live weather forecast
            weather = fetch_openmeteo_live_weather(st.latitude, st.longitude)
            
            # 3. Fetch fire indexes
            fire = fetch_upwind_fire_index(
                st.latitude, 
                st.longitude, 
                weather["wind_speed"], 
                weather["wind_direction"]
            )
            
            # 4. Commit normalized data to SQLite
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
                source="CPCBAPI",
                quality_flag=aq_data["quality_flag"]
            )
            synced_count += 1
        except Exception as e:
            logger.error(f"[Ingestion Scheduler] Sync failed for station {st.name} (ID: {st.id}): {e}")
            failures += 1
            
    db.close()
    print(f"[Ingestion Scheduler] Sync complete. Successful: {synced_count}, Failed: {failures}.")
    return {"status": "success", "synced": synced_count, "failures": failures}
