import os
import math
import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from backend.app.services.ml.config import config, BASE_DIR

logger = logging.getLogger(__name__)

FIRMS_DIR_DEFAULT = os.path.abspath(os.path.join(BASE_DIR, "data", "data", "firms"))

# India-wide bounding box bounds for fire filtering
INDIA_BOUNDS = {
    "min_lat": 8.0,
    "max_lat": 38.0,
    "min_lon": 68.0,
    "max_lon": 98.0,
    "max_radius_km": 300.0,
    "lat_deg_diff": 300.0 / 111.0,
    "lon_deg_diff": 300.0 / 100.0
}

class FirmsCollector:
    def __init__(self, data_dir: str = FIRMS_DIR_DEFAULT):
        self.data_dir = data_dir
        self.fires_df = pd.DataFrame()
        self.load_and_clean_data()

    def load_and_clean_data(self) -> None:
        """
        Loads and indexes MODIS & VIIRS fire archive CSV files.
        Filters records to keep only those within India's boundary bounds to speed up search.
        """
        logger.info(f"Initializing NASA FIRMS biomass data extraction from {self.data_dir}...")
        
        files = {
            "MODIS_ARCHIVE": "fire_archive_M-C61_774045.csv",
            "MODIS_NRT": "fire_nrt_M-C61_774045.csv",
            "VIIRS_ARCHIVE": "fire_archive_SV-C2_774046.csv",
            "VIIRS_NRT": "fire_nrt_SV-C2_774046.csv"
        }
        
        all_dfs = []
        for key, filename in files.items():
            path = os.path.join(self.data_dir, filename)
            if not os.path.exists(path):
                logger.warning(f"FIRMS archive file {filename} not found.")
                continue
                
            try:
                # Load only relevant columns for space efficiency
                df = pd.read_csv(path, usecols=["latitude", "longitude", "acq_date", "acq_time", "confidence", "frp"])
                
                # Confidence filter
                if "VIIRS" in key:
                    df = df[df["confidence"] != "l"]
                else:
                    df["confidence_numeric"] = pd.to_numeric(df["confidence"], errors="coerce")
                    df = df[(df["confidence_numeric"].isna()) | (df["confidence_numeric"] >= 50)]
                    df.drop(columns=["confidence_numeric"], inplace=True)
                    
                # Spatial crop: Keep only India fires
                in_india = (
                    (df["latitude"] >= INDIA_BOUNDS["min_lat"]) & (df["latitude"] <= INDIA_BOUNDS["max_lat"]) &
                    (df["longitude"] >= INDIA_BOUNDS["min_lon"]) & (df["longitude"] <= INDIA_BOUNDS["max_lon"])
                )
                df = df[in_india].copy()
                
                # Align timestamps
                df["time_str"] = df["acq_time"].astype(str).str.zfill(4)
                df["datetime_str"] = df["acq_date"] + " " + df["time_str"].str[:2] + ":" + df["time_str"].str[2:]
                df["timestamp_utc"] = pd.to_datetime(df["datetime_str"], errors="coerce").dt.round("h")
                df.dropna(subset=["timestamp_utc"], inplace=True)
                
                all_dfs.append(df[["latitude", "longitude", "timestamp_utc", "frp"]])
            except Exception as e:
                logger.error(f"Error reading FIRMS file {filename}: {e}")
                
        if all_dfs:
            self.fires_df = pd.concat(all_dfs, ignore_index=True)
            self.fires_df.sort_values("timestamp_utc", inplace=True)
            self.fires_df.set_index("timestamp_utc", inplace=True, drop=False)
            logger.info(f"Successfully loaded and indexed {len(self.fires_df):,} fire records.")
        else:
            logger.warning("No biomass fire detections loaded.")

    def get_upwind_fire_metrics(
        self, 
        lat: float, 
        lng: float, 
        timestamp: datetime, 
        wind_speed: float, 
        wind_deg: float
    ) -> Dict[str, Any]:
        """
        Calculates upwind fire metrics (vectorized implementation for fast evaluation).
        """
        metrics = {"upwind_fire_intensity": 0.0, "upwind_fire_count": 0}
        if self.fires_df.empty:
            return metrics
            
        # Limit calculations to last 24 hours
        start_time = timestamp - timedelta(hours=24)
        try:
            active_fires = self.fires_df.loc[start_time:timestamp]
        except KeyError:
            active_fires = self.fires_df[(self.fires_df["timestamp_utc"] >= start_time) & (self.fires_df["timestamp_utc"] <= timestamp)]
            
        if active_fires.empty:
            return metrics
            
        # Coarse filter box to speed up distance checks
        in_bbox = (
            (active_fires["latitude"] >= lat - INDIA_BOUNDS["lat_deg_diff"]) &
            (active_fires["latitude"] <= lat + INDIA_BOUNDS["lat_deg_diff"]) &
            (active_fires["longitude"] >= lng - INDIA_BOUNDS["lon_deg_diff"]) &
            (active_fires["longitude"] <= lng + INDIA_BOUNDS["lon_deg_diff"])
        )
        spatial_fires = active_fires[in_bbox]
        if spatial_fires.empty:
            return metrics
            
        # Vectorized Haversine & Bearing calculations
        lat1, lon1 = math.radians(lat), math.radians(lng)
        lat2 = np.radians(spatial_fires["latitude"].values)
        lon2 = np.radians(spatial_fires["longitude"].values)
        frp = spatial_fires["frp"].values
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = np.sin(dlat / 2.0)**2 + math.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0)**2
        c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
        dists = 6371.0 * c  # distance in km
        
        y = np.sin(dlon) * np.cos(lat2)
        x = math.cos(lat1) * np.sin(lat2) - math.sin(lat1) * np.cos(lat2) * np.cos(dlon)
        bearings = (np.degrees(np.arctan2(y, x)) + 360.0) % 360.0
        
        # Wind alignment check (within 90 degrees wind sector)
        angle_diffs = np.abs(bearings - wind_deg)
        angle_diffs = np.minimum(angle_diffs, 360.0 - angle_diffs)
        
        mask = (dists <= INDIA_BOUNDS["max_radius_km"]) & (angle_diffs < 90.0)
        if not np.any(mask):
            return metrics
            
        valid_dists = dists[mask]
        valid_angles = angle_diffs[mask]
        valid_frp = frp[mask]
        
        cos_aligns = np.cos(np.radians(valid_angles))
        dist_factors = 1.0 / (valid_dists + 10.0)**2
        speed_mult = min(5.0, max(0.5, wind_speed / 3.6))
        
        intensities = valid_frp * dist_factors * (cos_aligns**2) * speed_mult
        
        metrics["upwind_fire_intensity"] = float(round(np.sum(intensities) * 1000.0, 2))
        metrics["upwind_fire_count"] = int(np.sum(mask))
        return metrics

# Singleton firms instance
_firms_instance = None

def get_firms_collector() -> FirmsCollector:
    global _firms_instance
    if _firms_instance is None:
        _firms_instance = FirmsCollector()
    return _firms_instance
