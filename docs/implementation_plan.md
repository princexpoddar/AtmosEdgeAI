# AtmosEdgeAI Ingestion Reliability & Standardization Plan

## Summary

This plan details improvements to the backend live sync ingestion architecture and the frontend status display without changing the forecasting pipeline, intelligence engine, or SQLite database schema.

---

## User Review Required

> [!IMPORTANT]
> **No Database Schema Changes**: All provider health stats and sync metadata will be managed in-memory in `cpcb.py` and combined dynamically on API request to avoid complex migration requirements.
> **Parallel Ingestion**: Government bulk queries and OpenAQ V3 calls will run concurrently to minimize sync latency.

---

## Proposed Changes

### Ingestion Subpackage

#### [MODIFY] [cpcb.py](file:///c:/Users/praba/OneDrive/Desktop/AtmosEdgeAI/backend/app/services/ingestion/cpcb.py)
* **Remove Hardcoded Defaults**: Remove `pm25 = 45.0` and `no2 = 18.0` tertiary fallback.
* **Implement Health Tracking**: Declare `_provider_health` dictionary tracking latencies, consecutive failures, status, last success, and last failure times for:
  - `DATA_GOV_IN` (bulk cache fetch)
  - `OPENAQ` (station-specific fallback)
  - `OPEN_METEO` (air quality estimator)
* **Concurrent Sync Fetches**: Run CPCB bulk fetch and OpenAQ V3 fetch in parallel using a `ThreadPoolExecutor` if the memory cache is missed. Use the first successful response that contains non-null pollutant values.
* **SQLite Fallback**: If both live providers fail, query the database for the most recent reading for that station. If found, return `source = "SQLITE_CACHE"`, `provider = "SQLITE"`, and `quality_status = "CACHED"` (or `"STALE"` if > 2 hours old).
* **Open-Meteo Air Quality Fallback**: If SQLite contains no historical records, call the Open-Meteo Air Quality API:
  `https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=pm2_5,nitrogen_dioxide`
  Mark it as `source = "OPEN_METEO"`, `provider = "OPEN_METEO"`, and `quality_status = "MODEL_ESTIMATE"`.
* **Data Unavailable**: If all steps fail, return `quality_status = "UNAVAILABLE"`, `source = "UNAVAILABLE"`, `provider = "NONE"`.

#### [MODIFY] [scheduler.py](file:///c:/Users/praba/OneDrive/Desktop/AtmosEdgeAI/backend/app/services/ingestion/scheduler.py)
* **Prevent Duplicate Syncs**: Add a thread-safe `_ingestion_in_progress` lock/boolean to drop duplicate manual/automatic sync jobs while a sync is running.
* **Skipping Unhealthy Providers**: Skip calling providers marked as `UNHEALTHY` (>= 3 consecutive failures) in health tracking.

---

### Backend API Endpoints

#### [MODIFY] [endpoints.py](file:///c:/Users/praba/OneDrive/Desktop/AtmosEdgeAI/backend/app/api/endpoints.py)
* **Update `/api/stations`**: Merge provider metadata (`source`, `provider`, `quality_status`, `last_updated`, `data_age_minutes`) into each station's returned dictionary.
* **Add `/api/v1/diagnostics/providers`**: Expose provider health diagnostics in a normalized JSON format.

---

### Frontend Components

#### [MODIFY] [RightPanel.jsx](file:///c:/Users/praba/OneDrive/Desktop/AtmosEdgeAI/frontend/src/components/layout/RightPanel.jsx)
* **Add Station Detail Header**: Render a new header card at the top of the right panel showing:
  - Station name and location
  - Current pollutant values: PM2.5, NO₂, Temp, Humidity, Wind Speed
  - Detailed status badge showing Source, Provider, and Quality Status (`Live Observation`, `Cached Observation`, `Model Estimate`, `Stale Data`, `Data Unavailable`)
  - Last updated and data age information.

#### [MODIFY] [Navbar.jsx](file:///c:/Users/praba/OneDrive/Desktop/AtmosEdgeAI/frontend/src/components/layout/Navbar.jsx)
* Render the diagnostics modal link if required or link to diagnostic endpoints.

---

## Verification Plan

### Automated Tests
* Run a verification script that disables mock internet connection (causing timeouts) and asserts that the API returns SQLite records (CACHED/STALE) or Open-Meteo records (MODEL_ESTIMATE) with proper metadata fields.

### Manual Verification
* Navigate to the dashboard.
* Verify the top header of the right panel correctly updates as stations are selected.
* Trigger a Sync and monitor the log for parallel task execution and health updates.
