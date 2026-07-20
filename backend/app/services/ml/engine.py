import os
import random
import logging
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from typing import Tuple, Dict, List

from backend.app.services.ml.config import config, MODELS_DIR
from backend.app.services.ml.model import TCNForecaster

logger = logging.getLogger(__name__)
CHECKPOINT_PATH = os.path.join(MODELS_DIR, "global_model.pth")

# Overfitting detection constants
_OVERFIT_RATIO_THRESHOLD = 2.0
_OVERFIT_WINDOW = 5
_OVERFIT_START_EPOCH = 10


def set_seed(seed: int = 42) -> None:
    """Sets random seeds for full reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = False
    torch.backends.cudnn.benchmark = True
    logger.info(f"Random seed set to {seed}")


class EarlyStopping:
    """
    Stops training when val_loss does not improve by min_delta for `patience`
    consecutive epochs. Resets counter on every new best.
    """

    def __init__(self, patience: int = 10, min_delta: float = 1e-5):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = float("inf")
        self.early_stop = False

    def check(self, val_loss: float) -> bool:
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        return self.early_stop


def _run_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    scaler,
    device: torch.device,
    use_amp: bool,
    is_train: bool,
) -> float:
    """
    Runs a single train or validation epoch.
    Returns average Huber loss over the full dataset.
    """
    model.train() if is_train else model.eval()
    total_loss = 0.0
    n_samples = 0

    ctx = torch.enable_grad if is_train else torch.no_grad
    with ctx():
        for batch_x_temp, batch_x_ward, batch_x_static, batch_y in loader:
            batch_x_temp = batch_x_temp.to(device)
            batch_x_ward = batch_x_ward.to(device)
            batch_x_static = batch_x_static.to(device)
            batch_y = batch_y.to(device)
            bs = batch_x_temp.size(0)

            if is_train:
                optimizer.zero_grad()

            with torch.amp.autocast(device_type=device.type, enabled=use_amp):
                outputs = model(batch_x_temp, batch_x_ward, batch_x_static)
                loss = criterion(outputs, batch_y)

            if is_train:
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=config.grad_clip)
                scaler.step(optimizer)
                scaler.update()

            total_loss += loss.item() * bs
            n_samples += bs

    return total_loss / max(n_samples, 1)


def train_model(
    train_loader: DataLoader,
    val_loader: DataLoader,
    temporal_dim: int,
    static_dim: int,
    num_wards: int,
    checkpoint_path: str = CHECKPOINT_PATH,
) -> Tuple[TCNForecaster, List[float], List[float]]:
    """
    Trains the TCNForecaster with:
    - Huber loss
    - Linear LR warmup then CosineAnnealingWarmRestarts
    - AdamW with weight decay
    - Gradient clipping
    - Early stopping + overfitting guard
    """
    set_seed(config.random_seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Device: {device}")
    logger.info(f"Training on device: {device}")

    model = TCNForecaster(
        temporal_dim=temporal_dim,
        static_dim=static_dim,
        num_wards=num_wards,
        seq_len=config.seq_len,
        channels=config.hidden_dim,
        dropout=config.dropout,
        output_dim=6,
    ).to(device)

    # Huber loss — quadratic for small residuals, linear for large spikes
    criterion = nn.HuberLoss(delta=config.huber_delta)

    optimizer = optim.AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    # Linear warmup scheduler (epochs 1 .. warmup_epochs)
    warmup_epochs = config.warmup_epochs

    def _warmup_lambda(epoch: int) -> float:
        if epoch < warmup_epochs:
            return float(epoch + 1) / float(max(warmup_epochs, 1))
        return 1.0

    warmup_scheduler = optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=_warmup_lambda)

    # Cosine annealing after warmup (T_0 chosen relative to patience)
    T_0 = max(10, config.patience // 2)
    cosine_scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=T_0, T_mult=2, eta_min=1e-6
    )

    early_stopper = EarlyStopping(patience=config.patience)

    use_amp = device.type == "cuda"
    grad_scaler = torch.amp.GradScaler(device=device.type, enabled=use_amp)

    train_losses: List[float] = []
    val_losses: List[float] = []
    best_val_loss = float("inf")
    best_epoch = 0

    print(f"\n  {'Epoch':>6} | {'Train':>10} | {'Val':>10} | {'V/T Ratio':>10} | {'LR':>10} | Status")
    print(f"  {'-'*6}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}")

    for epoch in range(1, config.epochs + 1):
        # Training pass
        epoch_train = _run_epoch(
            model, train_loader, criterion, optimizer,
            grad_scaler, device, use_amp, is_train=True,
        )

        # Validation pass
        epoch_val = _run_epoch(
            model, val_loader, criterion, optimizer,
            grad_scaler, device, use_amp, is_train=False,
        )

        train_losses.append(epoch_train)
        val_losses.append(epoch_val)

        # Step schedulers
        if epoch <= warmup_epochs:
            warmup_scheduler.step()
        else:
            cosine_scheduler.step(epoch - warmup_epochs - 1)
        current_lr = optimizer.param_groups[0]["lr"]

        vt_ratio = epoch_val / max(epoch_train, 1e-8)

        # Save best checkpoint on strict val_loss improvement
        status = ""
        if epoch_val < best_val_loss:
            best_val_loss = epoch_val
            best_epoch = epoch
            status = "[best]"
            checkpoint = {
                "epoch": epoch,
                "model_type": "TCNForecaster",
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_loss": best_val_loss,
                "config": {
                    "temporal_dim": temporal_dim,
                    "static_dim": static_dim,
                    "num_wards": num_wards,
                    "channels": config.hidden_dim,
                    "dropout": config.dropout,
                    "seq_len": config.seq_len,
                },
            }
            try:
                os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)
                torch.save(checkpoint, checkpoint_path)
                logger.info(f"Epoch {epoch}: New best checkpoint (val_loss={best_val_loss:.6f})")
            except Exception as e:
                logger.error(f"Failed saving checkpoint: {e}")

        # Console epoch log
        print(
            f"  {epoch:>6} | {epoch_train:>10.6f} | {epoch_val:>10.6f} | "
            f"{vt_ratio:>10.3f} | {current_lr:>10.2e} | {status}"
        )
        logger.info(
            f"Epoch {epoch}/{config.epochs} | Train={epoch_train:.6f} | Val={epoch_val:.6f} | "
            f"V/T={vt_ratio:.3f} | LR={current_lr:.2e} | BestValEpoch={best_epoch}"
        )

        # Overfitting guard: warn when val/train > 2.0 for _OVERFIT_WINDOW consecutive epochs
        if epoch >= _OVERFIT_START_EPOCH and len(train_losses) >= _OVERFIT_WINDOW:
            recent_vt = [
                v / max(t, 1e-8)
                for v, t in zip(
                    val_losses[-_OVERFIT_WINDOW:],
                    train_losses[-_OVERFIT_WINDOW:],
                )
            ]
            if all(r > _OVERFIT_RATIO_THRESHOLD for r in recent_vt):
                logger.warning(
                    f"overfitting detected: val/train ratio > {_OVERFIT_RATIO_THRESHOLD} "
                    f"for {_OVERFIT_WINDOW} consecutive epochs "
                    f"(latest ratios: {[round(r, 2) for r in recent_vt]})"
                )

        # Early stopping
        if early_stopper.check(epoch_val):
            print(f"\n  Early stopping at epoch {epoch} (no improvement for {config.patience} epochs).")
            logger.info(f"Early stopping at epoch {epoch}")
            break

    # Reload best weights before returning
    if os.path.exists(checkpoint_path):
        try:
            ckpt = torch.load(checkpoint_path, map_location=device, weights_only=True)
            model.load_state_dict(ckpt["model_state_dict"])
            print(f"\n  Best model restored from epoch {best_epoch} (val_loss={best_val_loss:.6f})")
            logger.info(f"Best weights loaded from epoch {best_epoch}")
        except Exception as e:
            logger.error(f"Failed to load best weights: {e}")

    return model, train_losses, val_losses


def evaluate_on_test(
    model: TCNForecaster,
    test_loader: DataLoader,
    device: torch.device,
    scaler_y=None,
    use_amp: bool = False,
) -> Dict[str, float]:
    """
    Evaluates the best-checkpoint model on the untouched test set.
    Returns per-horizon MAE and RMSE in both scaled and unscaled units.

    Pass scaler_y to get unscaled MAE and R² alongside scaled metrics.
    """
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    model.eval()
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for batch_x_temp, batch_x_ward, batch_x_static, batch_y in test_loader:
            batch_x_temp = batch_x_temp.to(device)
            batch_x_ward = batch_x_ward.to(device)
            batch_x_static = batch_x_static.to(device)

            with torch.amp.autocast(device_type=device.type, enabled=use_amp):
                outputs = model(batch_x_temp, batch_x_ward, batch_x_static)

            all_preds.append(outputs.cpu().numpy())
            all_targets.append(batch_y.numpy())

    preds = np.vstack(all_preds)    # (N, 6)
    targets = np.vstack(all_targets)  # (N, 6)

    names = ["pm25_24h", "pm25_48h", "pm25_72h", "no2_24h", "no2_48h", "no2_72h"]
    metrics: Dict[str, float] = {}

    for i, name in enumerate(names):
        mae = float(mean_absolute_error(targets[:, i], preds[:, i]))
        rmse = float(np.sqrt(mean_squared_error(targets[:, i], preds[:, i])))
        r2 = float(r2_score(targets[:, i], preds[:, i]))
        metrics[f"{name}_mae"] = mae
        metrics[f"{name}_rmse"] = rmse
        metrics[f"{name}_r2"] = r2

    # Unscaled metrics using scaler_y
    if scaler_y is not None:
        pm25_mean, pm25_std = float(scaler_y.mean_[0]), float(scaler_y.scale_[0])
        no2_mean,  no2_std  = float(scaler_y.mean_[1]), float(scaler_y.scale_[1])

        preds_unscaled = preds.copy()
        targets_unscaled = targets.copy()

        for col in range(3):   # pm25 horizons
            preds_unscaled[:, col]   = preds[:, col]   * pm25_std + pm25_mean
            targets_unscaled[:, col] = targets[:, col] * pm25_std + pm25_mean
        for col in range(3, 6):  # no2 horizons
            preds_unscaled[:, col]   = preds[:, col]   * no2_std  + no2_mean
            targets_unscaled[:, col] = targets[:, col] * no2_std  + no2_mean

        for i, name in enumerate(names):
            u_mae = float(mean_absolute_error(targets_unscaled[:, i], preds_unscaled[:, i]))
            u_r2  = float(r2_score(targets_unscaled[:, i], preds_unscaled[:, i]))
            metrics[f"{name}_unscaled_mae"] = u_mae
            metrics[f"{name}_unscaled_r2"]  = u_r2

    # Aggregate scaled summaries
    pm25_mae  = float(np.mean([metrics["pm25_24h_mae"],  metrics["pm25_48h_mae"],  metrics["pm25_72h_mae"]]))
    no2_mae   = float(np.mean([metrics["no2_24h_mae"],   metrics["no2_48h_mae"],   metrics["no2_72h_mae"]]))
    pm25_rmse = float(np.mean([metrics["pm25_24h_rmse"], metrics["pm25_48h_rmse"], metrics["pm25_72h_rmse"]]))
    no2_rmse  = float(np.mean([metrics["no2_24h_rmse"],  metrics["no2_48h_rmse"],  metrics["no2_72h_rmse"]]))

    metrics["pm25_avg_mae"]  = pm25_mae
    metrics["no2_avg_mae"]   = no2_mae
    metrics["pm25_avg_rmse"] = pm25_rmse
    metrics["no2_avg_rmse"]  = no2_rmse
    metrics["overall_mae"]   = float(np.mean([pm25_mae, no2_mae]))
    metrics["overall_rmse"]  = float(np.mean([pm25_rmse, no2_rmse]))

    return metrics
