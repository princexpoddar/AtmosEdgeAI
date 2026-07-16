import requests
import pandas as pd
from datetime import datetime
from typing import Optional

def calculate_stagnation(wind_speed_ms: float, pbl_height: float) -> float:
    """
    Computes an atmospheric stagnation index from wind speed (m/s) and boundary layer height (m).
    High values represent calm wind and shallow mixing layers, trapping pollution.
    """
    # Normalize wind factor: high stagnation at low wind (< 3 m/s)
    wind_factor = max(0.0, 1.0 - (wind_speed_ms / 6.0))
    # Normalize PBL factor: high stagnation at low PBL (< 500m)
    pbl_factor = max(0.0, 1.0 - (pbl_height / 1500.0))
    return float(round(wind_factor * pbl_factor, 2))

def fetch_openmeteo_history(latitude: float, longitude: float, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Fetches hourly historical meteorological data from Open-Meteo API.
    """
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={latitude}&longitude={longitude}&"
        f"start_date={start_str}&end_date={end_str}&"
        f"hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,boundary_layer_height"
    )
    
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        if "hourly" not in data:
            print("   [Weather Ingestion] Warning: No hourly data in Open-Meteo response.")
            return pd.DataFrame()
            
        hourly = data["hourly"]
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(hourly["time"]),
            "temp": hourly["temperature_2m"],
            "humidity": hourly["relative_humidity_2m"],
            "wind_speed": hourly["wind_speed_10m"],
            "wind_deg": hourly["wind_direction_10m"],
            "pbl_height": hourly.get("boundary_layer_height", [500.0] * len(hourly["time"]))
        })
        return df
    except Exception as e:
        print(f"   [Weather Ingestion] Error querying Open-Meteo: {e}")
        return pd.DataFrame()
