import torch
import torch.nn as nn
from typing import Dict, Any


class TemporalAttention(nn.Module):
    """
    Computes a softmax-weighted sum over LSTM hidden states across the time dimension.

    Input:  lstm_out  (B, T, hidden_dim)
    Output: context   (B, hidden_dim)

    The attention weights sum to 1.0 over the T dimension for every item in the batch.
    """

    def __init__(self, hidden_dim: int):
        super().__init__()
        self.attn = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, lstm_out: torch.Tensor) -> torch.Tensor:
        # scores: (B, T, 1)
        scores = self.attn(lstm_out)
        # weights: (B, T, 1) — softmax over time axis → sum to 1 over T
        weights = torch.softmax(scores, dim=1)
        # context: (B, hidden_dim)
        context = (weights * lstm_out).sum(dim=1)
        return context


class GlobalCNNLSTMForecaster(nn.Module):
    """
    Improved Global Forecasting CNN-LSTM Model with temporal attention.

    Architecture (to-be):
      x_temporal (B, 72, 50)
        -> Conv1D(50->hidden_dim, k=3, pad=1) -> BN -> ReLU -> Dropout
        -> LayerNorm(hidden_dim)
        -> LSTM(hidden_dim, hidden_dim, num_layers, dropout)  -> (B, 72, hidden_dim)
        -> TemporalAttention                                   -> context (B, hidden_dim)
        -> Cat[context, ward_emb(16), x_static(3)]            -> (B, hidden_dim+19)
        -> Linear -> ReLU -> Dropout -> Linear                -> (B, 6)

    Inputs:
      x_temporal : (B, seq_len, temporal_dim)
      x_ward     : (B,)             — integer station index for embedding
      x_static   : (B, static_dim)  — scaled [lat, lon, elevation]

    Output:
      (B, 6) — [pm25_24h, pm25_48h, pm25_72h, no2_24h, no2_48h, no2_72h]
    """

    def __init__(
        self,
        temporal_dim: int,
        static_dim: int,
        num_wards: int = 100,
        embedding_dim: int = 16,
        seq_len: int = 72,
        hidden_dim: int = 128,
        num_layers: int = 3,
        dropout: float = 0.35,
        output_dim: int = 6,
    ):
        super().__init__()
        self.seq_len = seq_len
        self.hidden_dim = hidden_dim

        # Ward / station embedding
        self.ward_embedding = nn.Embedding(
            num_embeddings=num_wards,
            embedding_dim=embedding_dim,
        )

        # 1-D Convolution over temporal dimension
        # Input to Conv1d: (B, temporal_dim, seq_len)
        self.conv1d = nn.Conv1d(
            in_channels=temporal_dim,
            out_channels=hidden_dim,
            kernel_size=3,
            padding=1,
        )
        self.bn = nn.BatchNorm1d(num_features=hidden_dim)
        self.relu = nn.ReLU()
        self.dropout_conv = nn.Dropout(p=dropout)

        # LayerNorm applied to LSTM inputs (after conv block, before LSTM)
        self.layer_norm = nn.LayerNorm(hidden_dim)

        # LSTM stack
        self.lstm = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        # Temporal attention over all LSTM output steps
        self.attention = TemporalAttention(hidden_dim)

        # Dense prediction head
        fc_input_dim = hidden_dim + embedding_dim + static_dim  # 128+16+3 = 147
        self.fc = nn.Sequential(
            nn.Linear(fc_input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(p=dropout),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(
        self,
        x_temporal: torch.Tensor,
        x_ward: torch.Tensor,
        x_static: torch.Tensor,
    ) -> torch.Tensor:
        # Permute for Conv1d: (B, temporal_dim, seq_len)
        x = x_temporal.permute(0, 2, 1)

        # Convolutional feature extraction
        x = self.dropout_conv(self.relu(self.bn(self.conv1d(x))))

        # Back to (B, seq_len, hidden_dim) for LSTM
        x = x.permute(0, 2, 1)

        # Layer normalisation before LSTM (stabilises deep LSTM training)
        x = self.layer_norm(x)

        # LSTM — produces all hidden states
        lstm_out, _ = self.lstm(x)  # (B, seq_len, hidden_dim)

        # Temporal attention — weighted context vector over all time steps
        context = self.attention(lstm_out)  # (B, hidden_dim)

        # Ward embedding
        ward_emb = self.ward_embedding(x_ward)  # (B, embedding_dim)

        # Concatenate and predict
        combined = torch.cat([context, ward_emb, x_static], dim=1)
        return self.fc(combined)
