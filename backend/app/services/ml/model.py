import torch
import torch.nn as nn
from typing import Dict, Any

class GlobalCNNLSTMForecaster(nn.Module):
    def __init__(
        self,
        temporal_dim: int,
        static_dim: int,
        num_wards: int = 100,
        embedding_dim: int = 16,
        seq_len: int = 24,
        hidden_dim: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        output_dim: int = 6
    ):
        """
        Global Forecasting CNN-LSTM Model.
        Inputs:
        - temporal sequence x_temporal: (batch, seq_len, temporal_dim)
        - ward index x_ward: (batch,)
        - static features x_static: (batch, static_dim) (scaled lat, lon, city)
        
        Architecture:
        x_temporal -> Conv1D -> BatchNorm -> ReLU -> Dropout -> LSTM -> last hidden state
        Concatenate(last hidden state, ward embedding, x_static) -> Dense Block -> Output (6 predictions)
        """
        super(GlobalCNNLSTMForecaster, self).__init__()
        self.seq_len = seq_len
        self.hidden_dim = hidden_dim
        
        # Ward embedding layer to capture ward-specific spatial signatures
        self.ward_embedding = nn.Embedding(
            num_embeddings=num_wards, 
            embedding_dim=embedding_dim
        )
        
        # 1D Convolution over temporal dimension
        # Input shape to Conv1d: (batch_size, temporal_dim, seq_len)
        self.conv1d = nn.Conv1d(
            in_channels=temporal_dim, 
            out_channels=hidden_dim, 
            kernel_size=3, 
            padding=1
        )
        self.bn = nn.BatchNorm1d(num_features=hidden_dim)
        self.relu = nn.ReLU()
        self.dropout_conv = nn.Dropout(p=dropout)
        
        # LSTM layer
        self.lstm = nn.LSTM(
            input_size=hidden_dim, 
            hidden_size=hidden_dim, 
            num_layers=num_layers, 
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )
        
        # Fully connected layer to map aggregated features to target predictions
        fc_input_dim = hidden_dim + embedding_dim + static_dim
        
        self.fc = nn.Sequential(
            nn.Linear(in_features=fc_input_dim, out_features=hidden_dim),
            nn.ReLU(),
            nn.Dropout(p=dropout),
            nn.Linear(in_features=hidden_dim, out_features=output_dim)
        )
        
    def forward(self, x_temporal: torch.Tensor, x_ward: torch.Tensor, x_static: torch.Tensor) -> torch.Tensor:
        # Permute x_temporal for Conv1d: (batch, temporal_dim, seq_len)
        x = x_temporal.permute(0, 2, 1)
        
        # Convolutional feature extraction
        conv_out = self.dropout_conv(self.relu(self.bn(self.conv1d(x))))
        
        # Permute back for LSTM: (batch, seq_len, hidden_dim)
        conv_out = conv_out.permute(0, 2, 1)
        
        # LSTM output
        lstm_out, _ = self.lstm(conv_out)
        
        # Extract last hidden state representing final step in temporal sequence
        last_step = lstm_out[:, -1, :]
        
        # Generate Ward ID Embeddings
        ward_emb = self.ward_embedding(x_ward)
        
        # Combine temporal features with static features and ward embeddings
        combined = torch.cat([last_step, ward_emb, x_static], dim=1)
        
        # Output prediction
        out = self.fc(combined)
        return out
