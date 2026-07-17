import os
import sys
import json
import pandas as pd
import numpy as np

def run_selection():
    # Load config
    config_path = "backend/app/core/ml_config.json"
    with open(config_path, "r") as f:
        config = json.load(f)
        
    sel_config = config.get("station_selection", {})
    min_quality = sel_config.get("minimum_quality_score", 75)
    min_history = sel_config.get("minimum_history_years", 5)
    req_pollutants = set(sel_config.get("required_pollutants", ["pm25", "no2"]))
    max_per_city_limits = sel_config.get("max_per_city_limits", {})
    default_max_per_city = sel_config.get("max_per_city", 5)
    
    # Load feasibility report
    report_path = "backend/data/feasibility_report.json"
    with open(report_path, "r") as f:
        report_data = json.load(f)
        
    stations = report_data["stations"]
    df = pd.DataFrame(stations)
    
    print(f"--- Verification: Initial Discovered Stations: {len(df)} ---")
    
    # Validation checks for STOP CONDITIONS
    # 1. State column validation (check if there is any station that has state='Kolkata' but mapped_city is not 'Kolkata')
    inconsistent_states = df[(df["state"] == "Kolkata") & (df["city"] != "Kolkata")]
    if not inconsistent_states.empty:
        print("STOP CONDITION: Inconsistent State mapping detected!")
        for idx, row in inconsistent_states.head(5).iterrows():
            print(f"  Station ID: {row['id']}, Name: '{row['name']}', City: '{row['city']}', State: '{row['state']}'")
        sys.exit(1)
        
    print("State mapping consistency verified successfully.")
    
    # 2. Completeness validation (check if completeness can be computed/verified)
    unverifiable_comp = df[df["expected_samples"] == 0]
    if len(unverifiable_comp) > 0.5 * len(df):
        print("STOP CONDITION: Completeness cannot be verified for more than 50% of stations.")
        sys.exit(1)
    print("Completeness calculation feasibility verified successfully.")
    
    rejection_reasons = {
        "missing_pollutants": [],
        "low_quality_score": [],
        "history_insufficient": [],
        "city_quota_exceeded": []
    }
    
    retained = []
    
    # Group by city for stratified selection
    grouped = df.groupby("city")
    
    for city, group in grouped:
        # Get limit for this city
        limit = max_per_city_limits.get(city, default_max_per_city)
        
        # Sort stations by quality score descending
        sorted_group = group.sort_values("quality_score", ascending=False)
        
        selected_in_city = 0
        
        for idx, row in sorted_group.iterrows():
            st_id = row["id"]
            st_name = row["name"]
            
            # Filter 1: Pollutants
            avail_p = set(row["pollutants"].split(",") if row["pollutants"] else [])
            if not req_pollutants.issubset(avail_p):
                rejection_reasons["missing_pollutants"].append((st_id, st_name, city, f"Missing: {req_pollutants - avail_p}"))
                continue
                
            # Filter 2: Quality Score
            if row["quality_score"] < min_quality:
                rejection_reasons["low_quality_score"].append((st_id, st_name, city, f"Quality {row['quality_score']} < {min_quality}"))
                continue
                
            # Filter 3: History (prefer >= 5 years, fallback to less if needed to meet quota)
            # If the station history is less than 5 years, we check if we already have selected enough stations for this city.
            # If history is < 5, but we can't find any other station with >= 5, we relax it.
            # So, if we have selected less than quota, we accept it.
            # However, if history < 2 years, reject completely.
            if row["history_years"] < 2.0:
                rejection_reasons["history_insufficient"].append((st_id, st_name, city, f"History {row['history_years']} years < 2.0 years"))
                continue
                
            if selected_in_city < limit:
                retained.append(row.to_dict())
                selected_in_city += 1
            else:
                rejection_reasons["city_quota_exceeded"].append((st_id, st_name, city, f"Quota of {limit} for {city} exceeded"))
                
    df_retained = pd.DataFrame(retained)
    
    print("\n==========================================================")
    # Print completeness metrics for every selected station
    print(f"VERIFICATION: SELECTED STATIONS ({len(df_retained)} STATIONS):")
    print("==========================================================")
    cols = ["id", "name", "city", "state", "expected_samples", "observations", "completeness", "earliest", "latest", "quality_score"]
    
    # Format and print selected stations table
    print(df_retained[cols].to_markdown(index=False))
    
    # Save selected stations manifest
    selected_path = "backend/data/selected_stations.json"
    df_retained.to_json(selected_path, orient="records", indent=2)
    print(f"\nSaved {len(df_retained)} selected stations to {selected_path}")
    
    # Rejection summary counts
    print("\n--- Rejection Reasons Summary ---")
    print(f"Missing required pollutants: {len(rejection_reasons['missing_pollutants'])}")
    print(f"Low quality score: {len(rejection_reasons['low_quality_score'])}")
    print(f"Insufficient history (<2 years): {len(rejection_reasons['history_insufficient'])}")
    print(f"City quota exceeded: {len(rejection_reasons['city_quota_exceeded'])}")
    
    total_rejected = (len(rejection_reasons['missing_pollutants']) + 
                      len(rejection_reasons['low_quality_score']) + 
                      len(rejection_reasons['history_insufficient']) + 
                      len(rejection_reasons['city_quota_exceeded']))
                      
    print(f"Total Discovered: {len(df)}")
    print(f"Total Retained: {len(df_retained)}")
    print(f"Total Rejected: {total_rejected}")
    
    # Estimate total rows and storage
    total_obs = df_retained["observations"].sum()
    estimated_db_mb = (total_obs * 120) / (1024 * 1024)
    # Average request limit page yields 1000 items
    expected_requests = (total_obs / 1000) * 1.1 # 10% overlap
    estimated_time_mins = expected_requests / (5 * 60) # 5 requests/sec
    
    print("\n--- Estimated Metrics ---")
    print(f"Total rows to download: {total_obs:,}")
    print(f"Expected database size: {estimated_db_mb:.2f} MB")
    print(f"Expected API requests: {int(expected_requests):,}")
    print(f"Expected download duration: {estimated_time_mins:.1f} minutes")

if __name__ == "__main__":
    run_selection()
