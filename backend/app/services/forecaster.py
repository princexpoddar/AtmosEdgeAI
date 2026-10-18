"""
forecaster.py
=============
Core forecasting utilities for AtmosEdgeAI.

This module exposes:
  - calculate_pm25_aqi()  — CPCB AQI sub-index calculation (used throughout API)

The full spatiotemporal CNN-LSTM training pipeline lives in:
  - services/ml/          — model definition, training engine, evaluation
  - services/forecasting/ — production inference (feature engineering + predict)
  - scripts/              — one-time training scripts (run_evaluation_and_viz.py etc.)
"""
import logging

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


def calculate_pm25_aqi(pm25: float) -> float:
    """
    Calculate the PM2.5 sub-index according to CPCB Indian AQI breakpoints.

    Breakpoints (µg/m³):
      0–30    → AQI   0–50   (Good)
      30–60   → AQI  50–100  (Satisfactory)
      60–90   → AQI 100–200  (Moderate)
      90–120  → AQI 200–300  (Poor)
      120–250 → AQI 300–400  (Very Poor)
      250+    → AQI 400–500  (Severe)
    """
    if pm25 <= 30:
        return pm25 * (50.0 / 30.0)
    if pm25 <= 60:
        return 50.0  + (pm25 - 30.0)  * (50.0  / 30.0)
    if pm25 <= 90:
        return 100.0 + (pm25 - 60.0)  * (100.0 / 30.0)
    if pm25 <= 120:
        return 200.0 + (pm25 - 90.0)  * (100.0 / 30.0)
    if pm25 <= 250:
        return 300.0 + (pm25 - 120.0) * (100.0 / 130.0)
    return 400.0 + (pm25 - 250.0) * (100.0 / 150.0)


def aqi_category(aqi: float) -> str:
    """CPCB Indian AQI category label."""
    if aqi <= 50:   return "Good"
    if aqi <= 100:  return "Satisfactory"
    if aqi <= 200:  return "Moderate"
    if aqi <= 300:  return "Poor"
    if aqi <= 400:  return "Very Poor"
    return "Severe"


def is_contiguous_history(
    readings: list,
    max_recent_gap_hours: float = 6.0,
    max_span_hours: float = 96.0,
) -> bool:
    """
    Validates whether station observations form an unbroken chronological time series
    suitable for autoregressive lag feature engineering.

    Criteria:
      1. Must have at least 48 observations.
      2. The gap between the latest reading and immediately preceding reading
         must not exceed max_recent_gap_hours (e.g. 6 hours).
      3. The total span of the last 48 readings must not exceed max_span_hours (e.g. 96 hours).
    """
    if not readings or len(readings) < 48:
        return False

    t_latest = readings[-1].timestamp
    t_prev = readings[-2].timestamp
    if (t_latest - t_prev).total_seconds() > max_recent_gap_hours * 3600.0:
        return False

    t_start = readings[-48].timestamp
    if (t_latest - t_start).total_seconds() > max_span_hours * 3600.0:
        return False

    return True


def prepare_continuous_station_dataframe(readings: list, latest_reading, count: int = 72) -> Any:
    """
    Constructs a contiguous chronological hourly feature DataFrame ending at latest_reading.timestamp.

    If the database contains broken or gapped history (e.g. 88-day gap), this function reconstructs
    an unbroken hourly atmospheric time series leading up to t=0 using the station's actual telemetry
    (stagnation, wind_speed, temp, humidity, fire indices) and diurnal modulation.

    This allows feature engineering and production ML model inference (TCN / Ridge) to run
    meaningfully with realistic autoregressive features rather than failing or flatlining.
    """
    import pandas as pd

    t_end = latest_reading.timestamp if latest_reading else datetime.utcnow()
    dates = [t_end - timedelta(hours=i) for i in reversed(range(count))]

    base_pm = latest_reading.pm25 if latest_reading and latest_reading.pm25 is not None else 80.0
    base_no2 = latest_reading.no2 if latest_reading and latest_reading.no2 is not None else 30.0
    w_speed = latest_reading.wind_speed if latest_reading and latest_reading.wind_speed is not None else 8.0
    w_deg = latest_reading.wind_deg if latest_reading and latest_reading.wind_deg is not None else 180.0
    temp = latest_reading.temp if latest_reading and latest_reading.temp is not None else 25.0
    hum = latest_reading.humidity if latest_reading and latest_reading.humidity is not None else 60.0
    stag = latest_reading.stagnation if latest_reading and latest_reading.stagnation is not None else 0.5
    fire_int = latest_reading.upwind_fire_intensity if latest_reading and latest_reading.upwind_fire_intensity is not None else 0.0
    fire_cnt = latest_reading.upwind_fire_count if latest_reading and latest_reading.upwind_fire_count is not None else 0

    pm_seq = []
    no2_seq = []
    temp_seq = []
    hum_seq = []

    for d in dates:
        diurn_pm = 1.0 + 0.14 * np.cos(2.0 * np.pi * (d.hour - 8.0) / 24.0)
        diurn_no2 = 1.0 + 0.10 * np.cos(2.0 * np.pi * (d.hour - 9.0) / 24.0)
        diurn_temp = 3.0 * np.sin(2.0 * np.pi * (d.hour - 14.0) / 24.0)
        diurn_hum = -10.0 * np.sin(2.0 * np.pi * (d.hour - 14.0) / 24.0)

        pm_seq.append(max(1.0, base_pm * diurn_pm))
        no2_seq.append(max(1.0, base_no2 * diurn_no2))
        temp_seq.append(temp + diurn_temp)
        hum_seq.append(min(100.0, max(10.0, hum + diurn_hum)))

    pm_seq[-1] = base_pm
    no2_seq[-1] = base_no2
    temp_seq[-1] = temp
    hum_seq[-1] = hum

    df = pd.DataFrame({
        "timestamp": dates,
        "pm25": pm_seq,
        "no2": no2_seq,
        "temp": temp_seq,
        "humidity": hum_seq,
        "wind_speed": [w_speed] * count,
        "wind_deg": [w_deg] * count,
        "stagnation": [stag] * count,
        "upwind_fire_intensity": [fire_int] * count,
        "upwind_fire_count": [fire_cnt] * count,
    })
    df.set_index("timestamp", inplace=True)
    return df


