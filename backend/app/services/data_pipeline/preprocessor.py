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

FEATURE_CACHE_PATH = os.path.join(BASE_DIR, "data", "station_dataset.parquet")
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

def generate_modeled_pm25_local(row, city_name: str) -> float:
    timestamp = row.name
    month = timestamp.month
    hour = timestamp.hour
    
    if "Delhi" in city_name:
        if month in [11, 12, 1]:  # Winter
            base = 190.0
        elif month in [10, 2]:    # Shoulder winter
            base = 135.0
        elif month in [3, 4, 9]:  # Spring/Autumn
            base = 85.0
        else:                     # Summer/Monsoon
            base = 48.0
    else:  # Bengaluru
        if month in [12, 1, 2]:
            base = 40.0
        else:
            base = 28.0
            
    import random
    wind_ms = (row.get("wind_speed") or 0.0) / 3.6
    pbl = row.get("pbl_height") or 500.0
    stagnation = calculate_stagnation(wind_ms, pbl)
    stagnation_mult = 0.5 + (stagnation * 1.5)
    
    humidity = row.get("humidity") or 50.0
    washout_mult = 1.0
    if humidity > 80.0 and month in [6, 7, 8]:
        washout_mult = 0.55
    elif humidity < 30.0:
        washout_mult = 1.15
        
    diurnal_mult = 1.0
    if (8 <= hour <= 10) or (18 <= hour <= 21):
        diurnal_mult = 1.35
    elif (2 <= hour <= 5):
        diurnal_mult = 0.75
        
    noise = random.uniform(0.88, 1.12)
    pm25 = base * stagnation_mult * washout_mult * diurnal_mult * noise
    return float(round(max(4.0, pm25), 2))

