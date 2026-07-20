# Requirements Document

## Introduction

AtmosEdgeAI currently deploys a Linear Regression model (`baseline_lr.pkl`) for production AQI forecasting because the `GlobalCNNLSTMForecaster` (CNN-LSTM) underperforms every baseline — including persistence — with an overall test MAE of 0.557 vs. Linear Regression's 0.488. The root causes are data pipeline bugs, insufficient model capacity, no regularisation strategy, and absent spatial context.

This document specifies requirements for a five-phase engineering roadmap to fix the pipeline, improve the model, add spatial context, and replace the LR model in production once the improved CNN-LSTM beats the existing baseline.

## Glossary

- **DatasetBuilder**: The class in `backend/app/services/ml/dataset_builder.py` responsible for loading, splitting, scaling, and sequencing the training dataset.
- **GlobalCNNLSTMForecaster**: The PyTorch model in `backend/app/services/ml/model.py`.
- **engineer_features**: The function in `backend/app/services/ml/features.py` that computes lag and rolling-window features.
- **scaler_X**: The `StandardScaler` fitted on all 41 temporal input features including raw `pm25` and `no2`.
- **scaler_y**: The `StandardScaler` fitted exclusively on the two target columns `pm25` and `no2`.
- **seq_len**: The look-back window (number of hourly steps) fed to the model as input context.
- **Scaled Units**: Predictions and targets expressed in standard-deviation units relative to the training set distribution.
- **Unscaled Units**: Physical units — µg/m³ for PM2.5 and NO2.
- **Baseline MAE**: The Linear Regression test-set overall MAE of 0.488 in scaled units.
- **Persistence Baseline**: Naively carrying the last observed value forward; MAE = 0.510 in scaled units.
- **Spatial Neighbour Features**: Mean and standard deviation of PM2.5 and NO2 readings from geographically nearby stations, appended as additional temporal input features.
- **AQI**: Air Quality Index — a derived categorical index computed from PM2.5 and NO2 concentrations per Indian CPCB breakpoints.
- **Huber Loss**: A regression loss that is quadratic for small residuals and linear for large ones, making it more robust to outliers than MSE.
- **Temporal Attention**: A learned weighting mechanism applied to the LSTM hidden-state sequence before the dense prediction head.
- **LayerNorm**: Layer Normalisation applied to LSTM inputs or outputs to stabilise training.

---

## Requirements

### Requirement 1: Fix Target Scaler Leakage in DatasetBuilder

**User Story:** As an ML engineer, I want `pm25` and `no2` target values to be scaled by only `scaler_y` (not also by `scaler_X`), so that the model receives consistent and non-redundantly-scaled inputs and targets.

#### Acceptance Criteria

1. WHEN `DatasetBuilder.fit_scalers()` is called, THE `DatasetBuilder` SHALL fit `scaler_X` on the 41 temporal input features that **exclude** raw `pm25` and `no2` columns.
2. WHEN `DatasetBuilder.fit_scalers()` is called, THE `DatasetBuilder` SHALL fit `scaler_y` on the two raw target columns `pm25` and `no2` from the combined training split.
3. WHEN `DatasetBuilder.transform_and_sequence()` is called, THE `DatasetBuilder` SHALL apply `scaler_X` only to the 39 non-target temporal features, not to `pm25` or `no2`.
4. WHEN `DatasetBuilder.transform_and_sequence()` is called, THE `DatasetBuilder` SHALL apply `scaler_y` exclusively to the target values (`pm25[t+24]`, `pm25[t+48]`, `pm25[t+72]`, `no2[t+24]`, `no2[t+48]`, `no2[t+72]`).
5. WHEN scaled feature sequences are constructed, THE `DatasetBuilder` SHALL still include `pm25` and `no2` **scaled by `scaler_y`** as input features within the temporal sequence (at their respective column positions) so the model can observe past target values.
6. THE `DatasetBuilder` SHALL save an updated `global_scaler.pkl` containing the re-fitted `scaler_X` (39 features), `scaler_y` (2 targets), and `scaler_static` (3 static features) after any re-fit.

---

### Requirement 2: Extend Sequence Length to 72 Steps

**User Story:** As an ML engineer, I want to increase the model's input context window from 24 to 72 hours, so that the model can observe one full monsoon/winter diurnal cycle before predicting 24h–72h ahead.

#### Acceptance Criteria

