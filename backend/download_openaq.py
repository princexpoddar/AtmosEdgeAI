import os
import sys
import json
import subprocess
import time

# Load config dynamically from core/ml_config.json
base_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(base_dir, "app", "core", "ml_config.json")

# Default values if config not found
STATION_IDS = [70273, 70295, 70354, 70367, 8556, 8160, 8161, 8180, 8185, 238383]
history_years = 2

if os.path.exists(config_path):
    try:
        with open(config_path, "r") as f:
            cfg = json.load(f)
            hist_stations = cfg.get("ingestion", {}).get("openaq_historical_stations", {})
            rt_stations = cfg.get("ingestion", {}).get("openaq_v3_realtime_locations", {})
            
            # Combine all unique station IDs
            all_stations = set(list(hist_stations.values()) + list(rt_stations.values()))
            if all_stations:
                STATION_IDS = sorted(list(all_stations))
            
            history_years = cfg.get("ingestion", {}).get("history_years", history_years)
    except Exception as e:
        print(f"Error loading ml_config.json: {e}. Using defaults.")

# Calculate YEARS based on history_years
current_year = time.localtime().tm_year
YEARS = list(range(current_year - history_years, current_year + 1))

S3_BUCKET = "s3://openaq-data-archive"
LOCAL_DIR = os.path.abspath(os.path.join(base_dir, "data", "openaq"))


print("--- Starting OpenAQ AWS CLI Data Download ---")
print(f"Target Stations: {STATION_IDS}")
print(f"Target Years: {YEARS}")
print(f"Destination: {LOCAL_DIR}\n")

os.makedirs(LOCAL_DIR, exist_ok=True)

start_time = time.time()
downloaded_folders = []

# Probe and download for all stations
for station_id in STATION_IDS:
    print(f"Checking S3 records for Station ID: {station_id}...")
    
    # Check what years are available by running aws s3 ls
    check_cmd = ["aws", "s3", "ls", "--no-sign-request", f"{S3_BUCKET}/records/csv.gz/locationid={station_id}/"]
    try:
        check_res = subprocess.run(check_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if check_res.returncode != 0:
            print(f"-> Station {station_id} folder not found or not accessible on S3. Skipping.\n")
            continue
        
        # Parse output to find which years exist
        available_years = []
        for line in check_res.stdout.splitlines():
            line = line.strip()
            if "PRE year=" in line:
                year_part = line.split("PRE year=")[1].replace("/", "")
                if year_part.isdigit():
                    available_years.append(int(year_part))
        
        print(f"-> Available years for Station {station_id} on S3: {available_years}")
        
        # Determine years to download
        years_to_download = [y for y in YEARS if y in available_years]
        if not years_to_download:
            print(f"-> No data for target years {YEARS} at Station {station_id}. Skipping.\n")
            continue
            
        print(f"-> Will download data for years: {years_to_download}")
        
        for year in years_to_download:
            s3_path = f"{S3_BUCKET}/records/csv.gz/locationid={station_id}/year={year}/"
            dest_path = os.path.join(LOCAL_DIR, f"locationid={station_id}", f"year={year}")
            
            # Ensure target directory exists
            os.makedirs(dest_path, exist_ok=True)
            
            # Download using AWS CLI s3 cp
            cp_cmd = ["aws", "s3", "cp", "--no-sign-request", "--recursive", s3_path, dest_path]
            print(f"   Downloading: {s3_path} -> {dest_path}")
            
            subprocess.run(cp_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            downloaded_folders.append((station_id, year))
            
        print(f"Finished Station {station_id}.\n")
            
    except Exception as e:
        print(f"Error checking/downloading Station {station_id}: {e}\n")

# Verify download results
print("--- Download Summary ---")
total_files = 0
total_size_bytes = 0

for root, dirs, files in os.walk(LOCAL_DIR):
    for f in files:
        if f.endswith(".csv.gz"):
            total_files += 1
            total_size_bytes += os.path.getsize(os.path.join(root, f))

print(f"Successfully downloaded folders: {downloaded_folders}")
print(f"Total downloaded files: {total_files}")
print(f"Total size: {total_size_bytes / (1024 * 1024):.2f} MB")
print(f"Time taken: {time.time() - start_time:.2f} seconds")
