# Ingestion Reliability Tasks

## Phase 1: In-Memory Health Tracking & Diagnostics
- [x] Initialize global health tracker and statistics dictionary in `cpcb.py`
- [x] Add diagnostic helper function to retrieve health parameters
- [x] Expose `/api/v1/diagnostics/providers` endpoint in `endpoints.py`

## Phase 2: Refactoring Fallback Ingestion (cpcb.py)
- [x] Remove hardcoded fallbacks (`pm25 = 45.0`, `no2 = 18.0`)
- [x] Implement parallel/concurrent fetch for Government API & OpenAQ V3 via thread pool
- [x] Add SQLite historical cache fallback (returning status `CACHED` or `STALE`)
- [x] Implement Open-Meteo Air Quality current conditions fallback (status `MODEL_ESTIMATE`)
- [x] Implement gracefully degraded fallback (status `UNAVAILABLE`)

## Phase 3: Scheduler Stability (scheduler.py)
- [x] Implement thread lock to prevent duplicate concurrent ingestion jobs
- [x] Add health-check checks to temporarily skip unhealthy providers (>=3 failures)
- [x] Log and update latency/health status records on each provider call

## Phase 4: API Endpoint Enhancement (endpoints.py)
- [x] Map provider metadata fields into `/api/stations` JSON payload
- [x] Ensure backward compatibility with forecasting & intelligence contexts

## Phase 5: Frontend Visualization (RightPanel.jsx)
- [x] Build glassmorphic station detail header card at the top of the right panel
- [x] Display Current values, Status, Source, Provider, and Last Updated/Data Age

## Phase 6: Verification
- [x] Start backend and run a manual sync to check concurrent execution
- [x] Verify that UI renders details without console errors
- [x] Git commit and push changes
