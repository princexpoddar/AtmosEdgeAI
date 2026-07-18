from backend.app.services.intelligence.context import IntelligenceContext

def analyze(context: IntelligenceContext, risk_results: dict, source_results: dict) -> dict:
    """
    Stateless decision engine. Uses risk ratings and primary source attributions
    to recommend high-impact municipal and citizen directives.
    """
    overall_risk = risk_results.get("overall_risk", "Low")
    primary_source = source_results.get("primary", {}).get("source", "Mixed Sources")
    
    actions = []
    citizen_actions = []
    
    # 1. Base traffic/dust suppression actions based on source category
    if primary_source == "Vehicular Emissions":
        actions.append({
            "type": "Traffic",
            "action": "Restrict heavy commercial vehicles along southern monitoring corridors.",
            "expected_impact": "High"
        })
        actions.append({
            "type": "Traffic",
            "action": "Coordinate traffic signal syncs to minimize commuter idling at Peenya hubs.",
            "expected_impact": "Medium"
        })
        citizen_actions.append("Avoid driving during peak hours (8 AM - 11 AM and 5 PM - 8 PM).")
        citizen_actions.append("Close windows and keep vehicle air circulation in recirculate mode during commutes.")
        
    elif primary_source == "Crop Burning":
        actions.append({
            "type": "Biomass",
            "action": "Trigger cross-border agricultural smoke monitoring alerts.",
            "expected_impact": "High"
        })
        actions.append({
            "type": "Public Health",
            "action": "Issue smog warnings across schools and outdoor community arenas.",
            "expected_impact": "High"
        })
        citizen_actions.append("Keep windows tightly shut; run indoor HEPA air filters continuously.")
        citizen_actions.append("Asthma patients must carry rescue inhalers and wear N95 masks outdoors.")
        
    elif primary_source == "Industrial Emissions":
        actions.append({
            "type": "Industry",
            "action": "Deploy inspectors to check stack emissions and coal logs at Peenya power zones.",
            "expected_impact": "High"
        })
        actions.append({
            "type": "Enforcement",
            "action": "Temporarily limit industrial boiler thresholds to 70% capacity.",
            "expected_impact": "Medium"
        })
        citizen_actions.append("Minimize outdoor exercise in the immediate vicinity of industrial zones.")
        
    elif primary_source == "Construction Dust":
        actions.append({
            "type": "Dust",
            "action": "Halt excavation and grading activities at the ward's active commercial corridors.",
            "expected_impact": "High"
        })
        actions.append({
            "type": "Dust",
            "action": "Deploy mechanical water mist sprayers along unpaved corridor loops.",
            "expected_impact": "Medium"
        })
        citizen_actions.append("Wear protective masks to filter coarse soil particles near construction hubs.")
    else:
        # Mixed/Unknown fallback
        actions.append({
            "type": "General",
            "action": "Increase mechanical sweeping frequencies across major arterial roads.",
            "expected_impact": "Medium"
        })
        citizen_actions.append("Monitor localized real-time AQI updates prior to planning outdoor events.")

    # 2. General risk-based escalations
    if overall_risk in ["High", "Critical"]:
        actions.append({
            "type": "Enforcement",
            "action": "Impose fines on garbage and leaf open waste-burning occurrences.",
            "expected_impact": "High"
        })
        citizen_actions.append("Children, seniors, and sensitive groups should completely restrict strenuous outdoor activities.")
    else:
        citizen_actions.append("Outdoor activities are generally safe for non-sensitive individuals.")
        
    priority_map = {
        "Low": "Low",
        "Medium": "Medium",
        "High": "High",
        "Critical": "Critical"
    }
    
    return {
        "priority": priority_map.get(overall_risk, "Low"),
        "actions": actions,
        "citizen_actions": citizen_actions
    }
