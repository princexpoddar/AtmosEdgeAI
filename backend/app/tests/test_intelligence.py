import requests

API_BASE = "http://127.0.0.1:8001/api"

def safe_print(text):
    # Replaces unicode subscript 2 with plain 2 for Windows CMD printing
    safe_text = text.replace("\u2082", "2").replace("\u00b5", "u").replace("\u00b3", "3")
    print(safe_text.encode("ascii", "replace").decode("ascii"))

def test_intelligence_endpoint(station_id: str):
    url = f"{API_BASE}/v1/intelligence/{station_id}"
    safe_print(f"Testing GET {url} ...")
    try:
        res = requests.get(url, timeout=10)
        safe_print(f"  Status Code: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            safe_print("  Successfully fetched v1 intelligence payload!")
            
            # Check keys
            intel = data.get("intelligence", {})
            safe_print(f"    Reasoning Engine text: {intel.get('reasoning', {}).get('text')}")
            safe_print(f"    Confidence Engine level: {intel.get('confidence', {}).get('level')} ({intel.get('confidence', {}).get('score') * 100}%)")
            safe_print(f"    Primary source: {intel.get('source_attribution', {}).get('primary', {}).get('source')}")
            
            rejected = intel.get('source_attribution', {}).get('rejected', [])
            if rejected:
                safe_print(f"    Rejected source: {rejected[0].get('source')} - {rejected[0].get('reason')}")
                
            safe_print(f"    Risk Assessment overall: {intel.get('risk_assessment', {}).get('overall_risk')}")
            safe_print(f"    Decision Engine priority: {intel.get('decision', {}).get('priority')}")
            safe_print(f"    Report Generator headline: {intel.get('report', {}).get('headline')}")
            
            # Assert validations
            assert "forecast" in data
            assert "source_attribution" in intel
            assert "risk_assessment" in intel
            assert "confidence" in intel
            assert "reasoning" in intel
            assert "decision" in intel
            assert "report" in intel
            safe_print("  ✓ All API v1 intelligence payload checks passed!")
            return True
        else:
            safe_print(f"  Error Response: {res.text}")
            return False
    except Exception as e:
        safe_print(f"  Exception occurred: {e}")
        return False

def main():
    safe_print("=== STARTING INTELLIGENCE PIPELINE TESTS ===")
    
    # Check active station (5657 has 100 historical readings)
    assert test_intelligence_endpoint("5657")
    
    # Check invalid station (should return 404)
    safe_print("\nTesting invalid station (expect 404)...")
    res = requests.get(f"{API_BASE}/v1/intelligence/9999", timeout=5)
    safe_print(f"  Status Code: {res.status_code}")
    assert res.status_code == 404
    
    safe_print("\n=== ALL INTELLIGENCE PIPELINE TESTS COMPLETED ===")

if __name__ == "__main__":
    main()
