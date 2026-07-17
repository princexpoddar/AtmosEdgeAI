import os
import pickle
import numpy as np
import pandas as pd
from backend.app.services.ml.config import MODELS_DIR
from backend.app.services.forecasting.feature_engineering import get_temporal_feature_names

SCALER_PATH = os.path.join(MODELS_DIR, "global_scaler.pkl")

scaler_X = None
scaler_y = None
scaler_static = None

if os.path.exists(SCALER_PATH):
    try:
        with open(SCALER_PATH, "rb") as f:
            scalers = pickle.load(f)
            scaler_X = scalers["scaler_X"]
            scaler_y = scalers["scaler_y"]
            scaler_static = scalers["scaler_static"]
    except Exception as e:
        print(f"Error loading global scalers in preprocessing: {e}")

def scale_temporal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes temporal features using scaler_X.
    """
    if scaler_X is None:
        return df.copy()
        
    df_scaled = df.copy()
    temporal_cols = get_temporal_feature_names()
    df_scaled[temporal_cols] = scaler_X.transform(df[temporal_cols].values)
    
    # Target columns scaling for targets mapping consistency
    df_scaled["pm25"] = (df["pm25"] - scaler_y.mean_[0]) / scaler_y.scale_[0]
    df_scaled["no2"] = (df["no2"] - scaler_y.mean_[1]) / scaler_y.scale_[1]
    
    return df_scaled

def scale_static(lat: float, lon: float, city_encoded: int) -> np.ndarray:
    """
    Normalizes static coordinates using scaler_static.
    """
    if scaler_static is None:
        return np.array([lat, lon, city_encoded], dtype=np.float32)
        
    arr = np.array([[lat, lon, city_encoded]], dtype=np.float32)
    return scaler_static.transform(arr)[0]

def inverse_scale_targets(scaled_targets: np.ndarray) -> np.ndarray:
    """
    Restores scaled predictions to normal values.
    """
    if scaler_y is None:
        return scaled_targets
        
    # scaled_targets is either shape (6,) or (N, 6)
    # The first 3 elements are PM2.5, last 3 elements are NO2.
    # self.scaler_y was fit on shape (N, 2) where col 0 is PM2.5 and col 1 is NO2.
    # So we restore using mean_ and scale_ coefficients explicitly.
    restored = np.zeros_like(scaled_targets, dtype=np.float32)
    
    if len(scaled_targets.shape) == 1:
        # PM2.5 (indices 0, 1, 2)
        restored[0] = scaled_targets[0] * scaler_y.scale_[0] + scaler_y.mean_[0]
        restored[1] = scaled_targets[1] * scaler_y.scale_[0] + scaler_y.mean_[0]
        restored[2] = scaled_targets[2] * scaler_y.scale_[0] + scaler_y.mean_[0]
        # NO2 (indices 3, 4, 5)
        restored[3] = scaled_targets[3] * scaler_y.scale_[1] + scaler_y.mean_[1]
        restored[4] = scaled_targets[4] * scaler_y.scale_[1] + scaler_y.mean_[1]
        restored[5] = scaled_targets[5] * scaler_y.scale_[1] + scaler_y.mean_[1]
    else:
        # Batch mode (N, 6)
        restored[:, 0] = scaled_targets[:, 0] * scaler_y.scale_[0] + scaler_y.mean_[0]
        restored[:, 1] = scaled_targets[:, 1] * scaler_y.scale_[0] + scaler_y.mean_[0]
        restored[:, 2] = scaled_targets[:, 2] * scaler_y.scale_[0] + scaler_y.mean_[0]
        restored[:, 3] = scaled_targets[:, 3] * scaler_y.scale_[1] + scaler_y.mean_[1]
        restored[:, 4] = scaled_targets[:, 4] * scaler_y.scale_[1] + scaler_y.mean_[1]
        restored[:, 5] = scaled_targets[:, 5] * scaler_y.scale_[1] + scaler_y.mean_[1]
        
    return restored