1. WHEN `ml_config.json` is updated with `"seq_len": 72`, THE `MLConfig` SHALL load and propagate `seq_len=72` to `DatasetBuilder` and `GlobalCNNLSTMForecaster`.
2. WHEN `DatasetBuilder.transform_and_sequence()` is called with `seq_len=72`, THE `DatasetBuilder` SHALL produce input sequences of shape `(N, 72, feature_dim)`.
3. WHEN `DatasetBuilder.transform_and_sequence()` constructs sequences, THE `DatasetBuilder` SHALL require a minimum of `seq_len + 72` rows per station split, rejecting stations with fewer rows.
4. WHEN `engineer_features()` is called, THE `engineer_features` function SHALL compute rolling window statistics using a minimum number of periods equal to 1 (not `window`), so that early rows within the sequence are not erroneously populated with `NaN` values due to insufficient prior history.
5. WHEN `seq_len` is changed in `ml_config.json`, THE `GlobalCNNLSTMForecaster` SHALL be re-instantiated and re-trained from scratch; the system SHALL NOT attempt to load a previously-saved checkpoint with a different `seq_len`.

---

### Requirement 3: Increase Model Capacity

**User Story:** As an ML engineer, I want to increase the hidden dimension and add a temporal attention layer over LSTM outputs, so that the model has sufficient representational capacity for 40 stations with 41+ input features.

#### Acceptance Criteria

1. WHEN `ml_config.json` is updated with `"hidden_dim": 128` and `"num_lstm_layers": 3`, THE `MLConfig` SHALL load these values and pass them to `GlobalCNNLSTMForecaster`.
2. WHEN `GlobalCNNLSTMForecaster` is constructed, THE model SHALL include a temporal attention module that computes a weighted sum over all `seq_len` LSTM hidden states, replacing the current "take last hidden state only" approach.
3. WHEN the temporal attention module computes attention weights, THE module SHALL apply a softmax over the time dimension so that weights sum to 1.0 for every item in the batch.
4. WHEN `GlobalCNNLSTMForecaster` is constructed, THE model SHALL apply `LayerNorm` to the LSTM input tensor (the output of the Conv1D block) before the first LSTM layer.
5. WHEN `GlobalCNNLSTMForecaster` is constructed, THE dense prediction head SHALL accept `attention_output_dim + embedding_dim + static_dim` as input, where `attention_output_dim == hidden_dim`.
6. WHEN the forward pass is executed, THE model SHALL produce an output tensor of shape `(batch_size, 6)` with no `NaN` or `Inf` values for valid (finite) inputs.

---

### Requirement 4: Improve Training Regularisation and Loss Function

**User Story:** As an ML engineer, I want to replace MSE loss with Huber loss, add warmup to the LR schedule, and apply stronger dropout and weight decay, so that the model generalises rather than memorises training sequences.

#### Acceptance Criteria

1. WHEN `train_model()` initialises the loss function, THE `train_model` function SHALL use `torch.nn.HuberLoss` with `delta=1.0` in place of `nn.MSELoss`.
2. WHEN `train_model()` initialises the scheduler, THE `train_model` function SHALL apply a linear warmup over the first 5 epochs before handing off to `CosineAnnealingWarmRestarts`.
3. WHEN the `ml_config.json` is updated with `"dropout": 0.35` and `"weight_decay": 5e-4`, THE `MLConfig` SHALL load and apply these values.
4. WHEN training completes for at least 10 epochs, THE training loop SHALL produce a `val_loss` that does not exceed `train_loss × 1.5` at the epoch of best `val_loss`.
5. WHEN `train_model()` is called, THE training loop SHALL log `train_loss`, `val_loss`, the current learning rate, and the `val/train loss ratio` for every epoch.
6. IF `val_loss` is greater than `train_loss × 2.0` for 5 consecutive epochs starting from epoch 10, THEN THE training loop SHALL emit a WARNING log entry containing the string `"overfitting detected"`.

---

### Requirement 5: Add Spatial Neighbour Context Features

**User Story:** As an ML engineer, I want to add mean and standard deviation of PM2.5 and NO2 from the K nearest neighbouring stations as additional input features, so that the model can learn spatial pollution propagation patterns without requiring a Graph Neural Network.

#### Acceptance Criteria

