import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def fetch_openmeteo_live_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Fetches real-time weather metrics from Open-Meteo.
    Returns normalized schema containing: temperature, humidity, wind_speed, wind_deg.
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&"
        f"current=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m&"
        f"forecast_days=1"
    )
    
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
        
        current = data.get("current", {})
        return {
            "temperature": float(current.get("temperature_2m", 25.0)),
            "humidity": float(current.get("relative_humidity_2m", 60.0)),
            "wind_speed": float(current.get("wind_speed_10m", 10.0)),
            "wind_direction": float(current.get("wind_direction_10m", 180.0)),
            "quality_flag": "LIVE"
        }
    except Exception as e:
        logger.warning(f"Weather fetch failed for ({lat}, {lon}) from Open-Meteo: {e}. Using cache/defaults.")
        return {
            "temperature": 25.0,
            "humidity": 60.0,
            "wind_speed": 10.0,
            "wind_direction": 180.0,
            "quality_flag": "FALLBACK"
        }
