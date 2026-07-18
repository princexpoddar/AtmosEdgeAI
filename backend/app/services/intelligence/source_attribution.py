from backend.app.services.intelligence.context import IntelligenceContext
from backend.app.config.intelligence_rules import HIGH_FIRE_INTENSITY_THRESHOLD, STAGNANT_WIND_SPEED_KMH

def analyze(context: IntelligenceContext) -> dict:
    """
    Stateless multi-criteria source attribution engine. Evaluates CPCB readings,
    meteorological variables, and NASA FIRMS indices to rank contributors.
    Includes rules-based hypothesis rejections.
    """
    latest = context.latest_reading
    weather = context.current_weather
    fire = context.fire_index
    
    # ── Modular Future-Ready Placeholders ──
    # These placeholders simulate future integration hooks for localized GIS metrics.
    has_nearby_construction_zone = False # Hook for municipal building permit records
    has_heavy_traffic_congestion = False # Hook for Google Maps Traffic APIs
    is_industrial_zone = "peenya" in context.station.name.lower() or "okhla" in context.station.name.lower()
    
    # Extract current parameters
    pm25 = latest.pm25 if (latest and latest.pm25 is not None) else 80.0
    no2 = latest.no2 if (latest and latest.no2 is not None) else 30.0
    wind_speed = weather.get("wind_speed", 10.0)
    wind_deg = weather.get("wind_direction", 180.0)
    temp = weather.get("temperature", 25.0)
    humidity = weather.get("humidity", 60.0)
    
    fire_intensity = fire.get("upwind_fire_intensity", 0.0)
    fire_count = fire.get("upwind_fire_count", 0)
    
    hypotheses = {}
    rejected = []
    
    # 1. Evaluate Crop Burning Hypothesis
    # North-westerly winds (270° to 360°) favor transport from farming clusters
    is_upwind_wind = (wind_deg > 270) or (wind_deg < 90)
    if fire_intensity > HIGH_FIRE_INTENSITY_THRESHOLD and is_upwind_wind:
        score = 0.5 + min(0.4, (fire_intensity - 15) / 100)
        hypotheses["Crop Burning"] = {
            "confidence": float(round(score, 2)),
            "evidence": [
                f"NASA FIRMS satellite detected {fire_count} upwind hotspots in regional corridors.",
                f"Wind direction vector ({wind_deg:.0f}°) favors active upwind pollutant transport."
            ]
        }
    else:
        # Document why crop burning is ruled out
        reason = "No upwind fires detected by NASA FIRMS satellite in the region." if fire_count == 0 else f"Wind direction ({wind_deg:.0f}°) does not align with upwind fire locations."
        rejected.append({
            "source": "Crop Burning",
            "reason": reason
        })
        
    # 2. Evaluate Vehicular Emissions Hypothesis
    # Rush hours and high NO2 ratios
    # Simulate rush hours: Hour of day is 8-11 or 17-20 UTC+5:30 (roughly 3-6 or 12-15 UTC)
    current_hour = latest.timestamp.hour if latest else 9
    is_rush_hour = current_hour in [8, 9, 10, 11, 17, 18, 19, 20]
    
    if no2 > 35.0 or is_rush_hour or has_heavy_traffic_congestion:
        veh_score = 0.45
        evidence = ["High NO₂ sub-index indicating fuel combustion."]
        if is_rush_hour:
            veh_score += 0.2
            evidence.append("Corresponds to temporal morning/evening peak commuter rush hours.")
        if wind_speed < STAGNANT_WIND_SPEED_KMH:
            veh_score += 0.15
            evidence.append("Stagnant weather trapping localized street-level emissions.")
            
        hypotheses["Vehicular Emissions"] = {
            "confidence": float(round(veh_score, 2)),
            "evidence": evidence
        }
    else:
        rejected.append({
            "source": "Vehicular Emissions",
            "reason": f"NO₂ concentration ({no2:.1f} µg/m³) is below traffic congestion indicators."
        })
        
    # 3. Evaluate Industrial Emissions Hypothesis
    # PEENYA / OKHLA zones have industrial emission footprints
    if is_industrial_zone:
        ind_score = 0.4
        evidence = ["Station sits inside active industrial monitoring quadrant."]
        if no2 > 40.0:
            ind_score += 0.25
            evidence.append("Co-pollutant indicators (NO₂) are elevated.")
        hypotheses["Industrial Emissions"] = {
            "confidence": float(round(ind_score, 2)),
            "evidence": evidence
        }
    else:
        rejected.append({
            "source": "Industrial Emissions",
            "reason": "Station sits in a low-density residential/commercial corridor far from industrial zones."
        })
        
    # 4. Evaluate Construction & Natural Dust Hypothesis
    # High temperature, low humidity, dry conditions
    if humidity < 40.0 and temp > 28.0:
        dust_score = 0.35
        evidence = ["Dry atmospheric profile and high temperatures facilitating dust resuspension."]
        if has_nearby_construction_zone:
            dust_score += 0.3
            evidence.append("Direct proximity to active infrastructure projects.")
        hypotheses["Construction Dust"] = {
            "confidence": float(round(dust_score, 2)),
            "evidence": evidence
        }
    else:
        rejected.append({
            "source": "Construction Dust",
            "reason": f"High humidity ({humidity:.1f}%) and moderate temperature suppress dust resuspension."
        })
        
    # 5. Evaluate Biomass & Waste Burning
    if temp < 15.0: # Winter season wood heating
        hypotheses["Biomass Burning"] = {
            "confidence": 0.55,
            "evidence": ["Cool temperatures increasing localized residential wood heating footprints."]
        }
        
    # Sort and return ranked contributors
    sorted_hypotheses = sorted(hypotheses.items(), key=lambda x: x[1]["confidence"], reverse=True)
    
    ranked = []
    for s_name, details in sorted_hypotheses:
        ranked.append({
            "source": s_name,
            "confidence": details["confidence"],
            "evidence": details["evidence"]
        })
        
    # Fallback if no hypotheses met
    if not ranked:
        ranked.append({
            "source": "Mixed Sources",
            "confidence": 0.50,
            "evidence": ["Normal ambient urban emissions mixture."]
        })
        
    return {
        "primary": ranked[0],
        "secondary": ranked[1] if len(ranked) > 1 else None,
        "alternatives": ranked[2:] if len(ranked) > 2 else [],
        "rejected": rejected
    }
