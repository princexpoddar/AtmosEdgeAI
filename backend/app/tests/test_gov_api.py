import os
import requests
from dotenv import load_dotenv

# Load env variables from root/parent directory if present
load_dotenv()

API_KEY = os.getenv("DATA_GOV_IN_API_KEY")
if not API_KEY:
    raise ValueError("DATA_GOV_IN_API_KEY environment variable is not set. Please define it in your .env file.")

RESOURCE_ID = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69" # Real-time Air Quality Index Resource ID
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
