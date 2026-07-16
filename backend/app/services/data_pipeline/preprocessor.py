import os
import sys
import glob
import json
import hashlib
import logging
import subprocess
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal, Station, StationReading
from backend.app.services.ml.config import config, BASE_DIR, MODELS_DIR
from backend.app.services.ml.features import engineer_features
from backend.app.services.data_pipeline.storage import upsert_stations, upsert_station_readings
from backend.app.services.data_pipeline.firms_collector import get_firms_collector
from backend.app.services.data_pipeline.openaq_collector import RAW_DIR, MANIFEST_PATH
from backend.app.services.data_pipeline.weather_collector import WEATHER_RAW_DIR

logger = logging.getLogger(__name__)

FEATURE_CACHE_PATH = os.path.join(BASE_DIR, "data", "feature_cache.pkl")
VERSION_PATH = os.path.join(MODELS_DIR, "dataset_version.json")

def get_git_commit() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "unknown"

def get_config_hash() -> str:
    config_path = os.path.join(BASE_DIR, "app", "core", "ml_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            pass
    return "unknown"

def calculate_stagnation(wind_speed_ms: float, pbl_height: float) -> float:
    wind_factor = max(0.0, 1.0 - (wind_speed_ms / 6.0))
    pbl_factor = max(0.0, 1.0 - (pbl_height / 1500.0))
    return float(round(wind_factor * pbl_factor, 2))

class DataPreprocessor:
    def __init__(
        self, 
        raw_aq_dir: str = RAW_DIR, 
        raw_weather_dir: str = WEATHER_RAW_DIR,
        feature_cache_path: str = FEATURE_CACHE_PATH,
        version_path: str = VERSION_PATH
    ):
        self.raw_aq_dir = raw_aq_dir
        self.raw_weather_dir = raw_weather_dir
        self.feature_cache_path = feature_cache_path
        self.version_path = version_path
        self.firms_coll = get_firms_collector()

    def parse_raw_openaq(self, station_id: str) -> pd.DataFrame:
        """
        Parses all raw OpenAQ JSON chunk files for a station.
        Standardizes columns and returns a sorted hourly pandas DataFrame.
        """
        station_dir = os.path.join(self.raw_aq_dir, station_id)
        if not os.path.exists(station_dir):
            return pd.DataFrame()
            
        json_files = glob.glob(os.path.join(station_dir, "*.json"))
        if not json_files:
            return pd.DataFrame()
            
        records = []
        for file_path in json_files:
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                for item in data:
                    # OpenAQ V3 structure
                    param_name = item.get("parameter", {}).get("name", "").lower()
                    val = item.get("value")
                    dt_str = item.get("period", {}).get("datetimeTo")
                    
                    if param_name and val is not None and dt_str:
                        records.append({
                            "timestamp": dt_str,
                            "parameter": param_name,
                            "value": float(val)
                        })
            except Exception as e:
                logger.error(f"Error parsing OpenAQ file {file_path}: {e}")
                
        if not records:
            return pd.DataFrame()
            
        df_raw = pd.DataFrame(records)
        df_raw["timestamp"] = pd.to_datetime(df_raw["timestamp"], utc=True).dt.tz_localize(None)
        
        # Pivot parameters to columns
        pivoted = df_raw.pivot_table(index="timestamp", columns="parameter", values="value", aggfunc="mean")
        
        # Standardize pollutant names
        pollutants_map = {"pm25": "pm25", "pm10": "pm10", "no2": "no2", "so2": "so2", "co": "co", "o3": "o3"}
        pivoted.rename(columns=pollutants_map, inplace=True)
        
        # Ensure all columns exist
        for col in pollutants_map.values():
            if col not in pivoted.columns:
                pivoted[col] = np.nan
                
        return pivoted

    def parse_raw_weather(self, station_id: str) -> pd.DataFrame:
        """
        Parses cached weather CSV files for a station.
        """
        station_dir = os.path.join(self.raw_weather_dir, station_id)
        if not os.path.exists(station_dir):
            return pd.DataFrame()
            
        csv_files = glob.glob(os.path.join(station_dir, "*.csv"))
        if not csv_files:
            return pd.DataFrame()
            
        dfs = []
        for path in csv_files:
            try:
                df = pd.read_csv(path)
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                dfs.append(df)
            except Exception as e:
                logger.error(f"Error reading weather file {path}: {e}")
                
        if not dfs:
            return pd.DataFrame()
            
        combined = pd.concat(dfs, ignore_index=True)
        combined.sort_values("timestamp", inplace=True)
        combined.drop_duplicates(subset=["timestamp"], inplace=True)
        combined.set_index("timestamp", inplace=True)
        return combined

    def clean_outliers_iqr(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Uses IQR (Interquartile Range) to clip extreme values.
        Treats anything outside [Q1 - 3*IQR, Q3 + 3*IQR] as NaN.
        """
        df = df.copy()
        pollutants = ["pm25", "no2", "pm10", "so2", "co", "o3"]
        
        for col in pollutants:
            if col in df.columns and not df[col].dropna().empty:
                # Filter negative values first
                df[col] = df[col].mask(df[col] < 0, np.nan)
                
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                
                # Extreme outlier thresholds
                lower_bound = Q1 - 3.0 * IQR
                upper_bound = Q3 + 3.0 * IQR
                
                # Mask values outside bounds
                df[col] = df[col].mask((df[col] < lower_bound) | (df[col] > upper_bound), np.nan)
                
        return df

    def impute_missing_gaps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies target time-series gap imputation rules:
        - Gap < 3h: Linear
        - Gap 3-12h: Time interpolation
        - Gap 12-24h: Forward/Backward fill
        - Gap > 24h: Discarded (left as NaN)
        """
        df = df.copy()
        pollutants = ["pm25", "no2", "pm10", "so2", "co", "o3"]
        
        for col in pollutants:
            if col in df.columns:
                # 1. Linear interpolation for gaps < 3h (limit=2)
                df[col] = df[col].interpolate(method="linear", limit=2)
                # 2. Time-based interpolation for gaps 3-12h (limit=11)
                df[col] = df[col].interpolate(method="time", limit=11)
                # 3. Ffill and Bfill for gaps 12-24h (limit=12)
                df[col] = df[col].ffill(limit=12)
                df[col] = df[col].bfill(limit=12)
                
        return df

    def align_and_merge(self, df_aq: pd.DataFrame, df_weather: pd.DataFrame, station_meta: Dict[str, Any]) -> pd.DataFrame:
        """
        Aligns air quality and meteorology on an hourly timeline.
        Integrates NASA FIRMS upwind fire calculations.
        """
        if df_aq.empty:
            return pd.DataFrame()
            
        # Reindex to a complete hourly timeline
        start_time = min(df_aq.index.min(), df_weather.index.min() if not df_weather.empty else df_aq.index.min())
        end_time = max(df_aq.index.max(), df_weather.index.max() if not df_weather.empty else df_aq.index.max())
        
        hourly_index = pd.date_range(start=start_time, end=end_time, freq="h")
        df_aq_aligned = df_aq.reindex(hourly_index)
        
        # Clean outliers & impute gaps
        df_aq_cleaned = self.clean_outliers_iqr(df_aq_aligned)
        df_aq_imputed = self.impute_missing_gaps(df_aq_cleaned)
        
        # Merge weather
        if not df_weather.empty:
            df_weather_aligned = df_weather.reindex(hourly_index)
            # Impute missing weather using linear interpolation
            df_weather_imputed = df_weather_aligned.interpolate(method="linear", limit=12)
            merged = df_aq_imputed.join(df_weather_imputed, how="left")
        else:
            merged = df_aq_imputed.copy()
            # Ensure met columns exist
            for c in ["temp", "humidity", "surface_pressure", "wind_speed", "wind_deg", "precipitation", "pbl_height", "solar_radiation", "cloud_cover", "dew_point", "visibility"]:
                merged[c] = np.nan
                
        # Fill missing stagnation and upwind fire features
        lat = station_meta["latitude"]
        lng = station_meta["longitude"]
        
        fire_intensities = []
        fire_counts = []
        stagnation_vals = []
        
        for idx, row in merged.iterrows():
            # Wind speed in m/s
            wind_speed = row.get("wind_speed") or 5.0
            wind_speed_ms = wind_speed / 3.6
            pbl = row.get("pbl_height") or 500.0
            
            # Stagnation
            stagnation = calculate_stagnation(wind_speed_ms, pbl)
            stagnation_vals.append(stagnation)
            
            # Fire calculations
            wind_deg = row.get("wind_deg") or 0.0
            fire_metrics = self.firms_coll.get_upwind_fire_metrics(lat, lng, idx, wind_speed, wind_deg)
            fire_intensities.append(fire_metrics["upwind_fire_intensity"])
            fire_counts.append(fire_metrics["upwind_fire_count"])
            
        merged["upwind_fire_intensity"] = fire_intensities
        merged["upwind_fire_count"] = fire_counts
        merged["stagnation"] = stagnation_vals
        
        # Reset index to timestamp column
        merged.index.name = "timestamp"
        merged.reset_index(inplace=True)
        return merged

    def run_preprocessing(self, db: Session, stations_meta: List[Dict[str, Any]], engine_type: str = "sqlite") -> int:
        """
        Runs the complete preprocessor sequence for all selected stations.
        Saves metadata and aligned readings directly to database storage.
        """
        logger.info(f"Running time-alignment and quality preprocessing for {len(stations_meta)} stations...")
        
        # Save stations to DB
        stations_data = []
        for s in stations_meta:
            stations_data.append({
                "id": s["id"],
                "name": s["name"],
                "city": s["city"],
                "state": s["state"],
                "latitude": s["latitude"],
                "longitude": s["longitude"],
                "elevation": s["elevation"],
                "station_type": s["station_type"],
                "installation_date": datetime.fromisoformat(s["installation_date"].replace("Z", "+00:00")).replace(tzinfo=None) if s.get("installation_date") else None,
                "available_pollutants": s["available_pollutants"],
                "quality_score": s["quality_score"]
            })
        upsert_stations(db, stations_data, engine_type)
        
        total_rows_inserted = 0
        
        for s in stations_meta:
            sid = s["id"]
            logger.info(f"Aligning observations for Station {sid}...")
            
            df_aq = self.parse_raw_openaq(sid)
            df_weather = self.parse_raw_weather(sid)
            
            if df_aq.empty:
                logger.warning(f"No AQ records found for Station {sid}. Skipping alignment.")
                continue
                
            aligned = self.align_and_merge(df_aq, df_weather, s)
            if aligned.empty:
                continue
                
            # Convert to DB readings format
            readings_data = []
            for _, row in aligned.iterrows():
                readings_data.append({
                    "station_id": sid,
                    "timestamp": row["timestamp"],
                    "pm25": float(row["pm25"]) if not pd.isna(row["pm25"]) else None,
                    "pm10": float(row["pm10"]) if not pd.isna(row["pm10"]) else None,
                    "no2": float(row["no2"]) if not pd.isna(row["no2"]) else None,
                    "so2": float(row["so2"]) if not pd.isna(row["so2"]) else None,
                    "o3": float(row["o3"]) if not pd.isna(row["o3"]) else None,
                    "co": float(row["co"]) if not pd.isna(row["co"]) else None,
                    "temp": float(row["temp"]) if not pd.isna(row["temp"]) else None,
                    "humidity": float(row["humidity"]) if not pd.isna(row["humidity"]) else None,
                    "surface_pressure": float(row["surface_pressure"]) if not pd.isna(row["surface_pressure"]) else None,
                    "wind_speed": float(row["wind_speed"]) if not pd.isna(row["wind_speed"]) else None,
                    "wind_deg": float(row["wind_deg"]) if not pd.isna(row["wind_deg"]) else None,
                    "precipitation": float(row["precipitation"]) if not pd.isna(row["precipitation"]) else None,
                    "pbl_height": float(row["pbl_height"]) if not pd.isna(row["pbl_height"]) else None,
                    "solar_radiation": float(row["solar_radiation"]) if not pd.isna(row["solar_radiation"]) else None,
                    "cloud_cover": float(row["cloud_cover"]) if not pd.isna(row["cloud_cover"]) else None,
                    "dew_point": float(row["dew_point"]) if not pd.isna(row["dew_point"]) else None,
                    "visibility": float(row["visibility"]) if not pd.isna(row["visibility"]) else None,
                    "upwind_fire_intensity": float(row["upwind_fire_intensity"]),
                    "upwind_fire_count": int(row["upwind_fire_count"]),
                    "stagnation": float(row["stagnation"])
                })
                
            upsert_station_readings(db, readings_data, engine_type)
            total_rows_inserted += len(readings_data)
            
        logger.info(f"Preprocessing completed. Ingested {total_rows_inserted} rows into database.")
        
        # Save Dataset Version manifest
        self.save_dataset_version(len(stations_meta), total_rows_inserted)
        
        return total_rows_inserted

    def save_dataset_version(self, station_count: int, row_count: int) -> None:
        """
        Creates and stores the dataset_version.json file.
        """
        version_data = {
            "dataset_version": "v1.0.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "rows": row_count,
            "stations": station_count,
            "features": [
                "pm25", "no2", "pm10", "so2", "o3", "co", "temp", "humidity", "surface_pressure", 
                "wind_speed", "wind_deg", "precipitation", "pbl_height", "solar_radiation", 
                "cloud_cover", "dew_point", "visibility", "upwind_fire_intensity", "upwind_fire_count"
            ],
            "training_split": {
                "train": 0.70,
                "validation": 0.15,
                "test": 0.15
            },
            "git_commit": get_git_commit(),
            "config_hash": get_config_hash()
        }
        try:
            os.makedirs(os.path.dirname(self.version_path), exist_ok=True)
            with open(self.version_path, "w") as f:
                json.dump(version_data, f, indent=2)
            logger.info(f"Dataset version saved successfully to {self.version_path}")
        except Exception as e:
            logger.error(f"Failed to write dataset version: {e}")

    def build_and_cache_features(self, db: Session) -> None:
        """
        Builds lag and rolling statistics for all station readings.
        Caches final engineered arrays to backend/data/feature_cache.pkl.
        """
        logger.info("Computing lag/rolling features and caching to feature_cache.pkl...")
        stations = db.query(Station).all()
        
        cached_features = {}
        
        for st in stations:
            readings = db.query(StationReading).filter(
                StationReading.station_id == st.id
            ).order_by(StationReading.timestamp.asc()).all()
            
            if len(readings) < 48:
                continue
                
            data = []
            for r in readings:
                data.append({
                    "timestamp": r.timestamp,
                    "pm25": r.pm25,
                    "no2": r.no2,
                    "temp": r.temp,
                    "humidity": r.humidity,
                    "wind_speed": r.wind_speed,
                    "wind_deg": r.wind_deg,
                    "stagnation": r.stagnation,
                    "upwind_fire_intensity": r.upwind_fire_intensity,
                    "upwind_fire_count": r.upwind_fire_count
                })
            df = pd.DataFrame(data)
            df.set_index("timestamp", inplace=True)
            
            # Apply feature engineering
            # Note: engineer_features drops NaNs internally
            df_feats = engineer_features(df, drop_na=True)
            if not df_feats.empty:
                cached_features[st.id] = df_feats
                
        try:
            os.makedirs(os.path.dirname(self.feature_cache_path), exist_ok=True)
            with open(self.feature_cache_path, "wb") as f:
                pickle.dump(cached_features, f)
            logger.info(f"Successfully cached feature engineered dataframes for {len(cached_features)} stations to {self.feature_cache_path}")
        except Exception as e:
            logger.error(f"Failed to write feature cache file: {e}")
