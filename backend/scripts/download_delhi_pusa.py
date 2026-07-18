import os
import requests

url = "https://data.opencity.in/dataset/0dc7b9fe-9fd4-46ee-a37e-88f0bd6f6362/resource/48881f84-b60b-4178-939e-0a0d1051be11/download/del-pusa-imd-2024-25.csv"
dest_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
dest_file = os.path.join(dest_dir, "delhi_pusa_imd_2024-25.csv")

print(f"Creating destination directory: {dest_dir}")
os.makedirs(dest_dir, exist_ok=True)

print(f"Downloading Pusa IMD Delhi Air Quality Dataset from:\n{url}")
try:
    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()
    
    with open(dest_file, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                
    print(f"Download successful! File saved at:\n{dest_file}")
    print(f"File size: {os.path.getsize(dest_file) / (1024*1024):.2f} MB")
except Exception as e:
    print(f"Error downloading Delhi dataset: {e}")
