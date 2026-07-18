# AtmosEdgeAI Production Cleanup — Implementation Plan

## Summary

A full audit of the repository reveals **7 categories of technical debt** requiring cleanup across backend, frontend, ML pipeline, and configuration. All changes preserve existing functionality.

---

## Audit Findings

### 🔴 CRITICAL: Orphaned Modules (No Active Callers)

| File | Issue |
|------|-------|
| `backend/app/services/realtime_updater.py` | Imports `seed_2years.generate_modeled_pm25` which no longer exists at that path. Never called from any endpoint or scheduler. |
| `backend/app/services/ingestion.py` | Top-level flat module. Its `calculate_stagnation` + `fetch_openmeteo_history` are DUPLICATED in `ingestion/openmeteo.py` and `data_pipeline/`. No endpoint imports it. |
| `backend/app/services/enforcement.py` | Top-level flat module. Provides `prioritize_enforcements()` on Ward/Reading tables (legacy). Never called from endpoints. Active enforcement is in `services/enforcement/pipeline.py`. |
| `backend/app/services/attribution.py` | Top-level flat module. 6563 bytes. No active endpoint imports it. |
| `backend/app/services/firms_processor.py` | 8048 bytes. Not imported by any active code. |
| `backend/app/services/data_pipeline/` | Entire directory (7 files). Used only by `seed_2years.py` (one-time historical seeder) and `forecaster.py`'s retrain path. **The retrain path is never triggered from any endpoint.** |

### 🟠 HIGH: Duplicate / Legacy ML Code

| Issue | Location |
|-------|----------|
| `CNNLSTMForecaster` class redefined in `forecaster.py` | Duplicate of `services/ml/model.py:GlobalCNNLSTMForecaster`. The `global_model.pth` is the production model and uses `GlobalCNNLSTMForecaster`. |
| `create_dataset_sequences()` in `forecaster.py` L77 | "Legacy sliding window" — never used in production inference path |
| `flatten_data()` in `endpoints.py` L24 | Defined but never called anywhere in endpoints.py |
| `lr_model`, `scaler_X`, `scaler_y`, `scaler_static` loaded at module level L35-51 in `endpoints.py` | These variables are loaded but **never used** — the actual inference uses `predict_forecast()` from `services/forecasting/inference.py` which loads its own scaler |
| `get_aqi_label_cpcb()` defined in `endpoints.py` L56 AND same function `get_aqi_category()` in `advisory.py` | Two functions doing same thing with slightly different names |
| `station_id_map` loaded at module level in `endpoints.py` | Loaded but never referenced |
| `generate_forecasts_for_all()` in `forecaster.py` | 200+ line function for full retrain+inference, never called from any endpoint; only the fast inference `predict_forecast()` is called |

### 🟠 HIGH: Legacy Root-level Script Files (Backend Root)

| File | Purpose | Status |
|------|---------|--------|
| `backend/seed_2years.py` | One-time 2-year historical seeder | DONE — already ran |
| `backend/data_quality_report.py` | Analysis script | One-time use |
| `backend/feasibility_study.py` | Research analysis | One-time use |
| `backend/run_analysis.py` | Evaluation script | One-time use |
| `backend/run_evaluation_and_viz.py` | Evaluation + plots | One-time use |
| `backend/run_selection.py` | Model selection | One-time use |
| `backend/download_firms.py` | One-time NASA FIRMS download | Done |
| `backend/download_openaq.py` | One-time OpenAQ download | Done |
| `backend/download_delhi_pusa.py` | One-time download | Done |

These are **one-time research scripts** — they should be moved to `scripts/` rather than cluttering the backend root.

### 🟡 MEDIUM: API Inconsistencies

| Issue | Detail |
|-------|--------|
| Mixed versioning | Some endpoints are `/api/v1/intelligence/` while others are unversioned `/api/predict`, `/api/stations`. No consistent versioning. |
| `/api/aqi/realtime` and `/api/aqi/history` | Use legacy Ward/Reading tables, never called by current frontend |
| `/api/forecast` | Uses legacy Ward/Forecast table, never called by current frontend |
| `/api/attribution` | Uses legacy Attribution table, never called by current frontend |
| `/api/advisory` | Uses legacy Advisory table, never called by current frontend |
| `/api/enforcement` | OLD enforcement using Ward/EnforcementTarget, duplicated by `/api/v1/enforcement` |
| `import threading; import time as _time` in endpoints.py L556 | Inline imports mid-file — should be at top |
| `flatten_data()` never used | Dead code in endpoints.py |

### 🟡 MEDIUM: Frontend Issues

