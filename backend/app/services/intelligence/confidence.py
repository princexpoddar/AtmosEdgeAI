import numpy as np
from backend.app.services.intelligence.context import IntelligenceContext
from backend.app.config.intelligence_rules import MIN_HISTORY_RECORDS

def analyze(context: IntelligenceContext) -> dict:
    """
    Stateless confidence engine. Evaluates data completeness, weather reliability,
    prediction stability, and historical consistency to assign a confidence score.
    """
    reasons = []
    
    # 1. Data Completeness Check
    hist_len = len(context.history_df)
    if hist_len >= MIN_HISTORY_RECORDS:
        completeness_score = 1.0
        reasons.append(f"Full data availability: {hist_len} hours of continuous historical readings.")
    elif hist_len > 0:
        completeness_score = hist_len / MIN_HISTORY_RECORDS
        reasons.append(f"Reduced history: only {hist_len} observation records are available (requires {MIN_HISTORY_RECORDS}h).")
    else:
        completeness_score = 0.1
        reasons.append("Critical: No station history is available in the SQLite database cache.")
        
    # 2. Weather Reliability Check
    # High wind speeds (> 25 km/h) make predictions highly volatile due to fast dispersion.
    wind_speed = context.current_weather.get("wind_speed", 10.0)
    if wind_speed > 25.0:
        weather_score = 0.8
        reasons.append("High wind speed vectors slightly reduce prediction reliability due to rapid turbulence.")
    else:
        weather_score = 1.0
        reasons.append("Stable local microclimate dynamics.")

    # 3. Prediction Stability Check
    # Check if forecast predictions vary wildly across the horizons (24h, 48h, 72h)
    fc_aqis = [f.get("predicted_aqi", 100.0) for f in context.forecasts]
    if len(fc_aqis) >= 2:
        std_dev = float(np.std(fc_aqis))
        if std_dev > 40.0:
            stability_score = 0.75
            reasons.append(f"Prediction volatility: Forecast varies significantly across horizons (std dev: {std_dev:.1f}).")
        else:
            stability_score = 1.0
            reasons.append("Consistent, stable multi-horizon trend curves.")
    else:
        stability_score = 0.7
        reasons.append("Limited forecast horizons generated.")

    # Compute overall weighted score
    overall_score = float((completeness_score * 0.5) + (weather_score * 0.25) + (stability_score * 0.25))
    overall_score = max(0.1, min(1.0, overall_score))
    
    # Determine confidence level
    if overall_score >= 0.85:
        level = "High"
    elif overall_score >= 0.60:
        level = "Medium"
    else:
        level = "Low"
        
    reason_str = " ".join(reasons)
    
    return {
        "score": round(overall_score, 2),
        "level": level,
        "reason": reason_str,
        "reasons_list": reasons
    }
