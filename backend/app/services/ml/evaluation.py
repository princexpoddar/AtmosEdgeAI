import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, List
from sklearn.metrics import mean_absolute_error, r2_score

from backend.app.services.ml.config import MODELS_DIR

logger = logging.getLogger(__name__)

METRICS_JSON_PATH = os.path.join(MODELS_DIR, "metrics.json")
METRICS_CSV_PATH = os.path.join(MODELS_DIR, "metrics.csv")

def calculate_mape(actual: np.ndarray, predicted: np.ndarray, epsilon: float = 1.0) -> float:
    """
    Computes Mean Absolute Percentage Error (MAPE).
    Filters out actual values < epsilon to avoid division by zero or inflated percentages for tiny values.
    """
    mask = np.abs(actual) >= epsilon
    if not np.any(mask):
        return 0.0
    return float(np.mean(np.abs(actual[mask] - predicted[mask]) / np.abs(actual[mask])) * 100.0)

def evaluate_predictions(
    y_true: np.ndarray, 
    y_pred: np.ndarray
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """
    Computes MAE, RMSE, R2, and MAPE for:
    - 24h, 48h, 72h PM2.5
    - 24h, 48h, 72h NO2
    
    y_true: np.ndarray of shape (N, 6)
    y_pred: np.ndarray of shape (N, 6)
    """
    targets = [
        ("pm25_24h", 0), ("pm25_48h", 1), ("pm25_72h", 2),
        ("no2_24h", 3), ("no2_48h", 4), ("no2_72h", 5)
    ]
    
    metrics_dict = {}
    rows = []
    
    for name, idx in targets:
        true_val = y_true[:, idx]
        pred_val = y_pred[:, idx]
        
        mae = float(mean_absolute_error(true_val, pred_val))
        rmse = float(np.sqrt(np.mean((true_val - pred_val) ** 2)))
        r2 = float(r2_score(true_val, pred_val))
        mape = calculate_mape(true_val, pred_val)
        
        metrics_dict[name] = {
            "MAE": mae,
            "RMSE": rmse,
            "R2": r2,
            "MAPE": mape
        }
        
        rows.append({
            "Target": name,
            "MAE": round(mae, 4),
            "RMSE": round(rmse, 4),
            "R2": round(r2, 4),
            "MAPE": round(mape, 4)
        })
        
    metrics_df = pd.DataFrame(rows)
    return metrics_dict, metrics_df


def save_metrics(metrics_dict: Dict[str, Any], metrics_df: pd.DataFrame) -> None:
    """
    Saves evaluation metrics to JSON and CSV in the models directory.
    """
    try:
        os.makedirs(MODELS_DIR, exist_ok=True)
        
        # Save JSON
        with open(METRICS_JSON_PATH, "w") as f:
            json.dump(metrics_dict, f, indent=2)
            
        # Save CSV
        metrics_df.to_csv(METRICS_CSV_PATH, index=False)
        
        logger.info(f"Successfully saved test evaluation metrics to {METRICS_JSON_PATH} and {METRICS_CSV_PATH}")
    except Exception as e:
        logger.error(f"Failed to save metrics: {e}")
