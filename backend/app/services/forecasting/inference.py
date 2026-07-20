"""
inference.py
============
Production forecasting inference for AtmosEdgeAI.

Model loading priority:
  1. CNN-LSTM   (global_model.pth) — loaded first; used if available
  2. LR fallback (baseline_lr.pkl) — used with a WARNING if CNN-LSTM fails

predict_forecast() returns per-horizon dicts including a derived AQI integer.
"""
import os
import pickle
import logging
import numpy as np
import pandas as pd
import torch

from backend.app.services.ml.config import MODELS_DIR
from backend.app.services.ml.model import GlobalCNNLSTMForecaster, TCNForecaster
from backend.app.services.forecasting.feature_engineering import get_temporal_feature_names
from backend.app.services.forecasting.preprocessing import (
    scale_temporal,
    scale_static,
    inverse_scale_targets,
)

logger = logging.getLogger(__name__)

CNN_LSTM_PATH = os.path.join(MODELS_DIR, "global_model.pth")
LR_PATH = os.path.join(MODELS_DIR, "baseline_lr.pkl")
SCALER_PATH = os.path.join(MODELS_DIR, "global_scaler.pkl")

# ---------------------------------------------------------------------------
# AQI computation — Indian CPCB breakpoints
# ---------------------------------------------------------------------------

# Each row: (pollutant_low, pollutant_high, aqi_low, aqi_high)
_PM25_BREAKPOINTS = [
    (0.0,   30.0,   0,   50),
    (30.0,  60.0,  51,  100),
    (60.0,  90.0, 101,  200),
    (90.0, 120.0, 201,  300),
    (120.0, 250.0, 301,  400),
    (250.0, 500.0, 401,  500),
]

_NO2_BREAKPOINTS = [
    (0.0,   40.0,   0,   50),
    (40.0,  80.0,  51,  100),
    (80.0, 180.0, 101,  200),
    (180.0, 280.0, 201,  300),
    (280.0, 400.0, 301,  400),
    (400.0, 800.0, 401,  500),
]


def _linear_interpolate(value: float, breakpoints: list) -> float:
    """Piecewise linear interpolation over CPCB breakpoint table."""
    for (c_lo, c_hi, i_lo, i_hi) in breakpoints:
        if value <= c_hi:
            if c_hi == c_lo:
                return float(i_hi)
            return i_lo + (value - c_lo) * (i_hi - i_lo) / (c_hi - c_lo)
    # Above the last breakpoint — cap at maximum
    return float(breakpoints[-1][3])


def compute_aqi(pm25: float, no2: float) -> int:
    """
    Computes Indian CPCB AQI as max(pm25_sub_index, no2_sub_index).

    - Negative inputs are clamped to 0.0.
    - Output is clamped to [0, 500].
    - compute_aqi(0.0, 0.0) == 0.
    """
    pm25 = max(0.0, pm25)
    no2 = max(0.0, no2)
    pm25_idx = _linear_interpolate(pm25, _PM25_BREAKPOINTS)
    no2_idx = _linear_interpolate(no2, _NO2_BREAKPOINTS)
    return min(500, max(0, int(round(max(pm25_idx, no2_idx)))))


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

_model = None          # loaded model instance (CNN-LSTM or LR)
_model_type = None     # "cnn_lstm" | "lr"


def _load_cnn_lstm():
    """Load TCNForecaster (or legacy GlobalCNNLSTMForecaster) from checkpoint."""
    ckpt = torch.load(CNN_LSTM_PATH, map_location="cpu", weights_only=True)
    cfg = ckpt.get("config", {})
    model_type = ckpt.get("model_type", "GlobalCNNLSTMForecaster")

    if model_type == "TCNForecaster":
        model = TCNForecaster(
            temporal_dim=cfg.get("temporal_dim", 50),
            static_dim=cfg.get("static_dim", 3),
            num_wards=cfg.get("num_wards", 100),
            seq_len=cfg.get("seq_len", 48),
            channels=cfg.get("channels", 64),
            dropout=0.0,
            output_dim=6,
        )
    else:
        # Legacy checkpoint
        model = GlobalCNNLSTMForecaster(
            temporal_dim=cfg.get("temporal_dim", 50),
            static_dim=cfg.get("static_dim", 3),
            num_wards=cfg.get("num_wards", 100),
            seq_len=cfg.get("seq_len", 72),
            hidden_dim=cfg.get("hidden_dim", 128),
            num_layers=cfg.get("num_lstm_layers", 3),
            dropout=0.0,
            output_dim=6,
        )
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model