def generate_modeled_no2_local(row, city_name: str) -> float:
    timestamp = row.name
    month = timestamp.month
    hour = timestamp.hour
    
    if "Delhi" in city_name:
        if month in [11, 12, 1]:  # Winter
            base = 65.0
        elif month in [10, 2]:    # Shoulder winter
            base = 45.0
        elif month in [3, 4, 9]:  # Spring/Autumn
            base = 35.0
        else:                     # Summer/Monsoon
            base = 22.0
    else:  # Bengaluru
        if month in [12, 1, 2]:
            base = 25.0
        else:
            base = 15.0
            
    import random
    wind_ms = (row.get("wind_speed") or 0.0) / 3.6
    pbl = row.get("pbl_height") or 500.0
    stagnation = calculate_stagnation(wind_ms, pbl)
    stagnation_mult = 0.6 + (stagnation * 1.2)
    
    diurnal_mult = 1.0
    if (8 <= hour <= 10) or (18 <= hour <= 21):
        diurnal_mult = 1.4
    elif (2 <= hour <= 5):
        diurnal_mult = 0.6
        
    noise = random.uniform(0.9, 1.1)
    no2 = base * stagnation_mult * diurnal_mult * noise
    return float(round(max(2.0, no2), 2))

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
        if station_id == "site_107":
            csv_path = os.path.join(BASE_DIR, "data", "data", "delhi_pusa_imd_2024-25.csv")
            if not os.path.exists(csv_path):
                csv_path = os.path.join(BASE_DIR, "backend", "data", "data", "delhi_pusa_imd_2024-25.csv")
            if not os.path.exists(csv_path):
                csv_path = "backend/data/data/delhi_pusa_imd_2024-25.csv"
            if not os.path.exists(csv_path):
                logger.error("Pusa Delhi IMD CSV not found at any location!")
                return pd.DataFrame()
            try:
                df_pusa = pd.read_csv(csv_path)
                df_pusa = df_pusa.rename(columns={
                    "Timestamp": "timestamp",
                    "PM2.5 (µg/m³)": "pm25",
                    "PM10 (µg/m³)": "pm10",
                    "NO2 (µg/m³)": "no2",
                    "SO2 (µg/m³)": "so2",
                    "Ozone (µg/m³)": "o3",
                    "CO (mg/m³)": "co"
                })
                df_pusa["timestamp"] = pd.to_datetime(df_pusa["timestamp"], utc=True).dt.tz_localize(None)
                keep_cols = ["timestamp", "pm25", "pm10", "no2", "so2", "o3", "co"]
                df_pusa = df_pusa[[c for c in keep_cols if c in df_pusa.columns]]
                # Aggregate to hourly (since it's 15-min data)
                df_pusa = df_pusa.set_index("timestamp").resample("1h").mean()
                
                # Standardize pollutant names and ensure all columns exist
                pollutants_map = {"pm25": "pm25", "pm10": "pm10", "no2": "no2", "so2": "so2", "co": "co", "o3": "o3"}
                for col in pollutants_map.values():
                    if col not in df_pusa.columns:
                        df_pusa[col] = np.nan
                return df_pusa
            except Exception as e:
                logger.error(f"Error parsing Delhi Pusa CSV: {e}")
                return pd.DataFrame()

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
                    dt_val = item.get("period", {}).get("datetimeTo")
                    
                    if isinstance(dt_val, dict):
                        dt_str = dt_val.get("utc") or dt_val.get("local")
                    else:
                        dt_str = dt_val
                    
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
                
        # Compute wind u/v components
        if "wind_speed" in merged.columns and "wind_deg" in merged.columns:
            wind_speed = merged["wind_speed"].fillna(0.0)
            wind_deg = merged["wind_deg"].fillna(0.0)
            wind_deg_rad = np.radians(wind_deg)
            merged["wind_u"] = wind_speed * np.cos(wind_deg_rad)
            merged["wind_v"] = wind_speed * np.sin(wind_deg_rad)
        else:
            merged["wind_u"] = np.nan
            merged["wind_v"] = np.nan
                    
        # Fill missing stagnation and upwind fire features
        lat = station_meta["latitude"]
        lng = station_meta["longitude"]
        
        # Pre-filter fires for this station for fast slicing
        station_fires = self.firms_coll.get_station_fires(lat, lng)
        
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
            fire_metrics = self.firms_coll.get_upwind_fire_metrics(lat, lng, idx, wind_speed, wind_deg, station_fires)
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
            inst_val = s.get("installation_date")
            inst_str = None
            if isinstance(inst_val, dict):
                inst_str = inst_val.get("utc")
            else:
                inst_str = inst_val
                
            inst_dt = None
            if inst_str:
                try:
                    inst_dt = datetime.fromisoformat(inst_str.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    pass

            stations_data.append({
                "id": s["id"],
                "name": s["name"],
                "city": s["city"],
                "state": s["state"],
                "latitude": s["latitude"],
                "longitude": s["longitude"],
                "elevation": s.get("elevation", 0.0) or 0.0,
                "station_type": s.get("station_type", "Government") or "Government",
                "installation_date": inst_dt,
                "available_pollutants": s.get("available_pollutants") or s.get("pollutants", ""),
                "quality_score": s.get("quality_score", 0.0)
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
                    "wind_u": float(row["wind_u"]) if not pd.isna(row["wind_u"]) else None,
                    "wind_v": float(row["wind_v"]) if not pd.isna(row["wind_v"]) else None,
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
                    "station_id": st.id,
                    "latitude": st.latitude,
                    "longitude": st.longitude,
                    "state": st.state,
                    "city": st.city,
                    "elevation": st.elevation,
                    "pm25": r.pm25,
                    "no2": r.no2,
                    "temp": r.temp,
                    "humidity": r.humidity,
                    "wind_speed": r.wind_speed if r.wind_speed is not None else 5.0,
                    "wind_deg": r.wind_deg if r.wind_deg is not None else 0.0,
                    "wind_u": r.wind_u,
                    "wind_v": r.wind_v,
                    "stagnation": r.stagnation if r.stagnation is not None else 0.0,
                    "upwind_fire_intensity": r.upwind_fire_intensity if r.upwind_fire_intensity is not None else 0.0,
                    "upwind_fire_count": r.upwind_fire_count if r.upwind_fire_count is not None else 0
                })
            df = pd.DataFrame(data)
            df.set_index("timestamp", inplace=True)
            
            # Apply feature engineering
            # Note: engineer_features drops NaNs internally
            df_feats = engineer_features(df, drop_na=True)
            if not df_feats.empty:
                # Remove station_id, latitude, longitude, state, city, elevation from dropping columns
                # they will be kept in the dataframe as they are columns, not index
                cached_features[st.id] = df_feats
                
        try:
            os.makedirs(os.path.dirname(self.feature_cache_path), exist_ok=True)
            all_dfs = []
            for sid, df_st in cached_features.items():
                df_st = df_st.copy()
                # station_id is already in the dataframe from our packing
                all_dfs.append(df_st)
            
            if all_dfs:
                combined_df = pd.concat(all_dfs)
                # Reset index to make timestamp a regular column in the parquet file
                combined_df = combined_df.reset_index()
                combined_df.to_parquet(self.feature_cache_path)
                logger.info(f"Successfully cached feature engineered dataframes for {len(cached_features)} stations to {self.feature_cache_path}")
            else:
                logger.warning("No feature engineered dataframes to cache.")
        except Exception as e:
            logger.error(f"Failed to write feature cache file: {e}")
