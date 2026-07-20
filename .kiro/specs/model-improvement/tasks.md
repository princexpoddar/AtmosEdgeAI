# Implementation Plan: Model Improvement

## Overview

Five-phase improvement to the AtmosEdgeAI ML pipeline. Phases must be applied in order — each phase's code must be consistent with the next before training is run.

## Tasks

- [-] 1. Fix feature engineering and expand feature set
  - [x] 1.1 Update `engineer_features()` in `features.py` to add `min_periods=1` to all rolling window calls and add the 5 new meteorological features (`pbl_height`, `dew_point`, `solar_radiation`, `wind_u`, `wind_v`) if present in the DataFrame
    - _Requirements: 2.4_
  - [x] 1.2 Update `get_temporal_feature_names()` to return 46 features (41 original + 5 new)
    - _Requirements: 2.1_
  - [x] 1.3 Add `get_input_feature_names()` (44 features, excludes raw `pm25`/`no2`) and `TARGET_COLS` constant
    - _Requirements: 1.1, 1.3_
  - [ ]* 1.4 Write property test for rolling features — for any DataFrame with ≥1 row, `engineer_features()` must produce no NaN in roll columns
    - **Property 10: Rolling features contain no NaN after min_periods=1 fix**
    - **Validates: Requirements 2.4**

- [x] 2. Update `ml_config.json` and `MLConfig`
  - [x] 2.1 Update `ml_config.json` training block: `seq_len=72`, `hidden_dim=128`, `num_lstm_layers=3`, `dropout=0.35`, `weight_decay=5e-4`, `batch_size=256`, `epochs=150`, `patience=25`, `warmup_epochs=5`, `huber_delta=1.0`, `k_neighbours=3`
    - _Requirements: 2.1, 3.1, 4.3_
  - [x] 2.2 Update `MLConfig.load_config()` to parse `warmup_epochs`, `huber_delta`, and `k_neighbours`
    - _Requirements: 4.2, 4.3_

- [-] 3. Fix scaler leakage and extend sequences in `dataset_builder.py`
  - [x] 3.1 Update `fit_scalers()` to fit `scaler_X` on 44 input features (excluding raw `pm25`/`no2`) and fit `scaler_y` on `["pm25", "no2"]`
    - _Requirements: 1.1, 1.2_
  - [x] 3.2 Update `transform_and_sequence()` to scale input features with `scaler_X`, scale `pm25`/`no2` sequence values with `scaler_y`, assemble the 46-column full sequence, and use `seq_len=72`
    - _Requirements: 1.3, 1.4, 1.5, 2.2_
  - [x] 3.3 Update `DatasetBuilder.__init__()` to accept `k_neighbours=3` parameter and compute Haversine distance matrix; inject 4 spatial neighbour features (`neighbour_pm25_mean`, `neighbour_pm25_std`, `neighbour_no2_mean`, `neighbour_no2_std`) per timestep
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  - [ ]* 3.4 Write property test — for any station split with ≥ `seq_len + 72` rows, `transform_and_sequence()` must return `X_temporal.shape == (N, 72, feature_dim)` and `y.shape == (N, 6)`
    - **Property 2: Sequence shape invariant**
    - **Validates: Requirements 2.2, 5.5**
  - [ ]* 3.5 Write property test — scaler separation: for any sample, `seq_x[:, -2]` (pm25 column) equals `(raw_pm25 - scaler_y.mean_[0]) / scaler_y.scale_[0]` within 1e-5
    - **Property 1: Scaler separation — target columns not double-scaled**
    - **Validates: Requirements 1.1, 1.3, 1.5**
  - [ ]* 3.6 Write property test — neighbour features add exactly 4 columns to the sequence
    - **Property 9: Neighbour feature shape invariant**
    - **Validates: Requirements 5.3, 5.5**

