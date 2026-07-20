"""
preprocessing.py
================
Inference-time feature scaling for AtmosEdgeAI forecasting.

Mirrors the scaler separation used in DatasetBuilder:
  - scaler_X  : fitted on 44 input features (excludes raw pm25/no2)
  - scaler_y  : fitted on pm25, no2 targets
  - scaler_static : fitted on lat, lon, elevation

This eliminates the double-scaling bug where pm25/no2 were transformed by
both scaler_X and scaler_y.
"""
import os
import pickle
import logging
import numpy as np
import pandas as pd

from backend.app.services.ml.config import MODELS_DIR
from backend.app.services.forecasting.feature_engineering import get_temporal_feature_names
from backend.app.services.ml.features import get_input_feature_names, TARGET_COLS

logger = logging.getLogger(__name__)

SCALER_PATH = os.path.join(MODELS_DIR, "global_scaler.pkl")

scaler_X = None
scaler_y = None
scaler_static = None

if os.path.exists(SCALER_PATH):
    try:
        with open(SCALER_PATH, "rb") as f:
            _scalers = pickle.load(f)
            scaler_X = _scalers.get("scaler_X")
            scaler_y = _scalers.get("scaler_y")
            scaler_static = _scalers.get("scaler_static")
    except Exception as e:
        logger.error(f"Error loading global scalers in preprocessing: {e}")


def scale_temporal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Scales temporal features using the separated scalers.

    - scaler_X is applied to the 44 input features (all except raw pm25/no2).
    - scaler_y is applied to pm25 and no2 separately.

    This is consistent with how DatasetBuilder.transform_and_sequence() works
    during training, preventing double-scaling of target columns.
    """
    if scaler_X is None or scaler_y is None:
        logger.warning("Scalers not loaded — returning unscaled DataFrame")
        return df.copy()

    df_scaled = df.copy()
    input_cols = get_input_feature_names()  # 44 cols (no pm25/no2)

    # Scale 44 input features with scaler_X
    available_input_cols = [c for c in input_cols if c in df.columns]
    if available_input_cols:
        # Handle case where df may have fewer columns than expected (e.g., old model path)
        if len(available_input_cols) == len(input_cols):
            df_scaled[input_cols] = scaler_X.transform(df[input_cols].values)
        else:
            logger.warning(
                f"scale_temporal: expected {len(input_cols)} input cols, "
                f"got {len(available_input_cols)}. Partial scaling applied."
            )
            df_scaled[available_input_cols] = scaler_X.transform(
                df[available_input_cols].values
            )

    # Scale pm25 and no2 with scaler_y (consistent with training targets)
    if "pm25" in df.columns:
        df_scaled["pm25"] = (df["pm25"] - scaler_y.mean_[0]) / scaler_y.scale_[0]
    if "no2" in df.columns:
        df_scaled["no2"] = (df["no2"] - scaler_y.mean_[1]) / scaler_y.scale_[1]

    return df_scaled


def scale_static(lat: float, lon: float, city_encoded: int) -> np.ndarray:
    """
    Normalises static station metadata using scaler_static.
    Returns a (3,) float32 array.
    """
    if scaler_static is None:
        return np.array([lat, lon, city_encoded], dtype=np.float32)

    arr = np.array([[lat, lon, city_encoded]], dtype=np.float32)
    return scaler_static.transform(arr)[0].astype(np.float32)


def inverse_scale_targets(scaled_targets: np.ndarray) -> np.ndarray:
    """
    Restores scaled predictions back to physical units (µg/m³).

    scaled_targets : shape (N, 6) or (6,)
        Columns: [pm25_24h, pm25_48h, pm25_72h, no2_24h, no2_48h, no2_72h]

    Returns an array of the same shape with values in original units.
    """
    if scaler_y is None:
        return scaled_targets.copy()

    restored = np.zeros_like(scaled_targets, dtype=np.float32)
    pm25_mean, pm25_std = float(scaler_y.mean_[0]), float(scaler_y.scale_[0])
    no2_mean,  no2_std  = float(scaler_y.mean_[1]), float(scaler_y.scale_[1])

    if scaled_targets.ndim == 1:
        restored[0] = scaled_targets[0] * pm25_std + pm25_mean
        restored[1] = scaled_targets[1] * pm25_std + pm25_mean
        restored[2] = scaled_targets[2] * pm25_std + pm25_mean
        restored[3] = scaled_targets[3] * no2_std  + no2_mean
        restored[4] = scaled_targets[4] * no2_std  + no2_mean
        restored[5] = scaled_targets[5] * no2_std  + no2_mean
    else:
        restored[:, 0] = scaled_targets[:, 0] * pm25_std + pm25_mean
        restored[:, 1] = scaled_targets[:, 1] * pm25_std + pm25_mean
        restored[:, 2] = scaled_targets[:, 2] * pm25_std + pm25_mean
        restored[:, 3] = scaled_targets[:, 3] * no2_std  + no2_mean
        restored[:, 4] = scaled_targets[:, 4] * no2_std  + no2_mean
        restored[:, 5] = scaled_targets[:, 5] * no2_std  + no2_mean

    return restored
