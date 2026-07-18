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
