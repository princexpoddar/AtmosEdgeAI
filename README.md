# 💨 AtmosEdgeAI

**Spatiotemporal Deep Learning Air Quality Forecast & Attribution Engine**

AtmosEdgeAI is an end-to-end real-time air quality intelligence platform built for urban ward-level environmental governance. It combines live sensor ingestion from certified government monitors, a PyTorch CNN-LSTM deep learning forecasting pipeline, NASA MODIS/VIIRS satellite fire detection, and a Gemini AI-powered citizen health assistant — all delivered through a glassmorphic React dashboard.

> Built for the ETAI Hackathon 2026. Covers 10 wards across **Delhi NCR** and **Bengaluru**.

---

## 🎯 Problem Being Solved

India's air quality crisis is poorly communicated to citizens and enforcement agencies at the ward level. Existing systems:

- Show city-level averages that mask hyperlocal pollution spikes
- Lack 24–72 hour ahead ward-specific AQI forecasts
- Do not attribute PM2.5 to its actual sources (traffic, crop fires, industry, dust)
- Provide no tools for enforcement officers to act on high-risk violations

AtmosEdgeAI solves all four problems in a single integrated system.

---

## ✨ Core Features

| Feature | Description |
| :--- | :--- |
| **Real-Time AQI Sync** | Pulls live PM2.5/NO₂ values from 10 certified OpenAQ V3 CAAQMS stations |
| **Deep Learning Forecast** | CNN-LSTM model predicts PM2.5, NO₂, and CPCB AQI at +24h, +48h, +72h horizons |
| **NASA Fire Attribution** | MODIS C61 + VIIRS C2 satellite crop fire data drives upwind biomass contribution |
| **Source Attribution** | Breaks PM2.5 into 5 source categories: vehicular, industrial, biomass, waste burning, dust |
| **Enforcement Queue** | Auto-generates risk-scored hotspot list for environmental inspectors |
| **Health Advisories** | Multilingual (EN/HI) real-time citizen health alerts per ward |
| **AI Chat Assistant** | Gemini 2.5 Flash-powered chatbot answering citizen queries with live AQI context |
| **CPCB AQI Standard** | All AQI sub-index computations follow official Indian CPCB PM2.5 breakpoints |
| **WAL SQLite DB** | Write-Ahead Logging enables concurrent reads during background ML training |
| **Model Cache** | 30 pre-trained `.pth` weight files and 10 `.pkl` scalers for instant inference |

---

## 🏗️ Architecture Overview

```
+---------------------------------------------+
|          React Frontend (Vite)              |
|   App.jsx  <->  FastAPI Backend (port 8000) |
+---------------------------------------------+
                      |
         +------------+------------+
         v            v            v
   OpenAQ V3    Open-Meteo    NASA FIRMS
  (Live PM2.5) (Meteorology) (Crop Fires)
         |            |            |
         +-----------++-----------+
                      v
          +--------------------+
          |  SQLite (WAL Mode) |
          |  geobreathe.db     |
          +--------------------+
                      |
         +------------+------------+
         v            v            v
   CNN-LSTM      Attribution    Advisory
  Forecaster     Engine        Generator
  (PyTorch)    (Physics+Fire) (Gemini/Rule)
         |
         v
    models/
  *.pth + *.pkl
  (weight cache)
```

---

## 🛠️ Technology Stack

### Backend
| Component | Technology |
| :--- | :--- |
| Web Framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.x |
| Database | SQLite 3 (WAL Mode, 30s busy timeout) |
| ML Framework | PyTorch (CPU) |
| ML Utilities | scikit-learn StandardScaler |
| Data Processing | pandas, NumPy |
| HTTP Client | requests |
| Geometry | Shapely |
| Serialization | Pydantic |

### Frontend
| Component | Technology |
| :--- | :--- |
| Framework | React 19 |
| Build Tool | Vite 8 |
| Styling | Vanilla CSS (glassmorphism + animations) |
| State Management | React Hooks (useState, useEffect, useRef) |
| Linter | oxlint |

### External APIs
| API | Purpose |
| :--- | :--- |
| OpenAQ V3 (api.openaq.org/v3) | Live PM2.5/NO2 from CAAQMS stations |
| Open-Meteo (archive-api.open-meteo.com) | Hourly weather: temp, humidity, wind, PBL height |
| Google Gemini 2.5 Flash | AI chat responses with ward air quality context |
| NASA FIRMS (CSV files) | Historical MODIS C61 + VIIRS C2 fire detections |

---

## 📁 Folder Structure

