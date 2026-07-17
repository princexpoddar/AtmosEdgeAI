import os
import pickle
import numpy as np
import pandas as pd
from backend.app.services.ml.config import MODELS_DIR
from backend.app.services.forecasting.feature_engineering import get_temporal_feature_names
from backend.app.services.forecasting.preprocessing import scale_temporal, scale_static, inverse_scale_targets

LR_PATH = os.path.join(MODELS_DIR, "baseline_lr.pkl")
lr_model = None

if os.path.exists(LR_PATH):
    try:
        with open(LR_PATH, "rb") as f:
            lr_model = pickle.load(f)
    except Exception as e:
        print(f"Error loading global Linear Regression model: {e}")

def predict_forecast(df_engineered: pd.DataFrame, lat: float, lon: float, city_encoded: int) -> dict:
    """
    Runs production inference using the deployed Linear Regression model.
    Expects df_engineered to have >= 24 chronological steps of 41-feature inputs.
    """
    if lr_model is None:
        raise RuntimeError("Production Linear Regression model baseline_lr.pkl is not loaded.")
        
    if len(df_engineered) < 24:
        raise ValueError(f"Inference requires a sequence of at least 24 steps, got {len(df_engineered)}")
        
    # 1. Scale temporal features
    df_scaled = scale_temporal(df_engineered)
    
    # 2. Extract last 24 steps
    temporal_cols = get_temporal_feature_names()
    last_seq = df_scaled.iloc[-24:][temporal_cols].values # (24, 41)
    
    # 3. Scale static features
    scaled_static = scale_static(lat, lon, city_encoded) # (3,)
    
    # 4. Flatten and concatenate to form shape (1, 987)
    flat_temp = last_seq.reshape(1, 24 * 41) # (1, 984)
    flat_static = scaled_static.reshape(1, 3) # (1, 3)
    feature_vector = np.hstack([flat_temp, flat_static]) # (1, 987)
    
    # 5. Predict
    preds_scaled = lr_model.predict(feature_vector) # (1, 6)
    
    # 6. Inverse scale targets
    preds_raw = inverse_scale_targets(preds_scaled)[0] # (6,)
    
    return {
        24: {"pm25": float(preds_raw[0]), "no2": float(preds_raw[3])},
        48: {"pm25": float(preds_raw[1]), "no2": float(preds_raw[4])},
        72: {"pm25": float(preds_raw[2]), "no2": float(preds_raw[5])}
    }
