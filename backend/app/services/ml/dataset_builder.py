import os
import json
import math
import pickle
import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, List, Optional
from sklearn.preprocessing import StandardScaler

from backend.app.services.ml.config import config, BASE_DIR, MODELS_DIR
from backend.app.services.ml.features import (
    get_input_feature_names,
    TARGET_COLS,
)

logger = logging.getLogger(__name__)

SCALER_PATH = os.path.join(MODELS_DIR, "global_scaler.pkl")
STATION_MAP_PATH = os.path.join(MODELS_DIR, "station_id_map.json")


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def _ensure_cols(df: pd.DataFrame, cols: List[str], fill: float = 0.0) -> pd.DataFrame:
    """Add any missing columns with a constant fill value."""
    df = df.copy()
    for c in cols:
        if c not in df.columns:
            df[c] = fill
    return df


class DatasetBuilder:
    def __init__(
        self,
        parquet_path: str = os.path.join(BASE_DIR, "data", "station_dataset.parquet"),
        scaler_path: str = SCALER_PATH,
        station_map_path: str = STATION_MAP_PATH,
        seq_len: Optional[int] = None,
        k_neighbours: Optional[int] = None,
    ):
        self.parquet_path = parquet_path
        self.scaler_path = scaler_path
        self.station_map_path = station_map_path
        self.seq_len = seq_len if seq_len is not None else config.seq_len
        self.k_neighbours = k_neighbours if k_neighbours is not None else config.k_neighbours
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()
        self.scaler_static = StandardScaler()
        self.station_id_map: Dict[str, int] = {}
        self._neighbours: Dict[str, List[str]] = {}

    def load_and_split(self):
        if not os.path.exists(self.parquet_path):
            raise FileNotFoundError(f"Parquet file not found at {self.parquet_path}")
        df = pd.read_parquet(self.parquet_path)
        unique_stations = sorted(df["station_id"].unique())
        self.station_id_map = {sid: idx for idx, sid in enumerate(unique_stations)}
        os.makedirs(os.path.dirname(self.station_map_path), exist_ok=True)
        with open(self.station_map_path, "w") as f:
            json.dump(self.station_id_map, f, indent=2)
        station_splits = {}
        for sid in unique_stations:
            df_st = df[df["station_id"] == sid].copy()
            df_st["timestamp"] = pd.to_datetime(df_st["timestamp"])
            df_st.sort_values("timestamp", inplace=True)
            df_st.set_index("timestamp", inplace=True)
            n = len(df_st)
            if n < 500:
                logger.warning(f"Station {sid} has too few rows ({n} < 500). Skipping.")
                continue
            train_end = int(n * 0.70)
            val_end = train_end + int(n * 0.15)
            train_df = df_st.iloc[:train_end]
            val_df   = df_st.iloc[train_end:val_end]
            test_df  = df_st.iloc[val_end:]
            if not train_df.empty and not val_df.empty:
                assert train_df.index.max() < val_df.index.min()
            if not val_df.empty and not test_df.empty:
                assert val_df.index.max() < test_df.index.min()
            station_splits[sid] = {"train": train_df, "val": val_df, "test": test_df}
        return station_splits, self.station_id_map

    def _compute_neighbours(self, station_splits):
        coords = {}
        for sid, splits in station_splits.items():
            df = splits["train"]
            if not df.empty and "latitude" in df.columns:
                coords[sid] = (float(df.iloc[0]["latitude"]), float(df.iloc[0]["longitude"]))
        self._neighbours = {}
        for sid, (lat1, lon1) in coords.items():
            dists = []
            for oid, (lat2, lon2) in coords.items():
                if oid != sid:
                    dists.append((_haversine_km(lat1, lon1, lat2, lon2), oid))
            dists.sort(key=lambda x: x[0])
            self._neighbours[sid] = [oid for _, oid in dists[:self.k_neighbours]]

    def fit_scalers(self, station_splits):
        input_cols = get_input_feature_names()
        train_dfs = [s["train"] for s in station_splits.values() if not s["train"].empty]
        if not train_dfs:
            raise ValueError("No training data available to fit scalers.")
        combined_train = pd.concat(train_dfs)
        # Fill any missing extra-met columns with 0 before fitting
        combined_train = _ensure_cols(combined_train, input_cols)
        self.scaler_X.fit(combined_train[input_cols].values)
        self.scaler_y.fit(combined_train[TARGET_COLS].values)
        static_data = []
        for splits in station_splits.values():
            df_tr = splits["train"]
            if not df_tr.empty:
                row = df_tr.iloc[0]
                static_data.append([float(row["latitude"]), float(row["longitude"]), float(row["elevation"])])
        self.scaler_static.fit(np.array(static_data))
        self._compute_neighbours(station_splits)
        os.makedirs(os.path.dirname(self.scaler_path), exist_ok=True)
        with open(self.scaler_path, "wb") as f:
            pickle.dump({"scaler_X": self.scaler_X, "scaler_y": self.scaler_y, "scaler_static": self.scaler_static}, f)
        logger.info(f"Fitted scalers saved to {self.scaler_path}")

    def transform_and_sequence(self, station_splits, split_name):
        input_cols = get_input_feature_names()
        feature_dim = len(input_cols) + len(TARGET_COLS) + 4  # 50

        scaled_pm25_by_station = {}
        scaled_no2_by_station  = {}
        for sid, splits in station_splits.items():
            df = splits[split_name]
            if df.empty:
                continue
            scaled_pm25_by_station[sid] = ((df["pm25"].values - self.scaler_y.mean_[0]) / self.scaler_y.scale_[0]).astype(np.float32)
            scaled_no2_by_station[sid]  = ((df["no2"].values  - self.scaler_y.mean_[1]) / self.scaler_y.scale_[1]).astype(np.float32)

        X_temp_list, X_station_list, X_static_list, y_list = [], [], [], []

        for sid, splits in station_splits.items():
            df = splits[split_name].copy()
            if df.empty or len(df) < self.seq_len + 72:
                continue
            # Fill missing extra-met columns with 0 before transform
            df = _ensure_cols(df, input_cols)
            scaled_inputs = self.scaler_X.transform(df[input_cols].values).astype(np.float32)
            scaled_pm25 = scaled_pm25_by_station[sid]
            scaled_no2  = scaled_no2_by_station[sid]
            full_temporal = np.concatenate([scaled_inputs, scaled_pm25[:, None], scaled_no2[:, None]], axis=1)
            static_meta = np.array([[float(df.iloc[0]["latitude"]), float(df.iloc[0]["longitude"]), float(df.iloc[0]["elevation"])]])
            scaled_static = self.scaler_static.transform(static_meta)[0].astype(np.float32)
            station_idx = self.station_id_map[sid]
            nbr_ids = self._neighbours.get(sid, [])
            for i in range(len(df) - self.seq_len - 72 + 1):
                t = i + self.seq_len - 1
                seq_core = full_temporal[i: i + self.seq_len]
                available_nbrs = [n for n in nbr_ids if n in scaled_pm25_by_station and len(scaled_pm25_by_station[n]) >= i + self.seq_len]
                if available_nbrs:
                    nbr_pm25 = np.stack([scaled_pm25_by_station[n][i:i+self.seq_len] for n in available_nbrs])
                    nbr_no2  = np.stack([scaled_no2_by_station[n][i:i+self.seq_len]  for n in available_nbrs])
                    nbr_features = np.stack([nbr_pm25.mean(0), nbr_pm25.std(0), nbr_no2.mean(0), nbr_no2.std(0)], axis=1).astype(np.float32)
                else:
                    nbr_features = np.zeros((self.seq_len, 4), dtype=np.float32)
                seq_x = np.concatenate([seq_core, nbr_features], axis=1)
                seq_y = np.array([scaled_pm25[t+24], scaled_pm25[t+48], scaled_pm25[t+72], scaled_no2[t+24], scaled_no2[t+48], scaled_no2[t+72]], dtype=np.float32)
                X_temp_list.append(seq_x)
                X_station_list.append(station_idx)
                X_static_list.append(scaled_static)
                y_list.append(seq_y)

        if not X_temp_list:
            return (np.empty((0,self.seq_len,feature_dim),dtype=np.float32), np.empty((0,),dtype=np.int64), np.empty((0,3),dtype=np.float32), np.empty((0,6),dtype=np.float32))
        return (np.array(X_temp_list,dtype=np.float32), np.array(X_station_list,dtype=np.int64), np.array(X_static_list,dtype=np.float32), np.array(y_list,dtype=np.float32))

    def generate_all_splits(self):
        station_splits, _ = self.load_and_split()
        self.fit_scalers(station_splits)
        return {
            "train": self.transform_and_sequence(station_splits, "train"),
            "val":   self.transform_and_sequence(station_splits, "val"),
            "test":  self.transform_and_sequence(station_splits, "test"),
        }