def _load_lr():
    """Load sklearn Linear Regression baseline. Returns model."""
    with open(LR_PATH, "rb") as f:
        return pickle.load(f)


def _ensure_models_loaded() -> None:
    global _model, _model_type
    if _model is not None:
        return

    # Try CNN-LSTM first
    if os.path.exists(CNN_LSTM_PATH):
        try:
            _model = _load_cnn_lstm()
            _model_type = "cnn_lstm"
            logger.info("Production inference: using CNN-LSTM model")
            return
        except Exception as e:
            logger.warning(f"falling back to LR baseline: CNN-LSTM load failed — {e}")

    # Fallback to LR
    if os.path.exists(LR_PATH):
        try:
            _model = _load_lr()
            _model_type = "lr"
            logger.warning("falling back to LR baseline: using baseline_lr.pkl for inference")
            return
        except Exception as e:
            logger.error(f"LR baseline also failed to load: {e}")

    raise RuntimeError("No production model available (CNN-LSTM and LR both failed to load)")


# Eagerly attempt load at import time (failures are non-fatal — retried per call)
try:
    _ensure_models_loaded()
except Exception as _boot_err:
    logger.error(f"Model boot failed: {_boot_err}")


# ---------------------------------------------------------------------------
# Scaler loading (shared across both model paths)
# ---------------------------------------------------------------------------

_scaler_y = None

if os.path.exists(SCALER_PATH):
    try:
        with open(SCALER_PATH, "rb") as _f:
            _scalers = pickle.load(_f)
            _scaler_y = _scalers.get("scaler_y")
    except Exception as _e:
        logger.error(f"Could not load scaler_y from {SCALER_PATH}: {_e}")


# ---------------------------------------------------------------------------
# Prediction entry point
# ---------------------------------------------------------------------------

def predict_forecast(
    df_engineered: pd.DataFrame,
    lat: float,
    lon: float,
    city_encoded: int,
) -> dict:
    """
    Runs production inference. Chooses CNN-LSTM or LR based on what loaded.

    Args:
        df_engineered : DataFrame with at least seq_len chronological steps
                        and all engineered temporal features.
        lat           : Station latitude (for static feature scaling).
        lon           : Station longitude.
        city_encoded  : Integer city encoding (used by LR static features).

    Returns:
        {
            24: {"pm25": float, "no2": float, "aqi": int},
            48: {"pm25": float, "no2": float, "aqi": int},
            72: {"pm25": float, "no2": float, "aqi": int},
        }
    """
    _ensure_models_loaded()

    if _model_type == "cnn_lstm":
        return _predict_cnn_lstm(df_engineered, lat, lon)
    else:
        return _predict_lr(df_engineered, lat, lon, city_encoded)


