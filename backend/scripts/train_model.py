"""
train_model.py
==============
Entry point for retraining the improved GlobalCNNLSTMForecaster (v2).

Usage:
    python -m backend.scripts.train_model

What this does:
  1. Loads the existing station_dataset.parquet
  2. Runs DatasetBuilder.generate_all_splits() to:
       - Apply the new scaler separation (scaler_X on 44 input cols, scaler_y on pm25/no2)
       - Build seq_len=72 sequences with spatial neighbour features (50 features total)
       - Save updated global_scaler.pkl and station_id_map.json
  3. Creates SpatiotemporalDataset instances and DataLoaders
  4. Trains the new CNN-LSTM v2 with:
       - Huber loss, LR warmup + cosine annealing
       - hidden_dim=128, 3 LSTM layers, TemporalAttention, LayerNorm
       - dropout=0.35, weight_decay=5e-4
  5. Evaluates on the test set and saves metrics.json
  6. Saves updated dataset_splits.pkl for use in run_evaluation_and_viz.py
"""
import os
import sys
import json
import pickle
import logging
import numpy as np
import torch
from torch.utils.data import DataLoader

# Ensure project root is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app.services.ml.config import config, MODELS_DIR
from backend.app.services.ml.dataset_builder import DatasetBuilder
from backend.app.services.ml.engine import train_model, evaluate_on_test, set_seed
from backend.app.services.ml.evaluation import evaluate_predictions, save_metrics
from backend.app.services.ml.preprocessing import SpatiotemporalDataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("train_model")

SPLITS_PATH = os.path.join(MODELS_DIR, "dataset_splits.pkl")
PARQUET_PATH = os.path.join(PROJECT_ROOT, "backend", "data", "station_dataset.parquet")


def main():
    set_seed(config.random_seed)

    # ------------------------------------------------------------------
    # 1. Build dataset
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  Phase 1 — DatasetBuilder")
    print("=" * 60)

    builder = DatasetBuilder(
        parquet_path=PARQUET_PATH,
        seq_len=config.seq_len,           # 72
        k_neighbours=config.k_neighbours, # 3
    )

    print(f"  seq_len       : {config.seq_len}")
    print(f"  k_neighbours  : {config.k_neighbours}")
    print(f"  parquet       : {PARQUET_PATH}")

    splits = builder.generate_all_splits()

    train_X, train_station, train_static, train_y = splits["train"]
    val_X,   val_station,   val_static,   val_y   = splits["val"]
    test_X,  test_station,  test_static,  test_y  = splits["test"]

    print(f"\n  Train: X={train_X.shape}, y={train_y.shape}")
    print(f"  Val:   X={val_X.shape},   y={val_y.shape}")
    print(f"  Test:  X={test_X.shape},  y={test_y.shape}")

    # Persist splits for evaluation script
    os.makedirs(MODELS_DIR, exist_ok=True)
    with open(SPLITS_PATH, "wb") as f:
        pickle.dump({"train": splits["train"], "val": splits["val"], "test": splits["test"]}, f)
    print(f"\n  Saved dataset splits -> {SPLITS_PATH}")

    # ------------------------------------------------------------------
    # 2. Create DataLoaders
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  Phase 2 — DataLoaders")
    print("=" * 60)

    train_dataset = SpatiotemporalDataset(train_X, train_station, train_static, train_y)
    val_dataset   = SpatiotemporalDataset(val_X,   val_station,   val_static,   val_y)
    test_dataset  = SpatiotemporalDataset(test_X,  test_station,  test_static,  test_y)

    train_loader = DataLoader(
        train_dataset, batch_size=config.batch_size, shuffle=True,  num_workers=0, pin_memory=False
    )
    val_loader = DataLoader(
        val_dataset,   batch_size=config.batch_size, shuffle=False, num_workers=0, pin_memory=False
    )
    test_loader = DataLoader(
        test_dataset,  batch_size=config.batch_size, shuffle=False, num_workers=0, pin_memory=False
    )

    temporal_dim = train_X.shape[2]   # 50
    static_dim   = train_static.shape[1]  # 3
    num_wards    = len(builder.station_id_map)

    print(f"  temporal_dim  : {temporal_dim}")
    print(f"  static_dim    : {static_dim}")
    print(f"  num_wards     : {num_wards}")
    print(f"  train batches : {len(train_loader)}")
    print(f"  val batches   : {len(val_loader)}")

    # ------------------------------------------------------------------
    # 3. Train
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  Phase 3 — Training CNN-LSTM v2")
    print("=" * 60)
    print(f"  hidden_dim    : {config.hidden_dim}")
    print(f"  num_layers    : {config.num_lstm_layers}")
    print(f"  dropout       : {config.dropout}")
    print(f"  weight_decay  : {config.weight_decay}")
    print(f"  lr            : {config.learning_rate}")
    print(f"  warmup_epochs : {config.warmup_epochs}")
    print(f"  huber_delta   : {config.huber_delta}")
    print(f"  epochs        : {config.epochs}")
    print(f"  patience      : {config.patience}")

    model, train_losses, val_losses = train_model(
        train_loader=train_loader,
        val_loader=val_loader,
        temporal_dim=temporal_dim,
        static_dim=static_dim,
        num_wards=num_wards,
    )

    # ------------------------------------------------------------------
    # 4. Evaluate on test set
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  Phase 4 — Test Set Evaluation")
    print("=" * 60)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    # Load scaler_y for unscaled metrics
    scaler_y = builder.scaler_y

    test_metrics = evaluate_on_test(
        model=model,
        test_loader=test_loader,
        device=device,
        scaler_y=scaler_y,
        use_amp=(device.type == "cuda"),
    )

    print("\n  Scaled metrics (test set):")
    for k, v in test_metrics.items():
        if "unscaled" not in k:
            print(f"    {k:30s}: {v:.4f}")

    print("\n  Unscaled metrics (µg/m³):")
    for k, v in test_metrics.items():
        if "unscaled" in k:
            print(f"    {k:40s}: {v:.2f}")

    # Save metrics.json
    metrics_path = os.path.join(MODELS_DIR, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(test_metrics, f, indent=2)
    print(f"\n  Saved test metrics -> {metrics_path}")

    # Save training curve metrics
    cnn_lstm_metrics = {
        "train_losses": train_losses,
        "val_losses":   val_losses,
        "test":         test_metrics,
    }
    with open(os.path.join(MODELS_DIR, "cnn_lstm_metrics.json"), "w") as f:
        json.dump(cnn_lstm_metrics, f, indent=2)

    # ------------------------------------------------------------------
    # 5. Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  Training complete")
    print("=" * 60)
    print(f"  Overall MAE  (scaled)  : {test_metrics['overall_mae']:.4f}")
    print(f"  Overall RMSE (scaled)  : {test_metrics['overall_rmse']:.4f}")
    lr_baseline = 0.488
    if test_metrics["overall_mae"] < lr_baseline:
        print(f"  [PASS] Beats LR baseline ({lr_baseline}) by {lr_baseline - test_metrics['overall_mae']:.4f}")
    else:
        gap = test_metrics["overall_mae"] - lr_baseline
        print(f"  [FAIL] Still {gap:.4f} above LR baseline ({lr_baseline}) -- consider more epochs or tuning")
    print(f"\n  Model checkpoint : {os.path.join(MODELS_DIR, 'global_model.pth')}")
    print(f"  Scalers          : {os.path.join(MODELS_DIR, 'global_scaler.pkl')}")


if __name__ == "__main__":
    main()
