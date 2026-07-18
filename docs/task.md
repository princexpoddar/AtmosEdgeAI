# Production Cleanup Tasks

## Phase 1: Remove Orphaned Modules
- [x] Verify frontend API calls before removing endpoints
- [ ] Delete `services/realtime_updater.py`
- [ ] Delete `services/ingestion.py` (flat legacy)
- [ ] Delete `services/enforcement.py` (flat legacy)
- [ ] Delete `services/attribution.py` (flat legacy)
- [ ] Delete `services/firms_processor.py` (flat legacy)
- [ ] Create `backend/scripts/` directory
- [ ] Move 9 root-level research scripts to `backend/scripts/`

## Phase 2: Clean endpoints.py
- [ ] Move imports to top (threading, time)
- [ ] Remove unused ML asset loading (lr_model, scalers, station_id_map, flatten_data)
- [ ] Remove legacy Ward-based endpoints
- [ ] Consolidate AQI label function

## Phase 3: Clean forecaster.py
- [ ] Remove duplicate CNNLSTMForecaster class
- [ ] Remove create_dataset_sequences() legacy function
- [ ] Clean unused imports

## Phase 4: Configuration
- [ ] Add python-dotenv, shap to requirements.txt
- [ ] Update main.py startup event to lifespan pattern

## Phase 5: Verify & Commit
- [ ] Restart backend, confirm startup
- [ ] Run endpoint health check
- [ ] Check frontend console for errors
- [ ] Git commit cleanup batch
- [ ] Generate walkthrough/docs
