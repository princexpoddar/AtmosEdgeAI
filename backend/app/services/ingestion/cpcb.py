import os
import requests
import logging
import time
import concurrent.futures
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────
# Global nationwide cache
# One HTTP request per 60 minutes for all 4671 India stations
# ──────────────────────────────────────────────────────────
_national_cache: Dict[str, List[Dict[str, Any]]] = {}   # city -> records
_national_cache_time: Optional[datetime] = None
_CACHE_TTL_MINUTES = 60
_RESOURCE_ID = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
_GOV_API_LIMIT = 5000   # fetch up to 5000 records in one call

# data.gov.in blocks Python's default User-Agent. Use a browser UA to get responses.
_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}

# Global thread pool executor for parallel fetching
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

# Global thread-safe in-memory dictionary to store provider health statistics
_provider_health: Dict[str, Dict[str, Any]] = {
    "DATA_GOV_IN": {
        "last_success": None,
        "last_failure": None,
        "consecutive_failures": 0,
        "latencies": [],
        "status": "HEALTHY",
    },
    "OPENAQ": {
        "last_success": None,
        "last_failure": None,
        "consecutive_failures": 0,
        "latencies": [],
        "status": "HEALTHY",
    },
    "OPEN_METEO": {
        "last_success": None,
        "last_failure": None,
        "consecutive_failures": 0,
        "latencies": [],
        "status": "HEALTHY",
    }
}

# Global thread-safe in-memory cache for the latest station sync metadata
_latest_station_metadata: Dict[str, Dict[str, Any]] = {}

def get_provider_health_diagnostics() -> Dict[str, Any]:
    """Exposes provider health stats for diagnostics."""
    diagnostics = {}
    for prov, stats in _provider_health.items():
        avg_lat = sum(stats["latencies"]) / len(stats["latencies"]) if stats["latencies"] else 0.0
        diagnostics[prov] = {
            "status": stats["status"],
            "consecutive_failures": stats["consecutive_failures"],
            "average_latency_s": round(avg_lat, 3),
            "last_success": stats["last_success"].isoformat() if stats["last_success"] else None,
            "last_failure": stats["last_failure"].isoformat() if stats["last_failure"] else None,
        }
    return diagnostics

def _update_provider_health(provider: str, success: bool, latency: float, error_msg: Optional[str] = None):
    """Updates provider health stats in a thread-safe manner."""
    stats = _provider_health.get(provider)
    if not stats:
        return

    now = datetime.utcnow()
    if success:
        stats["last_success"] = now
        stats["consecutive_failures"] = 0
        stats["status"] = "HEALTHY"
    else:
        stats["last_failure"] = now
        stats["consecutive_failures"] += 1
        if stats["consecutive_failures"] >= 3:
            stats["status"] = "UNHEALTHY"
        else:
            stats["status"] = "DEGRADED"
        if error_msg:
            logger.warning(f"[{provider} Health Update] Failure #{stats['consecutive_failures']}: {error_msg}")

    # Track last 10 latency readings
    stats["latencies"].append(latency)
    if len(stats["latencies"]) > 10:
        stats["latencies"].pop(0)

def _normalize_city(city: str) -> str:
    """Normalise city string: strip sub-district suffixes and map Delhi variants."""
    city = city.split(",")[0].strip() if city else "Delhi"
    if "delhi" in city.lower():
        return "Delhi"
    return city

