from backend.app.services.intelligence.context import IntelligenceContext

def analyze(
    context: IntelligenceContext,
    reasoning_results: dict,
    source_results: dict,
    risk_results: dict,
    decision_results: dict
) -> dict:
    """
    Stateless report generator. Integrates reasoning pipeline outputs
    into tailored, audience-specific briefings (Executive, Technical, Municipal, Citizen)
    with metadata severity tags.
    """
    primary_source = source_results.get("primary", {}).get("source", "Mixed Sources")
    overall_risk = risk_results.get("overall_risk", "Low")
    reasons_list = reasoning_results.get("reasons_list", [])
    
    # 1. Map Overall Risk to Severity Tags
    severity_map = {
        "Low": "Low",
        "Medium": "Medium",
        "High": "High",
        "Critical": "High"
    }
    severity = severity_map.get(overall_risk, "Low")
    
    # 2. Dynamic Headlines
    if overall_risk in ["High", "Critical"]:
        headline = f"Alert: High Environmental Risks Triggered by {primary_source}"
    else:
        headline = "Stable Local Environmental Conditions Maintained"
        
    # 3. Create Executive Summary (City Commissioners)
    exec_summary = (
        f"The regional air quality indices indicate a '{overall_risk}' overall risk footprint. "
        f"The primary driver contributing to local particulate counts is estimated to be {primary_source}."
    )
    if reasons_list:
        exec_details = f"Key operational updates: {reasons_list[0]}"
    else:
        exec_details = "All meteorology sensors indicate normal seasonal wind dispersion."
        
    # 4. Create Technical Summary (Environmental Engineers)
    tech_summary = (
        f"Meteorology sensors report a wind velocity of {context.current_weather.get('wind_speed', 10.0):.1f} km/h "
        f"with relative humidity at {context.current_weather.get('humidity', 60.0):.1f}%. "
        f"Data completeness index is scored at {context.history_df.shape[0] if hasattr(context.history_df, 'shape') else 0} historical entries."
    )
    tech_details = (
        f"Operational risks: {risk_results.get('operational_risk', 'Low')}. "
        f"Stagnation profile: {risk_results.get('environmental_reason', 'N/A')} "
        f"Exposure profile: {risk_results.get('exposure_reason', 'N/A')}"
    )

    # 5. Create Municipal Summary (Enforcement & Patrol Officers)
    mun_summary = (
        f"Mitigation priority is rated as {decision_results.get('priority', 'Low')}. "
        f"Enforcement squads must prioritize targeted sweeps matching the primary source footprint ({primary_source})."
    )
    mun_actions_text = "; ".join([a["action"] for a in decision_results.get("actions", [])])
    mun_details = f"Directives: {mun_actions_text}"

    # 6. Create Citizen Summary (General Commuters & Patients)
    latest_aqi = context.latest_reading.pm25 if (context.latest_reading and context.latest_reading.pm25 is not None) else 80.0
    cit_category = risk_results.get("health_risk", "Moderate")
    cit_summary = (
        f"Air quality indices in your ward are currently rated as {cit_category} (PM2.5: {latest_aqi:.1f} µg/m³). "
        f"Citizen precautions must be observed."
    )
    cit_actions_text = " ".join(decision_results.get("citizen_actions", []))
    cit_details = f"Directives: {cit_actions_text}"

    return {
        "headline": headline,
        "severity": severity,
        "briefings": {
            "executive": {
                "summary": exec_summary,
                "details": exec_details
            },
            "technical": {
                "summary": tech_summary,
                "details": tech_details
            },
            "municipal": {
                "summary": mun_summary,
                "details": mun_details
            },
            "citizen": {
                "summary": cit_summary,
                "details": cit_details
            }
        }
    }
