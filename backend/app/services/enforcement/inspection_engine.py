from backend.app.services.enforcement.context import EnforcementContext

def analyze(context: EnforcementContext, priority_results: dict) -> list:
    """
    Stateless Inspection Engine. Recommends patrol dispatches, factory compliance audits,
    and site inspections based on source attribution and overall priority.
    """
    priority = priority_results.get("priority", "Low")
    source_attr = context.source_attribution
    primary_source = source_attr.get("primary", {}).get("source", "Mixed Sources")
    
    recommendations = []
    
    # Check priority levels to assign urgency
    urgency = priority
    
    # 1. Industrial Emissions audit
    if primary_source == "Industrial Emissions":
        recommendations.append({
            "inspection_type": "Industrial Emission Audit",
            "reason": f"Station sits in industrial zone with primary threat identified as Industrial Emissions. Verify stack controls.",
            "urgency": urgency,
            "expected_impact": "High",
            "estimated_duration": "6 hours",
            "confidence": float(priority_results.get("confidence", 0.85))
        })
        
    # 2. Construction Site inspection
    elif primary_source == "Construction Dust":
        recommendations.append({
            "inspection_type": "Construction Site Inspection",
            "reason": "Dry ambient weather coupled with construction dust triggers. Audit commercial permits and dust sheets.",
            "urgency": urgency,
            "expected_impact": "High",
            "estimated_duration": "3 hours",
            "confidence": float(priority_results.get("confidence", 0.85))
        })
        
    # 3. Traffic restrictions review
    elif primary_source == "Vehicular Emissions":
        recommendations.append({
            "inspection_type": "Traffic Restriction Review",
            "reason": "Elevated street-level NO2 indicators and commuting peaks. Review truck restrictions and check idling spots.",
            "urgency": urgency,
            "expected_impact": "High",
            "estimated_duration": "4 hours",
            "confidence": float(priority_results.get("confidence", 0.85))
        })
        
    # 4. Waste burning patrol
    elif primary_source in ["Biomass Burning", "Waste Burning", "Crop Burning"]:
        recommendations.append({
            "inspection_type": "Waste Burning Patrol",
            "reason": "Satellite thermal anomalies or regional temperature drops indicate open fires or stove burning.",
            "urgency": urgency,
            "expected_impact": "Medium",
            "estimated_duration": "5 hours",
            "confidence": float(priority_results.get("confidence", 0.85))
        })
        
    # 5. Road dust sweeps
    else:
        recommendations.append({
            "inspection_type": "Road Dust Suppression Check",
            "reason": "General particulate drift under low wind speed conditions. Deploy municipal sweeping check.",
            "urgency": "Medium",
            "expected_impact": "Medium",
            "estimated_duration": "2 hours",
            "confidence": float(priority_results.get("confidence", 0.85))
        })
        
    return recommendations
