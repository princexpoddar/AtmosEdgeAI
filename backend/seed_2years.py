import os
import gzip
import math
import random
import requests
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Import backend resources
from backend.app.core.database import SessionLocal, City, Ward, Reading, Forecast, Attribution, EnforcementTarget, Advisory, init_db
from backend.app.services.ingestion import calculate_stagnation, fetch_openmeteo_history
from backend.app.services.forecaster import generate_forecasts_for_all
from backend.app.services.attribution import run_attribution_for_all
from backend.app.services.enforcement import prioritize_enforcements
from backend.app.services.advisory import generate_ward_advisories

LOCAL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "openaq"))

# Station bindings for Bengaluru wards to ensure spatial variety and full 2-year data coverage
BENGALURU_STATIONS = {
    "Whitefield": 8180,
    "Koramangala": 8161,
    "Indiranagar": 8180,
    "Electronic City": 8161,
    "Peenya Industrial Area": 8180
}

def load_local_openaq_data(station_id: int) -> pd.DataFrame:
    """
    Loads downloaded OpenAQ CSV files from the local data directory for a given station ID
    """
    station_dir = os.path.join(LOCAL_DIR, f"locationid={station_id}")
    if not os.path.exists(station_dir):
        print(f"   [OpenAQ] Local station directory for ID {station_id} not found.")
        return pd.DataFrame()
        
    dfs = []
    print(f"   [OpenAQ] Loading local files for station ID {station_id}...")
    for root, dirs, files in os.walk(station_dir):
        for f in files:
            if f.endswith(".csv.gz"):
                try:
                    with gzip.open(os.path.join(root, f), "rt", encoding="utf-8") as file:
                        df = pd.read_csv(file)
                        dfs.append(df)
                except Exception as e:
                    pass
                    
    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        # Handle mixed timezones by parsing to UTC first
        combined["datetime"] = pd.to_datetime(combined["datetime"], errors="coerce", utc=True)
        # Extract pm25 parameter
        pm25_df = combined[combined["parameter"] == "pm25"].copy()
        if pm25_df.empty:
            pm25_df = combined.copy()
        
        # Format index: convert to naive UTC
        pm25_df["timestamp_utc"] = pm25_df["datetime"].dt.tz_convert(None).dt.round("h")
        pm25_df = pm25_df.drop_duplicates(subset=["timestamp_utc"])
        pm25_df.set_index("timestamp_utc", inplace=True)
        print(f"   [OpenAQ] Loaded {len(pm25_df)} unique hourly records.")
        return pm25_df
        
    print(f"   [OpenAQ] No files found for station ID {station_id}.")
    return pd.DataFrame()

def load_delhi_pusa_data() -> pd.DataFrame:
    """
    Loads downloaded Pusa IMD Delhi CSV file, aggregates to hourly, and formats index
    """
    pusa_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "delhi_pusa_imd_2024-25.csv"))
    if not os.path.exists(pusa_file):
        print(f"   [Pusa IMD] Delhi file {pusa_file} not found.")
        return pd.DataFrame()
        
    print(f"   [Pusa IMD] Loading Delhi Pusa IMD dataset from {pusa_file}...")
    try:
        df = pd.read_csv(pusa_file)
        # Standardize columns to remove special characters
        df.columns = [c.encode('ascii', 'ignore').decode('utf-8').strip() for c in df.columns]
        
        # Parse timestamp to UTC DatetimeIndex
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce", utc=True)
        df.dropna(subset=["Timestamp"], inplace=True)
        
        # Convert timezone to naive UTC to match meteorology
        df["timestamp_utc"] = df["Timestamp"].dt.tz_convert(None).dt.round("h")
        
        # Extract PM2.5 column (which is 'PM2.5 (g/m)')
        pm25_col = "PM2.5 (g/m)"
        if pm25_col not in df.columns:
            # Try to find a match
            for col in df.columns:
                if "PM2.5" in col or "PM25" in col:
                    pm25_col = col
                    break
                    
        # Group by hourly timestamp and take mean
        df_hourly = df.groupby("timestamp_utc")[[pm25_col]].mean()
        df_hourly.rename(columns={pm25_col: "pm25"}, inplace=True)
        print(f"   [Pusa IMD] Loaded {len(df_hourly)} hourly records.")
        return df_hourly
    except Exception as e:
        print(f"   [Pusa IMD] Error loading Delhi Pusa IMD data: {e}")
        return pd.DataFrame()


