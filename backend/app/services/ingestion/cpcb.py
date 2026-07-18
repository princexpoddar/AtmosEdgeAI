import os
import requests
import logging
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
_RESOURCE_ID = "3b01bcb8-0b15-492c-b6f1-5fc5d0ab03db"
_GOV_API_LIMIT = 5000   # fetch up to 5000 records in one call


def _normalize_city(city: str) -> str:
    """Normalise city string: strip sub-district suffixes and map Delhi variants."""
    city = city.split(",")[0].strip() if city else "Delhi"
    if "delhi" in city.lower():
        return "Delhi"
    return city


def fetch_nationwide_records() -> bool:
    """
    Fetch ALL India CPCB records in a single API call and populate the national cache.
    This is the ONLY function that contacts api.data.gov.in.
    Returns True on success, False on failure.
    """
    global _national_cache, _national_cache_time

    api_key = os.getenv("DATA_GOV_IN_API_KEY")
    if not api_key:
        logger.warning("DATA_GOV_IN_API_KEY not set. Cannot fetch nationwide records.")
        return False

    url = (
        f"https://api.data.gov.in/resource/{_RESOURCE_ID}"
        f"?api-key={api_key}&format=json&limit={_GOV_API_LIMIT}"
    )
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            logger.warning(f"[Gov API] HTTP {r.status_code} on nationwide fetch.")
            return False

        records = r.json().get("records", [])
        logger.info(f"[Gov API] Nationwide fetch returned {len(records)} records.")

        # Group by city
        by_city: Dict[str, List[Dict[str, Any]]] = {}
        for rec in records:
            city_raw = rec.get("city", "Unknown")
            city = _normalize_city(city_raw)
            by_city.setdefault(city, []).append(rec)

        _national_cache = by_city
        _national_cache_time = datetime.utcnow()
        logger.info(f"[Gov API] Cache populated for {len(by_city)} cities.")
        return True

    except Exception as e:
        logger.warning(f"[Gov API] Nationwide fetch failed: {e}")
        return False


def fetch_city_records_cached(city: str) -> List[Dict[str, Any]]:
    """
    Return cached records for a city. Refreshes the nationwide cache if stale (> 60 min).
    Never makes a city-specific API call — uses the shared nationwide cache.
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
            val = float(rec.get("pollutant_avg", 0))
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


def get_openaq_api_key() -> Optional[str]:
    return os.getenv("OPENAQ_API_KEY")


def fetch_cpcb_live_reading(
    station_id: str,
    latitude: float,
    longitude: float,
    city: Optional[str] = None,
    station_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetches live PM2.5 and NO2 observations for a CPCB monitoring station.
    1. Primary: data.gov.in nationwide cache (refreshed every 60 min via one API call)
    2. Secondary: OpenAQ V3 fallback for select stations with known IDs
    3. Tertiary: Static defaults if all live sources fail
    """
    pm25 = None
    no2 = None
    quality_flag = "GOV_LIVE"

    # 1. Primary: Government data via national cache
    if city or station_name:
        gov_data = fetch_data_gov_in_fallback(city or "", station_name or "")
        if gov_data["pm25"] is not None:
            pm25 = gov_data["pm25"]
        if gov_data["no2"] is not None:
            no2 = gov_data["no2"]

    # 2. Secondary: OpenAQ V3 fallback (only for known station IDs)
    if pm25 is None or no2 is None:
        openaq_location_map = {
            "10545": 8118,  # Alwar
            "5569": 8504,   # Agra
            "5657": 8556,   # Bengaluru
            "6924": 8206    # Delhi
        }
        loc_id = openaq_location_map.get(station_id)
        if loc_id:
            try:
                openaq_key = get_openaq_api_key()
                headers = {"X-API-Key": openaq_key} if openaq_key else {}
                r = requests.get(
                    f"https://api.openaq.org/v3/locations/{loc_id}/latest",
                    headers=headers,
                    timeout=5
                )
                if r.status_code == 200:
                    for res in r.json().get("results", []):
                        param = res.get("parameter", {}).get("name", "").lower()
                        val = res.get("value")
                        if param == "pm25" and val is not None and val >= 0 and pm25 is None:
                            pm25 = float(val)
                            quality_flag = "LIVE"
                        elif param == "no2" and val is not None and val >= 0 and no2 is None:
                            no2 = float(val)
                            quality_flag = "LIVE"
            except Exception as e:
                logger.warning(f"OpenAQ fallback failed for station {station_id}: {e}")

    # 3. Tertiary: Static offline cache default
    if pm25 is None:
        pm25 = 45.0
        quality_flag = "CACHED"
    if no2 is None:
        no2 = 18.0
        if quality_flag != "CACHED":
            quality_flag = "PARTIAL"

    return {"pm25": pm25, "no2": no2, "quality_flag": quality_flag}
