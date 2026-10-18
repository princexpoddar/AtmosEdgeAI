# 🚀 AtmosEdgeAI — New User Getting Started & Running Guide

Welcome to **AtmosEdgeAI**! This guide walks you through setting up and running the complete AtmosEdgeAI system on your local machine from scratch.

---

## 📋 System Prerequisites

Ensure you have the following installed before starting:

| Tool | Minimum Version | Recommended Version | Verification Command |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10+ | 3.11 / 3.12 | `python --version` |
| **Node.js** | 18.0+ | 20.x or 22.x LTS | `node --version` |
| **npm** | 9.0+ | 10.x | `npm --version` |
| **Git** | 2.30+ | Latest | `git --version` |

> [!NOTE]
> No external database server (PostgreSQL/MySQL) or Redis cache is required for local evaluation. The system uses an embedded SQLite database with an autonomous auto-seeding engine.

---

## ⚡ 1-Minute Quick Launch (Windows)

If you are on Windows, you can start the backend instantly:

1. Clone and enter the repository:
   ```powershell
   git clone https://github.com/princexpoddar/AtmosEdgeAI.git
   cd AtmosEdgeAI
   ```
2. Set up your environment file:
   ```powershell
   Copy-Item .env.example .env
   ```
3. Run the backend batch script (automatically activates virtualenv, runs migrations, and starts the API on port 8001):
   ```cmd
   .\run_backend.bat
   ```
4. In a second terminal, start the frontend:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```
5. Open your browser to **`http://localhost:5173`**!

---

## 🛠️ Step-by-Step Manual Setup (Cross-Platform)

Follow these steps for **Windows (PowerShell)**, **macOS**, or **Linux**.

### Step 1: Clone the Repository

```bash
git clone https://github.com/princexpoddar/AtmosEdgeAI.git
cd AtmosEdgeAI
```

---

### Step 2: Configure Environment Variables

The project includes pre-configured environment templates. Copy `.env.example` to `.env`:

#### On Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```

#### On Linux / macOS:
```bash
cp .env.example .env
```

Open `.env` in any editor to customize your API keys:

```dotenv
# .env Configuration File
OPENAQ_API_KEY=your_openaq_api_key_here
NASA_FIRMS_MAP_KEY=your_nasa_firms_map_key_here
DATA_GOV_IN_API_KEY=your_data_gov_in_api_key_here
GEMMA_API_KEY=your_google_ai_studio_api_key_here
GEMINI_API_KEY=your_google_ai_studio_api_key_here
```

#### API Keys Reference:
| Key | Purpose | Required? | Fallback Behavior if Omitted |
| :--- | :--- | :--- | :--- |
| `GEMMA_API_KEY` | Powers the multi-lingual AI Citizen Advisory Chatbot using Google Gemma 2 open models | Recommended | Uses physics-grounded rule-based health recommendations |
| `DATA_GOV_IN_API_KEY` | Live syncing with CPCB CAAQMS stations across India | Optional | Uses the seeded database of 40 stations with realistic diurnal data |
| `NASA_FIRMS_MAP_KEY` | Satellite stubble burning / thermal anomaly detection | Optional | Fallback calculates upwind stubble burning factor from synthetic models |
| `OPENAQ_API_KEY` | Secondary validation sensor network | Optional | Uses internal telemetry and SQLite cache |

> [!TIP]
> **Zero Key Requirement for Local Demo:** Even if you do not provide any external API keys, the entire application (Spatial Map, XGBoost 72h Forecasts, 4-Factor Source Attribution, Ward Enforcement Directives, and Citizen Health Guidelines) runs seamlessly using autonomous mathematical fallbacks and seeded baseline telemetry!

---

### Step 3: Backend Setup (FastAPI & Machine Learning)

#### 3.1 Create and Activate a Python Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If you encounter an execution policy error on PowerShell, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` first).*

**Windows (Command Prompt):**
```cmd
python -m venv venv
.\venv\Scripts\activate.bat
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 3.2 Install Dependencies

Install the backend Python dependencies:
```bash
pip install -r backend/requirements.txt
```

> [!NOTE]
> Installing packages like `torch`, `xgboost`, and `scikit-learn` may take 1–2 minutes depending on your internet connection.

#### 3.3 Start the FastAPI Backend Server

Run Uvicorn from the **root directory** so package paths resolve correctly:

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8001 --reload
```

You should see output similar to:
```text
INFO:     Will watch for changes in these directories: ['...']
INFO:     Initializing database...
INFO:     Auto-seeding 40 CPCB stations and 72h baseline readings from selected_stations.json...
INFO:     Successfully seeded 40 stations and 72h baseline readings.
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
```

> [!IMPORTANT]
> **Zero-Setup Database Architecture:** You do NOT need to run database migrations, import SQLite dumps, or create tables. On first boot, `backend/app/main.py` detects if `geobreathe.db` exists. If not, it creates all tables and populates all 40 CPCB monitoring stations and 72 hours of historical hourly readings directly from [`backend/data/selected_stations.json`](../backend/data/selected_stations.json).

---

### Step 4: Frontend Setup (React 19 + Vite)

Open a **new terminal window** (keep the backend server running in the first terminal).

#### 4.1 Navigate to the Frontend Directory
```bash
cd frontend
```