def generate_modeled_pm25(row, city_name: str) -> float:
    """
    Generates high-fidelity weather-diurnal-seasonal PM2.5 proxy data for cases where ground data is missing (e.g. Delhi).
    """
    timestamp = row.name
    month = timestamp.month
    hour = timestamp.hour
    
    # 1. Base levels by city and season
    if "Delhi" in city_name:
        # High base in winter (Nov-Jan), moderate in spring/autumn, lower in monsoon (Jun-Aug)
        if month in [11, 12, 1]:  # Winter
            base = 190.0
        elif month in [10, 2]:    # Shoulder winter
            base = 135.0
        elif month in [3, 4, 9]:  # Spring/Autumn
            base = 85.0
        else:                     # Summer/Monsoon (May, Jun, Jul, Aug)
            base = 48.0
    else:  # Bengaluru
        if month in [12, 1, 2]:
            base = 40.0
        else:
            base = 28.0
            
    # 2. Meteorological dispersion (wind speed & PBL height / stagnation)
    wind_ms = (row["wind_speed"] or 0.0) / 3.6
    pbl = row["pbl_height"] or 500.0
    stagnation = calculate_stagnation(wind_ms, pbl)
    
    # Stagnation scale: 0.5x (clean/windy) to 2.0x (stagnant/calm)
    stagnation_mult = 0.5 + (stagnation * 1.5)
    
    # Washout effect from monsoon rain (represented by high humidity during summer/monsoon months)
    humidity = row["humidity"] or 50.0
    washout_mult = 1.0
    if humidity > 80.0 and month in [6, 7, 8]:
        washout_mult = 0.55
    elif humidity < 30.0:  # dry dust resuspended
        washout_mult = 1.15
        
    # Diurnal peak traffic hour spikes
    diurnal_mult = 1.0
    if (8 <= hour <= 10) or (18 <= hour <= 21):
        diurnal_mult = 1.35
    elif (2 <= hour <= 5):
        diurnal_mult = 0.75
        
    # Add random noise (+/- 12%)
    noise = random.uniform(0.88, 1.12)
    
    pm25 = base * stagnation_mult * washout_mult * diurnal_mult * noise
    return float(round(max(4.0, pm25), 2))

