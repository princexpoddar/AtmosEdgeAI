# Production Cleanup Tasks

## Phase 1: Remove Orphaned Modules
- [x] Verify frontend API calls before removing endpoints
- [x] Delete `services/realtime_updater.py`
- [x] Delete `services/ingestion.py` (flat legacy)
- [x] Delete `services/enforcement.py` (flat legacy)
- [x] Delete `services/attribution.py` (flat legacy)
- [x] Delete `services/firms_processor.py` (flat legacy)
- [x] Create `backend/scripts/` directory
- [x] Move 9 root-level research scripts to `backend/scripts/`

## Phase 2: Clean endpoints.py
- [x] Move imports to top (threading, time)
- [x] Remove unused ML asset loading (lr_model, scalers, station_id_map, flatten_data)
- [x] Remove legacy Ward-based endpoints
- [x] Consolidate AQI label function

## Phase 3: Clean forecaster.py
- [x] Remove duplicate CNNLSTMForecaster class
- [x] Remove create_dataset_sequences() legacy function
- [x] Clean unused imports

## Phase 4: Configuration
- [x] Add python-dotenv, shap to requirements.txt
- [x] Update main.py startup event to lifespan pattern

## Phase 5: Verify & Commit
- [x] Restart backend, confirm startup
- [x] Run endpoint health check
- [x] Check frontend console for errors
- [x] Git commit cleanup batch
- [x] Generate walkthrough/docs