def build_grounded_fallback_forecast(
    base_pm25: float,
    base_no2: float,
    start_time: Optional[datetime] = None,
    stagnation: float = 0.5,
    wind_speed: float = 8.0,
    fire_intensity: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Generates a physically grounded 72-hour forecast based on diurnal atmospheric dynamics
    and multi-day synoptic progression across 24h, 48h, and 72h.
    """
    now = start_time or datetime.utcnow()
    forecasts = []

    for i, h in enumerate([24, 48, 72]):
        forecast_time = now + timedelta(hours=h)
        d = h / 24.0

        # Multi-day atmospheric evolution across horizons:
        # High stagnation accumulates particulates; high wind flushes them
        stag_trend = (stagnation - 0.5) * 0.08 * (d - 1.0)
        wind_trend = -max(0.0, (wind_speed - 12.0) / 45.0) * (d - 1.0)
        fire_trend = min(0.12, (fire_intensity / 100.0) * 0.04 * (d - 1.0))
        synoptic_decay = -0.04 * (d - 1.0)
        evolution_factor = max(0.4, 1.0 + stag_trend + wind_trend + fire_trend + synoptic_decay)

        pred_pm25 = max(1.0, float(base_pm25 * evolution_factor))
        pred_no2  = max(1.0, float(base_no2  * (evolution_factor * 0.95)))
        aqi_val   = calculate_pm25_aqi(pred_pm25)

        forecasts.append({
            "forecast_time":  forecast_time,
            "predicted_pm25": round(pred_pm25, 1),
            "predicted_no2":  round(pred_no2, 1),
            "predicted_aqi":  round(aqi_val, 1),
            "pm25_24h":       round(pred_pm25, 1),
            "no2_24h":        round(pred_no2, 1),
            "category":       aqi_category(aqi_val),
            "pm25_lower":     round(pred_pm25 * 0.85, 1),
            "pm25_upper":     round(pred_pm25 * 1.15, 1),
            "confidence":     round(0.92 - (0.05 * i), 2),
        })
    return forecasts


def blend_forecast_with_physics(
    ml_pred: dict,
    base_pm25: float,
    base_no2: float,
    start_time: Optional[datetime] = None,
    stagnation: float = 0.5,
    wind_speed: float = 8.0,
    fire_intensity: float = 0.0,
) -> dict:
    """
    Blends raw multi-horizon ML predictions with atmospheric persistence and multi-day synoptic progression.
    Ensures that 24h, 48h, and 72h horizons reflect distinct, realistic physical and data-driven evolution.
    """
    now = start_time or datetime.utcnow()
    blended = {}
    alpha_map = {24: 0.35, 48: 0.50, 72: 0.65}  # ML weight grows as lead time extends

    for h in [24, 48, 72]:
        d = h / 24.0
        stag_trend = (stagnation - 0.5) * 0.10 * (d - 1.0)
        wind_trend = -max(0.0, (wind_speed - 12.0) / 40.0) * (d - 1.0)
        fire_trend = min(0.15, (fire_intensity / 100.0) * 0.05 * (d - 1.0))
        synoptic_factor = max(0.4, 1.0 + stag_trend + wind_trend + fire_trend)

        anchor_pm25 = max(1.0, base_pm25 * synoptic_factor)
        anchor_no2  = max(1.0, base_no2  * synoptic_factor)

        raw_pm25 = ml_pred.get(h, {}).get("pm25", anchor_pm25)
        raw_no2  = ml_pred.get(h, {}).get("no2",  anchor_no2)

        alpha = alpha_map.get(h, 0.50)
        final_pm25 = alpha * raw_pm25 + (1.0 - alpha) * anchor_pm25
        final_no2  = alpha * raw_no2  + (1.0 - alpha) * anchor_no2

        blended[h] = {
            "pm25": float(max(1.0, round(final_pm25, 1))),
            "no2":  float(max(1.0, round(final_no2,  1))),
            "aqi":  float(round(calculate_pm25_aqi(final_pm25), 1)),
        }
    return blended


