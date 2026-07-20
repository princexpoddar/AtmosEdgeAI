# Audit 4 — Frontend Data Flow & Placeholder Inspection

**Author / Persona**: Senior React Engineer, FastAPI Engineer, Technical Reviewer  
**Target Project**: `AtmosEdgeAI`  
**Date**: July 20, 2026  

---

## 1. Widget-to-API Mapping Catalog

| UI Page | Widget / Component | Populating API Endpoint | Data Status |
| :--- | :--- | :--- | :---: |
| **Dashboard (`/`)** | Station Directory & Map Markers | `GET /api/stations` | **Live DB Data** |
| **Dashboard (`/`)** | Real-Time Telemetry & Line Charts | `GET /api/stations/{id}/history` | **Live DB Data** |
| **Dashboard (`/`)** | 72-Hour Forecast Cards & Bounds | `GET /api/stations/{id}/forecast` | **Live ML Model Data** |
| **Dashboard (`/`)** | AI Intelligence Briefing Panel | `GET /api/v1/intelligence/{id}` | **Live Rule-Engine Data** |
| **Predictor (`/predict`)** | Station Dropdown & Predict Form | `POST /api/predict` | **Live ML Model Data** |
| **Enforcement (`/enforcement`)**| Hotspot Risk Queue & Action Cards | `GET /api/v1/enforcement` | **Live Rule-Engine Data** |
| **Analytics (`/analytics`)** | XGBoost Feature Importance Bar Chart | `GET /api/feature-importance` | ⚠️ **Hardcoded Placeholder** |
| **Analytics (`/analytics`)** | SHAP Source Breakdown Donut Chart | `GET /api/stations/{id}/explainability` | ⚠️ **Hardcoded Placeholder** |
| **Analytics (`/analytics`)** | Model Health Telemetry Gauge | `GET /api/monitoring` | ⚠️ **Hardcoded Placeholder** |

---

## 2. Placeholder Widgets & Fake Charts

1. **Feature Importance Bar Chart** on `Analytics.jsx`: Populated by `GET /api/feature-importance`, which returns a static array of 20 hardcoded XGBoost weights (`pm25_t`: 0.4852, etc.).
2. **Explainability Source Breakdown** on `Analytics.jsx`: Populated by `GET /api/stations/{id}/explainability`, which returns a static Python dictionary (`{"vehicular": 35.4, "industrial": 22.8, ...}`).
3. **Model Health Telemetry Gauge** on `Analytics.jsx`: Populated by `GET /api/monitoring`, which returns static dictionary metrics (`current_mae: 0.4880`, `prediction_drift: 0.0285`).

---

## 3. Unused & Dead Components

1. `CommandCenter.jsx`: Legacy v1.0 enforcement component file. Retained in `frontend/src/pages/`, but **never rendered** by `App.jsx` routes (superseded by `Enforcement.jsx`).
2. `WardSelector.jsx`: Legacy selector from v1.0 Ward architecture. Retained in `frontend/src/components/`, but **never imported or rendered**.

---

## 4. Unconsumed Backend API Endpoints

1. `GET /api/health`: Internal health check route. Unused by frontend.
2. `GET /api/debug/env`: Internal environment key verification route. Unused by frontend.
