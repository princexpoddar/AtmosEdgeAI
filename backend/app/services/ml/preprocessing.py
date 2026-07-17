import os
import pickle
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, List
from sklearn.preprocessing import StandardScaler
import torch
from torch.utils.data import Dataset

from backend.app.services.ml.config import MODELS_DIR
from backend.app.services.ml.features import get_temporal_feature_names

SCALER_PATH = os.path.join(MODELS_DIR, "global_scaler.pkl")

class SpatiotemporalDataset(Dataset):
    def __init__(self, x_temporal: np.ndarray, x_ward: np.ndarray, x_static: np.ndarray, y: np.ndarray):
        """
        PyTorch dataset for spatiotemporal inputs.
        x_temporal: (N, seq_len, temporal_dim)
        x_ward: (N,)
        x_static: (N, static_dim)
        y: (N, 6) -> PM2.5 (24, 48, 72) and NO2 (24, 48, 72)
        """
        self.x_temporal = torch.tensor(x_temporal, dtype=torch.float32)
        self.x_ward = torch.tensor(x_ward, dtype=torch.long)
        self.x_static = torch.tensor(x_static, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.x_temporal)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        return self.x_temporal[idx], self.x_ward[idx], self.x_static[idx], self.y[idx]


def split_chronologically(df: pd.DataFrame, train_ratio: float = 0.7, val_ratio: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Splits a DataFrame chronologically into train, validation, and test sets.
    """
    total_len = len(df)
    train_end = int(total_len * train_ratio)
    val_end = train_end + int(total_len * val_ratio)
    
    train_df = df.iloc[:train_end]
    val_df = df.iloc[train_end:val_end]
    test_df = df.iloc[val_end:]
    
    return train_df, val_df, test_df


def create_sequences_for_ward(
    df: pd.DataFrame, 
    ward_id: int, 
    lat: float, 
    lon: float, 
    city_encoded: int,
    seq_len: int = 24
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Generates multi-horizon sequences for a single ward.
    Returns:
    - X_temporal: (N, seq_len, num_temporal_features)
    - X_ward: (N,)
    - X_static: (N, 3) (latitude, longitude, city_encoded)
    - y: (N, 6) targets
    """
    temporal_features = get_temporal_feature_names()
    num_rows = len(df)
    
    X_temp_list = []
    y_list = []
    
    # We need inputs up to index t, and targets at t + 24, t + 48, t + 72
    # So max lead is 72. Loop ends at num_rows - 72.
    for i in range(num_rows - seq_len - 72 + 1):
        # Sequence ends at index t = i + seq_len - 1
        t = i + seq_len - 1
        
        # Temporal features slice
        seq_x = df.iloc[i : t + 1][temporal_features].values
        
        # Target values: PM2.5 and NO2 at t + 24, t + 48, t + 72
        pm25_24 = df.iloc[t + 24]["pm25"]
        pm25_48 = df.iloc[t + 48]["pm25"]
        pm25_72 = df.iloc[t + 72]["pm25"]
        
        no2_24 = df.iloc[t + 24]["no2"]
        no2_48 = df.iloc[t + 48]["no2"]
        no2_72 = df.iloc[t + 72]["no2"]
        
        seq_y = np.array([pm25_24, pm25_48, pm25_72, no2_24, no2_48, no2_72], dtype=np.float32)
        
        X_temp_list.append(seq_x)
        y_list.append(seq_y)
        
    N = len(X_temp_list)
    if N == 0:
        return np.empty((0, seq_len, len(temporal_features))), np.empty((0,)), np.empty((0, 3)), np.empty((0, 6))
        
    X_temporal = np.array(X_temp_list, dtype=np.float32)
    X_ward = np.full((N,), ward_id, dtype=np.int64)
    X_static = np.tile(np.array([lat, lon, city_encoded], dtype=np.float32), (N, 1))
    y = np.array(y_list, dtype=np.float32)
    
    return X_temporal, X_ward, X_static, y


class MLDataPipeline:
    def __init__(self):
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()
        self.scaler_static = StandardScaler()
        self.is_fitted = False

    def fit(self, train_dfs_dict: Dict[int, pd.DataFrame], static_features_dict: Dict[int, Dict[str, Any]]) -> None:
        """
        Fits scalers on combined training data from all wards.
        train_dfs_dict: Maps ward_id to its train DataFrame partition
        static_features_dict: Maps ward_id to its static parameters (lat, lon, city_encoded)
        """
        temporal_cols = get_temporal_feature_names()
        
        # 1. Fit temporal scaler
        combined_temporal_list = []
        for ward_id, df in train_dfs_dict.items():
            combined_temporal_list.append(df[temporal_cols].values)
            
        combined_temporal = np.vstack(combined_temporal_list)
        self.scaler_X.fit(combined_temporal)
        
        # 2. Fit target scaler (specifically PM2.5 and NO2)
        combined_targets = combined_temporal[:, :2] # Assumes first two cols are pm25 and no2
        self.scaler_y.fit(combined_targets)
        
        # 3. Fit static scaler
        static_vals_list = []
        for ward_id in train_dfs_dict.keys():
            meta = static_features_dict[ward_id]
            static_vals_list.append([meta["latitude"], meta["longitude"], meta["city_encoded"]])
            
        combined_static = np.array(static_vals_list, dtype=np.float32)
        self.scaler_static.fit(combined_static)
        
        self.is_fitted = True

    def transform_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms a DataFrame's temporal and target columns using fitted scalers.
        """
        if not self.is_fitted:
            raise ValueError("Scalers are not fitted. Call fit() first.")
            
        temporal_cols = get_temporal_feature_names()
        df_scaled = df.copy()
        
        # Scale temporal features
        df_scaled[temporal_cols] = self.scaler_X.transform(df[temporal_cols].values)
        
        # Wait, targets are pm25 and no2. We want to scale them in the scaled df as well!
        # Note: since pm25 and no2 are the first two columns of temporal_cols, the above step already scaled them using scaler_X!
        # But we must make sure that they are scaled by scaler_y.
        # Wait! It's much cleaner if they are scaled by scaler_y specifically to be used for target values.
        # Let's see: pm25 and no2 are at columns 0 and 1 of temporal_cols.
        # The values scaled by scaler_X are fine, but since we will generate targets, we should explicitly scale the targets using scaler_y.
        # Let's write a simple helper to scale pm25 and no2 via scaler_y for target extraction.
        # Since we use raw df to generate targets, we can scale them explicitly:
        df_scaled["pm25"] = (df["pm25"] - self.scaler_y.mean_[0]) / self.scaler_y.scale_[0]
        df_scaled["no2"] = (df["no2"] - self.scaler_y.mean_[1]) / self.scaler_y.scale_[1]
        
        return df_scaled

    def transform_static(self, lat: float, lon: float, city_encoded: int) -> np.ndarray:
        """
        Transforms static features.
        """
        if not self.is_fitted:
            raise ValueError("Scalers are not fitted. Call fit() first.")
            
        arr = np.array([[lat, lon, city_encoded]], dtype=np.float32)
        return self.scaler_static.transform(arr)[0]

    def inverse_transform_targets(self, pred_y: np.ndarray) -> np.ndarray:
        """
        Inverse-transforms predicted PM2.5 and NO2 targets.
        pred_y: numpy array of shape (N, 6)
        Returns: raw unscaled prediction of shape (N, 6)
        """
        # Columns 0, 1, 2 are PM2.5 (24, 48, 72h)
        # Columns 3, 4, 5 are NO2 (24, 48, 72h)
        raw_y = pred_y.copy()
        
        mean_pm, std_pm = self.scaler_y.mean_[0], self.scaler_y.scale_[0]
        mean_no, std_no = self.scaler_y.mean_[1], self.scaler_y.scale_[1]
        
        # Inverse transform PM2.5
        raw_y[:, 0:3] = pred_y[:, 0:3] * std_pm + mean_pm
        # Inverse transform NO2
        raw_y[:, 3:6] = pred_y[:, 3:6] * std_no + mean_no
        
        return raw_y

    def save(self, filepath: str = SCALER_PATH) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump({
                "scaler_X": self.scaler_X,
                "scaler_y": self.scaler_y,
                "scaler_static": self.scaler_static,
                "is_fitted": self.is_fitted
            }, f)

    def load(self, filepath: str = SCALER_PATH) -> None:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Scaler file not found at {filepath}")
            
        with open(filepath, "rb") as f:
            data = pickle.load(f)
            self.scaler_X = data["scaler_X"]
            self.scaler_y = data["scaler_y"]
            self.scaler_static = data["scaler_static"]
            self.is_fitted = data["is_fitted"]
