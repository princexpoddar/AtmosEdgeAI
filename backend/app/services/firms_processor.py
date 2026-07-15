import os
import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Bounding box constraints for coarse pre-filtering
DELHI_BOUNDS = {
    "min_lat": 23.0, "max_lat": 34.0,
    "min_lon": 71.0, "max_lon": 83.0,
    "max_radius_km": 600.0,
    "lat_deg_diff": 600.0 / 111.0,
    "lon_deg_diff": 600.0 / 97.0
}

BENGALURU_BOUNDS = {
    "min_lat": 11.5, "max_lat": 14.5,
    "min_lon": 76.0, "max_lon": 79.5,
    "max_radius_km": 150.0,
    "lat_deg_diff": 150.0 / 111.0,
    "lon_deg_diff": 150.0 / 108.0
}

class FirmsProcessor:
    def __init__(self, data_dir=None):
        if not data_dir:
            data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "firms"))
        self.data_dir = data_dir
        self.fires_df = pd.DataFrame()
        self.load_and_clean_data()

    def load_and_clean_data(self):
        """
        Loads and crops MODIS & VIIRS fire data to keep memory usage minimal and speed up queries
        """
        print("[FIRMS Processor] Initializing fire dataset cleaning and indexing...")
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
                print(f"  [FIRMS] Warning: File {filename} not found.")
                continue
                
            try:
                # Load only required columns
                df = pd.read_csv(path, usecols=["latitude", "longitude", "acq_date", "acq_time", "confidence", "frp"])
                
                # Confidence filtering
                if "VIIRS" in key:
                    df = df[df["confidence"] != "l"]
                else:
                    df["confidence_numeric"] = pd.to_numeric(df["confidence"], errors="coerce")
                    df = df[(df["confidence_numeric"].isna()) | (df["confidence_numeric"] >= 50)]
                    df.drop(columns=["confidence_numeric"], inplace=True)
                
                # Spatial crop: Keep only fires in Delhi NCR or Bengaluru search boundaries
                in_delhi = (df["latitude"] >= DELHI_BOUNDS["min_lat"]) & (df["latitude"] <= DELHI_BOUNDS["max_lat"]) & \
                           (df["longitude"] >= DELHI_BOUNDS["min_lon"]) & (df["longitude"] <= DELHI_BOUNDS["max_lon"])
                           
                in_bengaluru = (df["latitude"] >= BENGALURU_BOUNDS["min_lat"]) & (df["latitude"] <= BENGALURU_BOUNDS["max_lat"]) & \
                               (df["longitude"] >= BENGALURU_BOUNDS["min_lon"]) & (df["longitude"] <= BENGALURU_BOUNDS["max_lon"])
                               
                df = df[in_delhi | in_bengaluru].copy()
                
                # Standardize datetime
                df["time_str"] = df["acq_time"].astype(str).str.zfill(4)
                df["datetime_str"] = df["acq_date"] + " " + df["time_str"].str[:2] + ":" + df["time_str"].str[2:]
                df["timestamp_utc"] = pd.to_datetime(df["datetime_str"], errors="coerce").dt.round("h")
                df.dropna(subset=["timestamp_utc"], inplace=True)
                
                all_dfs.append(df[["latitude", "longitude", "timestamp_utc", "frp"]])
            except Exception as e:
                print(f"  [FIRMS] Error processing {filename}: {e}")
                
        if all_dfs:
            self.fires_df = pd.concat(all_dfs, ignore_index=True)
            self.fires_df.sort_values("timestamp_utc", inplace=True)
            self.fires_df.set_index("timestamp_utc", inplace=True, drop=False)
            print(f"[FIRMS Processor] Loaded {len(self.fires_df):,} filtered fire detections.")
        else:
            print("[FIRMS Processor] No fire detections loaded.")

    def get_upwind_fire_metrics(self, ward_lat: float, ward_lng: float, timestamp: datetime, wind_speed: float, wind_deg: float, city_name: str) -> dict:
        """
        Computes upwind fire metrics using NumPy vectorized operations (100x faster than raw loops)
        """
        metrics = {
            "upwind_fire_intensity": 0.0,
            "upwind_fire_count": 0
        }
        
        if self.fires_df.empty:
            return metrics
            
        # Target radius and degree bounds
        if "Delhi" in city_name:
            max_dist = DELHI_BOUNDS["max_radius_km"]
            lat_diff = DELHI_BOUNDS["lat_deg_diff"]
            lon_diff = DELHI_BOUNDS["lon_deg_diff"]
        else:
            max_dist = BENGALURU_BOUNDS["max_radius_km"]
            lat_diff = BENGALURU_BOUNDS["lat_deg_diff"]
            lon_diff = BENGALURU_BOUNDS["lon_deg_diff"]
            
        # 1. Temporal filter: active in the last 24 hours
        start_time = timestamp - timedelta(hours=24)
        try:
            active_fires = self.fires_df.loc[start_time:timestamp]
        except KeyError:
            active_fires = self.fires_df[(self.fires_df["timestamp_utc"] >= start_time) & (self.fires_df["timestamp_utc"] <= timestamp)]
            
        if active_fires.empty:
            return metrics
            
        # 2. Coarse Bounding Box spatial filtering (instantly filters out fires in other cities)
        in_bbox = (active_fires["latitude"] >= ward_lat - lat_diff) & \
                  (active_fires["latitude"] <= ward_lat + lat_diff) & \
                  (active_fires["longitude"] >= ward_lng - lon_diff) & \
                  (active_fires["longitude"] <= ward_lng + lon_diff)
                  
        spatial_fires = active_fires[in_bbox]
        if spatial_fires.empty:
            return metrics
            
        # 3. Vectorized distance and bearing calculations using NumPy
        lat1, lon1 = math.radians(ward_lat), math.radians(ward_lng)
        lat2 = np.radians(spatial_fires["latitude"].values)
        lon2 = np.radians(spatial_fires["longitude"].values)
        frp = spatial_fires["frp"].values
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        # Haversine formula
        a = np.sin(dlat/2.0)**2 + math.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2
        c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
        dists = 6371.0 * c  # in km
        
        # Bearing formula
        y = np.sin(dlon) * np.cos(lat2)
        x = math.cos(lat1) * np.sin(lat2) - math.sin(lat1) * np.cos(lat2) * np.cos(dlon)
        bearings = (np.degrees(np.arctan2(y, x)) + 360.0) % 360.0
        
        # 4. Wind alignment checks
        angle_diffs = np.abs(bearings - wind_deg)
        angle_diffs = np.minimum(angle_diffs, 360.0 - angle_diffs)
        
        # Upwind mask: within distance and within 90 degrees wind sector
        mask = (dists <= max_dist) & (angle_diffs < 90.0)
        
        if not np.any(mask):
            return metrics
            
        # Filter metrics
        valid_dists = dists[mask]
        valid_angles = angle_diffs[mask]
        valid_frp = frp[mask]
        
        # Compute dynamic intensity indices
        cos_aligns = np.cos(np.radians(valid_angles))
        dist_factors = 1.0 / (valid_dists + 10.0)**2  # regularized divisor
        speed_mult = min(5.0, max(0.5, wind_speed / 3.6))  # wind speed scale
        
        intensities = valid_frp * dist_factors * (cos_aligns**2) * speed_mult
        total_intensity = np.sum(intensities)
        fire_count = int(np.sum(mask))
        
        metrics["upwind_fire_intensity"] = float(round(total_intensity * 1000.0, 2))
        metrics["upwind_fire_count"] = fire_count
        return metrics

# Singleton instance
_processor_instance = None

def get_firms_processor() -> FirmsProcessor:
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = FirmsProcessor()
    return _processor_instance
