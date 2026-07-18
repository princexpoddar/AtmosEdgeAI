import requests

API_KEY = "your_api_key_here"
RESOURCE_ID = "3b01bcb8-0b15-492c-b6f1-5fc5d0ab03db" # Real-time Air Quality Index Resource ID
URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}?api-key={API_KEY}&format=json&limit=5"

try:
    print(f"Requesting: {URL}")
    res = requests.get(URL, timeout=10)
    print(f"Status Code: {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        print("Success! Response JSON:")
        import json
        print(json.dumps(data, indent=2)[:1000])
    else:
        print(f"Error: {res.text}")
except Exception as e:
    print(f"Exception: {e}")
