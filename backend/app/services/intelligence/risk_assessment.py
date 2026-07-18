from backend.app.services.intelligence.context import IntelligenceContext
from backend.app.config.intelligence_rules import STAGNANT_WIND_SPEED_KMH, CPCB_PM25_POOR, CPCB_PM25_VERY_POOR

def analyze(context: IntelligenceContext) -> dict:
    """
    Stateless risk assessment engine evaluating environmental, health, exposure,
    and operational indicators to produce a unified risk index.
    """
    latest = context.latest_reading
    weather = context.current_weather
    
    # 1. Health Risk based on current and forecasted PM2.5 levels
    pm25 = latest.pm25 if (latest and latest.pm25 is not None) else 80.0
    if pm25 > CPCB_PM25_VERY_POOR:
        health_risk = "Critical"
    elif pm25 > CPCB_PM25_POOR:
        health_risk = "High"
    elif pm25 > 60.0:
        health_risk = "Medium"
    else:
        health_risk = "Low"
        
    # 2. Environmental Risk based on stagnant atmospheric wind trap profile
    wind_speed = weather.get("wind_speed", 10.0)
    humidity = weather.get("humidity", 60.0)
    if wind_speed < STAGNANT_WIND_SPEED_KMH and humidity > 75.0:
        env_risk = "High"
        env_reason = "Severe weather trap: low wind dispersion coupled with high relative humidity."
    elif wind_speed < STAGNANT_WIND_SPEED_KMH:
        env_risk = "Medium"
        env_reason = "Stagnant winds reducing particulate dispersion."
    else:
        env_risk = "Low"
        env_reason = "Atmospheric wind vectors promoting normal pollutant dispersion."

    # 3. Exposure Risk based on population and residential zones
    station_name = context.station.name.lower()
    is_dense_urban = "vihar" in station_name or "peenya" in station_name or "okhla" in station_name or "railway" in station_name
    if is_dense_urban:
        exposure_risk = "High"
        exposure_reason = "Dense residential and commercial commuters in monitoring quadrant."
    else:
        exposure_risk = "Medium"
        exposure_reason = "Moderate population density footprint."

    # 4. Operational Risk - Should the city intervene immediately?
    # True if health risk is High/Critical and environmental dispersion is low
    if health_risk in ["High", "Critical"] and env_risk in ["Medium", "High"]:
        op_risk = "Critical"
        op_action = "Immediate municipal mitigation required: Deploy roadside suppression and halt heavy construction."
    elif health_risk == "High" or pm25 > 90.0:
        op_risk = "High"
        op_action = "Pre-emptive response: Increase localized sweeps and inspect industrial compliance."
    else:
        op_risk = "Low"
        op_action = "Normal operations. Monitor updates."

    # 5. Synthesize Overall Risk Rating
    risk_weights = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
    max_risk = max(
        risk_weights[health_risk],
        risk_weights[env_risk],
        risk_weights[exposure_risk]
    )
    
    overall_rating = "Low"
    if max_risk == 4:
        overall_rating = "Critical"
    elif max_risk == 3:
        overall_rating = "High"
    elif max_risk == 2:
        overall_rating = "Medium"
        
    return {
        "environmental_risk": env_risk,
        "environmental_reason": env_reason,
        "health_risk": health_risk,
        "exposure_risk": exposure_risk,
        "exposure_reason": exposure_reason,
        "operational_risk": op_risk,
        "operational_action": op_action,
        "overall_risk": overall_rating
    }
