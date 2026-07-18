import os
import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def fetch_data_gov_in_fallback(city: str, station_name: str) -> Dict[str, Optional[float]]:
    """
    CPCB government data.gov.in live API fallback. Fetches realtime AQI records
    filtered by city, matches matching station names, and extracts PM2.5/NO2 averages.
    """
    api_key = os.getenv("DATA_GOV_IN_API_KEY")
    if not api_key:
        return {"pm25": None, "no2": None}
        
    clean_city = city.split(",")[0].strip() if city else "Delhi"
    resource_id = "3b01bcb8-0b15-492c-b6f1-5fc5d0ab03db"
    url = f"https://api.data.gov.in/resource/{resource_id}?api-key={api_key}&format=json&filters[city]={clean_city}"
    
    pm25 = None
    no2 = None
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            records = r.json().get("records", [])
            station_records = []
            normalized_target = station_name.split(",")[0].lower().strip() if station_name else ""
            
            for rec in records:
                rec_station = rec.get("station", "").lower()
                if normalized_target and normalized_target in rec_station:
                    station_records.append(rec)
                    
            target_records = station_records if station_records else records
            
            pm25_vals = []
            no2_vals = []
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
                    
            if pm25_vals:
                pm25 = sum(pm25_vals) / len(pm25_vals)
            if no2_vals:
                no2 = sum(no2_vals) / len(no2_vals)
    except Exception as e:
        logger.warning(f"data.gov.in fallback fetch failed for {clean_city}: {e}")
        
    return {"pm25": pm25, "no2": no2}

def fetch_cpcb_live_reading(
    station_id: str,
    latitude: float,
    longitude: float,
    city: Optional[str] = None,
    station_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetches live PM2.5 and NO2 observations for a CPCB monitoring station.
    Queries primary CPCB data.gov.in API first, falls back to OpenAQ V3,
    and falls back to cache default values if offline.
    """
    pm25 = None
    no2 = None
    quality_flag = "GOV_LIVE"
    
    # 1. Primary: Attempt data.gov.in CPCB fetch
    if city or station_name:
        gov_data = fetch_data_gov_in_fallback(city, station_name)
        if gov_data["pm25"] is not None:
            pm25 = gov_data["pm25"]
        if gov_data["no2"] is not None:
            no2 = gov_data["no2"]
            
    # 2. Secondary Fallback: Attempt OpenAQ fetch
    if pm25 is None or no2 is None:
        openaq_location_map = {
            "10545": 8118, # Alwar
            "5569": 8504,  # Agra
            "5657": 8556,  # Bengaluru
            "6924": 8206   # Delhi
        }
        loc_id = openaq_location_map.get(station_id)
        if loc_id:
            try:
                url = f"https://api.openaq.org/v3/locations/{loc_id}/latest"
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    results = r.json().get("results", [])
                    for res in results:
                        param = res.get("parameter", {}).get("name", "").lower()
                        val = res.get("value")
                        if param == "pm25" and val is not None and val >= 0 and pm25 is None:
                            pm25 = float(val)
                            quality_flag = "LIVE"
                        elif param == "no2" and val is not None and val >= 0 and no2 is None:
                            no2 = float(val)
                            quality_flag = "LIVE"
            except Exception as e:
                logger.warning(f"Failed fetching openaq fallback for station {station_id}: {e}")
                
    # 3. Tertiary Offline cache fallback
    if pm25 is None:
        pm25 = 45.0
        quality_flag = "CACHED"
    if no2 is None:
        no2 = 18.0
        quality_flag = "CACHED"
        
    return {
        "pm25": pm25,
        "no2": no2,
        "quality_flag": quality_flag
    }