def _predict_cnn_lstm(
    df_engineered: pd.DataFrame,
    lat: float,
    lon: float,
) -> dict:
    """TCN / CNN-LSTM inference path."""
    from backend.app.services.ml.config import config as ml_config
    from backend.app.services.ml.features import get_input_feature_names, TARGET_COLS

    # Use seq_len from the loaded checkpoint config
    import pickle as _pk
    seq_len = ml_config.seq_len
    try:
        ckpt = torch.load(CNN_LSTM_PATH, map_location="cpu", weights_only=True)
        seq_len = ckpt.get("config", {}).get("seq_len", seq_len)
    except Exception:
        pass

    if len(df_engineered) < seq_len:
        raise ValueError(
            f"CNN-LSTM inference requires >= {seq_len} steps, got {len(df_engineered)}"
        )

    # Scale temporal features (fixed scaler separation)
    df_scaled = scale_temporal(df_engineered)

    # Extract last seq_len steps — assemble [input_cols | pm25 | no2] (46 cols)
    # Spatial neighbour features are zeroed out at inference (no neighbour data available)
    input_cols = get_input_feature_names()  # 44
    last_seq_inputs = df_scaled.iloc[-seq_len:][input_cols].values.astype(np.float32)  # (72, 44)
    last_seq_pm25   = df_scaled.iloc[-seq_len:]["pm25"].values.astype(np.float32)[:, None]  # (72, 1)
    last_seq_no2    = df_scaled.iloc[-seq_len:]["no2"].values.astype(np.float32)[:, None]   # (72, 1)

    # Core sequence (72, 46)
    seq_core = np.concatenate([last_seq_inputs, last_seq_pm25, last_seq_no2], axis=1)

    # Append zero spatial neighbour features (72, 4) — unknown at single-station inference
    nbr_zeros = np.zeros((seq_len, 4), dtype=np.float32)
    seq_full = np.concatenate([seq_core, nbr_zeros], axis=1)  # (72, 50)

    # Scale static
    scaled_static = scale_static(lat, lon, city_encoded)  # (3,)

    # Build tensors
    x_temporal = torch.tensor(seq_full, dtype=torch.float32).unsqueeze(0)    # (1, 72, 50)
    x_ward     = torch.tensor([0], dtype=torch.long)                          # (1,) — ward 0
    x_static   = torch.tensor(scaled_static, dtype=torch.float32).unsqueeze(0)  # (1, 3)

    with torch.no_grad():
        preds_scaled = _model(x_temporal, x_ward, x_static).numpy()[0]  # (6,)

    # Inverse scale
    preds_raw = inverse_scale_targets(preds_scaled[None, :])[0]

    return _build_result(preds_raw)


def _predict_lr(
    df_engineered: pd.DataFrame,
    lat: float,
    lon: float,
    city_encoded: int,
) -> dict:
    """Linear Regression fallback inference path (seq_len=24, 41 features)."""
    temporal_cols = get_temporal_feature_names()

    if len(df_engineered) < 24:
        raise ValueError(
            f"LR inference requires >= 24 steps, got {len(df_engineered)}"
        )

    df_scaled = scale_temporal(df_engineered)
    last_seq = df_scaled.iloc[-24:][temporal_cols].values     # (24, 41)
    scaled_static = scale_static(lat, lon, city_encoded)      # (3,)

    flat_temp   = last_seq.reshape(1, 24 * len(temporal_cols))
    flat_static = scaled_static.reshape(1, 3)
    feature_vec = np.hstack([flat_temp, flat_static])

    preds_scaled = _model.predict(feature_vec)                # (1, 6)
    preds_raw    = inverse_scale_targets(preds_scaled)[0]     # (6,)

    return _build_result(preds_raw)


def _build_result(preds_raw: np.ndarray) -> dict:
    """Clamp predictions, compute AQI, return standard result dict."""
    pm25_24 = max(0.0, float(preds_raw[0]))
    pm25_48 = max(0.0, float(preds_raw[1]))
    pm25_72 = max(0.0, float(preds_raw[2]))
    no2_24  = max(0.0, float(preds_raw[3]))
    no2_48  = max(0.0, float(preds_raw[4]))
    no2_72  = max(0.0, float(preds_raw[5]))

    return {
        24: {"pm25": pm25_24, "no2": no2_24, "aqi": compute_aqi(pm25_24, no2_24)},
        48: {"pm25": pm25_48, "no2": no2_48, "aqi": compute_aqi(pm25_48, no2_48)},
        72: {"pm25": pm25_72, "no2": no2_72, "aqi": compute_aqi(pm25_72, no2_72)},
    }
