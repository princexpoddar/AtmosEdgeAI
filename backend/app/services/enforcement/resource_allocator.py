from backend.app.services.enforcement.context import EnforcementContext

def analyze(context: EnforcementContext, priority_results: dict) -> list:
    """
    Stateless Resource Allocator. Suggests deployments of inspection teams,
    sprinklers, anti-smog guns, monitoring vans, and traffic officers tailored to station land-use and coordinates.
    """
    priority = priority_results.get("priority", "Low")
    source_attr = context.source_attribution
    primary_source = source_attr.get("primary", {}).get("source", "Mixed Sources")
    station_name = context.station_name
    
    profile = context.profile
    hotspots = profile.get("registered_hotspots", ["Station Catchment Corridor"])
    primary_hotspot = hotspots[0] if hotspots else "Local Transit Bay"
    spcb_auth = profile.get("spcb_authority", f"{context.city} SPCB")
    land_use = profile.get("land_use", "Urban Corridor")
    
    allocations = []

    if primary_source == "Vehicular Emissions" or "Traffic" in land_use:
        allocations.append({
            "resource": "Traffic Enforcement Squad & Heavy Truck Diversion Unit",
            "quantity": 4,
            "target_station": station_name,
            "target_hotspot": primary_hotspot,
            "spcb_authority": spcb_auth,
            "location_coords": {"lat": context.latitude, "lon": context.longitude},
            "priority": priority,
            "reason": f"Deploy 4 traffic officers to {primary_hotspot} to rerouting non-destined diesel trucks away from {station_name}."
        })
        allocations.append({
            "resource": "Mobile Real-Time CAAQMS Monitoring Van",
            "quantity": 1,
            "target_station": station_name,
            "target_hotspot": primary_hotspot,
            "spcb_authority": spcb_auth,
            "location_coords": {"lat": context.latitude, "lon": context.longitude},
            "priority": priority,
            "reason": f"Deploy mobile air analyzer to verify street-level NO2 particulate plume at {primary_hotspot}."
        })
        
    elif primary_source == "Construction Dust" or "Construction" in land_use:
        allocations.append({
            "resource": "High-Pressure mist Anti-Smog Gun Truck",
            "quantity": 3,
            "target_station": station_name,
            "target_hotspot": primary_hotspot,
            "spcb_authority": spcb_auth,
            "location_coords": {"lat": context.latitude, "lon": context.longitude},
            "priority": priority,
            "reason": f"Deploy 3 anti-smog mist sprinkler trucks along {primary_hotspot} near {station_name} to suppress concrete dust."
        })
        allocations.append({
            "resource": "Municipal Construction Site Inspector",
            "quantity": 2,
            "target_station": station_name,
            "target_hotspot": primary_hotspot,
            "spcb_authority": spcb_auth,
            "location_coords": {"lat": context.latitude, "lon": context.longitude},
            "priority": priority,
            "reason": f"Audit building permits and green mesh wind-break sheets at active construction sites around {primary_hotspot}."
        })
        
    elif primary_source == "Industrial Emissions" or "Industrial" in land_use:
        allocations.append({
            "resource": "SPCB Industrial Stack Inspection Team",
            "quantity": 2,
            "target_station": station_name,
            "target_hotspot": primary_hotspot,
            "spcb_authority": spcb_auth,
            "location_coords": {"lat": context.latitude, "lon": context.longitude},
            "priority": priority,
            "reason": f"Dispatch {spcb_auth} stack auditors to inspect boiler fuel parameters and CEMS sensors at {primary_hotspot}."
        })
        allocations.append({
            "resource": "Industrial Area Mechanical Dust Sweeper",
            "quantity": 1,
            "target_station": station_name,
            "target_hotspot": primary_hotspot,
            "spcb_authority": spcb_auth,
            "location_coords": {"lat": context.latitude, "lon": context.longitude},
            "priority": priority,
            "reason": f"Deploy heavy-duty mechanical road sweeper along industrial access roads in {primary_hotspot}."
        })
        
    elif primary_source in ["Biomass Burning", "Waste Burning", "Crop Burning"] or "Biomass" in land_use:
        allocations.append({
            "resource": "Municipal Open-Fire Patrol Squad",
            "quantity": 3,
            "target_station": station_name,
            "target_hotspot": primary_hotspot,
            "spcb_authority": spcb_auth,
            "location_coords": {"lat": context.latitude, "lon": context.longitude},
            "priority": priority,
            "reason": f"Dispatch 3 municipal patrol squads to douse open MSW garbage fires and commercial tandoor wood burning at {primary_hotspot}."
        })
        
    else:
        allocations.append({
            "resource": "Municipal Water Sprinkler Truck",
            "quantity": 2,
            "target_station": station_name,
            "target_hotspot": primary_hotspot,
            "spcb_authority": spcb_auth,
            "location_coords": {"lat": context.latitude, "lon": context.longitude},
            "priority": "Medium",
            "reason": f"Perform routine washdowns and dust suppression along {primary_hotspot} near {station_name}."
        })
        
    return allocations