- [x] 4. Checkpoint — verify dataset builder produces valid tensors
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Improve model architecture in `model.py`
  - [x] 5.1 Add `TemporalAttention` module (Linear(hidden_dim→1) → softmax over time dim → weighted sum)
    - _Requirements: 3.2, 3.3_
  - [x] 5.2 Update `GlobalCNNLSTMForecaster` to use `hidden_dim=128`, 3 LSTM layers, `LayerNorm` before LSTM, `TemporalAttention` replacing last-step extraction, updated `fc_input_dim = hidden_dim + embedding_dim + static_dim`
    - _Requirements: 3.1, 3.4, 3.5, 3.6_
  - [ ]* 5.3 Write property test — for any batch of finite inputs, `forward()` returns shape `(B, 6)` with no NaN or Inf
    - **Property 6: Forward pass produces finite outputs**
    - **Validates: Requirements 3.6**
  - [ ]* 5.4 Write property test — `TemporalAttention` weights sum to 1.0 over time dim within 1e-5 for any batch
    - **Property 5: Temporal attention weights sum to 1**
    - **Validates: Requirements 3.3**

- [ ] 6. Update training loop in `engine.py`
  - [x] 6.1 Replace `nn.MSELoss()` with `nn.HuberLoss(delta=config.huber_delta)` in `train_model()`
    - _Requirements: 4.1_
  - [x] 6.2 Add linear warmup scheduler for first `config.warmup_epochs` epochs before handing off to `CosineAnnealingWarmRestarts`; log `train_loss`, `val_loss`, current LR, and `val/train ratio` each epoch
    - _Requirements: 4.2, 4.5_
  - [x] 6.3 Add overfitting guard: if `val_loss > train_loss × 2.0` for 5 consecutive epochs starting from epoch 10, emit `logger.warning("overfitting detected ...")`
    - _Requirements: 4.6_
  - [x] 6.4 Update `evaluate_on_test()` to also compute and return unscaled MAE and R² for each of the 6 output horizons using `scaler_y` for inverse transformation
    - _Requirements: 6.5_

- [x] 7. Checkpoint — verify model trains one epoch without error
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Add `compute_aqi()` and wire CNN-LSTM into `inference.py`
  - [x] 8.1 Implement `compute_aqi(pm25: float, no2: float) -> int` in `inference.py` using Indian CPCB piecewise linear breakpoints for PM2.5 and NO2, clamping inputs to ≥ 0 and output to [0, 500]
    - _Requirements: 8.1, 8.2, 8.4, 8.5_
  - [x] 8.2 Replace the LR-only model loader with a CNN-LSTM-first loader that falls back to `baseline_lr.pkl` with a WARNING log on failure; update `predict_forecast()` to use the CNN-LSTM path and add `"aqi"` key to each horizon in the return dict
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 8.3_
  - [ ]* 8.3 Write property test — for any `(pm25 ≥ 0, no2 ≥ 0)`, `compute_aqi()` returns value in `[0, 500]`; for `(0, 0)` returns 0; for negative inputs returns same as `(0, 0)`
    - **Property 7: AQI clamp and zero case**
    - **Validates: Requirements 8.2, 8.4, 8.5**
  - [ ]* 8.4 Write property test — AQI is non-decreasing in PM2.5 for fixed NO2, and non-decreasing in NO2 for fixed PM2.5
    - **Property 8: AQI monotonicity**
    - **Validates: Requirements 8.1**

- [x] 9. Update `preprocessing.py` to mirror scaler fix
  - [x] 9.1 Update `scale_temporal()` to apply `scaler_X` to the 44 input features only (not `pm25`/`no2`), then scale `pm25`/`no2` separately using `scaler_y` — consistent with training
    - _Requirements: 7.2_
  - [ ]* 9.2 Write property test — inverse scaling round trip: for any array of scaled predictions, `inverse_scale_targets(scale(x))` equals `x` within 1e-4
    - **Property 4: Inverse scaling round-trip**
    - **Validates: Requirements 6.5, 7.3**

- [ ] 10. Final checkpoint — all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster iteration
- Phases must be applied in order: features → config → dataset → model → engine → inference
- After all code changes, retrain by running `python -m backend.app.services.ml.train` (or equivalent entry point)
- Property tests use [Hypothesis](https://hypothesis.readthedocs.io/) with `@settings(max_examples=100)`
- Target: overall MAE < 0.45 (scaled), beating LR baseline of 0.488
