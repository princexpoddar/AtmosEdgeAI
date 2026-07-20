import numpy as np
import pandas as pd
import logging
from typing import List

logger = logging.getLogger(__name__)

# Columns that are treated as targets — scaled by scaler_y, not scaler_X
TARGET_COLS = ["pm25", "no2"]

# Additional meteorological features that may be present in the parquet
EXTRA_MET_COLS = ["pbl_height", "dew_point", "solar_radiation", "wind_u", "wind_v"]


def get_season(month: int) -> int:
    """
    Returns season index:
    0: Winter (Dec, Jan, Feb)
    1: Summer (Mar, Apr, May)
    2: Monsoon (Jun, Jul, Aug, Sep)
    3: Post-Monsoon (Oct, Nov)
    """
    if month in [12, 1, 2]:
        return 0
    elif month in [3, 4, 5]:
        return 1
    elif month in [6, 7, 8, 9]:
        return 2
    else:
        return 3


def engineer_features(df: pd.DataFrame, drop_na: bool = True) -> pd.DataFrame:
    """
    Applies feature engineering on a per-ward pandas DataFrame.
    Assumes index is a DatetimeIndex (in UTC or local).

    Adds 5 extra meteorological features (pbl_height, dew_point, solar_radiation,
    wind_u, wind_v) when present in df. Rolling windows use min_periods=1 so that
    early rows always have valid statistics.
    """
    df = df.copy()

    # 1. Calendar/Temporal Features
    hours = df.index.hour
    df["hour_of_day"] = hours.astype(float)
    df["day_of_week"] = df.index.dayofweek.astype(float)
    df["month"] = df.index.month.astype(float)
    df["weekend"] = (df.index.dayofweek >= 5).astype(float)

    df["hour_sin"] = np.sin(2 * np.pi * hours / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * hours / 24.0)

    dayofyear = df.index.dayofyear
    df["dayofyear_sin"] = np.sin(2 * np.pi * dayofyear / 365.25)
    df["dayofyear_cos"] = np.cos(2 * np.pi * dayofyear / 365.25)

    # Season one-hot
    seasons = [get_season(m) for m in df.index.month]
    df["season_winter"] = [1.0 if s == 0 else 0.0 for s in seasons]
    df["season_summer"] = [1.0 if s == 1 else 0.0 for s in seasons]
    df["season_monsoon"] = [1.0 if s == 2 else 0.0 for s in seasons]
    df["season_post_monsoon"] = [1.0 if s == 3 else 0.0 for s in seasons]

    # NASA FIRMS fire transport index
    wind_speed_ms = df["wind_speed"] / 3.6
    df["upwind_fire_transport_index"] = df["upwind_fire_intensity"] * wind_speed_ms

    # 2. Lag Features
    for col in ["pm25", "no2"]:
        for lag in [1, 2, 3, 24]:
            df[f"{col}_lag_{lag}"] = df[col].shift(lag)

    # 3. Rolling window statistics — min_periods=1 ensures no NaN for early rows
    for col in ["pm25", "no2"]:
        for window in [6, 12, 24]:
            df[f"{col}_roll_mean_{window}"] = (
                df[col].rolling(window=window, min_periods=1).mean()
            )
            df[f"{col}_roll_std_{window}"] = (
                df[col].rolling(window=window, min_periods=1).std(ddof=0)
            )

    # 4. Extra meteorological features (conditionally added when present)
    for col in EXTRA_MET_COLS:
        if col not in df.columns:
            df[col] = 0.0  # fill with neutral value if missing from parquet

    if drop_na:
        before = len(df)
        df.dropna(inplace=True)
        logger.debug(f"Feature engineering dropped {before - len(df)} rows due to NaNs.")

    return df


def get_temporal_feature_names() -> List[str]:
    """
    Returns the full list of 46 temporal features used by the global forecasting model.
    Includes the 5 new meteorological features (pbl_height, dew_point, solar_radiation,
    wind_u, wind_v).
    """
    return [
        # Core pollutants (scaled by scaler_y — kept as model inputs)
        "pm25", "no2",
        # Meteorological
        "temp", "humidity", "wind_speed", "stagnation",
        "upwind_fire_intensity", "upwind_fire_count", "upwind_fire_transport_index",
        # New meteorological features
        "pbl_height", "dew_point", "solar_radiation", "wind_u", "wind_v",
        # Calendar encodings
        "hour_of_day", "day_of_week", "month", "weekend",
        "hour_sin", "hour_cos", "dayofyear_sin", "dayofyear_cos",
        "season_winter", "season_summer", "season_monsoon", "season_post_monsoon",
        # Lag features
        "pm25_lag_1", "pm25_lag_2", "pm25_lag_3", "pm25_lag_24",
        "no2_lag_1", "no2_lag_2", "no2_lag_3", "no2_lag_24",
        # Rolling statistics
        "pm25_roll_mean_6", "pm25_roll_std_6",
        "pm25_roll_mean_12", "pm25_roll_std_12",
        "pm25_roll_mean_24", "pm25_roll_std_24",
        "no2_roll_mean_6", "no2_roll_std_6",
        "no2_roll_mean_12", "no2_roll_std_12",
        "no2_roll_mean_24", "no2_roll_std_24",
    ]


def get_input_feature_names() -> List[str]:
    """
    Returns the 44 features passed to scaler_X (all temporal features except
    raw pm25 and no2, which are scaled separately by scaler_y).
    """
    return [f for f in get_temporal_feature_names() if f not in TARGET_COLS]


def get_model_feature_names() -> List[str]:
    """
    Returns the 50 features assembled for the model temporal sequence:
    44 input features (scaler_X) + pm25/no2 (scaler_y) + 4 spatial neighbour features.
    """
    return get_input_feature_names() + TARGET_COLS + [
        "neighbour_pm25_mean", "neighbour_pm25_std",
        "neighbour_no2_mean", "neighbour_no2_std",
    ]