```
AtmosEdgeAI/
|
+-- .env                          # API keys (OPENAQ_API_KEY, NASA_FIRMS_MAP_KEY)
+-- .gitignore
+-- LICENSE                       # MIT License
+-- README.md
|
+-- backend/
|   +-- requirements.txt          # Python dependencies
|   +-- geobreathe.db             # SQLite database (WAL mode, ~30 MB)
|   +-- seed_2years.py            # One-time 2-year historical data seeding script
|   +-- download_openaq.py        # Historical OpenAQ batch downloader
|   +-- download_delhi_pusa.py    # Delhi Pusa IMD data downloader
|   |
|   +-- data/
|   |   +-- firms/                # NASA MODIS/VIIRS fire CSV files (4 files, 356k records)
|   |   +-- openaq/               # Downloaded historical OpenAQ CSVs (.csv.gz)
|   |   +-- delhi_pusa_imd_2024-25.csv  # IMD Delhi ground truth data
|   |
|   +-- app/
|       +-- main.py               # FastAPI app entry point + CORS middleware
|       |
|       +-- api/
|       |   +-- endpoints.py      # All REST API route handlers (11 endpoints)
|       |
|       +-- core/
|       |   +-- database.py       # SQLAlchemy models, WAL engine, SessionLocal
|       |
|       +-- services/
|           +-- ingestion.py      # Open-Meteo weather fetcher + stagnation index
|           +-- realtime_updater.py  # OpenAQ V3 sync orchestrator
|           +-- forecaster.py     # CNN-LSTM model definition, training, cache, inference
|           +-- firms_processor.py   # NASA FIRMS loader + upwind fire engine (singleton)
|           +-- attribution.py    # PM2.5 5-source attribution model
|           +-- enforcement.py    # Enforcement hotspot risk scoring
|           +-- advisory.py       # Health advisory generator + Gemini 2.5 Flash chat
|
+-- frontend/
|   +-- index.html
|   +-- package.json
|   +-- vite.config.js
|   +-- src/
|       +-- main.jsx              # React entry point
|       +-- App.jsx               # Single-page dashboard (all UI components inline)
|       +-- App.css               # Glassmorphic design system + animations
|       +-- index.css             # Global reset and font imports
|
+-- models/
    +-- model_ward_{1-10}_lead_{24,48,72}.pth   # 30 cached PyTorch model weights
    +-- scaler_ward_{1-10}.pkl                  # 10 cached StandardScaler objects
```

---

## ⚙️ Installation

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- pip

### 1. Clone the Repository

```bash
git clone https://github.com/princexpoddar/AtmosEdgeAI.git
cd AtmosEdgeAI
```

### 2. Set Up Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 3. Install Backend Dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Install Frontend Dependencies

```bash
cd frontend && npm install && cd ..
```

### 5. Configure Environment Variables

Create `.env` at the project root:

```env
OPENAQ_API_KEY=your_openaq_api_key_here
NASA_FIRMS_MAP_KEY=your_nasa_firms_key_here
```

- OpenAQ key: https://openaq.org
- FIRMS key: https://firms.modaps.eosdis.nasa.gov/api/area/

---

## 🚀 Running Locally

### Step 1: Seed the Database (run once)

```bash
./venv/bin/python backend/seed_2years.py
```

> Takes 10-20 minutes. Populates 2 years of hourly readings for all 10 wards.

### Step 2: Pre-train CNN-LSTM Models (run once)

```bash
./venv/bin/python -c "
from backend.app.core.database import SessionLocal
from backend.app.services.forecaster import generate_forecasts_for_all
db = SessionLocal()
generate_forecasts_for_all(db, retrain=True)
"
```

> Takes ~20-25 minutes on CPU. Saves 30 model files + 10 scalers to models/

### Step 3: Start Backend