1. WHEN `DatasetBuilder` is initialised, THE `DatasetBuilder` SHALL accept a `k_neighbours` parameter (default 3) specifying how many nearest stations to aggregate.
2. WHEN `DatasetBuilder.fit_scalers()` is called, THE `DatasetBuilder` SHALL compute a station-to-station Haversine distance matrix from the latitude/longitude columns and persist it in memory.
3. WHEN `DatasetBuilder.transform_and_sequence()` constructs a sequence for station `s` at time index `i`, THE `DatasetBuilder` SHALL append the mean and standard deviation of PM2.5 and NO2 across the K nearest neighbours' scaled values at the same time index as 4 additional features: `[neighbour_pm25_mean, neighbour_pm25_std, neighbour_no2_mean, neighbour_no2_std]`.
4. WHEN fewer than `k_neighbours` neighbour stations have data at a given time index, THE `DatasetBuilder` SHALL compute the aggregation over however many neighbours are available (minimum 1), without raising an error.
5. WHEN neighbour features are added, THE `temporal_dim` passed to `GlobalCNNLSTMForecaster` SHALL reflect the updated feature count (original features + 4 spatial neighbour features).
6. WHEN `get_temporal_feature_names()` is called, THE function SHALL return a list that includes `["neighbour_pm25_mean", "neighbour_pm25_std", "neighbour_no2_mean", "neighbour_no2_std"]` at the end of the feature list.

---

### Requirement 6: Achieve Performance Targets and Beat Linear Regression Baseline

**User Story:** As an ML engineer, I want the improved CNN-LSTM to achieve measurable performance targets on the held-out test set, so that there is a clear, objective criterion for replacing the Linear Regression model in production.

#### Acceptance Criteria

1. WHEN `evaluate_on_test()` is called on the improved CNN-LSTM, THE model SHALL achieve an `overall_mae` ≤ 0.45 in scaled units on the held-out test set.
2. WHEN `evaluate_on_test()` is called on the improved CNN-LSTM, THE model SHALL achieve an `overall_mae` strictly less than the Linear Regression `overall_mae` of 0.488 in scaled units.
3. WHEN `evaluate_on_test()` is called on the improved CNN-LSTM, THE model SHALL achieve a PM2.5 72h MAE ≤ 19.0 µg/m³ (unscaled) compared to the current 22.0 µg/m³.
4. WHEN `evaluate_on_test()` is called on the improved CNN-LSTM, THE model SHALL achieve a NO2 72h MAE ≤ 12.0 µg/m³ (unscaled) compared to the current 14.3 µg/m³.
5. WHEN `evaluate_on_test()` is called, THE `evaluate_on_test` function SHALL also compute and return unscaled MAE and R² for each of the 6 output horizons using `scaler_y` for inverse transformation.

---

### Requirement 7: Replace Linear Regression with CNN-LSTM in Production Inference

**User Story:** As an ML engineer, I want to swap `baseline_lr.pkl` for the improved `global_model.pth` in `inference.py` once the performance threshold is met, so that real-time forecasts use the best available model.

#### Acceptance Criteria

1. WHEN the improved CNN-LSTM achieves `overall_mae` < 0.488 in scaled units, THE `inference.py` module SHALL load `global_model.pth` and use `GlobalCNNLSTMForecaster` for production inference instead of `baseline_lr.pkl`.
2. WHEN `predict_forecast()` is called with a `df_engineered` DataFrame of at least `seq_len` steps, THE inference function SHALL scale temporal features using the updated `scaler_X` (39 features, no target leakage) and static features using `scaler_static`.
3. WHEN `predict_forecast()` produces predictions, THE function SHALL apply `inverse_scale_targets()` using `scaler_y` and clamp all outputs to ≥ 0.0.
4. WHEN `predict_forecast()` is called, THE function SHALL return a dict with keys `24`, `48`, `72`, each mapping to `{"pm25": float, "no2": float, "aqi": int}` — where the `aqi` key is a new addition (see Requirement 8).
5. IF `global_model.pth` is missing or fails to load, THEN THE `inference.py` module SHALL fall back to `baseline_lr.pkl` and log a WARNING containing `"falling back to LR baseline"`.

---

### Requirement 8: Add AQI Index as a Derived Forecast Output

**User Story:** As a frontend engineer, I want each forecast horizon to include an AQI integer value alongside PM2.5 and NO2, so that the UI can display a single actionable air quality rating without computing it client-side.

#### Acceptance Criteria

1. THE `inference.py` module SHALL implement a `compute_aqi(pm25: float, no2: float) -> int` function that returns an AQI integer in the range [0, 500] using Indian CPCB breakpoints for PM2.5 and returning the maximum of the sub-index for PM2.5 and NO2.
2. WHEN `compute_aqi()` receives `pm25 < 0` or `no2 < 0`, THE function SHALL clamp inputs to 0.0 before computing the AQI.
3. WHEN `predict_forecast()` is called, THE function SHALL call `compute_aqi(pm25, no2)` for each horizon and include the result under the `"aqi"` key in the returned dict.
4. WHEN `compute_aqi()` receives inputs that map to an AQI above 500, THE function SHALL return 500 (maximum AQI cap).
5. WHEN `compute_aqi()` receives `pm25=0.0` and `no2=0.0`, THE function SHALL return `0`.