#### 4.2 Verify Frontend Environment File
Check that `frontend/.env` exists. If not, copy `frontend/.env.example`:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```
**Linux / macOS:**
```bash
cp .env.example .env
```

The file contains:
```dotenv
VITE_API_URL=http://127.0.0.1:8001
```

#### 4.3 Install Dependencies
```bash
npm install
```

#### 4.4 Start the Vite Development Server
```bash
npm run dev
```

You will see:
```text
  VITE v6.x.x  ready in 240 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

Now open **`http://localhost:5173`** in your browser!

---

## 🌐 Port & Network Layout

| Service | Protocol | Local URL | Description |
| :--- | :--- | :--- | :--- |
| **Frontend UI** | HTTP | `http://localhost:5173` | React 19 Single-Page App with Dark/Light theme, Leaflet maps, and real-time dials |
| **Backend API** | HTTP | `http://127.0.0.1:8001` | FastAPI REST API Gateway |
| **Interactive Docs** | Swagger | `http://127.0.0.1:8001/docs` | OpenAPI documentation with interactive "Try It Out" test sandbox |
| **ReDoc Specs** | ReDoc | `http://127.0.0.1:8001/redoc` | Alternative clean REST endpoint documentation |
| **Health Check** | JSON | `http://127.0.0.1:8001/api/health` | System health probe (`{"status":"ok","version":"2.1.0"}`) |
| **Key Diagnostics** | JSON | `http://127.0.0.1:8001/api/debug/env` | Verifies which external keys are currently active |

---

## 🧪 Verifying the Installation & Running Tests

### 1. Test Backend Endpoints via Curl

In a terminal, run:

```bash
# 1. Health Probe
curl http://127.0.0.1:8001/api/health

# 2. Check 40 Stations
curl http://127.0.0.1:8001/api/stations

# 3. Check 72h Continuous Forecast for Punjabi Bagh (ID: 6924)
curl http://127.0.0.1:8001/api/stations/6924/forecast

# 4. Check Municipal Enforcement Ward Rankings
curl http://127.0.0.1:8001/api/v1/enforcement
```

### 2. Run Frontend Test Suite (Vitest)

In the `frontend` folder:
```bash
npm test
```
All 26 unit and component tests should pass green.

### 3. Build Frontend for Production

To test production bundling:
```bash
npm run build
```
Vite will compile and output clean distribution files to `frontend/dist` in approximately 1.5–2.0 seconds with zero lint errors.

---

## 🧭 Application Walkthrough & Key Features

Once `http://localhost:5173` is loaded:

1. **Executive Dashboard (`/dashboard`)**:
   - Interactive Leaflet map displaying 40 stations across Delhi-NCR and major metropolitan clusters.
   - Click on any station marker (e.g., *Punjabi Bagh*, *Anand Vihar*, *RK Puram*) to load real-time AQI dials, 72h continuous forecast charts, and fractional source attribution (Crustal Dust, Diesel Traffic, Stubble Smoke, Industrial Emissions).
2. **Municipal Command Center (`/command-center`)**:
   - View priority ward risk rankings computed via dynamic risk scoring.
   - Review active Stage-III GRAP directives and dispatch municipal assets (anti-smog water cannons, truck rerouting).
3. **Citizen AI Advisory (`/advisory`)**:
   - Select your vulnerability persona (General Public, Asthmatic, Elderly, Child, Outdoor Worker).
   - Chat in 6 Indian languages (Hindi, Kannada, Tamil, Marathi, Bengali, English).
   - Powered by Google Gemma 2 open model architecture with instant streaming responses.

---

## ❓ Troubleshooting & Frequently Asked Questions

### 1. `ModuleNotFoundError: No module named 'backend'`
- **Cause:** You ran `uvicorn` from inside the `backend/` folder instead of the project root.
- **Fix:** `cd` back to the repository root and run:
  ```bash
  uvicorn backend.app.main:app --host 127.0.0.1 --port 8001 --reload
  ```

### 2. Port `8001` or `5173` is already in use
- **Windows:** Check what process is listening:
  ```powershell
  netstat -ano | findstr :8001
  taskkill /F /PID <PID>
  ```
- **macOS / Linux:**
  ```bash
  lsof -i :8001
  kill -9 <PID>
  ```
- Alternatively, you can change the port for uvicorn with `--port 8002` and update `frontend/.env` to `VITE_API_URL=http://127.0.0.1:8002`.

### 3. PowerShell says `running scripts is disabled on this system`
- **Cause:** Windows default execution policy restricts PowerShell scripts.
- **Fix:** Run this command once in your current PowerShell session:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
  ```
  Then re-run `.\venv\Scripts\Activate.ps1`.

### 4. How do I reset or re-seed the SQLite database?
- Simply delete `geobreathe.db` in the repository root while the backend is stopped:
  ```powershell
  Remove-Item geobreathe.db
  ```
  When you next start the backend, it will automatically recreate the database and re-seed all 40 stations and 72-hour baselines from `backend/data/selected_stations.json`.

---

## 👥 Support & Contribution

If you experience any issues or have questions regarding problem statement PS 5 evaluation, open an issue on GitHub:
👉 **[princexpoddar/AtmosEdgeAI](https://github.com/princexpoddar/AtmosEdgeAI/issues)**