def seed_2years_history():
    db: Session = SessionLocal()
    try:
        print("\n--- Initializing Database Structure ---")
        init_db()
        
        # Define 2-year range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=365 * 2)
        print(f"Target Seeding Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        print("\n--- Clearing Existing Database Records ---")
        # Clear readings and downstream analysis tables to avoid duplicates and mismatches
        deleted_readings = db.query(Reading).delete()
        deleted_forecasts = db.query(Forecast).delete()
        deleted_attributions = db.query(Attribution).delete()
        deleted_enforcements = db.query(EnforcementTarget).delete()
        deleted_advisories = db.query(Advisory).delete()
        db.commit()
        print(f"Cleared table records: Readings: {deleted_readings}, Forecasts: {deleted_forecasts}, Attributions: {deleted_attributions}, Enforcements: {deleted_enforcements}, Advisories: {deleted_advisories}")
        
        # Pre-load Delhi data to avoid reloading for every Delhi ward
        delhi_pusa_df = load_delhi_pusa_data()

        wards = db.query(Ward).all()
        if not wards:
            print("ERROR: Wards not found in the database. Please run FastAPI once or initialize cities/wards first.")
            return

        for ward in wards:
            city_name = ward.city.name
            print(f"\n==================================================")
            print(f"Processing Seeding for Ward: {ward.name} ({city_name})")
            print(f"==================================================")
            
            # 1. Fetch 2 Years of Weather from Open-Meteo ERA5
            print(f"   [Weather] Fetching 2 years of ERA5 reanalysis from Open-Meteo...")
            met_df = fetch_openmeteo_history(ward.latitude, ward.longitude, start_date, end_date)
            
            if met_df.empty:
                print(f"   [Weather] WARNING: Failed to fetch weather. Skipping ward {ward.name}.")
                continue
                
            met_df["timestamp_utc"] = met_df["timestamp"].dt.tz_localize(None).dt.round("h")
            met_df = met_df.drop_duplicates(subset=["timestamp_utc"])
            met_df.set_index("timestamp_utc", inplace=True)
            print(f"   [Weather] Retained {len(met_df)} hourly weather records.")
            
            # 2. Gather PM2.5 Data (Ground Local OpenAQ vs. Modeled Fallback)
            pm25_df = pd.DataFrame()
            is_modeled = False
            
            if "Bengaluru" in city_name:
                station_id = BENGALURU_STATIONS.get(ward.name, 8180)
                pm_df = load_local_openaq_data(station_id)
                if not pm_df.empty:
                    # Filter columns to only what we need
                    pm25_df = pm_df[["value"]].rename(columns={"value": "pm25"})
            elif "Delhi" in city_name:
                if not delhi_pusa_df.empty:
                    pm25_df = delhi_pusa_df.copy()
            
            # Fallback to model if ground data is missing or sparse (e.g. for Delhi NCR)
            if pm25_df.empty or len(pm25_df) < 500:
                print(f"   [PM2.5] Ground data missing/sparse. Generating weather-modeled PM2.5 proxy...")
                is_modeled = True
                
            # 3. Align and Merge
            readings_to_add = []
            
            # Pre-compute mapped weather variables
            for index, row in met_df.iterrows():
                # Get PM2.5
                if is_modeled:
                    pm25 = generate_modeled_pm25(row, city_name)
                else:
                    # Try to lookup PM2.5 in ground data
                    if index in pm25_df.index:
                        pm25 = float(pm25_df.loc[index, "pm25"])
                        # Handle NaN or negative ground data readings
                        if pd.isna(pm25) or pm25 <= 0:
                            pm25 = generate_modeled_pm25(row, city_name)
                    else:
                        pm25 = generate_modeled_pm25(row, city_name)
                
                # PM10 proxy
                pm10 = pm25 * 1.6
                
                # Wind and Boundary Layer
                wind_ms = (row["wind_speed"] or 0) / 3.6
                pbl = row["pbl_height"] or 500.0
                stagnation = calculate_stagnation(wind_ms, pbl)
                
                # Estimate criteria gases based on PM2.5 proxy coefficients
                no2 = pm10 * 0.4
                so2 = pm10 * 0.1
                o3 = 25.0 + 15.0 * math.sin((index.hour - 6) * math.pi / 12.0)
                co = pm10 * 0.005
                
                r = Reading(
                    ward_id=ward.id,
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
                readings_to_add.append(r)
                
            if readings_to_add:
                print(f"   [Database] Saving {len(readings_to_add)} hourly records to SQLite...")
                db.bulk_save_objects(readings_to_add)
                db.commit()
                print(f"   [Database] Completed save for ward {ward.name}.")
                
        print("\n==================================================")
        print("Re-running Post-Ingestion Analytical Pipelines...")
        print("==================================================")
        
        print("\n[ML Engine] Re-training Random Forest forecasters...")
        generate_forecasts_for_all(db)
        
        print("\n[Source Attribution] Calculating pollution attribution percentages...")
        run_attribution_for_all(db)
        
        print("\n[Enforcement Queue] Scoring and prioritizing violations...")
        prioritize_enforcements(db)
        
        print("\n[Citizen Advisory] Re-generating health guidance alerts...")
        generate_ward_advisories(db)
        
        print("\nDatabase 2-year Seeding & Analytics run finished successfully.")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_2years_history()
