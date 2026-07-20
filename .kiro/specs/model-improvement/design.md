# Design Document: Model Improvement

## Overview

This document describes the technical design for a five-phase improvement to the AtmosEdgeAI ML pipeline. The CNN-LSTM currently underperforms every baseline (overall MAE 0.557 vs. LR's 0.488) due to a combination of data pipeline bugs, insufficient model capacity, and weak regularisation. The phases address root causes in dependency order:

1. **Phase 1 — Data Pipeline Fixes**: Eliminate target-scaler leakage; extend `seq_len` to 72; fix rolling-window `min_periods`.
2. **Phase 2 — Architecture Improvements**: Increase `hidden_dim` to 128, add 3rd LSTM layer, temporal attention, LayerNorm.
3. **Phase 3 — Training Improvements**: Huber loss, LR warmup + cosine annealing, stronger dropout/weight decay, overfitting guard.
4. **Phase 4 — Spatial Context Features**: K-nearest-neighbour aggregated PM2.5/NO2 as 4 extra input features.
5. **Phase 5 — Production Swap + AQI Output**: Replace LR inference with CNN-LSTM when performance threshold is met; add `compute_aqi()`.

The phases are designed to be applied sequentially; each phase's test suite must pass before the next begins.

---

## Architecture

### Current Architecture (as-is)

```
x_temporal (B, 24, 41) → Conv1D(41→64, k=3) → BN → ReLU → Dropout
                       → LSTM(64, 64, 2 layers, dropout=0.3)
                       → last_hidden (B, 64)
                       → Cat[last_hidden, ward_emb(16), x_static(3)] (B, 83)
                       → Linear(83→64) → ReLU → Dropout → Linear(64→6)
```

### Target Architecture (to-be)

```
x_temporal (B, 72, 45) → Conv1D(45→128, k=3) → BN → ReLU → Dropout
                       → LayerNorm(128)
                       → LSTM(128, 128, 3 layers, dropout=0.35)
                       → lstm_all_steps (B, 72, 128)
                       → TemporalAttention → context_vector (B, 128)
                       → Cat[context_vector, ward_emb(16), x_static(3)] (B, 147)
                       → Linear(147→128) → ReLU → Dropout(0.35) → Linear(128→6)
```

Key changes:
- `temporal_dim`: 41 → 45 (+ 4 spatial neighbour features)
- `seq_len`: 24 → 72
- `hidden_dim`: 64 → 128
- `num_layers`: 2 → 3
- Last-step extraction → temporal attention over all 72 steps
- Added `LayerNorm` between Conv1D and LSTM
- Loss: `MSELoss` → `HuberLoss(delta=1.0)`

---

## Components and Interfaces

### Phase 1: DatasetBuilder Changes (`dataset_builder.py`)

#### 1.1 Scaler Leakage Fix

**Problem**: `scaler_X` is fit on all 41 temporal features including raw `pm25` and `no2`. The same columns are also scaled by `scaler_y` for targets. At inference time, `scale_temporal()` in `preprocessing.py` re-applies `scaler_y` on top of already-`scaler_X`-scaled values — double-scaling the target columns.

**Fix**: Split the feature list into `input_cols` (39 features, excluding raw `pm25` and `no2`) and `target_cols` (`["pm25", "no2"]`). `scaler_X` fits and transforms only `input_cols`. The `pm25` and `no2` values in the temporal sequence (as model inputs) are scaled by `scaler_y` directly, keeping the scale consistent with the target vector.

```python
# New constants in features.py
TARGET_COLS = ["pm25", "no2"]

def get_input_feature_names() -> List[str]:
    """39 features: all temporal features EXCEPT raw pm25 and no2."""
    all_features = get_temporal_feature_names()  # 41 features
    return [f for f in all_features if f not in TARGET_COLS]

def get_model_feature_names() -> List[str]:
    """41 features for model input: input_cols + target_cols (scaled by scaler_y) + spatial neighbour cols."""
    return get_input_feature_names() + TARGET_COLS
```

The `fit_scalers()` method changes:

```python
def fit_scalers(self, station_splits):
    input_cols = get_input_feature_names()   # 39 cols
    target_cols = ["pm25", "no2"]            # 2 cols

    combined_train = pd.concat([s["train"] for s in station_splits.values()])

    self.scaler_X.fit(combined_train[input_cols].values)       # fits 39 features
    self.scaler_y.fit(combined_train[target_cols].values)      # fits pm25, no2
    # scaler_static unchanged
```

The `transform_and_sequence()` method assembles the sequence as:

```python
# Scale input features (39 cols, no pm25/no2)
scaled_inputs = scaler_X.transform(df[input_cols].values)

# Scale pm25/no2 for use as sequence inputs AND as targets
scaled_pm25_seq = (df["pm25"].values - scaler_y.mean_[0]) / scaler_y.scale_[0]
scaled_no2_seq  = (df["no2"].values  - scaler_y.mean_[1]) / scaler_y.scale_[1]

# Assemble full 41-column sequence: [scaled_inputs(39), scaled_pm25(1), scaled_no2(1)]
full_seq = np.concatenate([scaled_inputs, scaled_pm25_seq[:, None], scaled_no2_seq[:, None]], axis=1)

# Targets: same scaled_pm25/no2 values at future horizons
y = [scaled_pm25[t+24], scaled_pm25[t+48], scaled_pm25[t+72],
     scaled_no2[t+24],  scaled_no2[t+48],  scaled_no2[t+72]]
```

#### 1.2 Sequence Length Extension

Update `ml_config.json`:
```json
"seq_len": 72
```

Update `DatasetBuilder.transform_and_sequence()`:
- Minimum rows per station per split: `seq_len + 72` (was `seq_len + 72` — unchanged, still correct).
- The loop index runs: `range(num_rows - seq_len - 72 + 1)` — this is already correct; only `seq_len` changes.

Update `GlobalCNNLSTMForecaster.__init__()` to receive `seq_len=72` from config.

#### 1.3 Rolling Window `min_periods` Fix

In `engineer_features()`:

```python
# Before (incorrect — NaN for first window-1 rows):
df[f"{col}_roll_mean_{window}"] = df[col].rolling(window=window).mean()

# After (correct — uses available data for early rows):
df[f"{col}_roll_mean_{window}"] = df[col].rolling(window=window, min_periods=1).mean()
df[f"{col}_roll_std_{window}"]  = df[col].rolling(window=window, min_periods=1).std(ddof=0)
```

This ensures early rows within each station's time series have valid (non-NaN) rolling statistics even when fewer than `window` prior samples exist. This is especially important since `seq_len` is now 72, so we consume more early rows per station.

---

### Phase 2: Architecture Improvements (`model.py`)

#### 2.1 TemporalAttention Module

```python
class TemporalAttention(nn.Module):
    """
    Computes a weighted sum over LSTM hidden states across the time dimension.
    Input:  lstm_out (B, T, hidden_dim)
    Output: context  (B, hidden_dim)
    """
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.attn = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, lstm_out: torch.Tensor) -> torch.Tensor:
        # scores: (B, T, 1)
        scores = self.attn(lstm_out)
        # weights: (B, T, 1) — sum to 1 over T
        weights = torch.softmax(scores, dim=1)
        # context: (B, hidden_dim)
        context = (weights * lstm_out).sum(dim=1)
        return context
```

#### 2.2 Updated GlobalCNNLSTMForecaster

```python
class GlobalCNNLSTMForecaster(nn.Module):
    def __init__(
        self,
        temporal_dim: int,        # 45 after spatial features added
        static_dim: int,          # 3
        num_wards: int = 100,
        embedding_dim: int = 16,
        seq_len: int = 72,
        hidden_dim: int = 128,
        num_layers: int = 3,
        dropout: float = 0.35,
        output_dim: int = 6
    ):
        ...
        self.conv1d = nn.Conv1d(temporal_dim, hidden_dim, kernel_size=3, padding=1)
        self.bn     = nn.BatchNorm1d(hidden_dim)
        self.layer_norm = nn.LayerNorm(hidden_dim)   # NEW: before LSTM
        self.relu   = nn.ReLU()
        self.dropout_conv = nn.Dropout(p=dropout)

        self.lstm = nn.LSTM(
            input_size=hidden_dim, hidden_size=hidden_dim,
            num_layers=num_layers, batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        self.attention = TemporalAttention(hidden_dim)  # NEW

        fc_input_dim = hidden_dim + embedding_dim + static_dim  # 128+16+3=147
        self.fc = nn.Sequential(
            nn.Linear(fc_input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(p=dropout),
            nn.Linear(hidden_dim, output_dim)
        )

    def forward(self, x_temporal, x_ward, x_static):
        x = x_temporal.permute(0, 2, 1)                    # (B, D, T)
        x = self.dropout_conv(self.relu(self.bn(self.conv1d(x))))
        x = x.permute(0, 2, 1)                             # (B, T, D)
        x = self.layer_norm(x)                             # NEW
        lstm_out, _ = self.lstm(x)                         # (B, T, H)
        context = self.attention(lstm_out)                 # (B, H)
        ward_emb = self.ward_embedding(x_ward)             # (B, 16)
        combined = torch.cat([context, ward_emb, x_static], dim=1)
        return self.fc(combined)
```

---

### Phase 3: Training Improvements (`engine.py`)

#### 3.1 Huber Loss

```python
criterion = nn.HuberLoss(delta=1.0)
```

Huber loss is quadratic for residuals < delta and linear beyond — this reduces the gradient contribution from extreme PM2.5 spikes (e.g., stubble burning events) that would otherwise dominate MSE gradient updates.

#### 3.2 Warmup + Cosine Schedule

```python
def get_scheduler_with_warmup(optimizer, warmup_epochs, total_epochs, T_0, eta_min=1e-6):
    """Linear warmup for first `warmup_epochs`, then CosineAnnealingWarmRestarts."""
    def lr_lambda(epoch):
        if epoch < warmup_epochs:
            return float(epoch + 1) / float(warmup_epochs)
        return 1.0

    warmup_sched = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    cosine_sched = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=T_0, T_mult=2, eta_min=eta_min
    )
    return warmup_sched, cosine_sched
```

Training loop steps both schedulers: warmup for epochs 1–5, cosine from epoch 6 onwards.

#### 3.3 Overfitting Guard

```python
OVERFIT_RATIO_THRESHOLD = 2.0
OVERFIT_WINDOW = 5
OVERFIT_START_EPOCH = 10

# Inside training loop, after epoch >= OVERFIT_START_EPOCH:
recent_ratios = [v / t for v, t in zip(val_losses[-OVERFIT_WINDOW:], train_losses[-OVERFIT_WINDOW:])]
if all(r > OVERFIT_RATIO_THRESHOLD for r in recent_ratios):
    logger.warning("overfitting detected: val/train ratio > 2.0 for 5 consecutive epochs")
```

#### 3.4 Config Changes (`ml_config.json`)

```json
"training": {
  "seq_len": 72,
  "learning_rate": 0.001,
  "batch_size": 256,
  "epochs": 150,
  "patience": 25,
  "grad_clip": 1.0,
  "hidden_dim": 128,
  "num_lstm_layers": 3,
  "dropout": 0.35,
  "weight_decay": 5e-4,
  "random_seed": 42,
  "warmup_epochs": 5,
  "huber_delta": 1.0
}
```

`MLConfig` will be updated to parse `warmup_epochs` and `huber_delta`.

---

### Phase 4: Spatial Neighbour Features (`dataset_builder.py`)

#### 4.1 Haversine Distance Matrix

```python
def _compute_distance_matrix(self, station_splits) -> Dict[str, List[str]]:
    """
    Returns {station_id: [neighbour_id_1, neighbour_id_2, ...]} sorted by distance asc.
    Uses the Haversine formula on station lat/lon from the first row of each station's data.
    """
    coords = {}
    for sid, splits in station_splits.items():
        df = splits["train"]
        if not df.empty:
            coords[sid] = (float(df.iloc[0]["latitude"]), float(df.iloc[0]["longitude"]))

    neighbours = {}
    for sid, (lat1, lon1) in coords.items():
        dists = []
        for oid, (lat2, lon2) in coords.items():
            if oid == sid:
                continue
            d = haversine_km(lat1, lon1, lat2, lon2)
            dists.append((d, oid))
        dists.sort()
        neighbours[sid] = [oid for _, oid in dists[:self.k_neighbours]]
    return neighbours
```

#### 4.2 Neighbour Feature Injection

After scaling each station's sequences, look up the K neighbours' scaled `pm25`/`no2` arrays and compute per-timestep statistics:

```python
# For station s, at sequence index i (covering time steps i..i+seq_len-1):
nbr_pm25 = np.stack([scaled_pm25_by_station[nbr][i:i+seq_len] for nbr in neighbours[sid]], axis=0)
nbr_no2  = np.stack([scaled_no2_by_station[nbr][i:i+seq_len]  for nbr in neighbours[sid]], axis=0)

nbr_features = np.stack([
    nbr_pm25.mean(axis=0),   # (seq_len,)
    nbr_pm25.std(axis=0),    # (seq_len,)
    nbr_no2.mean(axis=0),    # (seq_len,)
    nbr_no2.std(axis=0),     # (seq_len,)
], axis=1)                   # (seq_len, 4)

seq_x = np.concatenate([seq_x, nbr_features], axis=1)  # (seq_len, 45)
```

`get_temporal_feature_names()` returns 45 features after this change (41 original + 4 spatial).

---

### Phase 5: Inference Swap + AQI (`inference.py`, `preprocessing.py`)

#### 5.1 Model Loading with LR Fallback

```python
# inference.py
CNN_LSTM_PATH = os.path.join(MODELS_DIR, "global_model.pth")
LR_PATH       = os.path.join(MODELS_DIR, "baseline_lr.pkl")

_model = None
_model_type = None   # "cnn_lstm" | "lr"

def _load_models():
    global _model, _model_type
    if os.path.exists(CNN_LSTM_PATH):
        try:
            _model = _load_cnn_lstm(CNN_LSTM_PATH)
            _model_type = "cnn_lstm"
            return
        except Exception as e:
            logger.warning(f"falling back to LR baseline: {e}")
    _model = _load_lr(LR_PATH)
    _model_type = "lr"
```

#### 5.2 AQI Computation

Indian CPCB AQI uses PM2.5 (24h average) and NO2 (hourly) sub-indices computed from piecewise linear breakpoints:

**PM2.5 breakpoints (µg/m³ → AQI)**:

| PM2.5 Low | PM2.5 High | AQI Low | AQI High |
|-----------|-----------|---------|---------|
| 0         | 30        | 0       | 50      |
| 30        | 60        | 51      | 100     |
| 60        | 90        | 101     | 200     |
| 90        | 120       | 201     | 300     |
| 120       | 250       | 301     | 400     |
| 250       | 500       | 401     | 500     |

**NO2 breakpoints (µg/m³ → AQI)**:

| NO2 Low | NO2 High | AQI Low | AQI High |
|---------|---------|---------|---------|
| 0       | 40      | 0       | 50      |
| 40      | 80      | 51      | 100     |
| 80      | 180     | 101     | 200     |
| 180     | 280     | 201     | 300     |
| 280     | 400     | 301     | 400     |
| 400     | 800     | 401     | 500     |

```python
def compute_aqi(pm25: float, no2: float) -> int:
    """
    Computes Indian CPCB AQI as max(pm25_sub_index, no2_sub_index).
    Clamps inputs to [0, ∞) and output to [0, 500].
    """
    pm25 = max(0.0, pm25)
    no2  = max(0.0, no2)
    pm25_aqi = _linear_interpolate(pm25, PM25_BREAKPOINTS)
    no2_aqi  = _linear_interpolate(no2,  NO2_BREAKPOINTS)
    return min(500, max(0, int(round(max(pm25_aqi, no2_aqi)))))
```

#### 5.3 Updated `predict_forecast()` Return Type

```python
# Returns:
{
    24: {"pm25": float, "no2": float, "aqi": int},
    48: {"pm25": float, "no2": float, "aqi": int},
    72: {"pm25": float, "no2": float, "aqi": int},
}
```

#### 5.4 Inference Preprocessing Fix

`scale_temporal()` in `preprocessing.py` must be updated to mirror the Phase 1 scaler fix:

```python
def scale_temporal(df: pd.DataFrame) -> pd.DataFrame:
    df_scaled = df.copy()
    input_cols = get_input_feature_names()    # 39 non-target cols
    df_scaled[input_cols] = scaler_X.transform(df[input_cols].values)

    # Scale pm25/no2 using scaler_y (consistent with training)
    df_scaled["pm25"] = (df["pm25"] - scaler_y.mean_[0]) / scaler_y.scale_[0]
    df_scaled["no2"]  = (df["no2"]  - scaler_y.mean_[1]) / scaler_y.scale_[1]
    return df_scaled
```

---

## Data Models

### Sequence Tensor Shapes (after all phases)

| Tensor | Shape | Dtype |
|--------|-------|-------|
| `x_temporal` | `(B, 72, 45)` | float32 |
| `x_ward` | `(B,)` | int64 |
| `x_static` | `(B, 3)` | float32 |
| `y` | `(B, 6)` | float32 |

### Scaler Serialisation (`global_scaler.pkl`)

```python
{
    "scaler_X":      StandardScaler,  # fit on 39 input features
    "scaler_y":      StandardScaler,  # fit on pm25, no2 (2 cols)
    "scaler_static": StandardScaler,  # fit on lat, lon, elevation (3 cols)
}
```

### `ml_config.json` Training Block (final)

```json
{
  "seq_len": 72,
  "learning_rate": 0.001,
  "batch_size": 256,
  "epochs": 150,
  "patience": 25,
  "grad_clip": 1.0,
  "hidden_dim": 128,
  "num_lstm_layers": 3,
  "dropout": 0.35,
  "weight_decay": 5e-4,
  "warmup_epochs": 5,
  "huber_delta": 1.0,
  "k_neighbours": 3,
  "random_seed": 42
}
```

### Feature Name Lists

| List | Count | Source |
|------|-------|--------|
| `get_input_feature_names()` | 39 | All temporal features except raw `pm25`, `no2` |
| `get_temporal_feature_names()` | 41 | Original full list (used for legacy reference) |
| `get_model_feature_names()` | 45 | Input features + `pm25`, `no2` (scaler_y-scaled) + 4 spatial |

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

The following properties are derived from the acceptance criteria and implemented using [Hypothesis](https://hypothesis.readthedocs.io/) — the Python property-based testing library. Each test runs a minimum of 100 iterations over generated inputs.

---

**Property 1: Scaler separation — target columns not double-scaled**

*For any* training split, the scaled `pm25` and `no2` values in the temporal sequence (model inputs) must be scaled using `scaler_y` statistics, not `scaler_X` statistics. Concretely: after `transform_and_sequence()`, for any sample, `seq_x[:, -2]` (the `pm25` input column) must equal `(raw_pm25 - scaler_y.mean_[0]) / scaler_y.scale_[0]` within floating-point tolerance.

**Validates: Requirements 1.1, 1.3, 1.5**

---

**Property 2: Sequence shape invariant**

*For any* valid station split with at least `seq_len + 72` rows, the output of `transform_and_sequence()` must return tensors where `X_temporal.shape == (N, seq_len, feature_dim)` and `y.shape == (N, 6)`, and `N >= 1`.

**Validates: Requirements 2.2, 5.5**

---

**Property 3: Target value range after scaling**

*For any* batch of targets `y` produced by `transform_and_sequence()`, every element of `y` must lie within `[-10, 10]` in scaled units (a reasonable bound; values outside this range would indicate a scaling bug, since the training data PM2.5 values range roughly 0–400 µg/m³ and σ ≈ 40).

**Validates: Requirements 1.4**

---

**Property 4: Inverse scaling round-trip**

*For any* array of scaled predictions of shape `(N, 6)`, applying `inverse_scale_targets()` and then re-scaling using `scaler_y` must return an array that is element-wise equal to the original within tolerance `1e-4`.

**Validates: Requirements 6.5, 7.3**

---

**Property 5: Temporal attention weights sum to 1**

*For any* batch input to `TemporalAttention.forward()`, the attention weights tensor (before the weighted sum) must sum to 1.0 over the time dimension for every item in the batch, within tolerance `1e-5`.

**Validates: Requirements 3.3**

---

**Property 6: Forward pass produces finite outputs**

*For any* batch of valid (finite) inputs to `GlobalCNNLSTMForecaster.forward()`, the output tensor must contain no `NaN` or `Inf` values, and must have shape `(batch_size, 6)`.

**Validates: Requirements 3.6**

---

**Property 7: AQI clamp and zero case**

*For any* pair `(pm25, no2)` where both are ≥ 0, `compute_aqi()` must return a value in `[0, 500]`. When `pm25=0.0` and `no2=0.0`, it must return `0`. For negative inputs, it must return the same value as for `(0.0, 0.0)`.

**Validates: Requirements 8.2, 8.4, 8.5**

---

**Property 8: AQI monotonicity**

*For any* fixed `no2` value, `compute_aqi(pm25_a, no2)` must be ≥ `compute_aqi(pm25_b, no2)` whenever `pm25_a >= pm25_b`. AQI must be non-decreasing in both PM2.5 and NO2.

**Validates: Requirements 8.1**

---

**Property 9: Neighbour feature shape invariant**

*For any* station with K valid neighbours, the spatial neighbour features appended to the temporal sequence must add exactly 4 columns, resulting in `seq_x.shape[-1] == original_feature_dim + 4`.

**Validates: Requirements 5.3, 5.5**

---

**Property 10: Rolling features contain no NaN after min_periods=1 fix**

*For any* station DataFrame with at least 1 row, after calling `engineer_features()`, the columns `pm25_roll_mean_6`, `pm25_roll_std_6`, etc., must contain no `NaN` values.

**Validates: Requirements 2.4**

---

## Error Handling

| Scenario | Component | Behaviour |
|----------|-----------|-----------|
| `global_model.pth` missing or corrupt | `inference.py` | Log WARNING `"falling back to LR baseline"`, load `baseline_lr.pkl` |
| Station has < `seq_len + 72` rows | `DatasetBuilder.transform_and_sequence()` | Skip station silently, log DEBUG |
| Fewer than `k_neighbours` neighbours have data at a given timestep | `DatasetBuilder.transform_and_sequence()` | Aggregate over available neighbours (min 1), no error raised |
| Negative PM2.5 or NO2 from model | `inference.py predict_forecast()` | Clamp to 0.0 before AQI computation and in response dict |
| `NaN`/`Inf` in model output | `inference.py predict_forecast()` | Replace with 0.0, log ERROR, continue |
| Config key missing from `ml_config.json` | `MLConfig.load_config()` | Use existing default, log WARNING |
| Scaler file not found at inference startup | `preprocessing.py` | Set scalers to `None`, fall through to un-scaled path (degrades gracefully) |

---

## Testing Strategy

### Dual Testing Approach

Testing uses both unit tests (specific examples, edge cases) and property-based tests (universal correctness across generated inputs). Both are required; neither replaces the other.

**Unit tests** cover:
- Specific regression examples with known inputs/outputs
- Integration between `DatasetBuilder` and `GlobalCNNLSTMForecaster`
- AQI breakpoint boundary values

**Property tests** cover:
- Data invariants that must hold for all valid inputs (Properties 1–10 above)
- Generated with [Hypothesis](https://hypothesis.readthedocs.io/) (`pip install hypothesis`)
- Each property test runs a minimum of 100 iterations (`@settings(max_examples=100)`)

### Property Test Tagging

Each property test is tagged with a comment:

```python
# Feature: model-improvement, Property N: <property_text>
@settings(max_examples=100)
@given(...)
def test_property_N_name(...):
    ...
```

### Test File Layout

```
backend/tests/ml/
├── test_dataset_builder.py    # Properties 1, 2, 3, 9, 10
├── test_model.py              # Properties 5, 6
├── test_preprocessing.py      # Property 4
└── test_inference.py          # Properties 7, 8
```

### Integration Test

After all phases are implemented, a single integration test runs the full `DatasetBuilder.generate_all_splits()` on a 2-station mini-dataset (generated from Hypothesis) and verifies:
- No NaN in any split
- `X_temporal.shape[-1] == 45`
- `y.shape[-1] == 6`
- Round-trip: scale targets → inverse scale → within 1e-4 of original