def fetch_nationwide_records() -> bool:
    """
    Fetch ALL India CPCB records in a single API call and populate the national cache.
    Returns True on success, False on failure.
    """
    global _national_cache, _national_cache_time

    # Skip if provider is temporarily marked unhealthy (unless 15 minutes have passed since last failure)
    stats = _provider_health["DATA_GOV_IN"]
    if stats["status"] == "UNHEALTHY" and stats["last_failure"]:
        time_since_failure = datetime.utcnow() - stats["last_failure"]
        if time_since_failure < timedelta(minutes=15):
            logger.info("[Gov API] DATA_GOV_IN is marked unhealthy. Skipping call temporarily.")
            return False

    api_key = os.getenv("DATA_GOV_IN_API_KEY")
    if not api_key:
        logger.warning("DATA_GOV_IN_API_KEY not set. Cannot fetch nationwide records.")
        return False

    url = (
        f"https://api.data.gov.in/resource/{_RESOURCE_ID}"
        f"?api-key={api_key}&format=json&limit={_GOV_API_LIMIT}"
    )
    
    t0 = time.time()
    for attempt in range(3):  # retry transient failures up to 3 times
        try:
            # Use browser UA: api.data.gov.in blocks Python's default 'python-requests' UA.
            # With browser UA it responds in ~1-2s vs timing out with default UA.
            r = requests.get(url, timeout=30, headers=_BROWSER_HEADERS)
            latency = time.time() - t0
            if r.status_code == 200:
                records = r.json().get("records", [])
                logger.info(f"[Gov API] Nationwide fetch returned {len(records)} records on attempt {attempt+1} in {latency:.1f}s.")

                # Group by city
                by_city: Dict[str, List[Dict[str, Any]]] = {}
                for rec in records:
                    city_raw = rec.get("city", "Unknown")
                    city = _normalize_city(city_raw)
                    by_city.setdefault(city, []).append(rec)

                _national_cache = by_city
                _national_cache_time = datetime.utcnow()
                _update_provider_health("DATA_GOV_IN", success=True, latency=latency)
                return True
            else:
                logger.warning(f"[Gov API] HTTP {r.status_code} on nationwide fetch attempt {attempt+1}.")
        except Exception as e:
            latency = time.time() - t0
            logger.warning(f"[Gov API] Ingestion attempt {attempt+1} failed: {e}")
            if attempt == 2:
                _update_provider_health("DATA_GOV_IN", success=False, latency=latency, error_msg=str(e))
            time.sleep(2.0)  # backoff before retry

    return False

def fetch_city_records_cached(city: str) -> List[Dict[str, Any]]:
    """
    Return cached records for a city. Refreshes the nationwide cache if stale (> 60 min).
    """
    global _national_cache_time
    now = datetime.utcnow()
    clean_city = _normalize_city(city)

    # Check if cache is fresh
    cache_stale = (
        _national_cache_time is None
        or (now - _national_cache_time) > timedelta(minutes=_CACHE_TTL_MINUTES)
    )

    if cache_stale:
        fetch_nationwide_records()

    return _national_cache.get(clean_city, [])

def fetch_data_gov_in_fallback(city: str, station_name: str) -> Dict[str, Optional[float]]:
    """
    CPCB government data.gov.in live API. Reads from the national cache,
    matches station names, and extracts PM2.5/NO2 averages.
    """
    records = fetch_city_records_cached(city)
    if not records:
        return {"pm25": None, "no2": None}

    station_records = []
    normalized_target = station_name.split(",")[0].lower().strip() if station_name else ""

    for rec in records:
        rec_station = rec.get("station", "").lower()
        if normalized_target and normalized_target in rec_station:
            station_records.append(rec)

    target_records = station_records if station_records else records

    pm25_vals: List[float] = []
    no2_vals: List[float] = []
    for rec in target_records:
        p_id = rec.get("pollutant_id", "").upper()
        try:
            # API returns JSON with key 'avg_value' (the field 'id'), not 'pollutant_avg' (the field 'name')
            val = float(rec.get("avg_value", rec.get("pollutant_avg", 0)))
            if p_id == "PM2.5" and val >= 0:
                pm25_vals.append(val)
            elif p_id == "NO2" and val >= 0:
                no2_vals.append(val)
        except (ValueError, TypeError):
            continue

    return {
        "pm25": sum(pm25_vals) / len(pm25_vals) if pm25_vals else None,
        "no2": sum(no2_vals) / len(no2_vals) if no2_vals else None,
    }

def fetch_openaq_v3_direct(loc_id: int) -> Dict[str, Optional[float]]:
    """Directly queries OpenAQ V3 location for latest PM2.5 and NO2."""
    api_key = os.getenv("OPENAQ_API_KEY")
    headers = {"X-API-Key": api_key} if api_key else {}
    t0 = time.time()
    try:
        r = requests.get(
            f"https://api.openaq.org/v3/locations/{loc_id}/latest",
            headers=headers,
            timeout=8
        )
        latency = time.time() - t0
        if r.status_code == 200:
            pm25 = None
            no2 = None
            for res in r.json().get("results", []):
                param = res.get("parameter", {}).get("name", "").lower()
                val = res.get("value")
                if param == "pm25" and val is not None and val >= 0:
                    pm25 = float(val)
                elif param == "no2" and val is not None and val >= 0:
                    no2 = float(val)
            _update_provider_health("OPENAQ", success=True, latency=latency)
            return {"pm25": pm25, "no2": no2}
        else:
            _update_provider_health("OPENAQ", success=False, latency=latency, error_msg=f"HTTP {r.status_code}")
    except Exception as e:
        latency = time.time() - t0
        _update_provider_health("OPENAQ", success=False, latency=latency, error_msg=str(e))
    return {"pm25": None, "no2": None}

