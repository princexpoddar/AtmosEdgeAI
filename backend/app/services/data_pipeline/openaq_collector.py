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

    def fetch_station_chunk(
        self, 
        station_id: str, 
        start_date: datetime, 
        end_date: datetime, 
        headers: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Downloads a chunk of measurements for a single station with exponential backoff.
        """
        url = f"https://api.openaq.org/v3/locations/{station_id}/measurements"
        
        # Format times as ISO strings in UTC
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        params = {
            "date_from": start_str,
            "date_to": end_str,
            "limit": 1000,
            "page": 1
        }
        
        all_measurements = []
        max_retries = 5
        
        while True:
            retry_count = 0
            backoff = 2.0
            
            while retry_count < max_retries:
                try:
                    r = requests.get(url, headers=headers, params=params, timeout=20)
                    if r.status_code == 200:
                        data = r.json()
                        results = data.get("results", [])
                        all_measurements.extend(results)
                        
                        # Pagination check
                        meta = data.get("meta", {})
                        total = meta.get("found", 0)
                        limit = params["limit"]
                        page = params["page"]
                        
                        if page * limit >= total or not results:
                            return all_measurements
                        else:
                            params["page"] += 1
                            break # Go to next page
                    elif r.status_code == 429:
                        logger.warning(f"Rate limit (429) hit for station {station_id}. Retrying in {backoff}s...")
                        time.sleep(backoff)
                        backoff *= 2.0
                        retry_count += 1
                    else:
                        logger.error(f"OpenAQ API returned error {r.status_code} for station {station_id}")
                        return all_measurements
                except Exception as e:
                    logger.error(f"API request failed: {e}. Retrying...")
                    time.sleep(backoff)
                    backoff *= 2.0
                    retry_count += 1
            
            if retry_count >= max_retries:
                logger.error(f"Max retries exceeded for station {station_id} in period {start_str} - {end_str}")
                return all_measurements

    def collect_station_historical(
        self, 
        station_id: str, 
        start_year: int, 
        end_year: int, 
        chunk_days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Performs incremental data collection for a single station.
        Splits timeframe into chunks and caches results locally.
        """
        station_dir = os.path.join(self.raw_dir, station_id)
        os.makedirs(station_dir, exist_ok=True)
        
        headers = get_openaq_headers()
        
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
            
            # Check if this chunk is already downloaded
            if os.path.exists(chunk_file) and chunk_key in station_manifest.get("completed_chunks", []):
                # Already processed
                current_dt = chunk_end
                continue
                
            logger.info(f"Downloading OpenAQ chunk for Station {station_id}: {chunk_key}")
            chunk_data = self.fetch_station_chunk(station_id, current_dt, chunk_end, headers)
            
            if chunk_data:
                try:
                    with open(chunk_file, "w") as f:
                        json.dump(chunk_data, f, indent=2)
                    downloaded_count += len(chunk_data)
                except Exception as e:
                    logger.error(f"Failed to save chunk file {chunk_file}: {e}")
            
            # Record chunk in manifest
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
        Executes multi-threaded historical collection for all station IDs.
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
