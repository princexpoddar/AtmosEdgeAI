import os
import sys
import json
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up backend paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def get_api_key():
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("OPENAQ_API_KEY="):
                    return line.split("=")[1].strip()
    return None

def map_city(name, city_field):
    name_lower = name.lower()
    city_lower = (city_field or "").lower()
    
    known_cities = [
        "delhi", "mumbai", "hyderabad", "chennai", "lucknow", "kolkata", 
        "pune", "ahmedabad", "bengaluru", "bangalore", "patna", "jaipur",
        "kanpur", "agra", "varanasi", "gwalior", "chandigarh", "amritsar",
        "ludhiana", "gurugram", "noida", "ghaziabad", "faridabad", "howrah",
        "thane", "navi mumbai", "nagpur", "nashik", "coimbatore", "madurai",
        "visakhapatnam", "vijayawada", "kochi", "thiruvananthapuram", "bhopal",
        "indore", "ranchi", "guwahati", "dehradun", "raipur", "bhubaneswar",
        "jabalpur", "udaipur", "jodhpur", "kota", "alwar", "jalandhar"
    ]
    
    for c in known_cities:
        if c in city_lower or c in name_lower:
            if c == "bangalore":
                return "Bengaluru"
            return c.title()
            
    if city_field and city_field != "Unknown City" and len(city_field) > 2:
        return city_field.title()
        
    return "Other"

def map_state(city, name):
    name_lower = name.lower()
    city_lower = city.lower()
    
    # State mapping based on PCB (Pollution Control Board) initials
    pcbs = {
        "dpcc": "Delhi",
        "tspcb": "Telangana",
        "hspcb": "Haryana",
        "uppcb": "Uttar Pradesh",
        "kspcb": "Karnataka",
        "apcb": "Assam",
        "mppcb": "Madhya Pradesh",
        "mppb": "Madhya Pradesh",
        "wbpcb": "West Bengal",
        "appcb": "Andhra Pradesh",
        "tnpcb": "Tamil Nadu",
        "gpcl": "Gujarat",
        "gpcb": "Gujarat",
        "ppcc": "Puducherry",
        "rspcb": "Rajasthan",
        "bspcb": "Bihar",
        "jspcb": "Jharkhand",
        "osppb": "Odisha",
        "opcb": "Odisha",
        "cspcb": "Chhattisgarh",
        "jkpcb": "Jammu & Kashmir",
        "ueppcb": "Uttarakhand",
        "hppcb": "Himachal Pradesh",
        "ppcb": "Punjab",
        "apspcb": "Arunachal Pradesh",
        "mikes": "Other"
    }
    
    for board, state_name in pcbs.items():
        if f"- {board}" in name_lower or f" {board}" in name_lower or f"_{board}" in name_lower:
            return state_name
            
    # City-based fallback mapping
    city_state_map = {
        "Delhi": "Delhi",
        "Gurugram": "Haryana",
        "Panchkula": "Haryana",
        "Faridabad": "Haryana",
        "Bengaluru": "Karnataka",
        "Mangalore": "Karnataka",
        "Mysore": "Karnataka",
        "Hyderabad": "Telangana",
        "Chennai": "Tamil Nadu",
        "Coimbatore": "Tamil Nadu",
        "Madurai": "Tamil Nadu",
        "Mumbai": "Maharashtra",
        "Thane": "Maharashtra",
        "Navi Mumbai": "Maharashtra",
        "Pune": "Maharashtra",
        "Nagpur": "Maharashtra",
        "Nashik": "Maharashtra",
        "Lucknow": "Uttar Pradesh",
        "Agra": "Uttar Pradesh",
        "Kanpur": "Uttar Pradesh",
        "Prayagraj": "Uttar Pradesh",
        "Varanasi": "Uttar Pradesh",
        "Noida": "Uttar Pradesh",
        "Ghaziabad": "Uttar Pradesh",
        "Kolkata": "West Bengal",
        "Howrah": "West Bengal",
        "Ahmedabad": "Gujarat",
        "Gandhinagar": "Gujarat",
        "Guwahati": "Assam",
        "Patna": "Bihar",
        "Jaipur": "Rajasthan",
        "Bhopal": "Madhya Pradesh",
        "Indore": "Madhya Pradesh",
        "Ranchi": "Jharkhand",
        "Bhubaneswar": "Odisha",
        "Dehradun": "Uttarakhand",
        "Srinagar": "Jammu & Kashmir",
        "Jammu": "Jammu & Kashmir",
        "Raipur": "Chhattisgarh"
    }
    
    if city in city_state_map:
        return city_state_map[city]
        
    for c, s in city_state_map.items():
        if c.lower() in name_lower:
            return s
            
    return "Other"