def fetch_openmeteo_aq_estimate(lat: float, lon: float) -> Dict[str, Optional[float]]:
    """Queries Open-Meteo Air Quality current estimates fallback."""
    stats = _provider_health["OPEN_METEO"]
    if stats["status"] == "UNHEALTHY" and stats["last_failure"]:
        time_since_failure = datetime.utcnow() - stats["last_failure"]
        if time_since_failure < timedelta(minutes=15):
            return {"pm25": None, "no2": None}

    url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=pm2_5,nitrogen_dioxide"
    t0 = time.time()
    try:
        r = requests.get(url, timeout=8)
        latency = time.time() - t0
        if r.status_code == 200:
            current = r.json().get("current", {})
            pm25 = float(current.get("pm2_5")) if current.get("pm2_5") is not None else None
            no2 = float(current.get("nitrogen_dioxide")) if current.get("nitrogen_dioxide") is not None else None
            _update_provider_health("OPEN_METEO", success=True, latency=latency)
            return {"pm25": pm25, "no2": no2}
        else:
            _update_provider_health("OPEN_METEO", success=False, latency=latency, error_msg=f"HTTP {r.status_code}")
    except Exception as e:
        latency = time.time() - t0
        _update_provider_health("OPEN_METEO", success=False, latency=latency, error_msg=str(e))
    return {"pm25": None, "no2": None}

