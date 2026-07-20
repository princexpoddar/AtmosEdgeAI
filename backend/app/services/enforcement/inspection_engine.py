from backend.app.services.enforcement.context import EnforcementContext

def analyze(context: EnforcementContext, priority_results: dict) -> list:
    """
    Stateless Inspection Engine. Recommends patrol dispatches, factory compliance audits,
    and site inspections based on source attribution, station land-use profile, and registered hotspots.
    """
    priority = priority_results.get("priority", "Low")
    source_attr = context.source_attribution
    primary_source = source_attr.get("primary", {}).get("source", "Mixed Sources")
    
    profile = context.profile
    hotspots = profile.get("registered_hotspots", ["Local Emission Hub"])
    primary_hotspot = hotspots[0] if hotspots else "Local Catchment Hotspot"
    spcb_auth = profile.get("spcb_authority", f"{context.city} Pollution Control Board")
    spcb_framework = profile.get("spcb_framework", "NCAP Statutory Action Plan")
    land_use = profile.get("land_use", "Urban Catchment Zone")
    
    recommendations = []
    urgency = priority

    # 1. Industrial Emissions audit
    if primary_source == "Industrial Emissions" or "Industrial" in land_use:
        recommendations.append({
            "inspection_type": "Industrial Emission & Stack Compliance Audit",
            "target_station": context.station_name,
            "target_hotspot": primary_hotspot,
            "spcb_authority": spcb_auth,
            "spcb_mandate": spcb_framework,
            "location_coords": {"lat": context.latitude, "lon": context.longitude},
            "reason": f"Station {context.station_name} sits in an {land_use}. Industrial PM2.5 threat active at {primary_hotspot}. Audit boiler stacks and continuous emission monitor logs under {spcb_auth} rules.",
            "urgency": urgency,
            "expected_impact": "High (-15% PM2.5 in 6h)",
            "estimated_duration": "6 hours",
            "confidence": float(priority_results.get("confidence", 0.85))
        })
        
    # 2. Construction Site inspection
    if primary_source == "Construction Dust" or "Construction" in land_use:
        recommendations.append({
            "inspection_type": "Construction Site & Fugitive Dust Audit",
            "target_station": context.station_name,
            "target_hotspot": primary_hotspot,
            "spcb_authority": spcb_auth,
            "spcb_mandate": spcb_framework,
            "location_coords": {"lat": context.latitude, "lon": context.longitude},
            "reason": f"Fugitive dust buildup detected at {primary_hotspot} near {context.station_name}. Audit commercial building permits, wind barrier sheet coverage, and water misting canons.",
            "urgency": urgency,
            "expected_impact": "High (-20% PM10 in 4h)",
            "estimated_duration": "3 hours",
            "confidence": float(priority_results.get("confidence", 0.85))
        })
        
    # 3. Traffic restrictions review
    if primary_source == "Vehicular Emissions" or "Traffic" in land_use:
        recommendations.append({
            "inspection_type": "Arterial Transit & Heavy Vehicle Corridor Audit",
            "target_station": context.station_name,
            "target_hotspot": primary_hotspot,
            "spcb_authority": spcb_auth,
            "spcb_mandate": spcb_framework,
            "location_coords": {"lat": context.latitude, "lon": context.longitude},
            "reason": f"Street-level NO2 surge at {context.station_name}. Dispatch traffic enforcement squad to {primary_hotspot} for non-destined diesel truck diversion and idling checks.",
            "urgency": urgency,
            "expected_impact": "High (-18% NO2 in 3h)",
            "estimated_duration": "4 hours",
            "confidence": float(priority_results.get("confidence", 0.85))
        })
        
    # 4. Waste burning patrol
    if primary_source in ["Biomass Burning", "Waste Burning", "Crop Burning"] or "Biomass" in land_use:
        recommendations.append({
            "inspection_type": "Biomass & Waste Burning Anti-Smog Patrol",
            "target_station": context.station_name,
            "target_hotspot": primary_hotspot,
            "spcb_authority": spcb_auth,
            "spcb_mandate": spcb_framework,
            "location_coords": {"lat": context.latitude, "lon": context.longitude},
            "reason": f"Thermal anomalies detected in catchment of {context.station_name}. Patrol {primary_hotspot} to douse open municipal solid waste burning and commercial wood stoves.",
            "urgency": urgency,
            "expected_impact": "Medium (-12% PM2.5 in 5h)",
            "estimated_duration": "5 hours",
            "confidence": float(priority_results.get("confidence", 0.85))
        })
        
    # 5. Default Fallback Road dust sweep
    if not recommendations:
        recommendations.append({
            "inspection_type": "Mechanical Road Dust Suppression Sweep",
            "target_station": context.station_name,
            "target_hotspot": primary_hotspot,
            "spcb_authority": spcb_auth,
            "spcb_mandate": spcb_framework,
            "location_coords": {"lat": context.latitude, "lon": context.longitude},
            "reason": f"Low wind dispersion around {context.station_name}. Dispatch mechanical sweeping & water sprinkling unit along {primary_hotspot}.",
            "urgency": "Medium",
            "expected_impact": "Medium (-10% PM10 in 2h)",
            "estimated_duration": "2 hours",
            "confidence": float(priority_results.get("confidence", 0.85))
        })
        
    return recommendations
