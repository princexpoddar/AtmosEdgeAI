"""
train_baselines.py
==================
Retrain XGBoost and Linear Regression on the new properly-scaled 50-feature data.

Usage:
    python -m backend.scripts.train_baselines

Uses the dataset_splits.pkl built by train_model.py (run that first if splits don't exist).
If splits don't exist, builds them automatically.

Saves:
  - backend/models/baseline_lr.pkl       (replaces old one)
  - backend/models/baseline_xgb.pkl      (replaces old one)
  - backend/models/baseline_metrics.json (updated)
"""
import os
import sys
import json
import pickle
import logging
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sklearn.linear_model import Ridge
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

from backend.app.services.ml.config import config, MODELS_DIR
from backend.app.services.ml.dataset_builder import DatasetBuilder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_baselines")

SPLITS_PATH   = os.path.join(MODELS_DIR, "dataset_splits.pkl")
LR_PATH       = os.path.join(MODELS_DIR, "baseline_lr.pkl")
XGB_PATH      = os.path.join(MODELS_DIR, "baseline_xgb.pkl")
METRICS_PATH  = os.path.join(MODELS_DIR, "baseline_metrics.json")
PARQUET_PATH  = os.path.join(PROJECT_ROOT, "backend", "data", "station_dataset.parquet")


def flatten(X_temp: np.ndarray, X_static: np.ndarray) -> np.ndarray:
    """Flatten (N, seq_len, feat_dim) + (N, 3) -> (N, seq_len*feat_dim + 3)."""
    N, T, D = X_temp.shape
    return np.hstack([X_temp.reshape(N, T * D), X_static])


def evaluate(y_true: np.ndarray, y_pred: np.ndarray, name: str) -> dict:
    targets = ["pm25_24h", "pm25_48h", "pm25_72h", "no2_24h", "no2_48h", "no2_72h"]
    m = {}
    for i, t in enumerate(targets):
        m[f"{t}_mae"]  = float(mean_absolute_error(y_true[:, i], y_pred[:, i]))
        m[f"{t}_rmse"] = float(np.sqrt(mean_squared_error(y_true[:, i], y_pred[:, i])))
        m[f"{t}_r2"]   = float(r2_score(y_true[:, i], y_pred[:, i]))
    m["pm25_avg_mae"] = float(np.mean([m["pm25_24h_mae"], m["pm25_48h_mae"], m["pm25_72h_mae"]]))
    m["no2_avg_mae"]  = float(np.mean([m["no2_24h_mae"],  m["no2_48h_mae"],  m["no2_72h_mae"]]))
    m["overall_mae"]  = float(np.mean([m["pm25_avg_mae"], m["no2_avg_mae"]]))
    m["overall_rmse"] = float(np.mean([
        np.mean([m["pm25_24h_rmse"], m["pm25_48h_rmse"], m["pm25_72h_rmse"]]),
        np.mean([m["no2_24h_rmse"],  m["no2_48h_rmse"],  m["no2_72h_rmse"]]),
    ]))
    print(f"\n  {name}")
    print(f"    Overall MAE  : {m['overall_mae']:.4f}")
    print(f"    Overall RMSE : {m['overall_rmse']:.4f}")
    print(f"    PM2.5 MAE    : {m['pm25_avg_mae']:.4f}")
    print(f"    NO2  MAE     : {m['no2_avg_mae']:.4f}")
    return m


def main():
    # ------------------------------------------------------------------
    # Load or build splits
    # ------------------------------------------------------------------
    if os.path.exists(SPLITS_PATH):
        print(f"Loading existing splits from {SPLITS_PATH}")
        with open(SPLITS_PATH, "rb") as f:
            splits = pickle.load(f)
        train_X, train_st, train_static, train_y = splits["train"]
        val_X,   val_st,   val_static,   val_y   = splits["val"]
        test_X,  test_st,  test_static,  test_y  = splits["test"]
    else:
        print("Splits not found — building dataset...")
        builder = DatasetBuilder(parquet_path=PARQUET_PATH,
                                 seq_len=config.seq_len,
                                 k_neighbours=config.k_neighbours)
        splits = builder.generate_all_splits()
        train_X, train_st, train_static, train_y = splits["train"]
        val_X,   val_st,   val_static,   val_y   = splits["val"]
        test_X,  test_st,  test_static,  test_y  = splits["test"]
        os.makedirs(MODELS_DIR, exist_ok=True)
        with open(SPLITS_PATH, "wb") as f:
            pickle.dump(splits, f)

    print(f"\n  Train: {train_X.shape}, Val: {val_X.shape}, Test: {test_X.shape}")

    # Combine train+val for baseline fitting (baselines don't need val for early stopping)
    combined_X = np.concatenate([train_X, val_X], axis=0)
    combined_static = np.concatenate([train_static, val_static], axis=0)
    combined_y = np.concatenate([train_y, val_y], axis=0)

    X_train_flat = flatten(combined_X, combined_static)
    X_test_flat  = flatten(test_X, test_static)

    print(f"  Flattened train: {X_train_flat.shape}")
    print(f"  Flattened test : {X_test_flat.shape}")

    all_metrics = {}

    # ------------------------------------------------------------------
    # Ridge Regression (replaces LR — more stable with high-dim input)
    # ------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("  Training Ridge Regression...")
    ridge = Ridge(alpha=1.0, fit_intercept=True)
    ridge.fit(X_train_flat, combined_y)
    lr_pred = ridge.predict(X_test_flat)
    all_metrics["ridge"] = evaluate(test_y, lr_pred, "Ridge Regression")

    with open(LR_PATH, "wb") as f:
        pickle.dump(ridge, f)
    print(f"  Saved -> {LR_PATH}")

    # ------------------------------------------------------------------
    # XGBoost
    # ------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("  Training XGBoost (this takes ~2-3 minutes)...")
    xgb_base = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        tree_method="hist",
        device="cuda",   # use GPU
    )
    xgb_model = MultiOutputRegressor(xgb_base, n_jobs=1)
    xgb_model.fit(X_train_flat, combined_y)
    xgb_pred = xgb_model.predict(X_test_flat)
    all_metrics["xgboost"] = evaluate(test_y, xgb_pred, "XGBoost")

    with open(XGB_PATH, "wb") as f:
        pickle.dump(xgb_model, f)
    print(f"  Saved -> {XGB_PATH}")

    # ------------------------------------------------------------------
    # Save metrics
    # ------------------------------------------------------------------
    with open(METRICS_PATH, "w") as f:
        json.dump(all_metrics, f, indent=2)
    print(f"\n  Saved baseline metrics -> {METRICS_PATH}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 50)
    print("  BASELINE SUMMARY")
    print("=" * 50)
    lr_mae  = all_metrics["ridge"]["overall_mae"]
    xgb_mae = all_metrics["xgboost"]["overall_mae"]
    old_lr  = 0.488
    print(f"  Ridge     MAE: {lr_mae:.4f}  ({'PASS' if lr_mae < old_lr else 'FAIL'} vs old LR {old_lr})")
    print(f"  XGBoost   MAE: {xgb_mae:.4f}  ({'PASS' if xgb_mae < old_lr else 'FAIL'} vs old LR {old_lr})")
    best = "Ridge" if lr_mae < xgb_mae else "XGBoost"
    print(f"\n  Best baseline: {best} (MAE={min(lr_mae, xgb_mae):.4f})")


if __name__ == "__main__":
    main()
