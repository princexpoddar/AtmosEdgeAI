import os
import json
import pickle
import logging
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any, List
from sklearn.preprocessing import StandardScaler

from backend.app.services.ml.config import config, BASE_DIR, MODELS_DIR
from backend.app.services.ml.features import get_temporal_feature_names

logger = logging.getLogger(__name__)

SCALER_PATH = os.path.join(MODELS_DIR, "global_scaler.pkl")
STATION_MAP_PATH = os.path.join(MODELS_DIR, "station_id_map.json")


class DatasetBuilder:
    def __init__(
        self,
        parquet_path: str = os.path.join(BASE_DIR, "data", "station_dataset.parquet"),
        scaler_path: str = SCALER_PATH,
        station_map_path: str = STATION_MAP_PATH,
        seq_len: int = 24
    ):
        self.parquet_path = parquet_path
        self.scaler_path = scaler_path
        self.station_map_path = station_map_path
        self.seq_len = seq_len
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()
        self.scaler_static = StandardScaler()
        self.station_id_map = {}

    def load_and_split(self) -> Tuple[Dict[str, Dict[str, pd.DataFrame]], Dict[str, int]]:
        """
        Loads the Parquet file, builds station encoding map, and performs
        per-station chronological splits (70% train, 15% val, 15% test).
        Returns a dict mapping station_id to its train/val/test dataframes,
        and the station_id_map encoding dict.
        """
        if not os.path.exists(self.parquet_path):
            raise FileNotFoundError(f"Parquet file not found at {self.parquet_path}")

        df = pd.read_parquet(self.parquet_path)

        # Build station integer encoding map for embedding layers
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
            if n < 500:  # Exclude stations with fewer than 500 rows
                logger.warning(f"Station {sid} has too few rows ({n} < 500). Skipping.")
                continue

            train_end = int(n * 0.70)
            val_end = train_end + int(n * 0.15)

            train_df = df_st.iloc[:train_end]
            val_df = df_st.iloc[train_end:val_end]
            test_df = df_st.iloc[val_end:]

            # Leakage checks
            if not train_df.empty and not val_df.empty:
                assert train_df.index.max() < val_df.index.min(), \
                    f"Temporal leak between train & val at station {sid}!"
            if not val_df.empty and not test_df.empty:
                assert val_df.index.max() < test_df.index.min(), \
                    f"Temporal leak between val & test at station {sid}!"

            station_splits[sid] = {
                "train": train_df,
                "val": val_df,
                "test": test_df
            }

        return station_splits, self.station_id_map

    def fit_scalers(self, station_splits: Dict[str, Dict[str, pd.DataFrame]]) -> None:
        """
        Fits StandardScaler ONLY on the combined training splits from all stations.
        Global scaling keeps all features (inputs and targets) on a consistent scale,
        which is essential for the CNN-LSTM to learn cross-feature relationships.
        """
        temporal_cols = get_temporal_feature_names()

        train_dfs = [splits["train"] for splits in station_splits.values()
                     if not splits["train"].empty]
        if not train_dfs:
            raise ValueError("No training data available to fit scalers.")

        combined_train = pd.concat(train_dfs)

        # 1. Global temporal input feature scaler (X)
        self.scaler_X.fit(combined_train[temporal_cols].values)

        # 2. Global target scaler (PM2.5, NO2)
        combined_targets = combined_train[["pm25", "no2"]].values
        self.scaler_y.fit(combined_targets)

        # 3. Static metadata scaler [latitude, longitude, elevation]
        static_data = []
        for sid, splits in station_splits.items():
            df_tr = splits["train"]
            if not df_tr.empty:
                row = df_tr.iloc[0]
                static_data.append([
                    float(row["latitude"]),
                    float(row["longitude"]),
                    float(row["elevation"])
                ])
        self.scaler_static.fit(np.array(static_data))

        # Persist all scalers
        os.makedirs(os.path.dirname(self.scaler_path), exist_ok=True)
        with open(self.scaler_path, "wb") as f:
            pickle.dump({
                "scaler_X": self.scaler_X,
                "scaler_y": self.scaler_y,
                "scaler_static": self.scaler_static
            }, f)
        logger.info(f"Fitted global scalers on train set and saved to {self.scaler_path}")

    def transform_and_sequence(
        self,
        station_splits: Dict[str, Dict[str, pd.DataFrame]],
        split_name: str
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Scales the requested split using the globally fitted scalers and
        constructs fixed-length temporal sequences.

        All features — inputs, lag/rolling features, and targets — are scaled
        by the same global statistics, ensuring a consistent feature space
        for the CNN-LSTM regardless of the time period or station.

        Returns:
        - X_temporal : (N, seq_len, feature_dim)   float32
        - X_station  : (N,)                         int64
        - X_static   : (N, 3)                       float32
        - y          : (N, 6) [pm25_24h, pm25_48h, pm25_72h, no2_24h, no2_48h, no2_72h] float32
        """
        temporal_cols = get_temporal_feature_names()

        X_temp_list    = []
        X_station_list = []
        X_static_list  = []
        y_list         = []

        for sid, splits in station_splits.items():
            df = splits[split_name].copy()
            if df.empty or len(df) < self.seq_len + 72:
                continue

            # Scale temporal features (global scaler — consistent with training)
            scaled_temporal = self.scaler_X.transform(df[temporal_cols].values)
            df_scaled = pd.DataFrame(scaled_temporal, index=df.index, columns=temporal_cols)

            # Scale static metadata
            static_meta = np.array([[
                float(df.iloc[0]["latitude"]),
                float(df.iloc[0]["longitude"]),
                float(df.iloc[0]["elevation"])
            ]])
            scaled_static = self.scaler_static.transform(static_meta)[0]

            # Scale targets using the global y-scaler
            scaled_pm25 = (df["pm25"].values - self.scaler_y.mean_[0]) / self.scaler_y.scale_[0]
            scaled_no2  = (df["no2"].values  - self.scaler_y.mean_[1]) / self.scaler_y.scale_[1]

            station_idx = self.station_id_map[sid]
            num_rows = len(df)

            for i in range(num_rows - self.seq_len - 72 + 1):
                t = i + self.seq_len - 1

                seq_x = df_scaled[temporal_cols].iloc[i: t + 1].values.astype(np.float32)

                seq_y = np.array([
                    scaled_pm25[t + 24], scaled_pm25[t + 48], scaled_pm25[t + 72],
                    scaled_no2[t + 24],  scaled_no2[t + 48],  scaled_no2[t + 72]
                ], dtype=np.float32)

                X_temp_list.append(seq_x)
                X_station_list.append(station_idx)
                X_static_list.append(scaled_static)
                y_list.append(seq_y)

        if not X_temp_list:
            return (
                np.empty((0, self.seq_len, len(temporal_cols)), dtype=np.float32),
                np.empty((0,), dtype=np.int64),
                np.empty((0, 3), dtype=np.float32),
                np.empty((0, 6), dtype=np.float32)
            )

        return (
            np.array(X_temp_list, dtype=np.float32),
            np.array(X_station_list, dtype=np.int64),
            np.array(X_static_list, dtype=np.float32),
            np.array(y_list, dtype=np.float32)
        )

    def generate_all_splits(self) -> Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
        """
        Convenience execution flow to load, split, fit scalers, transform, and package
        train/val/test splits.
        """
        station_splits, _ = self.load_and_split()
        self.fit_scalers(station_splits)

        train = self.transform_and_sequence(station_splits, "train")
        val   = self.transform_and_sequence(station_splits, "val")
        test  = self.transform_and_sequence(station_splits, "test")

        return {
            "train": train,
            "val":   val,
            "test":  test
        }
