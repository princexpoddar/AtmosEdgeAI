import os
import gzip
import math
import random
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Import backend resources
from backend.app.core.database import SessionLocal, City, Ward, Reading, Forecast, Attribution, EnforcementTarget, Advisory, init_db, Station, StationReading
from backend.app.services.ml.config import config
from backend.app.services.data_pipeline.station_manager import StationManager
from backend.app.services.data_pipeline.openaq_collector import OpenAQCollector
from backend.app.services.data_pipeline.weather_collector import WeatherCollector
from backend.app.services.data_pipeline.preprocessor import DataPreprocessor
from backend.app.services.data_pipeline.reporting import PipelineReporter
from backend.app.services.forecaster import generate_forecasts_for_all
from backend.app.services.attribution import run_attribution_for_all
from backend.app.services.enforcement import prioritize_enforcements
from backend.app.services.advisory import generate_ward_advisories

logger = logging.getLogger(__name__)

def seed_2years_history():
    db: Session = SessionLocal()
    try:
        print("\n--- Initializing Database Structure ---")
        init_db()
        
        print("\n--- Clearing Existing Database Records ---")
        deleted_readings = db.query(Reading).delete()
        deleted_forecasts = db.query(Forecast).delete()
        deleted_attributions = db.query(Attribution).delete()
        deleted_enforcements = db.query(EnforcementTarget).delete()
        deleted_advisories = db.query(Advisory).delete()
        
        # Clear new station tables
        deleted_stations = db.query(Station).delete()
        deleted_station_readings = db.query(StationReading).delete()
        
        db.commit()
        
        print(f"Cleared table records: Readings: {deleted_readings}, Forecasts: {deleted_forecasts}, Attributions: {deleted_attributions}, Enforcements: {deleted_enforcements}, Advisories: {deleted_advisories}")
        print(f"Cleared station records: Stations: {deleted_stations}, StationReadings: {deleted_station_readings}")
        
        # 1. Station Discovery & Quality Filtering
        print("\n--- Station Discovery & Quality Filtering ---")
        station_mgr = StationManager()
        discovered = station_mgr.discover_stations(use_cache=True)
        
        retained = station_mgr.filter_stations(discovered, {
            "minimum_years": config.history_years,
            "required_pollutants": config.discovery.get("required_pollutants", ["pm25", "no2"])
        })
        
        retained_ids = {s["id"] for s in retained}
        discarded = [s for s in discovered if s["id"] not in retained_ids]
        
        # Add rejection reasons
        for ds in discarded:
            ds["reason"] = "Failed Quality Score or history criteria"
            
        print(f"Discovered {len(discovered)} stations. Retained {len(retained)} quality stations.")
        
        # Limit to top 15 stations to speed up download verification
        retained = sorted(retained, key=lambda x: x["quality_score"], reverse=True)[:15]
        print(f"Selecting top {len(retained)} highest quality stations for training...")
        
        # 2. Ingest Historical AQ Data
        print("\n--- Downloading Historical Air Quality Data ---")
        openaq_coll = OpenAQCollector()
        station_ids = [s["id"] for s in retained]
        openaq_coll.run_parallel_collection(station_ids, config.start_year, config.end_year, max_workers=4)
        
        # 3. Ingest Historical Meteorology
        print("\n--- Downloading Historical Weather Data ---")
        weather_coll = WeatherCollector()
        for s in retained:
            weather_coll.collect_station_weather(
                s["id"], 
                s["latitude"], 
                s["longitude"], 
                config.start_year, 
                config.end_year
            )
            
        # 4. Alignment & Quality Checking
        print("\n--- Running Time-Alignment and Imputation Pipeline ---")
        preprocessor = DataPreprocessor()
        total_samples = preprocessor.run_preprocessing(db, retained, config.db_engine)
        
        # Generate lag and rolling features cache
        preprocessor.build_and_cache_features(db)
        
        # 5. Statistical Computations (EDA)
        print("\n--- Executing Statistical Correlation & EDA Metrics ---")
        reporter = PipelineReporter()
        readings_query = db.query(StationReading).all()
        
        data_list = []
        for r in readings_query:
            data_list.append({
                "pm25": r.pm25,
                "no2": r.no2,
                "pm10": r.pm10,
                "so2": r.so2,
                "o3": r.o3,
                "co": r.co,
                "temp": r.temp,
                "humidity": r.humidity,
                "surface_pressure": r.surface_pressure,
                "wind_speed": r.wind_speed,
                "wind_deg": r.wind_deg,
                "precipitation": r.precipitation,
                "pbl_height": r.pbl_height,
                "solar_radiation": r.solar_radiation,
                "cloud_cover": r.cloud_cover,
                "dew_point": r.dew_point,
                "visibility": r.visibility,
                "upwind_fire_intensity": r.upwind_fire_intensity,
                "upwind_fire_count": r.upwind_fire_count,
                "stagnation": r.stagnation
            })
            
        df_combined = pd.DataFrame(data_list)
        reporter.calculate_eda_metrics(df_combined)
        
        # Compile reports
        discarded_reasons = [
            {"station_id": ds["id"], "name": ds["name"], "city": ds["city"], "reason": ds["reason"]} 
            for ds in discarded[:20]
        ]
        reporter.compile_reports(db, total_samples, discarded_reasons)
        
        print("\n==================================================")
        print("Re-running Post-Ingestion Analytical Pipelines...")
        print("==================================================")
        
        print("\n[ML Engine] Re-training the global forecasting model...")
        generate_forecasts_for_all(db, retrain=True)
        
        # Run downstream attribution for Wards
        print("\n[Source Attribution] Calculating pollution attribution percentages...")
        run_attribution_for_all(db)
        
        print("\n[Enforcement Queue] Scoring and prioritizing violations...")
        prioritize_enforcements(db)
        
        print("\n[Citizen Advisory] Re-generating health guidance alerts...")
        generate_ward_advisories(db)
        
        print("\nDatabase Seeding & ML Pipeline run finished successfully.")
        
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_2years_history()
