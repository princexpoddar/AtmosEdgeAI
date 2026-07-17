import numpy as np
import pandas as pd
import logging
from typing import List

logger = logging.getLogger(__name__)

def get_season(month: int) -> int:
    """
    Returns season index:
    0: Winter, 1: Summer, 2: Monsoon, 3: Post-Monsoon
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
    Applies unified feature engineering on pandas DataFrame.
    Expects DatetimeIndex.
    """
    df = df.copy()
    
    # 1. Temporal encodings
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
    
    # Seasons
    seasons = [get_season(m) for m in df.index.month]
    df["season_winter"] = [1.0 if s == 0 else 0.0 for s in seasons]
    df["season_summer"] = [1.0 if s == 1 else 0.0 for s in seasons]
    df["season_monsoon"] = [1.0 if s == 2 else 0.0 for s in seasons]
    df["season_post_monsoon"] = [1.0 if s == 3 else 0.0 for s in seasons]
    
    # NASA FIRMS Upwind Fire Transport Index
    wind_speed_ms = df["wind_speed"] / 3.6
    df["upwind_fire_transport_index"] = df["upwind_fire_intensity"] * wind_speed_ms
    
    # 2. Lag Features
    for col in ["pm25", "no2"]:
        for lag in [1, 2, 3, 24]:
            df[f"{col}_lag_{lag}"] = df[col].shift(lag)
            
    # 3. Rolling window statistics
    for col in ["pm25", "no2"]:
        for window in [6, 12, 24]:
            df[f"{col}_roll_mean_{window}"] = df[col].rolling(window=window).mean()
            df[f"{col}_roll_std_{window}"] = df[col].rolling(window=window).std(ddof=0)
            
    if drop_na:
        df.dropna(inplace=True)
        
    return df

def get_temporal_feature_names() -> List[str]:
    return [
        "pm25", "no2", "temp", "humidity", "wind_speed", "stagnation", 
        "upwind_fire_intensity", "upwind_fire_count", "upwind_fire_transport_index",
        "hour_of_day", "day_of_week", "month", "weekend",
        "hour_sin", "hour_cos", "dayofyear_sin", "dayofyear_cos",
        "season_winter", "season_summer", "season_monsoon", "season_post_monsoon",
        "pm25_lag_1", "pm25_lag_2", "pm25_lag_3", "pm25_lag_24",
        "no2_lag_1", "no2_lag_2", "no2_lag_3", "no2_lag_24",
        "pm25_roll_mean_6", "pm25_roll_std_6", "pm25_roll_mean_12", "pm25_roll_std_12", "pm25_roll_mean_24", "pm25_roll_std_24",
        "no2_roll_mean_6", "no2_roll_std_6", "no2_roll_mean_12", "no2_roll_std_12", "no2_roll_mean_24", "no2_roll_std_24"
    ]
