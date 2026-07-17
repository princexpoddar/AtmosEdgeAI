import os
import json
import math
import logging
import requests
from datetime import datetime
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from backend.app.core.database import Ward, Station, Forecast
from backend.app.services.ml.config import config, BASE_DIR

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join(BASE_DIR, "data", "stations_cache.json")

def get_openaq_headers() -> Dict[str, str]:
    headers = {}
    # Check env or config for OpenAQ API Key
    from backend.app.services.realtime_updater import get_openaq_api_key
    api_key = get_openaq_api_key()
    if api_key:
        headers["X-API-Key"] = api_key
    return headers

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes the great-circle distance between two points in kilometers.
    """
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2.0)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

class StationManager:
    def __init__(self, cache_path: str = CACHE_PATH):
        self.cache_path = cache_path
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)

    def discover_stations(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Discovers OpenAQ stations in India dynamically.
        Uses cached metadata if use_cache=True and the cache file exists.
        """
        if use_cache and os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r") as f:
                    cached_data = json.load(f)
                logger.info(f"Loaded {len(cached_data)} stations from cache.")
                return cached_data
            except Exception as e:
                logger.error(f"Failed to read stations cache: {e}. Re-discovering...")

        logger.info("Discovering air quality stations in India via OpenAQ API...")
        headers = get_openaq_headers()
        
        # OpenAQ V3 location endpoint
        # Countries ID for India in OpenAQ is IN. Let's try iso=IN and countries_id=IN.
        url = "https://api.openaq.org/v3/locations"
        params = {
            "iso": "IN",
            "limit": 500
        }
        
        discovered = []
        try:
            r = requests.get(url, headers=headers, params=params, timeout=20)
            if r.status_code == 200:
                results = r.json().get("results", [])
                for loc in results:
                    coords = loc.get("coordinates", {})
                    lat = coords.get("latitude")
                    lng = coords.get("longitude")
                    if lat is None or lng is None:
                        continue
                        
                    # Extract available pollutants
                    sensors = loc.get("sensors", [])
                    pollutants = [s.get("parameter", {}).get("name", "").lower() for s in sensors]
                    pollutants = [p for p in pollutants if p]
                    
                    first_date = loc.get("datetimeFirst")
                    last_date = loc.get("datetimeLast")
                    
                    station_data = {
                        "id": str(loc.get("id")),
                        "name": loc.get("name", "Unknown Station"),
                        "city": loc.get("locality", "Unknown City"),
                        "state": loc.get("timezone", "IN"),
                        "latitude": float(lat),
                        "longitude": float(lng),
                        "elevation": float(coords.get("elevation", 0.0) or 0.0),
                        "station_type": loc.get("type", "Government"),
                        "installation_date": first_date,
                        "available_pollutants": ",".join(pollutants),
                        "quality_score": 0.0,
                        "datetimeFirst": first_date,
                        "datetimeLast": last_date
                    }
                    discovered.append(station_data)
                    
                # Cache the discovered stations
                with open(self.cache_path, "w") as f:
                    json.dump(discovered, f, indent=2)
                logger.info(f"Successfully discovered and cached {len(discovered)} stations.")
            else:
                logger.error(f"OpenAQ locations API returned status {r.status_code}: {r.text}")
        except Exception as e:
            logger.error(f"Error querying OpenAQ locations API: {e}")
            
        return discovered

    def filter_stations(self, stations: List[Dict[str, Any]], discovery_rules: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Applies filtering rules and calculates Quality Scores.
        Rules: min history length, completeness checks, required pollutants.
        """
        if not discovery_rules:
            # Default fallback rules matching the 10/10 plan
            discovery_rules = {
                "minimum_years": 1,
                "required_pollutants": ["pm25", "no2"]
            }
            
        filtered = []
        min_years = discovery_rules.get("minimum_years", 1)
        req_pollutants = set(discovery_rules.get("required_pollutants", ["pm25", "no2"]))
        
        for st in stations:
            # Check pollutants
            avail_pollutants = set(st["available_pollutants"].split(","))
            if not req_pollutants.issubset(avail_pollutants):
                continue
                
            # History calculation
            try:
                first_val = st.get("datetimeFirst")
                last_val = st.get("datetimeLast")
                
                if isinstance(first_val, dict):
                    first_str = first_val.get("utc")
                else:
                    first_str = first_val
                    
                if isinstance(last_val, dict):
                    last_str = last_val.get("utc")
                else:
                    last_str = last_val
                
                if not first_str or not last_str:
                    raise ValueError("Missing first or last datetime")
                    
                first = datetime.fromisoformat(first_str.replace("Z", "+00:00"))
                last = datetime.fromisoformat(last_str.replace("Z", "+00:00"))
                history_days = (last - first).days
                history_years = history_days / 365.25
            except Exception:
                history_years = 0.0
                
            if history_years < min_years:
                continue
                
            # Compute Q Score: initial estimate (outliers default to 0% initially)
            # weights: 40% History, 30% Completeness (default 100%), 20% Pollutants, 10% Outliers (default 100%)
            history_score = min(100.0, (history_years / 5.0) * 100.0)
            
            # Target pollutants ratio
            target_matches = len(avail_pollutants.intersection(req_pollutants))
            pollutant_score = (target_matches / len(req_pollutants)) * 100.0
            
            q_score = 0.4 * history_score + 0.3 * 100.0 + 0.2 * pollutant_score + 0.1 * 100.0
            st["quality_score"] = float(round(q_score, 2))
            
            filtered.append(st)
            
        logger.info(f"Filtered down to {len(filtered)} stations based on ML quality rules.")
        return filtered

    def get_idw_weights(self, ward_lat: float, ward_lng: float, stations: List[Station], K: int = 3) -> List[Tuple[Station, float]]:
        """
        Locates the K-nearest stations and calculates Inverse Distance Weights (IDW).
        """
        dists = []
        for st in stations:
            d = calculate_haversine_distance(ward_lat, ward_lng, st.latitude, st.longitude)
            dists.append((st, d))
            
        # Sort by distance
        dists.sort(key=lambda x: x[1])
        nearest = dists[:K]
        
        if not nearest:
            return []
            
        # Compute weights: w_i = 1 / (d_i + epsilon)^2
        epsilon = 0.1  # prevents division by zero
        weights = []
        total_w = 0.0
        
        for st, d in nearest:
            w = 1.0 / (d + epsilon)**2
            weights.append((st, w))
            total_w += w
            
        # Normalize weights
        normalized = [(st, w / total_w) for st, w in weights]
        return normalized

    def aggregate_station_predictions(
        self, 
        db: Session, 
        station_predictions: Dict[str, Dict[int, Tuple[float, float]]], 
        now: datetime
    ) -> None:
        """
        Ward Aggregation Layer:
        Aggregates station predictions to Ward forecasts using Inverse Distance Weighting (IDW).
        Saves the results in the Forecast table.
        """
        from backend.app.services.forecaster import calculate_pm25_aqi, _save_forecast
        
        # Load active stations from database
        stations_in_db = db.query(Station).filter(Station.id.in_(list(station_predictions.keys()))).all()
        if not stations_in_db:
            logger.warning("No stations found in database for aggregation mapping.")
            return
            
        wards = db.query(Ward).all()
        for ward in wards:
            # Get IDW weights for K=3
            weights = self.get_idw_weights(ward.latitude, ward.longitude, stations_in_db, K=3)
            if not weights:
                continue
                
            # Perform aggregation for each lead hour (24, 48, 72)
            for lead in [24, 48, 72]:
                agg_pm25 = 0.0
                agg_no2 = 0.0
                
                for st, weight in weights:
                    pred_pm, pred_no2 = station_predictions[st.id][lead]
                    agg_pm25 += pred_pm * weight
                    agg_no2 += pred_no2 * weight
                    
                agg_pm25 = float(round(max(5.0, agg_pm25), 2))
                agg_no2 = float(round(max(2.0, agg_no2), 2))
                agg_aqi = float(round(calculate_pm25_aqi(agg_pm25), 1))
                
                f_time = now + timedelta(hours=lead)
                _save_forecast(db, ward.id, now, f_time, agg_pm25, agg_no2, agg_aqi)
                
        db.commit()
        logger.info("Successfully aggregated station predictions to Ward forecasts via IDW.")