| Issue | Detail |
|-------|--------|
| `getFeatureImportance` imported in `api.js` but only used in Explainability.jsx — OK |
| `getMonitoring` called but monitoring state used only in header badge — minor |
| Inline `import threading` mid-file in endpoints.py | Should be at top |
| `fmt()` helper defined but barely used in App.jsx | Could be removed |

### 🟢 LOW: Code Quality

| Issue | Location |
|-------|----------|
| `print()` statements in scheduler.py and endpoints.py | Should be `logger.info/warning` |
| `@app.on_event("startup")` deprecated in FastAPI | Should use `lifespan` context manager |
| `declarative_base()` deprecated in SQLAlchemy 2.x | Should use `DeclarativeBase` |
| Missing type hints on many endpoint functions | |
| `pickle` imported in endpoints.py but unused after ML model variables removed | |
| `import numpy as np`, `import pandas as pd` in endpoints.py used only in fallback | |

---

## Proposed Changes

### Phase 1: Remove Dead Code / Orphaned Modules

#### [DELETE] `backend/app/services/realtime_updater.py`
Never imported by any endpoint or scheduler. Has broken import (`seed_2years.generate_modeled_pm25`).

#### [DELETE] `backend/app/services/ingestion.py`
Orphaned flat module. Its `calculate_stagnation` is duplicated in `data_pipeline/preprocessor.py`.

#### [DELETE] `backend/app/services/enforcement.py`
Orphaned flat module. Active enforcement is in `services/enforcement/pipeline.py`.

#### [DELETE] `backend/app/services/attribution.py`
Orphaned flat module. Attribution logic is in `services/intelligence/source_attribution.py`.

#### [DELETE] `backend/app/services/firms_processor.py`
Orphaned flat module. FIRMS data is handled by `services/ingestion/firms.py`.

#### [MOVE] `backend/*.py` research scripts → `backend/scripts/`
Move `seed_2years.py`, `data_quality_report.py`, `feasibility_study.py`, `run_analysis.py`, `run_evaluation_and_viz.py`, `run_selection.py`, `download_firms.py`, `download_openaq.py`, `download_delhi_pusa.py`.

---

### Phase 2: Clean endpoints.py

#### Remove unused ML asset loading (L31-51)
`lr_model`, `scaler_X`, `scaler_y`, `scaler_static`, `station_id_map` loaded at module level but never used.

#### Remove `flatten_data()` (L24-27)
Dead code — never called.

#### Move `import threading; import time as _time` to top of file

#### Remove unused legacy endpoints (L414-543)
- `/api/aqi/realtime` — legacy Ward-based, not called by frontend
- `/api/aqi/history` — legacy Ward-based, not called by frontend
- `/api/forecast` — legacy Ward-based forecast, not called by frontend
- `/api/attribution` — legacy Attribution table, not called by frontend
- `/api/advisory` — legacy Advisory table, not called by frontend
- `/api/advisory/chat` — ChatRequest model and advisory_chat endpoint
- `/api/enforcement` (old Ward-based one) — duplicated by `/api/v1/enforcement`
- `/api/enforcement/inspect/{target_id}` — operates on old EnforcementTarget table

> [!IMPORTANT]  
> Before removing, I'll verify these are truly unused by checking frontend API calls.

#### Consolidate `get_aqi_label_cpcb()` → single function

---

### Phase 3: Clean forecaster.py

#### Remove `CNNLSTMForecaster` class (L32-58)
Duplicate of `services/ml/model.py:GlobalCNNLSTMForecaster`. Remove and import from canonical location.

#### Remove `create_dataset_sequences()` (L77-89)
Never used in any active code path.

#### Remove `generate_forecasts_for_all()` retrain code path
The retrain path is never triggered from any endpoint. Keep only the inference path.

---

### Phase 4: requirements.txt

Add missing `python-dotenv` and `shap` (used in Explainability.jsx backend).

---

### Phase 5: main.py

Update deprecated `@app.on_event("startup")` → lifespan context manager.

---

## Verification Plan

- Backend starts without import errors
- `/api/stations` returns data
- `/api/stations/{id}/forecast` returns forecasts
- `/api/v1/intelligence/{id}` returns intelligence
- `/api/v1/enforcement` returns enforcement data
- Frontend dashboard loads with no console errors
- All API calls in `services/api.js` get 200 responses

## Open Questions

1. Should legacy Ward-based endpoints be kept for backward compatibility or removed? (My recommendation: remove — they're never called by the frontend)
2. Should `backend/scripts/` be gitignored or kept tracked?
3. Should `data_pipeline/` directory be removed entirely or kept for potential future retraining?
