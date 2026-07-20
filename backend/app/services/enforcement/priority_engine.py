from backend.app.services.enforcement.context import EnforcementContext

def analyze(context: EnforcementContext) -> dict:
    """
    Stateless Priority Engine. Evaluates forecasting trends, operational risks,
    weather dispersion limits, and exposure density to assign a municipal priority index.
    """
    forecast = context.forecast
    risk = context.risk_assessment
    source = context.source_attribution
    conf = context.confidence
    
    score = 0.0
    reasons = []
    
    # 1. Forecast AQI Contribution
    # Extract maximum predicted AQI across the horizons (24h, 48h, 72h)
    fc_aqis = [f.get("predicted_aqi", 100.0) for f in forecast]
    max_aqi = max(fc_aqis) if fc_aqis else 100.0
    
    if max_aqi > 250.0:
        score += 35.0
        reasons.append(f"Forecast AQI peaks at a Critical level ({max_aqi:.0f} AQI).")
    elif max_aqi > 150.0:
        score += 25.0
        reasons.append(f"Forecast AQI peaks at an elevated level ({max_aqi:.0f} AQI).")
    elif max_aqi > 90.0:
        score += 15.0
        reasons.append(f"Forecast AQI is Moderate ({max_aqi:.0f} AQI).")
    else:
        score += 5.0
        reasons.append("Air quality levels remain within healthy bounds.")

    # 2. Risk Assessment Matrix Contributions
    health_val = risk.get("health_risk", "Low")
    op_val = risk.get("operational_risk", "Low")
    exposure_val = risk.get("exposure_risk", "Medium")
    
    # Health risk
    if health_val == "Critical":
        score += 25.0
        reasons.append("Immediate public health hazard due to extreme particulate levels.")
    elif health_val == "High":
        score += 18.0
        reasons.append("High warning threshold: vulnerable groups are at immediate risk.")
    elif health_val == "Medium":
        score += 10.0
        reasons.append("Moderate health exposure warnings active.")
    else:
        score += 3.0
        
    # Operational risk (Should the city intervene immediately?)
    if op_val == "Critical":
        score += 20.0
        reasons.append("Municipal intervention status is Critical: local dispersion pathways are blocked.")
    elif op_val == "High":
        score += 15.0
        reasons.append("Operational protocols recommend priority cleanup.")
    else:
        score += 5.0

    # Exposure risk & Station Catchment Receptors
    profile = context.profile
    receptors = profile.get("receptors", {})
    vuln = receptors.get("vulnerability_level", "Medium")
    schools_count = receptors.get("schools", 0)
    hospitals_count = receptors.get("hospitals", 0)

    if vuln == "Critical" or (schools_count + hospitals_count) > 15:
        score += 12.0
        reasons.append(f"Station catchment contains {schools_count} schools and {hospitals_count} hospitals with Critical vulnerability.")
    elif vuln == "High" or (schools_count + hospitals_count) > 8:
        score += 8.0
        reasons.append(f"High population exposure ({schools_count} schools, {hospitals_count} hospitals within 2km).")
    else:
        score += 4.0

    # 3. Microclimate stagnation factors
    wind_speed = context.weather.get("wind_speed", 10.0)
    if wind_speed < 8.0:
        score += 10.0
        reasons.append(f"Stagnant microclimatic wind trap ({wind_speed:.1f} km/h) favors pollutant retention.")

    # Cap score
    overall_score = float(min(100.0, score))
    
    # Map score to label
    if overall_score >= 80.0:
        priority = "Critical"
    elif overall_score >= 65.0:
        priority = "High"
    elif overall_score >= 45.0:
        priority = "Medium"
    else:
        priority = "Low"
        
    reasoning_str = " ".join(reasons)
    
    return {
        "priority": priority,
        "priority_score": round(overall_score, 1),
        "reasoning": reasoning_str,
        "confidence": conf.get("score", 0.85)
    }
