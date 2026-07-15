# Task Board

- `[x]` Install requirements and database changes
  - `[x]` Add `torch` to `backend/requirements.txt` and install dependencies
  - `[x]` Add `predicted_no2` column to `Forecast` model in `backend/app/core/database.py` and refresh database tables
- `[x]` Implement NASA FIRMS processing service
  - `[x]` Create `backend/app/services/firms_processor.py` to filter/index MODIS & VIIRS fire data and compute the Upwind Fire Transport Index (UFTI)
- `[x]` Refactor source attribution engine
  - `[x]` Refactor `backend/app/services/attribution.py` to use the dynamic upwind fire index for biomass burning calculations
- `[x]` Implement PyTorch spatiotemporal CNN-LSTM forecaster
  - `[x]` Implement `CNNLSTMForecaster` model in `backend/app/services/forecaster.py`
  - `[x]` Implement training loop and save predictions (PM2.5, NO2, AQI) to SQLite database
- `[x]` Update API endpoints
  - `[x]` Update `/forecast` in `backend/app/api/endpoints.py` to serialize `predicted_no2`
- `[x]` Verify changes
  - `[x]` Create and run verification script `backend/app/tests/verify_pipeline.py` to check model training and forecasting metrics (RMSE, $R^2$)
