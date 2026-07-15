# 📓 Google Colab Migration Guide

Follow this step-by-step guide to move the AtmosEdgeAI backend, database, and datasets onto Google Colab. This allows collaborative development, free GPU-accelerated model training, and public API hosting.

---

## 📁 Phase A: Prepare and Upload Datasets to Google Drive

Since Git ignores large database files and raw CSV records, we will use **Google Drive** to store and persist them.

1. **Locate your local data files**:
   * **Database**: `c:\Users\praba\OneDrive\Desktop\AtmosEdgeAI\backend\geobreathe.db`
   * **Datasets**: `c:\Users\praba\OneDrive\Desktop\AtmosEdgeAI\backend\data` (contains `openaq/` and `firms/`)
2. **Zip the folders for faster upload** (Optional but highly recommended):
   * Right-click the `data` folder -> **Compress to ZIP file** (name it `data.zip`).
3. **Upload to Google Drive**:
   * Open [Google Drive](https://drive.google.com/).
   * Create a folder named **`AtmosEdgeAI_Colab`** at the root of your Drive.
   * Upload `geobreathe.db` and `data.zip` directly into that folder.

---

## 💻 Phase B: Push the Code to GitHub

Make sure GitHub is synchronized with the latest code changes. Run these commands from your local workspace terminal:
```bash
# Verify all changes are committed
git status

# Push all committed code to main
git push origin main
```

---

## 🚀 Phase C: Setup Google Colab Notebook

1. Open [Google Colab](https://colab.research.google.com/) and click **New Notebook**.
2. **Enable GPU Acceleration**:
   * Go to **Runtime** -> **Change runtime type**.
   * Select **T4 GPU** under Hardware accelerator, and click **Save**.

### Cell 1: Mount Google Drive
Run this code to link Google Drive to your Colab workspace:
```python
from google.colab import drive
drive.mount('/content/drive')
```
*(Colab will show a popup asking for permission to access your Google Drive. Approve it.)*

### Cell 2: Clone Codebase from GitHub
Run this to clone the project repository:
```python
# Clone the repository
!git clone https://github.com/princexpoddar/AtmosEdgeAI.git
%cd AtmosEdgeAI
```

### Cell 3: Install Required Dependencies
Colab has PyTorch pre-installed. You only need to install the web/database packages:
```python
!pip install fastapi uvicorn sqlalchemy pydantic shapely requests pandas scikit-learn numpy
```

### Cell 4: Extract and Link Datasets from Google Drive
Extract the dataset zip file and database from Google Drive into the cloned project folder:
```python
import os

# Copy the geobreathe.db SQLite database from Google Drive
!cp /content/drive/MyDrive/AtmosEdgeAI_Colab/geobreathe.db backend/geobreathe.db

# Extract data.zip into backend/data
!mkdir -p backend/data
!unzip -q /content/drive/MyDrive/AtmosEdgeAI_Colab/data.zip -d backend/

print("Database and Datasets linked successfully!")
```

---

## ⚡ Phase D: Run Seeding & Pipeline Verification

To ensure that PyTorch and the CNN-LSTM models execute correctly on the Colab GPU, run the verification test:
```python
import os
# Set PYTHONPATH so Python can resolve the backend package
os.environ['PYTHONPATH'] = "/content/AtmosEdgeAI"

!python backend/app/tests/verify_pipeline.py
```

---

## 🌐 Phase E: Run Backend Server and Expose Public API

To make the Colab backend accessible to your local React frontend, run the FastAPI server and tunnel it using **localtunnel**:

### Cell 5: Start FastAPI Server
```python
import subprocess
import time

# Start FastAPI server in the background on port 8000
server_process = subprocess.Popen(["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"])
time.sleep(5)  # Wait for server startup
print("FastAPI server is running in the background.")
```

### Cell 6: Start Localtunnel
```python
# 1. Install localtunnel
!npm install -g localtunnel

# 2. Retrieve Colab's public IP (used as security password for localtunnel)
import urllib.request
public_ip = urllib.request.urlopen('https://ipv4.icanhazip.com').read().decode('utf8').strip()
print(f"==================================================")
print(f"YOUR TUNNEL PASSWORD (IP): {public_ip}")
print(f"==================================================")

# 3. Expose port 8000
!lt --port 8000
```
This cell will output a public URL (e.g. `https://dry-bears-sing.loca.lt`).

1. Click on the link.
2. In the landing page, paste the **TUNNEL PASSWORD (IP)** printed in Colab and submit.
3. Your Colab FastAPI endpoints (e.g. `/docs`) are now live and publicly accessible!

---

## 🎨 Phase F: Connect Frontend React Dashboard

Open your local frontend code file `frontend/src/App.jsx` (or wherever your API base URL is set) and replace the local API path with the localtunnel URL:

```javascript
// Replace local server URL:
// const API_BASE_URL = "http://localhost:8000/api";

// With your public Colab localtunnel URL:
const API_BASE_URL = "https://dry-bears-sing.loca.lt/api";
```

Now, your local React frontend will communicate directly with the PyTorch CNN-LSTM models running in Google Colab!
