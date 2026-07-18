import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.core.database import Station
from backend.app.services.ingestion.cache import retrieve_station_lag_history
from backend.app.services.forecaster import calculate_pm25_aqi
from backend.app.api.endpoints import get_station_forecast
from backend.app.services.intelligence import reasoning_engine, source_attribution, confidence, risk_assessment, decision_engine, report_generator
from backend.app.services.intelligence.context import IntelligenceContext
from backend.app.services.enforcement.context import EnforcementContext
from backend.app.services.enforcement import priority_engine, inspection_engine, intervention_engine, resource_allocator
import pandas as pd

def run_enforcement_pipeline(db: Session) -> dict:
    """
    Orchestrates the municipal enforcement pipeline. Runs forecasts and intelligence context
    creation across all stations, aggregates priority rankings, identifies hotspots
    (improving, deteriorating, stable), allocates resources, and summarizes alerts.
    """
    stations = db.query(Station).all()
    station_contexts = []
    
    # Process each station to gather intelligence & construct EnforcementContext
    for st in stations:
        readings = retrieve_station_lag_history(db, st.id, 100)
        # Require 48h history for feature pipeline stability
        if len(readings) < 48:
            continue
            
        try:
            # Build pandas DataFrame for history
            data = [{
                "timestamp": r.timestamp,
                "pm25": r.pm25 if r.pm25 is not None else 80.0,
                "no2": r.no2 if r.no2 is not None else 30.0,
                "temp": r.temp if r.temp is not None else 25.0,
                "humidity": r.humidity if r.humidity is not None else 60.0,
                "wind_speed": r.wind_speed if r.wind_speed is not None else 10.0,
                "wind_deg": r.wind_deg if r.wind_deg is not None else 180.0,
                "upwind_fire_intensity": r.upwind_fire_intensity if r.upwind_fire_intensity is not None else 0.0,
                "upwind_fire_count": r.upwind_fire_count if r.upwind_fire_count is not None else 0,
                "stagnation": r.stagnation if r.stagnation is not None else 0.5
            } for r in readings]
            
            df = pd.DataFrame(data)
            df.set_index("timestamp", inplace=True)
            
            # Forecast calculations
            forecast_records = get_station_forecast(st.id, db)
            
            latest = readings[-1]
            pm25 = latest.pm25 if (latest and latest.pm25 is not None) else 80.0
            no2 = latest.no2 if (latest and latest.no2 is not None) else 30.0
            
            current_weather = {
                "temperature": latest.temp if latest.temp is not None else 25.0,
                "humidity": latest.humidity if latest.humidity is not None else 60.0,
                "wind_speed": latest.wind_speed if latest.wind_speed is not None else 10.0,
                "wind_direction": latest.wind_deg if latest.wind_deg is not None else 180.0
            }
            
            fire_index = {
                "upwind_fire_intensity": latest.upwind_fire_intensity if latest.upwind_fire_intensity is not None else 0.0,
                "upwind_fire_count": latest.upwind_fire_count if latest.upwind_fire_count is not None else 0
            }
            
            # Phase 1 Intelligence pipeline components
            intel_ctx = IntelligenceContext(
                station=st,
                latest_reading=latest,
                history_df=df,
                forecasts=forecast_records,
                current_weather=current_weather,
                fire_index=fire_index
            )
            
            r_engine = reasoning_engine.RuleBasedReasoningEngine()
            reasoning_res = r_engine.analyze(intel_ctx)
            source_res = source_attribution.analyze(intel_ctx)
            confidence_res = confidence.analyze(intel_ctx)
            risk_res = risk_assessment.analyze(intel_ctx)
            decision_res = decision_engine.analyze(intel_ctx, risk_res, source_res)
            report_res = report_generator.analyze(intel_ctx, reasoning_res, source_res, risk_res, decision_res)
            
            # Calculate 24h trend delta
            pm25_recent = df["pm25"].tail(24).values
            trend_delta = float(pm25_recent[-1] - pm25_recent[0]) if len(pm25_recent) >= 24 else 0.0
            
            # Construct EnforcementContext
            enforce_ctx = EnforcementContext(
                station_id=st.id,
                station_name=st.name,
                city=st.city,
                latitude=st.latitude,
                longitude=st.longitude,
                forecast=forecast_records,
                risk_assessment=risk_res,
                source_attribution=source_res,
                confidence=confidence_res,
                municipal_recommendations=decision_res.get("citizen_actions", []),
                weather=current_weather,
                history_trend={"delta_24h": trend_delta}
            )
            station_contexts.append(enforce_ctx)
        except Exception as e:
            continue
            
    # Process priority rankings
    priority_list = []
    inspections = []
    interventions = []
    allocations = []
    
    for ctx in station_contexts:
        priority_res = priority_engine.analyze(ctx)
        insp_res = inspection_engine.analyze(ctx, priority_res)
        int_res = intervention_engine.analyze(ctx, priority_res)
        alloc_res = resource_allocator.analyze(ctx, priority_res)
        
        priority_list.append({
            "station_id": ctx.station_id,
            "station_name": ctx.station_name,
            "city": ctx.city,
            "priority": priority_res["priority"],
            "score": priority_res["priority_score"],
            "reasoning": priority_res["reasoning"],
            "trend_delta": ctx.history_trend.get("delta_24h", 0.0),
            "current_aqi": calculate_pm25_aqi(ctx.forecast[0]["predicted_pm25"] if ctx.forecast else 80.0)
        })
        
        # Append target labels
        for insp in insp_res:
            insp["target_station"] = ctx.station_name
            inspections.append(insp)
            
        for inter in int_res:
            inter["target_station"] = ctx.station_name
            interventions.append(inter)
            
        for alloc in alloc_res:
            allocations.append(alloc)
            
    # Sort by priority score descending
    priority_list = sorted(priority_list, key=lambda x: x["score"], reverse=True)
    
    # Sort lists for Hotspot groupings
    top_priority = priority_list[:5]
    
    # Sorting by trend delta
    sorted_improving = sorted(priority_list, key=lambda x: x["trend_delta"]) # lowest delta is best improving
    top_improving = sorted_improving[:5]
    
    sorted_deteriorating = sorted(priority_list, key=lambda x: x["trend_delta"], reverse=True) # highest delta is worsening
    top_deteriorating = sorted_deteriorating[:5]
    
    # Stable: lowest absolute value delta
    sorted_stable = sorted(priority_list, key=lambda x: abs(x["trend_delta"]))
    top_stable = sorted_stable[:5]
    
    # Executive brief aggregation
    critical_count = sum(1 for p in priority_list if p["priority"] == "Critical")
    high_count = sum(1 for p in priority_list if p["priority"] == "High")
    
    headline = "Stable Local Environmental Conditions Maintained"
    if critical_count > 0:
        headline = f"Alert: {critical_count} Municipal Wards under Critical Air Quality Priority!"
    elif high_count > 0:
        headline = f"Advisory: {high_count} Wards at High priority intervention status."
        
    executive_summary = {
        "headline": headline,
        "total_evaluated": len(priority_list),
        "critical_count": critical_count,
        "high_count": high_count,
        "direct_orders": (
            "Deploy sweepers and restrict commercial diesel vehicles along the Peenya industrial corridors."
            if critical_count > 0 else "Routine operations. Inspect local construction sites."
        )
    }
    
    return {
        "metadata": {
            "timestamp": datetime.utcnow().isoformat(),
            "total_stations_evaluated": len(priority_list)
        },
        "priority_rankings": priority_list,
        "hotspots": {
            "highest_priority": top_priority,
            "improving": top_improving,
            "deteriorating": top_deteriorating,
            "stable": top_stable
        },
        "inspection_recommendations": inspections,
        "intervention_recommendations": interventions,
        "resource_allocation": allocations,
        "executive_summary": executive_summary
    }
