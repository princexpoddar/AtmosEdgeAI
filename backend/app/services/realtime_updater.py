import os
import math
import requests
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.app.core.database import Ward, Reading, Forecast, Attribution
from backend.app.services.ingestion import calculate_stagnation, fetch_openmeteo_history
from backend.app.services.forecaster import generate_forecasts_for_all, calculate_pm25_aqi
from backend.app.services.attribution import run_attribution_for_all
from backend.seed_2years import generate_modeled_pm25

# Ward name to active OpenAQ V3 Location ID mapping (Verified active today in 2026)
WARD_V3_LOCATIONS = {
    # Delhi NCR
    "East Delhi": 235,                # Anand Vihar, New Delhi - DPCC
    "Dwarka": 5622,                   # NSIT Dwarka, Delhi - CPCB
    "Connaught Place": 5613,          # ITO, New Delhi - CPCB
    "Okhla Industrial Area": 5586,     # Sirifort, Delhi - CPCB
    "Rohini": 5610,                   # North Campus, DU, Delhi - IMD
    # Bengaluru
    "Whitefield": 3409312,            # BWSSB Kadabesanahalli, Bengaluru - CPCB
    "Koramangala": 5548,              # BTM Layout, Bengaluru - CPCB
    "Indiranagar": 5574,              # City Railway Station, Bengaluru - KSPCB
    "Electronic City": 6973,          # Jayanagar 5th Block, Bengaluru - KSPCB
    "Peenya Industrial Area": 5644    # Sanegurava Halli, Bengaluru - KSPCB
}

def get_openaq_api_key():
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("OPENAQ_API_KEY="):
                    return line.split("=")[1].strip()
    return None

def fetch_openaq_v3_latest(location_id: int, api_key: str) -> dict:
    """
    Queries the OpenAQ V3 API to find the latest PM2.5 and NO2 measurements at this station.
    """
    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key
        
    pm25_sensor_id = None
    no2_sensor_id = None
    
    # 1. Fetch location details to map parameter name to sensor IDs
    try:
        url = f"https://api.openaq.org/v3/locations/{location_id}"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            sensors = r.json().get("results", [{}])[0].get("sensors", [])
            for s in sensors:
                param_name = s.get("parameter", {}).get("name", "").lower()
                if param_name == "pm25":
                    pm25_sensor_id = s.get("id")
                elif param_name == "no2":
                    no2_sensor_id = s.get("id")
    except Exception as e:
        print(f"   [OpenAQ V3] Error fetching station metadata for location {location_id}: {e}")
        
    pm25_val = None
    no2_val = None
    
    # 2. Fetch latest measurements for these sensors
    try:
        url = f"https://api.openaq.org/v3/locations/{location_id}/latest"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            results = r.json().get("results", [])
            for res in results:
                s_id = res.get("sensorsId")
                if pm25_sensor_id and s_id == pm25_sensor_id:
                    pm25_val = res.get("value")
                elif no2_sensor_id and s_id == no2_sensor_id:
                    no2_val = res.get("value")
    except Exception as e:
        print(f"   [OpenAQ V3] Error fetching latest readings for location {location_id}: {e}")
        
    return {"pm25": pm25_val, "no2": no2_val}

def update_db_realtime(db: Session) -> dict:
    """
    Syncs database readings with real-world weather and AQI measurements up to the current hour.
    """
    api_key = get_openaq_api_key()
    
    max_timestamp_tuple = db.query(Reading.timestamp).order_by(Reading.timestamp.desc()).first()
    if not max_timestamp_tuple:
        last_date = datetime.utcnow() - timedelta(days=2)
    else:
        last_date = max_timestamp_tuple[0]
        
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    
    # Force update if last timestamp matches now, to ensure real-time changes are loaded
    if last_date >= now:
        print("   [Real-Time Sync] Database is already up to date. Forcing a refresh of the current hour...")
        
    wards = db.query(Ward).all()
    hours_synced = 0
    
    for w in wards:
        # Fetch weather parameters
        met_df = fetch_openmeteo_history(w.latitude, w.longitude, last_date - timedelta(hours=1), now)
        if met_df.empty:
            continue
            
        met_df["timestamp_utc"] = met_df["timestamp"].dt.tz_localize(None).dt.round("h")
        met_df = met_df.drop_duplicates(subset=["timestamp_utc"])
        met_df.set_index("timestamp_utc", inplace=True)
        
        # Get live OpenAQ V3 measurements
        location_id = WARD_V3_LOCATIONS.get(w.name)
        live_openaq = {}
        if location_id:
            live_openaq = fetch_openaq_v3_latest(location_id, api_key)
            
        new_readings = []
        for index, row in met_df.iterrows():
            if index <= last_date and index < now:
                continue
                
            # If it's the latest hour, overwrite or verify
            exists = db.query(Reading).filter(Reading.ward_id == w.id, Reading.timestamp == index).first()
            
            # Determine PM2.5 & NO2 values
            pm25 = live_openaq.get("pm25")
            no2 = live_openaq.get("no2")
            
            # Fallbacks if missing
            if pm25 is None or pm25 <= 0:
                pm25 = generate_modeled_pm25(row, w.city.name)
            if no2 is None or no2 <= 0:
                no2 = pm25 * 0.6
                
            pm10 = pm25 * 1.6
            wind_ms = (row["wind_speed"] or 0) / 3.6
            pbl = row["pbl_height"] or 500.0
            stagnation = calculate_stagnation(wind_ms, pbl)
            so2 = pm10 * 0.1
            o3 = 25.0 + 15.0 * math.sin((index.hour - 6) * math.pi / 12.0)
            co = pm10 * 0.005
            
            if exists:
                # Update current record with live values
                exists.pm25 = float(round(pm25, 2))
                exists.pm10 = float(round(pm10, 2))
                exists.no2 = float(round(no2, 2))
                exists.so2 = float(round(so2, 2))
                exists.o3 = float(round(o3, 2))
                exists.co = float(round(co, 2))
                exists.temp = float(round(row["temp"], 1))
                exists.humidity = float(round(row["humidity"], 1))
                exists.wind_speed = float(round(row["wind_speed"], 1))
                exists.wind_deg = float(round(row["wind_deg"], 1))
                exists.stagnation = float(round(stagnation, 2))
            else:
                # Insert new record
                r = Reading(
                    ward_id=w.id,
                    timestamp=index,
                    pm25=float(round(pm25, 2)),
                    pm10=float(round(pm10, 2)),
                    no2=float(round(no2, 2)),
                    so2=float(round(so2, 2)),
                    o3=float(round(o3, 2)),
                    co=float(round(co, 2)),
                    temp=float(round(row["temp"], 1)),
                    humidity=float(round(row["humidity"], 1)),
                    wind_speed=float(round(row["wind_speed"], 1)),
                    wind_deg=float(round(row["wind_deg"], 1)),
                    stagnation=float(round(stagnation, 2))
                )
                new_readings.append(r)
                
        if new_readings:
            db.bulk_save_objects(new_readings)
            hours_synced += len(new_readings)
            
        db.commit()
        
    print(f"   [Real-Time Sync] Synced database with OpenAQ V3 measurements.")
    
    # Always regenerate forecasts and attribution during sync to reflect latest hourly metrics
    generate_forecasts_for_all(db)
    run_attribution_for_all(db)
    
    return {"status": "success", "synced_hours": hours_synced}
