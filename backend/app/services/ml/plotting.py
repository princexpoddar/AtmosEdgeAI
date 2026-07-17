import os
import logging
import numpy as np
import matplotlib
# Use Agg backend for non-interactive plot generation
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from backend.app.services.ml.config import MODELS_DIR

logger = logging.getLogger(__name__)

def plot_learning_curves(
    train_losses: list, 
    val_losses: list, 
    save_dir: str = MODELS_DIR
) -> None:
    """
    Plots training and validation MSE loss curves over epochs.
    """
    plt.figure(figsize=(10, 6))
    plt.plot(train_losses, label="Training Loss", color="royalblue", lw=2)
    plt.plot(val_losses, label="Validation Loss", color="orange", lw=2)
    plt.xlabel("Epochs", fontsize=12)
    plt.ylabel("MSE Loss", fontsize=12)
    plt.title("Model Training and Validation Curves", fontsize=14, fontweight="bold")
    plt.legend(fontsize=11)
    plt.grid(True, linestyle="--", alpha=0.6)
    
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, "learning_curves.png")
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved learning curves plot to {filepath}")

def plot_prediction_vs_actual(
    y_true: np.ndarray, 
    y_pred: np.ndarray, 
    save_dir: str = MODELS_DIR
) -> None:
    """
    Generates prediction vs actual scatter plots for PM2.5 and NO2 at 24h, 48h, 72h.
    """
    targets = [
        ("PM2.5 24h", 0), ("PM2.5 48h", 1), ("PM2.5 72h", 2),
        ("NO2 24h", 3), ("NO2 48h", 4), ("NO2 72h", 5)
    ]
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()
    
    for i, (name, idx) in enumerate(targets):
        ax = axes[i]
        true = y_true[:, idx]
        pred = y_pred[:, idx]
        
        # Scatter plot
        ax.scatter(true, pred, alpha=0.4, color="teal", edgecolors="w", s=15)
        
        # Ideal identity line (y = x)
        min_val = min(true.min(), pred.min())
        max_val = max(true.max(), pred.max())
        ax.plot([min_val, max_val], [min_val, max_val], 'r--', lw=2, label="Ideal")
        
        ax.set_xlabel("Actual Values", fontsize=10)
        ax.set_ylabel("Predicted Values", fontsize=10)
        ax.set_title(name, fontsize=12, fontweight="bold")
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend()
        
    plt.suptitle("Prediction vs. Actual (Test Set)", fontsize=16, fontweight="bold", y=0.98)
    plt.tight_layout()
    
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, "prediction_vs_actual.png")
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved prediction vs actual plot to {filepath}")

def plot_residuals(
    y_true: np.ndarray, 
    y_pred: np.ndarray, 
    save_dir: str = MODELS_DIR
) -> None:
    """
    Generates residual histograms showing error distributions for PM2.5 and NO2.
    """
    targets = [
        ("PM2.5 24h", 0), ("PM2.5 48h", 1), ("PM2.5 72h", 2),
        ("NO2 24h", 3), ("NO2 48h", 4), ("NO2 72h", 5)
    ]
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()
    
    for i, (name, idx) in enumerate(targets):
        ax = axes[i]
        residuals = y_true[:, idx] - y_pred[:, idx]
        
        # Plot distribution histogram
        ax.hist(residuals, bins=40, color="crimson", alpha=0.7, edgecolor="black")
        ax.axvline(0, color="black", linestyle="--", lw=2)
        
        ax.set_xlabel("Residual (Actual - Predicted)", fontsize=10)
        ax.set_ylabel("Frequency", fontsize=10)
        ax.set_title(f"Residuals for {name}", fontsize=12, fontweight="bold")
        ax.grid(True, linestyle="--", alpha=0.5)
        
    plt.suptitle("Residual Error Distributions (Test Set)", fontsize=16, fontweight="bold", y=0.98)
    plt.tight_layout()
    
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, "residuals.png")
    plt.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info(f"Saved residuals distribution plot to {filepath}")
