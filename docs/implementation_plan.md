# Data Ingestion Analysis and Preprocessing/Model Training Plan

This document outlines a complete check of the data currently available in the project, an evaluation of its sufficiency, and a detailed implementation plan to design features, clean the datasets, and train the advanced forecasting and attribution models matching the project's PDF architecture.

---

## 📊 Data Sufficiency & Volume Check

We verified the database and satellite fire files. We have substantial, high-quality data spanning the exact same **2-year window (July 15, 2024 – July 15, 2026)**:

| Dataset | Volume / Record Count | Coverage Period | Spatial Boundaries |
| :--- | :--- | :--- | :--- |
| **Meteorological Data** (Open-Meteo ERA5) | **175,440** hourly rows | 2024-07-15 to 2026-07-15 | All 10 wards in Delhi & Bengaluru |
| **Ground Air Quality** (OpenAQ Local) | **46,861** ground readings | 2024-01-01 to 2026-07-11 | Bengaluru (`8180`, `8161`, `8185`, `8160`) |
| **Ground Air Quality** (Pusa IMD Delhi) | **70,177** ground readings | 2024-01-01 to 2025-12-31 | Delhi NCR (`site_107` Pusa) |
| **NASA FIRMS MODIS** (M-C61 Standard + NRT) | **183,695** fire detections | 2024-07-15 to 2026-07-15 | India-wide ($8^\circ\text{N}$ to $34.7^\circ\text{N}$) |
| **NASA FIRMS VIIRS** (SV-C2 Standard + NRT) | **1,267,715** fire detections | 2024-07-16 to 2026-07-10 | India-wide ($8^\circ\text{N}$ to $34.7^\circ\text{N}$) |

### Sufficiency Verdict
> [!TIP]
> **The dataset is highly sufficient.** The spatial overlap covers all of India (specifically targeting the coordinates of Delhi and Bengaluru), and the temporal overlap gives us 2 full years of continuous meteorological, satellite-fire, and ground-level measurements. This is perfect for training robust seasonal models and predicting spatial-temporal pollution transport.

---

## 🛠️ Proposed Preprocessing & Feature Engineering

### 1. NASA FIRMS Data Cleaning and Indexing
* **Confidence Filtering**: 
  * For **VIIRS**: Exclude low confidence (`confidence == 'l'`). Retain only nominal (`n`) and high (`h`) confidence points.
  * For **MODIS**: Retain entries with `confidence >= 50`.
* **Spatial Partitioning**:
  * Set a spatial search radius of **600 km** around Delhi (capturing crop fires/stubble burning in Punjab/Haryana) and **150 km** around Bengaluru.
* **Upwind Fire Transport Index (UFTI)**:
  * For each hour, compute a dynamic index representing active fires upwind of each ward:
    $$\text{UFTI} = \sum_{\text{fire } i} \frac{\text{FRP}_i}{\text{Distance}_i^2} \times \cos(\Delta\theta_i)^2$$
    Where $\text{FRP}_i$ is Fire Radiative Power (intensity), $\text{Distance}_i$ is distance to ward, and $\Delta\theta_i$ is the angular difference between the current wind direction and the bearing from the ward to the fire (active only when the fire is upwind: $\Delta\theta_i < 90^\circ$).

### 2. Air Quality Mapping & Alignment
* **Bengaluru Wards**: Integrated Ground PM2.5 measurements from local OpenAQ files.
* **Delhi NCR Wards**: Integrate Pusa IMD Delhi Ground Dataset (aggregated to hourly intervals) and use the weather-diurnal proxy model only to fill the remaining 2026 months where ground data is missing, creating a highly realistic 2-year hybrid record.
* **Lag Features**: Create lagged inputs for the deep learning models (e.g., $t-1$, $t-2$, $t-24$ hour readings) to provide memory of recent trends.

---

## 🤖 Proposed Changes & Architectural Enhancements

We will implement a deep spatiotemporal neural network matching the CNN-LSTM architecture described in the project PDF, expand database columns, and refactor the attribution calculations.

### Ingestion Layer

#### [MODIFY] [requirements.txt](file:///c:/Users/praba/OneDrive/Desktop/AtmosEdgeAI/backend/requirements.txt)
* Add `torch` (PyTorch) to the python package dependencies list.

#### [MODIFY] [database.py](file:///c:/Users/praba/OneDrive/Desktop/AtmosEdgeAI/backend/app/core/database.py)
* Add `predicted_no2 = Column(Float)` to the SQLite `Forecast` model.

### Data Layer

#### [NEW] [firms_processor.py](file:///c:/Users/praba/OneDrive/Desktop/AtmosEdgeAI/backend/app/services/firms_processor.py)
* Parse the raw FIRMS csv datasets, perform confidence and spatial bounds filtering, and expose an efficient lookup for hourly upwind fire statistics (cumulative counts, total FRP, and bearing).

### Services Layer

#### [MODIFY] [forecaster.py](file:///c:/Users/praba/OneDrive/Desktop/AtmosEdgeAI/backend/app/services/forecaster.py)
* Replace `RandomForestRegressor` with a PyTorch **CNN-LSTM spatiotemporal model** (`CNNLSTMForecaster`):
  * **Input Features**: `[pm25_now, pm25_lag_1, pm25_lag_24, target_temp, target_humidity, target_wind_speed, target_stagnation, upwind_fire_intensity, hour, dayofweek]`
  * **Architecture**: 
    1. `Conv1d` layer (extracts local temporal patterns from sliding window of past 24 hours).
    2. `LSTM` layer (models sequence time-dependency).
    3. `Linear` fully connected head outputs.
  * **Targets (Outputs)**: Multi-horizon predictions (24h, 48h, and 72h lead times) for both `PM2.5` and `NO2`.
  * **AQI Mapping**: Compute overall CPCB AQI based on the predicted pollutant levels.

#### [MODIFY] [attribution.py](file:///c:/Users/praba/OneDrive/Desktop/AtmosEdgeAI/backend/app/services/attribution.py)
* Replace the hardcoded `season_factor` for biomass burning with a real-time computation using the active `Upwind Fire Transport Index (UFTI)`. This will dynamically attribute high PM2.5 to crop fires during intensive stubble burning events and vehicular/industrial sources during clean periods.

### API Layer

#### [MODIFY] [endpoints.py](file:///c:/Users/praba/OneDrive/Desktop/AtmosEdgeAI/backend/app/api/endpoints.py)
* Update the `/forecast` endpoint serialization to include `"predicted_no2": f.predicted_no2` in the response payload.

---

## 🧪 Verification Plan

### Automated Tests
* We will write a validation script to train models and test forecasting accuracy:
  ```powershell
  $env:PYTHONPATH="c:\Users\praba\OneDrive\Desktop\AtmosEdgeAI"; .\venv\Scripts\python.exe backend/app/tests/verify_pipeline.py
  ```
* Output the **Root Mean Squared Error (RMSE)** and **R-squared ($R^2$)** metrics for 24h, 48h, and 72h predictions to confirm the accuracy improvement after incorporating FIRMS data and PyTorch CNN-LSTM modeling.

### Manual Verification
* Run the backend and verify on the frontend dashboard that:
  1. The spatiotemporal maps show actual hotspot attribution.
  2. The forecast graphs reflect changes corresponding to simulated wind vectors and fire events.