def fetch_all_locations(headers):
    print("Fetching all locations in India from OpenAQ...")
    url = "https://api.openaq.org/v3/locations"
    params = {
        "iso": "IN",
        "limit": 100,
        "page": 1
    }
    
    all_locations = []
    
    while True:
        try:
            r = requests.get(url, headers=headers, params=params, timeout=20)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                if not results:
                    break
                all_locations.extend(results)
                
                print(f"Page {params['page']} fetched: {len(results)} locations. Cumulative: {len(all_locations)}...")
                params["page"] += 1
                time.sleep(0.1)
            else:
                print(f"Error fetching locations: HTTP {r.status_code}")
                break
        except Exception as e:
            print(f"Exception fetching locations: {e}")
            break
            
    print(f"Total locations discovered: {len(all_locations)}")
    return all_locations

def fetch_sensors_for_location(location_id, headers):
    url = f"https://api.openaq.org/v3/locations/{location_id}/sensors"
    max_retries = 3
    backoff = 1.0
    for retry in range(max_retries):
        try:
            r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200:
                return location_id, r.json().get("results", [])
            elif r.status_code == 429:
                time.sleep(backoff)
                backoff *= 2.0
            else:
                break
        except Exception:
            time.sleep(backoff)
            backoff *= 2.0
    return location_id, []