```bash
./venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs

### Step 4: Start Frontend

```bash
cd frontend && npm run dev
```

Dashboard: http://localhost:5173

---

## 🌐 Application Flow

```
User Opens Dashboard (http://localhost:5173)
       |
       v
React GET /api/cities
       |
       v
User selects City -> GET /api/wards?city_id=N
                  -> GET /api/enforcement?city_id=N
       |
       v
User selects Ward -> parallel:
  +-- GET /api/aqi/realtime?city_id=N   (latest reading for the ward)
  +-- GET /api/forecast?ward_id=N       (CNN-LSTM +24h/+48h/+72h predictions)
  +-- GET /api/attribution?ward_id=N    (5-source PM2.5 breakdown)
  +-- GET /api/advisory?ward_id=N       (EN/HI health alert)
       |
       v
User clicks "Sync Live Data"
       |
       v
POST /api/aqi/sync ->
  +-- fetch_openaq_v3_latest()          (live PM2.5/NO2 per station)
  +-- fetch_openmeteo_history()         (hourly weather)
  +-- upsert Reading rows in SQLite
  +-- generate_forecasts_for_all()      (load cached models, run inference)
  +-- run_attribution_for_all()         (recompute 5-source breakdown)
       |
       v
Frontend: green success toast -> 2.2s delay -> window.location.reload()
```

---

## 📡 API Endpoints

| Method | URL | Description |
| :--- | :--- | :--- |
| GET | /api/cities | List all cities |
| GET | /api/wards?city_id=N | List wards for a city |
| GET | /api/aqi/realtime?city_id=N | Latest readings for all city wards |
| GET | /api/aqi/history?ward_id=N&hours=24 | Historical readings (last N hours) |
| POST | /api/aqi/sync | Trigger full live sync pipeline |
| GET | /api/forecast?ward_id=N | CNN-LSTM +24h/+48h/+72h forecast |
| GET | /api/attribution?ward_id=N | PM2.5 source attribution breakdown |
| GET | /api/enforcement?city_id=N | Enforcement hotspot queue |
| POST | /api/enforcement/inspect/{id} | Update enforcement target status |
| GET | /api/advisory?ward_id=N | Health advisory (EN + HI) |
| POST | /api/advisory/chat | AI chatbot with Gemini/fallback |

---

## 🗄️ Database Schema

SQLite database: `backend/geobreathe.db` (WAL mode, ~30 MB)

### cities
`id | name | latitude | longitude | ncap_target`

### wards
`id | city_id | name | latitude | longitude | population | boundary_geojson`

### readings
`id | ward_id | timestamp | pm25 | pm10 | no2 | so2 | o3 | co | temp | humidity | wind_speed | wind_deg | stagnation`

### forecasts
`id | ward_id | timestamp | forecast_time | predicted_pm25 | predicted_no2 | predicted_aqi`

### attributions
`id | ward_id | timestamp | vehicular_pct | industrial_pct | biomass_pct | waste_burning_pct | dust_pct | confidence`

### enforcement_targets
`id | ward_id | name | type | latitude | longitude | risk_score | evidence_packet | status | created_at`

### advisories
`id | ward_id | timestamp | level | message_en | message_hi | message_local`

---

## 🔬 CPCB AQI Breakpoints (PM2.5)

| PM2.5 (µg/m³) | AQI | Category |
| :---: | :---: | :--- |
| 0–30 | 0–50 | Good |
| 30–60 | 50–100 | Satisfactory |
| 60–90 | 100–200 | Moderate |
| 90–120 | 200–300 | Poor |
| 120–250 | 300–400 | Very Poor |
| >250 | 400–500 | Severe |

---

## 🗺️ Ward-to-Station Mapping

| Ward | City | OpenAQ V3 ID | CAAQMS Station |
| :--- | :--- | :---: | :--- |
| East Delhi | Delhi NCR | 235 | Anand Vihar - DPCC |
| Dwarka | Delhi NCR | 5622 | NSIT Dwarka - CPCB |
| Connaught Place | Delhi NCR | 5613 | ITO - CPCB |
| Okhla Industrial Area | Delhi NCR | 5586 | Sirifort - CPCB |
| Rohini | Delhi NCR | 5610 | North Campus DU - IMD |
| Whitefield | Bengaluru | 3409312 | BWSSB Kadabesanahalli - CPCB |
| Koramangala | Bengaluru | 5548 | BTM Layout - CPCB |
| Indiranagar | Bengaluru | 5574 | City Railway Station - KSPCB |
| Electronic City | Bengaluru | 6973 | Jayanagar 5th Block - KSPCB |
| Peenya Industrial Area | Bengaluru | 5644 | Sanegurava Halli - KSPCB |

---

## 🚀 Performance Optimizations

- **100-record inference slice:** Sync queries only the last 100 readings per ward, cutting sync time from 19 min to 25 sec
- **Model weight cache:** 30 `.pth` files loaded from disk; no retraining on sync
- **Diurnal physics fallback:** Sinusoidal prediction prevents thread blocking if cache is missing
- **WAL mode SQLite:** Concurrent reads + writes without lock errors during background training
- **FIRMS singleton:** 356,872 fire records loaded once into memory, never reloaded
- **NumPy vectorization:** Haversine + bearing computed with array operations (100x vs loops)
- **Bulk DB inserts:** `db.bulk_save_objects()` for batch reading inserts

---

## 🔐 Security Notes

- Gemini API key stored **client-side only** in `localStorage`, never sent to backend
- OpenAQ key stored in `.env`, loaded at runtime, excluded from git
- CORS currently set to `allow_origins=["*"]` — restrict in production
- No authentication layer — add JWT for production enforcement officer endpoints

---

## ⚠️ Known Limitations

- SQLite unsuitable for multi-worker/horizontal production scaling
- FIRMS data is static CSV; not auto-refreshed when new fires are detected
- No real-time WebSocket streaming; users must manually click Sync
- `--reload` mode in Uvicorn can cause SQLite locks during active training

---

## 🔮 Future Improvements

- Migrate to PostgreSQL for production scaling
- JWT authentication for enforcement endpoints
- Nightly cron job to auto-download latest FIRMS fire data
- WebSocket real-time AQI streaming to frontend
- Expand to tier-2 Indian cities
- PM10 and SO2 model predictions
- Mobile PWA for citizen use

---

## 📄 License

MIT License © 2026 Prabal Poddar
