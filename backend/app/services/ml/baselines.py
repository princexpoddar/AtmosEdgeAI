import os
import pickle
import logging
import numpy as np
from typing import Dict, Any, Tuple
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

from backend.app.services.ml.config import config, BASE_DIR, MODELS_DIR

logger = logging.getLogger(__name__)

class BaselineTrainer:
    def __init__(self, models_dir: str = MODELS_DIR):
        self.models_dir = models_dir
        os.makedirs(self.models_dir, exist_ok=True)
        
        self.lr_path = os.path.join(self.models_dir, "baseline_lr.pkl")
        self.rf_path = os.path.join(self.models_dir, "baseline_rf.pkl")
        self.xgb_path = os.path.join(self.models_dir, "baseline_xgb.pkl")

    def flatten_data(self, X_temp: np.ndarray, X_static: np.ndarray) -> np.ndarray:
        """
        Flattens sequential temporal inputs (N, seq_len, feat_dim) to (N, seq_len * feat_dim)
        and concatenates with static metadata features (N, static_dim).
        """
        N, seq_len, feat_dim = X_temp.shape
        X_temp_flat = X_temp.reshape(N, seq_len * feat_dim)
        return np.hstack([X_temp_flat, X_static])

    def evaluate(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """
        Computes regression metrics for PM2.5 and NO2 targets.
        y_true, y_pred shape: (N, 6)
        Columns: pm25_24, pm25_48, pm25_72, no2_24, no2_48, no2_72
        """
        metrics = {}
        
        targets = ["pm25_24", "pm25_48", "pm25_72", "no2_24", "no2_48", "no2_72"]
        for idx, name in enumerate(targets):
            mae = mean_absolute_error(y_true[:, idx], y_pred[:, idx])
            rmse = np.sqrt(mean_squared_error(y_true[:, idx], y_pred[:, idx]))
            r2 = r2_score(y_true[:, idx], y_pred[:, idx])
            
            metrics[f"{name}_mae"] = float(mae)
            metrics[f"{name}_rmse"] = float(rmse)
            metrics[f"{name}_r2"] = float(r2)
            
        # Summary metrics
        metrics["pm25_mae"] = float(np.mean([metrics["pm25_24_mae"], metrics["pm25_48_mae"], metrics["pm25_72_mae"]]))
        metrics["pm25_rmse"] = float(np.mean([metrics["pm25_24_rmse"], metrics["pm25_48_rmse"], metrics["pm25_72_rmse"]]))
        metrics["pm25_r2"] = float(np.mean([metrics["pm25_24_r2"], metrics["pm25_48_r2"], metrics["pm25_72_r2"]]))
        
        metrics["no2_mae"] = float(np.mean([metrics["no2_24_mae"], metrics["no2_48_mae"], metrics["no2_72_mae"]]))
        metrics["no2_rmse"] = float(np.mean([metrics["no2_24_rmse"], metrics["no2_48_rmse"], metrics["no2_72_rmse"]]))
        metrics["no2_r2"] = float(np.mean([metrics["no2_24_r2"], metrics["no2_48_r2"], metrics["no2_72_r2"]]))
        
        metrics["overall_mae"] = float(np.mean([metrics["pm25_mae"], metrics["no2_mae"]]))
        metrics["overall_rmse"] = float(np.mean([metrics["pm25_rmse"], metrics["no2_rmse"]]))
        metrics["overall_r2"] = float(np.mean([metrics["pm25_r2"], metrics["no2_r2"]]))
        
        return metrics

    def run_persistence(self, X_temp: np.ndarray, y_true: np.ndarray) -> Dict[str, float]:
        """
        Persistence Baseline: predicted value at t+k is simply the target value at t.
        PM2.5 index: 0, NO2 index: 1.
        X_temp shape: (N, seq_len, feat_dim) where pm25 is index 0 and no2 is index 1.
        """
        # Take target values from the last timestep in the sequence (index -1)
        pm25_t = X_temp[:, -1, 0]
        no2_t = X_temp[:, -1, 1]
        
        N = len(X_temp)
        y_pred = np.zeros_like(y_true)
        
        # Broadcast the t-value to all forecast horizons (t+24, t+48, t+72)
        y_pred[:, 0] = pm25_t
        y_pred[:, 1] = pm25_t
        y_pred[:, 2] = pm25_t
        
        y_pred[:, 3] = no2_t
        y_pred[:, 4] = no2_t
        y_pred[:, 5] = no2_t
        
        return self.evaluate(y_true, y_pred)

    def train_linear_regression(self, X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        logger.info("Training Baseline: Linear Regression...")
        model = LinearRegression()
        model.fit(X_train, y_train)
        
        with open(self.lr_path, "wb") as f:
            pickle.dump(model, f)
            
        y_pred = model.predict(X_test)
        return self.evaluate(y_test, y_pred)

    def train_random_forest(self, X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        logger.info("Training Baseline: Random Forest Regressor...")
        # Use low depth & estimators to keep baseline training execution very fast
        model = RandomForestRegressor(n_estimators=50, max_depth=8, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
        
        with open(self.rf_path, "wb") as f:
            pickle.dump(model, f)
            
        y_pred = model.predict(X_test)
        return self.evaluate(y_test, y_pred)

    def train_xgboost(self, X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        logger.info("Training Baseline: XGBoost...")
        # XGBoost MultiOutputRegressor
        base_xgb = xgb.XGBRegressor(n_estimators=50, max_depth=5, learning_rate=0.1, random_state=42, n_jobs=-1)
        model = MultiOutputRegressor(base_xgb)
        model.fit(X_train, y_train)
        
        with open(self.xgb_path, "wb") as f:
            pickle.dump(model, f)
            
        y_pred = model.predict(X_test)
        return self.evaluate(y_test, y_pred)
