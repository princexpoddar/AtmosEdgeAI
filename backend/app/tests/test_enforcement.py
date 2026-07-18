import requests

API_BASE = "http://127.0.0.1:8001/api"

def safe_print(text):
    # Replaces unicode subscript 2 with plain 2 for Windows CMD printing
    safe_text = text.replace("\u2082", "2").replace("\u00b5", "u").replace("\u00b3", "3").replace("\u2713", "v")
    print(safe_text.encode("ascii", "replace").decode("ascii"))

def test_enforcement_endpoint():
    url = f"{API_BASE}/v1/enforcement"
    safe_print(f"Testing GET {url} ...")
    try:
        res = requests.get(url, timeout=15)
        safe_print(f"  Status Code: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            safe_print("  Successfully fetched v1 enforcement dashboard payload!")
            
            # Print highlights
            meta = data.get("metadata", {})
            exec_sum = data.get("executive_summary", {})
            rankings = data.get("priority_rankings", [])
            inspections = data.get("inspection_recommendations", [])
            interventions = data.get("intervention_recommendations", [])
            allocations = data.get("resource_allocation", [])
            
            safe_print(f"    Evaluated: {meta.get('total_stations_evaluated')} stations.")
            safe_print(f"    Headline: {exec_sum.get('headline')}")
            safe_print(f"    Critical Priority Count: {exec_sum.get('critical_count')}")
            
            if rankings:
                safe_print(f"    Highest Ranked Ward: {rankings[0].get('station_name')} (Score: {rankings[0].get('score')})")
            if inspections:
                safe_print(f"    First Inspection Queue Item: {inspections[0].get('inspection_type')} at {inspections[0].get('target_station')}")
            if interventions:
                safe_print(f"    First Intervention Recommendation: {interventions[0].get('action')} [Category: {interventions[0].get('category')}]")
            if allocations:
                safe_print(f"    First Resource Dispatch: {allocations[0].get('quantity')}x {allocations[0].get('resource')} deployed to {allocations[0].get('target_station')}")
                
            # Assert schema validations
            assert "metadata" in data
            assert "priority_rankings" in data
            assert "hotspots" in data
            assert "inspection_recommendations" in data
            assert "intervention_recommendations" in data
            assert "resource_allocation" in data
            assert "executive_summary" in data
            
            safe_print("  v All API v1 enforcement dashboard schema validations passed!")
            return True
        else:
            safe_print(f"  Error Response: {res.text}")
            return False
    except Exception as e:
        safe_print(f"  Exception occurred: {e}")
        return False

def main():
    safe_print("=== STARTING ENFORCEMENT ENGINE TESTS ===")
    assert test_enforcement_endpoint()
    safe_print("=== ALL ENFORCEMENT PIPELINE TESTS COMPLETED ===")

if __name__ == "__main__":
    main()
