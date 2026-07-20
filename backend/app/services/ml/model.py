import torch
import torch.nn as nn
from typing import Optional


class TemporalBlock(nn.Module):
    """
    Residual block for TCN: two dilated causal convolutions + skip connection.
    Uses plain Conv1d (no weight_norm) to avoid CUDA hang on PyTorch 2.6.
    """
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int,
                 dilation: int, dropout: float = 0.5):
        super().__init__()
        pad = (kernel_size - 1) * dilation
        self.conv1 = nn.Conv1d(in_channels, out_channels, kernel_size, padding=pad, dilation=dilation)
        self.conv2 = nn.Conv1d(out_channels, out_channels, kernel_size, padding=pad, dilation=dilation)
        self.pad = pad
        self.relu = nn.ReLU()
        self.drop = nn.Dropout(dropout)
        self.norm1 = nn.BatchNorm1d(out_channels)
        self.norm2 = nn.BatchNorm1d(out_channels)
        self.downsample = nn.Conv1d(in_channels, out_channels, 1) if in_channels != out_channels else None
        nn.init.kaiming_normal_(self.conv1.weight, nonlinearity="relu")
        nn.init.kaiming_normal_(self.conv2.weight, nonlinearity="relu")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.conv1(x)
        if self.pad > 0:
            out = out[:, :, :-self.pad]
        out = self.drop(self.relu(self.norm1(out)))
        out = self.conv2(out)
        if self.pad > 0:
            out = out[:, :, :-self.pad]
        out = self.drop(self.relu(self.norm2(out)))
        res = x if self.downsample is None else self.downsample(x)
        return self.relu(out + res)


class TCNForecaster(nn.Module):
    """
    Temporal Convolutional Network for multi-horizon air quality forecasting.
    ~300k parameters, 3 dilated residual blocks, global average pooling.
    """
    def __init__(self, temporal_dim: int, static_dim: int, num_wards: int = 100,
                 embedding_dim: int = 16, seq_len: int = 48, channels: int = 64,
                 kernel_size: int = 3, num_levels: int = 4, dropout: float = 0.4,
                 output_dim: int = 6):
        super().__init__()
        self.ward_embedding = nn.Embedding(num_wards, embedding_dim)
        layers = []
        in_ch = temporal_dim
        for i in range(num_levels):
            layers.append(TemporalBlock(in_ch, channels, kernel_size, 2 ** i, dropout))
            in_ch = channels
        self.tcn = nn.Sequential(*layers)
        fc_in = channels + embedding_dim + static_dim
        self.fc = nn.Sequential(
            nn.Linear(fc_in, channels), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(channels, output_dim),
        )

    def forward(self, x_temporal, x_ward, x_static):
        x = self.tcn(x_temporal.permute(0, 2, 1))  # (B, channels, T)
        context = x.mean(dim=-1)                    # global avg pool
        combined = torch.cat([context, self.ward_embedding(x_ward), x_static], dim=1)
        return self.fc(combined)


class TemporalAttention(nn.Module):
    """Kept for checkpoint compatibility."""
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.attn = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, lstm_out):
        return (torch.softmax(self.attn(lstm_out), dim=1) * lstm_out).sum(dim=1)


class GlobalCNNLSTMForecaster(nn.Module):
    """Legacy CNN-LSTM — kept for loading old checkpoints only."""
    def __init__(self, temporal_dim, static_dim, num_wards=100, embedding_dim=16,
                 seq_len=72, hidden_dim=128, num_layers=3, dropout=0.35, output_dim=6):
        super().__init__()
        self.ward_embedding = nn.Embedding(num_wards, embedding_dim)
        self.conv1d = nn.Conv1d(temporal_dim, hidden_dim, 3, padding=1)
        self.bn = nn.BatchNorm1d(hidden_dim)
        self.relu = nn.ReLU()
        self.dropout_conv = nn.Dropout(dropout)
        self.layer_norm = nn.LayerNorm(hidden_dim)
        self.lstm = nn.LSTM(hidden_dim, hidden_dim, num_layers, batch_first=True,
                            dropout=dropout if num_layers > 1 else 0.0)
        self.attention = TemporalAttention(hidden_dim)
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim + embedding_dim + static_dim, hidden_dim),
            nn.ReLU(), nn.Dropout(dropout), nn.Linear(hidden_dim, output_dim))

    def forward(self, x_temporal, x_ward, x_static):
        x = self.dropout_conv(self.relu(self.bn(self.conv1d(x_temporal.permute(0, 2, 1)))))
        x = self.layer_norm(x.permute(0, 2, 1))
        lstm_out, _ = self.lstm(x)
        context = self.attention(lstm_out)
        return self.fc(torch.cat([context, self.ward_embedding(x_ward), x_static], dim=1))
