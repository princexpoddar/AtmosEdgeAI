"""
enforcement/pipeline.py
=======================
Orchestrates the municipal enforcement pipeline.

Performance optimisations (vs. original):
  • All stations + city-index map fetched ONCE at the top (removes 40 × DB queries).
  • Readings fetched ONCE per station and reused for both the history DataFrame
    and the ML forecast (removes a second retrieve_station_lag_history call).
  • ML inference (_build_forecast) is called inline — no round-trip through the
    HTTP endpoint helper, which was the main bottleneck.
  • A 5-minute in-memory TTL cache returns the cached payload on subsequent
    requests so cold-start latency only hits once per cache window.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.app.core.database import Station
from backend.app.services.forecaster import calculate_pm25_aqi
from backend.app.services.forecasting.feature_engineering import engineer_features
from backend.app.services.forecasting.inference import predict_forecast
from backend.app.services.ingestion.cache import retrieve_station_lag_history
from backend.app.services.intelligence import (
    confidence,
    decision_engine,
    reasoning_engine,
    report_generator,
    risk_assessment,
    source_attribution,
)
from backend.app.services.intelligence.context import IntelligenceContext
from backend.app.services.enforcement import (
    inspection_engine,
    intervention_engine,
    priority_engine,
    resource_allocator,
)
from backend.app.services.enforcement.context import EnforcementContext

logger = logging.getLogger(__name__)

# ── In-memory TTL cache ───────────────────────────────────────────────────────
_CACHE_TTL_SECONDS = 300          # 5 minutes
_cache_payload: Optional[Dict]   = None
_cache_expires_at: float          = 0.0


# ── AQI helpers ───────────────────────────────────────────────────────────────

def _aqi_category(aqi: float) -> str:
    if aqi <= 50:  return "Good"
    if aqi <= 100: return "Satisfactory"
    if aqi <= 200: return "Moderate"
    if aqi <= 300: return "Poor"
    if aqi <= 400: return "Very Poor"
    return "Severe"


def _build_reading_dataframe(readings) -> pd.DataFrame:
    """Convert StationReading ORM list to a feature DataFrame (timestamp index)."""
    data = [
        {
            "timestamp":             r.timestamp,
            "pm25":                  r.pm25               if r.pm25               is not None else 80.0,
            "no2":                   r.no2                if r.no2                is not None else 30.0,
            "temp":                  r.temp               if r.temp               is not None else 25.0,
            "humidity":              r.humidity           if r.humidity           is not None else 60.0,
            "wind_speed":            r.wind_speed         if r.wind_speed         is not None else 10.0,
            "wind_deg":              r.wind_deg           if r.wind_deg           is not None else 180.0,
            "upwind_fire_intensity": r.upwind_fire_intensity if r.upwind_fire_intensity is not None else 0.0,
            "upwind_fire_count":     r.upwind_fire_count  if r.upwind_fire_count  is not None else 0,
            "stagnation":            r.stagnation         if r.stagnation         is not None else 0.5,
        }
        for r in readings
    ]
    df = pd.DataFrame(data)
    df.set_index("timestamp", inplace=True)
    return df


def _fallback_forecast(base_pm25: float, base_no2: float) -> List[Dict[str, Any]]:
    """Sinusoidal fallback when ML inference is unavailable."""
    forecasts = []
    for i, h in enumerate([24, 48, 72]):
        factor    = 1.0 + 0.12 * np.sin(h * np.pi / 24.0)
        pred_pm25 = base_pm25 * factor
        pred_no2  = base_no2  * (factor * 0.9)
        aqi       = calculate_pm25_aqi(pred_pm25)
        forecasts.append({
            "forecast_time":  datetime.utcnow() + timedelta(hours=h),
            "predicted_pm25": round(pred_pm25, 1),
            "predicted_no2":  round(pred_no2,  1),
            "predicted_aqi":  round(aqi, 1),
            "category":       _aqi_category(aqi),
            "pm25_lower":     round(pred_pm25 * 0.85, 1),
            "pm25_upper":     round(pred_pm25 * 1.15, 1),
            "confidence":     round(0.92 - 0.05 * i, 2),
        })
    return forecasts


def _build_forecast(
    readings,
    station_lat: float,
    station_lon: float,
    city_encoded: int,
    base_pm25: float,
    base_no2: float,
) -> List[Dict[str, Any]]:
    """
    Run ML forecast for a single station using already-fetched readings.
    Falls back to sinusoidal model if inference fails.
    """
    if len(readings) < 48:
        return _fallback_forecast(base_pm25, base_no2)
    try:
        df_engineered = engineer_features(_build_reading_dataframe(readings), drop_na=True)
        if len(df_engineered) < 24:
            raise ValueError("Not enough rows after feature engineering")
        pred_dict = predict_forecast(df_engineered, station_lat, station_lon, city_encoded)
        return [
            {
                "forecast_time":  datetime.utcnow() + timedelta(hours=h),
                "predicted_pm25": round(pred_dict[h]["pm25"], 1),
                "predicted_no2":  round(pred_dict[h]["no2"],  1),
                "predicted_aqi":  round(calculate_pm25_aqi(pred_dict[h]["pm25"]), 1),
                "category":       _aqi_category(calculate_pm25_aqi(pred_dict[h]["pm25"])),
                "pm25_lower":     round(pred_dict[h]["pm25"] * 0.85, 1),
                "pm25_upper":     round(pred_dict[h]["pm25"] * 1.15, 1),
                "confidence":     round(0.92 - 0.05 * i, 2),
            }
            for i, h in enumerate([24, 48, 72])
        ]
    except Exception as exc:
        logger.warning("Forecast fallback for station (%.4f, %.4f): %s", station_lat, station_lon, exc)
        return _fallback_forecast(base_pm25, base_no2)


from backend.app.services.enforcement.station_profiles import get_station_profile

# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_enforcement_pipeline(db: Session, station_id: Optional[str] = None, city: Optional[str] = None) -> dict:
    """
    Orchestrates the municipal enforcement pipeline.

    Optimised: single station-list fetch, single readings fetch per station,
    inline ML inference, station land-use dossier integration, and a 5-minute result cache.
    """
    global _cache_payload, _cache_expires_at

    # ── Cache hit (only for global unfiltered calls) ─────────────────────────
    now = time.monotonic()
    if station_id is None and city is None and _cache_payload is not None and now < _cache_expires_at:
        logger.info("Enforcement pipeline: returning cached result (%.0fs remaining)",
                    _cache_expires_at - now)
        return _cache_payload

    logger.info("Enforcement pipeline: computing fresh result…")
    t_start = time.monotonic()

    # ── Fetch all stations ONCE ────────────────────────────────────────────────
    query = db.query(Station)
    if station_id:
        query = query.filter(Station.id == str(station_id))
    elif city:
        query = query.filter(Station.city == str(city))

    stations = query.all()
    all_stations_db = db.query(Station).all()
    cities   = sorted({st.city for st in all_stations_db if st.city})
    city_idx = {c: i for i, c in enumerate(cities)}

    # ── Per-station processing ─────────────────────────────────────────────────
    station_contexts: List[EnforcementContext] = []

    for st in stations:
        readings = retrieve_station_lag_history(db, st.id, 100)
        if len(readings) < 48:
            continue

        try:
            latest   = readings[-1]
            base_pm25 = latest.pm25 if latest.pm25 is not None else 80.0
            base_no2  = latest.no2  if latest.no2  is not None else 30.0

            current_weather = {
                "temperature":   latest.temp       if latest.temp       is not None else 25.0,
                "humidity":      latest.humidity   if latest.humidity   is not None else 60.0,
                "wind_speed":    latest.wind_speed if latest.wind_speed is not None else 10.0,
                "wind_direction":latest.wind_deg   if latest.wind_deg   is not None else 180.0,
            }
            fire_index = {
                "upwind_fire_intensity": latest.upwind_fire_intensity if latest.upwind_fire_intensity is not None else 0.0,
                "upwind_fire_count":     latest.upwind_fire_count     if latest.upwind_fire_count     is not None else 0,
            }

            # Build DataFrame for intelligence context (reuse readings already in memory)
            df = _build_reading_dataframe(readings)

            # ML forecast — inline, no redundant DB round-trip
            city_encoded   = city_idx.get(st.city, 0)
            forecast_records = _build_forecast(readings, st.latitude, st.longitude,
                                               city_encoded, base_pm25, base_no2)

            # Intelligence pipeline
            intel_ctx = IntelligenceContext(
                station=st,
                latest_reading=latest,
                history_df=df,
                forecasts=forecast_records,
                current_weather=current_weather,
                fire_index=fire_index,
            )
            r_engine     = reasoning_engine.RuleBasedReasoningEngine()
            reasoning_res = r_engine.analyze(intel_ctx)
            source_res    = source_attribution.analyze(intel_ctx)
            confidence_res= confidence.analyze(intel_ctx)
            risk_res      = risk_assessment.analyze(intel_ctx)
            decision_res  = decision_engine.analyze(intel_ctx, risk_res, source_res)

            # 24h trend delta
            pm25_recent = df["pm25"].tail(24).values
            trend_delta = float(pm25_recent[-1] - pm25_recent[0]) if len(pm25_recent) >= 24 else 0.0

            # Station Dossier Profile
            st_profile = get_station_profile(st.id, st.name, st.city, st.state or "")

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
                history_trend={"delta_24h": trend_delta},
                profile=st_profile,
            )
            station_contexts.append(enforce_ctx)

        except Exception as exc:
            logger.debug("Skipping station %s: %s", st.id, exc)
            continue

    # ── Priority ranking & enforcement analysis ────────────────────────────────
    priority_list: List[Dict] = []
    inspections:   List[Dict] = []
    interventions: List[Dict] = []
    allocations:   List[Dict] = []

    for ctx in station_contexts:
        priority_res = priority_engine.analyze(ctx)
        insp_res     = inspection_engine.analyze(ctx, priority_res)
        int_res      = intervention_engine.analyze(ctx, priority_res)
        alloc_res    = resource_allocator.analyze(ctx, priority_res)

        priority_list.append({
            "station_id":          ctx.station_id,
            "station_name":        ctx.station_name,
            "city":                ctx.city,
            "priority":            priority_res["priority"],
            "score":               priority_res["priority_score"],
            "reasoning":           priority_res["reasoning"],
            "trend_delta":         ctx.history_trend.get("delta_24h", 0.0),
            "current_aqi":         calculate_pm25_aqi(
                ctx.forecast[0]["predicted_pm25"] if ctx.forecast else 80.0
            ),
            "land_use":            ctx.profile.get("land_use", "Urban Corridor"),
            "zone_type":           ctx.profile.get("zone_type", "Residential/Commercial"),
            "spcb_authority":      ctx.profile.get("spcb_authority", "SPCB"),
            "registered_hotspots": ctx.profile.get("registered_hotspots", []),
            "receptors":           ctx.profile.get("receptors", {}),
        })

        for insp in insp_res:
            insp["target_station"] = ctx.station_name
            inspections.append(insp)
        for inter in int_res:
            inter["target_station"] = ctx.station_name
            interventions.append(inter)
        for alloc in alloc_res:
            allocations.append(alloc)

    # ── Sort & aggregate ───────────────────────────────────────────────────────
    priority_list      = sorted(priority_list, key=lambda x: x["score"], reverse=True)
    top_priority       = priority_list[:5]
    top_improving      = sorted(priority_list, key=lambda x: x["trend_delta"])[:5]
    top_deteriorating  = sorted(priority_list, key=lambda x: x["trend_delta"], reverse=True)[:5]
    top_stable         = sorted(priority_list, key=lambda x: abs(x["trend_delta"]))[:5]

    critical_count = sum(1 for p in priority_list if p["priority"] == "Critical")
    high_count     = sum(1 for p in priority_list if p["priority"] == "High")

    if critical_count > 0:
        headline = f"Alert: {critical_count} Municipal Wards under Critical Air Quality Priority!"
    elif high_count > 0:
        headline = f"Advisory: {high_count} Wards at High priority intervention status."
    else:
        headline = "Stable Local Environmental Conditions Maintained"

    elapsed = time.monotonic() - t_start
    logger.info("Enforcement pipeline: completed in %.2fs (%d stations)", elapsed, len(priority_list))

    result = {
        "metadata": {
            "timestamp":                datetime.utcnow().isoformat(),
            "total_stations_evaluated": len(priority_list),
            "compute_time_seconds":     round(elapsed, 2),
            "filter_station_id":        station_id,
            "filter_city":              city,
        },
        "priority_rankings":           priority_list,
        "hotspots": {
            "highest_priority": top_priority,
            "improving":        top_improving,
            "deteriorating":    top_deteriorating,
            "stable":           top_stable,
        },
        "inspection_recommendations":  inspections,
        "intervention_recommendations":interventions,
        "resource_allocation":         allocations,
        "executive_summary": {
            "headline":         headline,
            "total_evaluated":  len(priority_list),
            "critical_count":   critical_count,
            "high_count":       high_count,
            "direct_orders": (
                f"Deploy sweepers and restrict commercial diesel vehicles along {priority_list[0]['station_name']} corridors ({priority_list[0]['spcb_authority']})."
                if priority_list else
                "Routine operations. Inspect local construction sites."
            ),
        },
    }

    # Cache global unfiltered results
    if station_id is None and city is None:
        _cache_payload    = result
        _cache_expires_at = time.monotonic() + _CACHE_TTL_SECONDS

    return result
