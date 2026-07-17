import os
import json
import logging
import time
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from backend.app.services.ml.config import config, BASE_DIR
from backend.app.services.data_pipeline.station_manager import get_openaq_headers

logger = logging.getLogger(__name__)

RAW_DIR = os.path.join(BASE_DIR, "data", "raw", "openaq")
MANIFEST_PATH = os.path.join(BASE_DIR, "models", "download_manifest.json")

class OpenAQCollector:
    def __init__(self, raw_dir: str = RAW_DIR, manifest_path: str = MANIFEST_PATH):
        self.raw_dir = raw_dir
        self.manifest_path = manifest_path
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)

    def load_manifest(self) -> Dict[str, Any]:
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading manifest: {e}")
        return {
            "OpenAQ": {},
            "Weather": {},
            "FIRMS": {},
            "api_version": "v3",
            "last_updated": datetime.utcnow().isoformat()
        }

    def save_manifest(self, manifest: Dict[str, Any]) -> None:
        manifest["last_updated"] = datetime.utcnow().isoformat()
        try:
            with open(self.manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")

    def get_station_sensors(self, station_id: str, headers: Dict[str, str]) -> Dict[str, int]:
        """
        Fetches the mapping of pollutant name to sensor ID for a location in OpenAQ V3.
        """
        url = f"https://api.openaq.org/v3/locations/{station_id}/sensors"
        max_retries = 5
        backoff = 2.0
        
        for retry in range(max_retries):
            try:
                time.sleep(1.2) # Rate limit protection
                r = requests.get(url, headers=headers, timeout=20)
                if r.status_code == 200:
                    results = r.json().get("results", [])
                    mapping = {}
                    for sensor in results:
                        sensor_id = sensor.get("id")
                        param_name = sensor.get("parameter", {}).get("name", "").lower()
                        if sensor_id and param_name:
                            mapping[param_name] = sensor_id
                    return mapping
                elif r.status_code == 429:
                    logger.warning(f"Rate limited (429) on location {station_id} sensors. Sleeping {backoff}s...")
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    logger.error(f"Error fetching sensors for location {station_id}: {r.status_code}")
                    if r.status_code >= 500:
                        time.sleep(backoff)
                        backoff *= 2.0
                    else:
                        break
            except Exception as e:
                logger.error(f"Exception fetching sensors for location {station_id}: {e}")
                time.sleep(backoff)
                backoff *= 2.0
                
        return {}

    def fetch_sensor_measurements(
        self, 
        sensor_id: int, 
        parameter_name: str,
        start_date: datetime, 
        end_date: datetime, 
        headers: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Fetches raw measurements for a specific sensor ID with backoff and pagination.
        Formats values into standard format compatible with the preprocessor parser.
        Returns None if download fails after retries.
        """
        url = f"https://api.openaq.org/v3/sensors/{sensor_id}/measurements"
        
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        params = {
            "date_from": start_str,
            "date_to": end_str,
            "limit": 1000,
            "page": 1
        }
        
        measurements = []
        max_retries = 5
        
        while True:
            retry_count = 0
            backoff = 2.0
            success = False
            
            while retry_count < max_retries:
                try:
                    time.sleep(1.2) # Rate limit protection
                    r = requests.get(url, headers=headers, params=params, timeout=20)
                    if r.status_code == 200:
                        data = r.json()
                        results = data.get("results", [])
                        
                        # Convert to compatible parsing format
                        for item in results:
                            dt_str = item.get("period", {}).get("datetimeTo")
                            val = item.get("value")
                            if val is not None and dt_str:
                                measurements.append({
                                    "parameter": {"name": parameter_name},
                                    "value": float(val),
                                    "period": {"datetimeTo": dt_str}
                                })
                                
                        meta = data.get("meta", {})
                        found_val = meta.get("found", 0)
                        if isinstance(found_val, str):
                            found_val = found_val.replace(">", "").strip()
                        total = int(found_val or 0)
                        limit = params["limit"]
                        page = params["page"]
                        
                        success = True
                        if page * limit >= total or not results:
                            return measurements
                        else:
                            params["page"] += 1
                            break # Move to next page
                    elif r.status_code == 429:
                        logger.warning(f"Rate limited (429) on sensor {sensor_id}. Sleeping {backoff}s...")
                        time.sleep(backoff)
                        backoff *= 2.0
                    else:
                        logger.error(f"Error {r.status_code} fetching measurements for sensor {sensor_id}. Sleeping {backoff}s...")
                        time.sleep(backoff)
                        backoff *= 2.0
                        retry_count += 1
                except Exception as e:
                    logger.error(f"Exception fetching measurements for sensor {sensor_id}: {e}")
                    time.sleep(backoff)
                    backoff *= 2.0
                    retry_count += 1
                    
            if not success:
                logger.error(f"Max retries exceeded for sensor {sensor_id}")
                return None

    def collect_station_historical(
        self, 
        station_id: str, 
        start_year: int, 
        end_year: int, 
        chunk_days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Runs incremental data collection by querying active sensors and fetching their observations.
        """
        station_dir = os.path.join(self.raw_dir, station_id)
        os.makedirs(station_dir, exist_ok=True)
        
        headers = get_openaq_headers()
        
        # Discover sensors first
        sensor_mapping = self.get_station_sensors(station_id, headers)
        if not sensor_mapping:
            logger.warning(f"No sensors mapped for Station {station_id}. Skipping.")
            return []
            
        manifest = self.load_manifest()
        station_manifest = manifest["OpenAQ"].get(station_id, {})
        
        start_dt = datetime(start_year, 1, 1)
        end_dt = datetime(end_year, 12, 31)
        
        current_dt = start_dt
        delta = timedelta(days=chunk_days)
        
        downloaded_count = 0
        
        while current_dt < end_dt:
            chunk_end = min(current_dt + delta, end_dt)
            chunk_key = f"{current_dt.strftime('%Y%m%d')}_{chunk_end.strftime('%Y%m%d')}"
            
            chunk_file = os.path.join(station_dir, f"{chunk_key}.json")
            
            # Check manifest for completeness
            if os.path.exists(chunk_file) and chunk_key in station_manifest.get("completed_chunks", []):
                current_dt = chunk_end
                continue
                
            logger.info(f"Downloading OpenAQ chunk for Station {station_id}: {chunk_key}")
            
            # Fetch measurements for target pollutants
            chunk_data = []
            chunk_failed = False
            for param, sensor_id in sensor_mapping.items():
                if param in ["pm25", "no2", "pm10", "so2", "co", "o3"]:
                    sensor_measurements = self.fetch_sensor_measurements(
                        sensor_id, param, current_dt, chunk_end, headers
                    )
                    if sensor_measurements is None:
                        chunk_failed = True
                        break
                    chunk_data.extend(sensor_measurements)
            
            if chunk_failed:
                logger.error(f"Failed to complete download for chunk {chunk_key} of station {station_id}. Will retry on next run.")
                current_dt = chunk_end
                continue
                
            if chunk_data:
                try:
                    with open(chunk_file, "w") as f:
                        json.dump(chunk_data, f, indent=2)
                    downloaded_count += len(chunk_data)
                except Exception as e:
                    logger.error(f"Failed to save chunk file {chunk_file}: {e}")
            
            if "completed_chunks" not in station_manifest:
                station_manifest["completed_chunks"] = []
            if chunk_key not in station_manifest["completed_chunks"]:
                station_manifest["completed_chunks"].append(chunk_key)
                
            station_manifest["last_downloaded"] = datetime.utcnow().isoformat()
            manifest["OpenAQ"][station_id] = station_manifest
            self.save_manifest(manifest)
            
            current_dt = chunk_end
            
        logger.info(f"Finished OpenAQ collection for Station {station_id}. Downloaded {downloaded_count} records.")
        return []

    def run_parallel_collection(self, station_ids: List[str], start_year: int, end_year: int, max_workers: int = 4) -> None:
        """
        Executes multi-threaded historical collection.
        """
        logger.info(f"Starting parallel OpenAQ historical download for {len(station_ids)} stations ({start_year}-{end_year})...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.collect_station_historical, sid, start_year, end_year): sid
                for sid in station_ids
            }
            
            for fut in as_completed(futures):
                sid = futures[fut]
                try:
                    fut.result()
                except Exception as e:
                    logger.error(f"Station {sid} download failed: {e}")
                    
        logger.info("OpenAQ parallel historical download complete.")
