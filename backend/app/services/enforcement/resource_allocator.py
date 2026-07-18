from backend.app.services.enforcement.context import EnforcementContext

def analyze(context: EnforcementContext, priority_results: dict) -> list:
    """
    Stateless Resource Allocator. Suggests deployments of inspection teams,
    sprinklers, monitoring vans, and traffic officers depending on priority and source.
    """
    priority = priority_results.get("priority", "Low")
    source_attr = context.source_attribution
    primary_source = source_attr.get("primary", {}).get("source", "Mixed Sources")
    station_name = context.station_name
    
    allocations = []
    
    # 1. Dispatch allocation based on primary threats
    if primary_source == "Vehicular Emissions":
        allocations.append({
            "resource": "Traffic Officer Squad",
            "quantity": 4,
            "target_station": station_name,
            "priority": priority,
            "reason": "Deploy traffic officers to redirect heavy commercial truck traffic away from street congestion zones."
        })
        allocations.append({
            "resource": "Mobile Monitoring Van",
            "quantity": 1,
            "target_station": station_name,
            "priority": priority,
            "reason": "Verify localized street-level NO2 particulate drift."
        })
        
    elif primary_source == "Construction Dust":
        allocations.append({
            "resource": "Water Sprinkler Truck",
            "quantity": 3,
            "target_station": station_name,
            "priority": priority,
            "reason": "Deploy mist sprinklers along commercial corridors to suppress concrete particles."
        })
        allocations.append({
            "resource": "Inspection Officer",
            "quantity": 1,
            "target_station": station_name,
            "priority": priority,
            "reason": "Audit building permit compliance and verify dust sheeting barriers."
        })
        
    elif primary_source == "Industrial Emissions":
        allocations.append({
            "resource": "Industrial Inspection Team",
            "quantity": 2,
            "target_station": station_name,
            "priority": priority,
            "reason": "Audit factory boilers emission logsheets and verify fuel parameters."
        })
        
    elif primary_source in ["Biomass Burning", "Waste Burning", "Crop Burning"]:
        allocations.append({
            "resource": "Patrol Officer Team",
            "quantity": 2,
            "target_station": station_name,
            "priority": priority,
            "reason": "Increase patrols to restrict open wood combustion and garbage fires."
        })
        
    else:
        # Fallback allocation
        allocations.append({
            "resource": "Water Sprinkler Truck",
            "quantity": 1,
            "target_station": station_name,
            "priority": "Medium",
            "reason": "Perform routine particulate washdowns along the corridor."
        })
        
    return allocations
