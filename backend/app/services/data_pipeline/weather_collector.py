import os
import json
import logging
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any

from backend.app.services.ml.config import config, BASE_DIR
from backend.app.services.data_pipeline.openaq_collector import RAW_DIR, MANIFEST_PATH

logger = logging.getLogger(__name__)

WEATHER_RAW_DIR = os.path.join(BASE_DIR, "data", "raw", "weather")

class WeatherCollector:
    def __init__(self, raw_dir: str = WEATHER_RAW_DIR, manifest_path: str = MANIFEST_PATH):
        self.raw_dir = raw_dir
        self.manifest_path = manifest_path
        os.makedirs(self.raw_dir, exist_ok=True)

    def fetch_openmeteo_chunk(
        self, 
        latitude: float, 
        longitude: float, 
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Fetches meteorological parameters from Open-Meteo with parameter fallback.
        """
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # Primary comprehensive parameter list
        params_comprehensive = (
            f"latitude={latitude}&longitude={longitude}&"
            f"start_date={start_str}&end_date={end_str}&"
            f"hourly=temperature_2m,relative_humidity_2m,surface_pressure,wind_speed_10m,wind_direction_10m,"
            f"precipitation,boundary_layer_height,shortwave_radiation,cloud_cover,dew_point_2m,visibility"
        )
        
        # Safe fallback parameter list (core parameters only)
        params_fallback = (
            f"latitude={latitude}&longitude={longitude}&"
            f"start_date={start_str}&end_date={end_str}&"
            f"hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,boundary_layer_height"
        )
        
        url_base = "https://archive-api.open-meteo.com/v1/archive?"
        
        # Try comprehensive first, fallback if it returns HTTP 400
        for params in [params_comprehensive, params_fallback]:
            url = f"{url_base}{params}"
            max_retries = 3
            backoff = 2.0
            
            for retry in range(max_retries):
                try:
                    r = requests.get(url, timeout=20)
                    if r.status_code == 200:
                        data = r.json()
                        if "hourly" in data:
                            hourly = data["hourly"]
                            df = pd.DataFrame()
                            df["timestamp"] = pd.to_datetime(hourly["time"])
                            df["temp"] = hourly.get("temperature_2m")
                            df["humidity"] = hourly.get("relative_humidity_2m")
                            df["surface_pressure"] = hourly.get("surface_pressure", [1013.25] * len(df))
                            df["wind_speed"] = hourly.get("wind_speed_10m")
                            df["wind_deg"] = hourly.get("wind_direction_10m")
                            df["precipitation"] = hourly.get("precipitation", [0.0] * len(df))
                            df["pbl_height"] = hourly.get("boundary_layer_height", [500.0] * len(df))
                            df["solar_radiation"] = hourly.get("shortwave_radiation", [0.0] * len(df))
                            df["cloud_cover"] = hourly.get("cloud_cover", [0.0] * len(df))
                            df["dew_point"] = hourly.get("dew_point_2m", [0.0] * len(df))
                            df["visibility"] = hourly.get("visibility", [10000.0] * len(df))
                            return df
                    elif r.status_code == 400:
                        logger.warning(f"Open-Meteo HTTP 400. Trying parameter fallback.")
                        break # break inner retry loop, proceed to fallback params
                    elif r.status_code == 429:
                        logger.warning(f"Open-Meteo Rate Limit. Sleeping {backoff}s...")
                        time.sleep(backoff)
                        backoff *= 2.0
                    else:
                        logger.error(f"Open-Meteo error {r.status_code}: {r.text}")
                except Exception as e:
                    logger.error(f"Failed to fetch weather from Open-Meteo: {e}")
                    time.sleep(backoff)
                    backoff *= 2.0
                    
        return pd.DataFrame()

    def collect_station_weather(
        self, 
        station_id: str, 
        latitude: float, 
        longitude: float, 
        start_year: int, 
        end_year: int
    ) -> None:
        """
        Incremental downloader for weather. Caches station weather in annually partitioned files.
        """
        station_dir = os.path.join(self.raw_dir, station_id)
        os.makedirs(station_dir, exist_ok=True)
        
        # Load Manifest
        from backend.app.services.data_pipeline.openaq_collector import OpenAQCollector
        collector_helper = OpenAQCollector(manifest_path=self.manifest_path)
        manifest = collector_helper.load_manifest()
        
        weather_manifest = manifest["Weather"].get(station_id, {})
        
        for year in range(start_year, end_year + 1):
            year_key = str(year)
            year_file = os.path.join(station_dir, f"{year_key}.csv")
            
            # Check manifest for completeness
            if os.path.exists(year_file) and year_key in weather_manifest.get("completed_years", []):
                continue
                
            logger.info(f"Downloading Open-Meteo Weather for Station {station_id} in {year}")
            
            start_date = datetime(year, 1, 1)
            end_date = datetime(year, 12, 31)
            
            df = self.fetch_openmeteo_chunk(latitude, longitude, start_date, end_date)
            if not df.empty:
                try:
                    df.to_csv(year_file, index=False)
                    # Update manifest
                    if "completed_years" not in weather_manifest:
                        weather_manifest["completed_years"] = []
                    if year_key not in weather_manifest["completed_years"]:
                        weather_manifest["completed_years"].append(year_key)
                except Exception as e:
                    logger.error(f"Failed saving weather file {year_file}: {e}")
                    
            weather_manifest["last_downloaded"] = datetime.utcnow().isoformat()
            manifest["Weather"][station_id] = weather_manifest
            collector_helper.save_manifest(manifest)
            
        logger.info(f"Finished Weather collection for Station {station_id}.")