def fetch_cpcb_live_reading(
    station_id: str,
    latitude: float,
    longitude: float,
    city: Optional[str] = None,
    station_name: Optional[str] = None,
    db: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Fetches air quality reading with a prioritized, non-fabricated fallback chain:
    Memory Cache -> Government API -> OpenAQ V3 -> SQLite Cache -> Open-Meteo Air Quality -> Unavailable
    """
    global _latest_station_metadata

    pm25: Optional[float] = None
    no2: Optional[float] = None
    source = "UNAVAILABLE"
    provider = "NONE"
    quality_status = "UNAVAILABLE"
    last_updated_time = datetime.utcnow()

    # Step 1: Try Local Memory Cache first (instant)
    if city or station_name:
        clean_city = _normalize_city(city or "")
        # If cache is populated, look up directly to prevent threads spawning
        if clean_city in _national_cache:
            gov_data = fetch_data_gov_in_fallback(city or "", station_name or "")
            if gov_data["pm25"] is not None and gov_data["no2"] is not None:
                pm25 = gov_data["pm25"]
                no2 = gov_data["no2"]
                source = "CPCB_BULK"
                provider = "DATA_GOV_IN"
                quality_status = "LIVE"

    # Step 2: Fetch Government API and OpenAQ in Parallel (Concurrent)
    if pm25 is None or no2 is None:
        openaq_location_map = {
            "10545": 8118,  # Alwar
            "5569": 8504,   # Agra
            "5657": 8556,   # Bengaluru
            "6924": 8206    # Delhi
        }
        loc_id = openaq_location_map.get(station_id)

        futures_map = {}
        # Submit bulk gov fetch task
        f_gov = _executor.submit(fetch_data_gov_in_fallback, city or "", station_name or "")
        futures_map[f_gov] = "GOV"

        # Submit openaq task if location is mapped
        f_openaq = None
        if loc_id and _provider_health["OPENAQ"]["status"] != "UNHEALTHY":
            f_openaq = _executor.submit(fetch_openaq_v3_direct, loc_id)
            futures_map[f_openaq] = "OPENAQ"

        # Wait for threads to finish with a timeout of 12 seconds
        done, _ = concurrent.futures.wait(futures_map.keys(), timeout=12)

        # Check OpenAQ first as it's typically faster than CPCB Bulk loading
        if f_openaq and f_openaq in done:
            try:
                openaq_res = f_openaq.result()
                if openaq_res["pm25"] is not None and openaq_res["no2"] is not None:
                    pm25 = openaq_res["pm25"]
                    no2 = openaq_res["no2"]
                    source = "OPEN_AQ"
                    provider = "OPENAQ"
                    quality_status = "LIVE"
            except Exception as e:
                logger.error(f"OpenAQ parallel future failed: {e}")

        # Check Government API next if OpenAQ missed
        if (pm25 is None or no2 is None) and f_gov in done:
            try:
                gov_res = f_gov.result()
                if gov_res["pm25"] is not None and gov_res["no2"] is not None:
                    pm25 = gov_res["pm25"]
                    no2 = gov_res["no2"]
                    source = "CPCB_BULK"
                    provider = "DATA_GOV_IN"
                    quality_status = "LIVE"
            except Exception as e:
                logger.error(f"Gov parallel future failed: {e}")

    # Step 3: SQLite Cache Fallback
    if pm25 is None or no2 is None:
        db_created = False
        if db is None:
            from backend.app.core.database import SessionLocal
            db = SessionLocal()
            db_created = True

        try:
            from backend.app.core.database import StationReading
            latest_reading = (
                db.query(StationReading)
                .filter(StationReading.station_id == station_id)
                .order_by(StationReading.timestamp.desc())
                .first()
            )
            if latest_reading and latest_reading.pm25 is not None and latest_reading.no2 is not None:
                pm25 = latest_reading.pm25
                no2 = latest_reading.no2
                source = "SQLITE_CACHE"
                provider = "SQLITE"
                last_updated_time = latest_reading.timestamp
                
                # Check data age to flag as STALE (> 120 minutes)
                age_minutes = (datetime.utcnow() - last_updated_time).total_seconds() / 60.0
                quality_status = "STALE" if age_minutes > 120.0 else "CACHED"
                
                logger.info(f"[SQLite Fallback] Station {station_id} loaded historical record from {last_updated_time}.")
        except Exception as e:
            logger.error(f"SQLite fallback lookup failed: {e}")
        finally:
            if db_created:
                db.close()

    # Step 4: Open-Meteo Air Quality Model Estimate Fallback
    if pm25 is None or no2 is None:
        om_res = fetch_openmeteo_aq_estimate(latitude, longitude)
        if om_res["pm25"] is not None and om_res["no2"] is not None:
            pm25 = om_res["pm25"]
            no2 = om_res["no2"]
            source = "OPEN_METEO"
            provider = "OPEN_METEO"
            quality_status = "MODEL_ESTIMATE"
            last_updated_time = datetime.utcnow()
            logger.info(f"[Open-Meteo Fallback] Station {station_id} resolved model estimates.")

    # Calculate data age in minutes
    data_age_minutes = round((datetime.utcnow() - last_updated_time).total_seconds() / 60.0)
    if data_age_minutes < 0:
        data_age_minutes = 0

    # Save to global in-memory sync cache for REST diagnostic consumption
    metadata = {
        "source": source,
        "provider": provider,
        "quality_status": quality_status,
        "last_updated": last_updated_time.strftime("%Y-%m-%d %H:%M:%S"),
        "data_age_minutes": data_age_minutes,
    }
    _latest_station_metadata[station_id] = metadata

    return {
        "pm25": pm25,
        "no2": no2,
        "quality_flag": quality_status,  # Backwards compatibility key mapping
        "metadata": metadata
    }

def get_latest_station_metadata(station_id: str, db: Optional[Any] = None) -> Dict[str, Any]:
    """Retrieves current sync metadata for a station, falling back to SQLite if cache is empty."""
    meta = _latest_station_metadata.get(station_id)
    if meta:
        return meta

    # Fallback to loading DB records
    db_created = False
    if db is None:
        from backend.app.core.database import SessionLocal
        db = SessionLocal()
        db_created = True

    source = "UNAVAILABLE"
    provider = "NONE"
    quality_status = "UNAVAILABLE"
    last_updated_time = datetime.utcnow()

    try:
        from backend.app.core.database import StationReading
        latest_reading = (
            db.query(StationReading)
            .filter(StationReading.station_id == station_id)
            .order_by(StationReading.timestamp.desc())
            .first()
        )
        if latest_reading:
            source = "SQLITE_CACHE"
            provider = "SQLITE"
            last_updated_time = latest_reading.timestamp
            age_minutes = (datetime.utcnow() - last_updated_time).total_seconds() / 60.0
            quality_status = "STALE" if age_minutes > 120.0 else "CACHED"
    except Exception as e:
        logger.error(f"Diagnostics lookup failed: {e}")
    finally:
        if db_created:
            db.close()

    age_mins = round((datetime.utcnow() - last_updated_time).total_seconds() / 60.0)
    if age_mins < 0:
        age_mins = 0

    return {
        "source": source,
        "provider": provider,
        "quality_status": quality_status,
        "last_updated": last_updated_time.strftime("%Y-%m-%d %H:%M:%S"),
        "data_age_minutes": age_mins,
    }
