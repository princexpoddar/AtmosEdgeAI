import json
import pandas as pd
import numpy as np

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

def run_analysis():
    with open("backend/data/feasibility_report.json", "r") as f:
        data = json.load(f)
        
    metadata = data["metadata"]
    stations = data["stations"]
    
    df = pd.DataFrame(stations)
    
    # Map cities properly
    df["mapped_city"] = df.apply(lambda r: map_city(r["name"], r["city"]), axis=1)
    
    # Filter only stations that have valid locations/coordinates
    df = df.dropna(subset=["latitude", "longitude"])
    
    # Rank every station by quality score
    df["rank"] = df["quality_score"].rank(ascending=False, method="first").astype(int)
    df_sorted = df.sort_values("rank")
    
    # Output Ranked Stations
    print("RANKED STATIONS (TOP 20):")
    cols = ["rank", "id", "name", "mapped_city", "history_years", "completeness", "quality_score", "pollutants"]
    print(df_sorted[cols].head(20).to_markdown(index=False))
    
    # Step 4: City Summary Table
    # Target cities: Delhi, Mumbai, Hyderabad, Chennai, Lucknow, Kolkata, Pune, Ahmedabad, Bengaluru
    target_cities = ["Delhi", "Mumbai", "Hyderabad", "Chennai", "Lucknow", "Kolkata", "Pune", "Ahmedabad", "Bengaluru"]
    
    city_summary_rows = []
    for c in target_cities:
        city_df = df[df["mapped_city"] == c]
        if not city_df.empty:
            num_stations = len(city_df)
            avg_years = float(round(city_df["history_years"].mean(), 2))
            avg_comp = float(round(city_df["completeness"].mean(), 2))
            avg_q = float(round(city_df["quality_score"].mean(), 2))
        else:
            num_stations = 0
            avg_years = 0.0
            avg_comp = 0.0
            avg_q = 0.0
            
        city_summary_rows.append({
            "City": c,
            "Number of Stations": num_stations,
            "Average Years Available": avg_years,
            "Average Completeness (%)": avg_comp,
            "Average Quality Score": avg_q
        })
        
    city_summary_df = pd.DataFrame(city_summary_rows)
    print("\nCITY SUMMARY:")
    print(city_summary_df.to_markdown(index=False))
    
    # Step 5: Dataset Size Estimation
    # Disk size per row in CSV: ~100 bytes (e.g. timestamp, id, pollutants)
    # Disk size in SQLite db (including indexing): ~120 bytes per row
    print("\nDATASET SIZE ESTIMATIONS:")
    estimations = []
    for limit in [10, 20, 50, 100]:
        top_n = df_sorted.head(limit)
        total_obs = top_n["observations"].sum()
        # Sum of actual available observations
        total_years = top_n["history_years"].sum()
        unique_cities = top_n["mapped_city"].nunique()
        
        # Estimate size in MB (SQLite database)
        estimated_db_mb = (total_obs * 120) / (1024 * 1024)
        
        estimations.append({
            "Selection": f"Top {limit} Stations",
            "Stations Count": len(top_n),
            "Total Rows (Observations)": f"{total_obs:,}",
            "Sum of History Years": f"{total_years:.1f} yrs",
            "Unique Cities": unique_cities,
            "Estimated SQLite Size (MB)": f"{estimated_db_mb:.2f} MB"
        })
        
    est_df = pd.DataFrame(estimations)
    print(est_df.to_markdown(index=False))
    
if __name__ == "__main__":
    run_analysis()