def analyze_feasibility():
    key = get_api_key()
    headers = {"X-API-Key": key} if key else {}
    
    locations = fetch_all_locations(headers)
    if not locations:
        print("Error: No locations found. Metadata validation fails.")
        sys.exit(1)
        
    print("\nFetching sensor details for all discovered locations in parallel...")
    location_details = {}
    
    # Run parallel collection of sensor detailed coverage metadata
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch_sensors_for_location, loc["id"], headers): loc["id"]
            for loc in locations
        }
        
        completed = 0
        for fut in as_completed(futures):
            loc_id = futures[fut]
            try:
                lid, sensors = fut.result()
                location_details[lid] = sensors
            except Exception as e:
                print(f"Failed to fetch sensors for location {loc_id}: {e}")
            completed += 1
            if completed % 50 == 0:
                print(f"Fetched sensor details for {completed}/{len(locations)} locations...")

    station_records = []
    
    for loc in locations:
        lid = loc["id"]
        sensors = location_details.get(lid, []) or []
        
        # Identify pollutants
        pollutants = []
        
        pm25_obs = 0
        no2_obs = 0
        
        pm25_first = None
        pm25_last = None
        no2_first = None
        no2_last = None
        
        for s in sensors:
            if not s:
                continue
            param = s.get("parameter", {}).get("name", "").lower()
            if param:
                pollutants.append(param)
            
            coverage = s.get("coverage") or {}
            obs_cnt = coverage.get("observedCount", 0)
            
            dfirst = s.get("datetimeFirst") or {}
            dlast = s.get("datetimeLast") or {}
            
            ts_first = pd.to_datetime(dfirst.get("utc")) if dfirst.get("utc") else None
            ts_last = pd.to_datetime(dlast.get("utc")) if dlast.get("utc") else None
            
            if param == "pm25":
                pm25_obs = obs_cnt
                pm25_first = ts_first
                pm25_last = ts_last
            elif param == "no2":
                no2_obs = obs_cnt
                no2_first = ts_first
                no2_last = ts_last
                
        # We define earliest and latest based on target pollutants PM2.5 and NO2 specifically
        target_firsts = [t for t in [pm25_first, no2_first] if t is not None]
        target_lasts = [t for t in [pm25_last, no2_last] if t is not None]
        
        earliest_ts = min(target_firsts) if target_firsts else None
        latest_ts = max(target_lasts) if target_lasts else None
        
        # Fallback to overall location timestamps if targets are missing
        if earliest_ts is None and loc.get("datetimeFirst"):
            dfirst = loc["datetimeFirst"]
            if isinstance(dfirst, dict) and dfirst.get("utc"):
                earliest_ts = pd.to_datetime(dfirst["utc"])
            elif isinstance(dfirst, str):
                earliest_ts = pd.to_datetime(dfirst)
                
        if latest_ts is None and loc.get("datetimeLast"):
            dlast = loc["datetimeLast"]
            if isinstance(dlast, dict) and dlast.get("utc"):
                latest_ts = pd.to_datetime(dlast["utc"])
            elif isinstance(dlast, str):
                latest_ts = pd.to_datetime(dlast)
                
        # History calculation
        history_years = 0.0
        if earliest_ts and latest_ts:
            history_days = (latest_ts - earliest_ts).days
            history_years = history_days / 365.25
            
        # Expected hourly samples
        expected_samples = 0
        if history_years > 0:
            expected_samples = int(history_years * 8760)
            
        # Completeness based specifically on the target variables we will download
        has_pm25 = "pm25" in pollutants
        has_no2 = "no2" in pollutants
        
        actual_records = 0
        if has_pm25 and has_no2:
            actual_records = int((pm25_obs + no2_obs) / 2)
        elif has_pm25:
            actual_records = pm25_obs
        elif has_no2:
            actual_records = no2_obs
            
        completeness = 0.0
        if expected_samples > 0:
            completeness = (actual_records / expected_samples) * 100.0
            completeness = min(100.0, completeness)
            
        missing_pct = 100.0 - completeness
        
        # Quality Scoring
        # History score: up to 5 years (35%)
        history_score = min(100.0, (history_years / 5.0) * 100.0)
        # Completeness score: (35%)
        comp_score = completeness
        # Pollutants coverage score (30%):
        if has_pm25 and has_no2:
            coverage_score = 100.0
        elif has_pm25 or has_no2:
            coverage_score = 50.0
        else:
            coverage_score = 0.0
            
        q_score = 0.35 * history_score + 0.35 * comp_score + 0.30 * coverage_score
        
        # Locality / City
        city = map_city(loc.get("name", ""), loc.get("locality"))
        
        # Robust State mapping
        state = map_state(city, loc.get("name", ""))
        
        # Metadata validation check - if state is still "Kolkata" when city is not Kolkata, raise error
        if state == "Kolkata" and city != "Kolkata":
            print(f"STOP CONDITION: Inconsistent State mapping detected for Location {lid} ({loc.get('name')}): City is {city} but State mapped to Kolkata.")
            sys.exit(1)
            
        station_records.append({
            "id": lid,
            "name": loc.get("name") or f"Location {lid}",
            "city": city,
            "state": state,
            "latitude": loc.get("coordinates", {}).get("latitude"),
            "longitude": loc.get("coordinates", {}).get("longitude"),
            "pollutants": ",".join(sorted(list(set(pollutants)))),
            "has_pm25": has_pm25,
            "has_no2": has_no2,
            "has_both": has_pm25 and has_no2,
            "earliest": earliest_ts.isoformat() if earliest_ts else None,
            "latest": latest_ts.isoformat() if latest_ts else None,
            "history_years": float(round(history_years, 2)),
            "observations": actual_records,
            "expected_samples": expected_samples,
            "completeness": float(round(completeness, 2)),
            "missing_pct": float(round(missing_pct, 2)),
            "quality_score": float(round(q_score, 2))
        })
        
    df = pd.DataFrame(station_records)
    
    # Save the output to disk
    report_data = {
        "metadata": {
            "total_stations": len(df),
            "stations_with_pm25": int(df["has_pm25"].sum()),
            "stations_with_no2": int(df["has_no2"].sum()),
            "stations_with_both": int(df["has_both"].sum()),
            "greater_than_2_years": int((df["history_years"] > 2.0).sum()),
            "greater_than_3_years": int((df["history_years"] > 3.0).sum()),
            "greater_than_5_years": int((df["history_years"] > 5.0).sum()),
            "greater_than_7_years": int((df["history_years"] > 7.0).sum()),
        },
        "stations": df.sort_values("quality_score", ascending=False).to_dict(orient="records")
    }
    
    report_path = "backend/data/feasibility_report.json"
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)
        
    print(f"\nFeasibility report written to {report_path}")
    print("STEP 1 to 5 metrics successfully processed.")

if __name__ == "__main__":
    analyze_feasibility()
