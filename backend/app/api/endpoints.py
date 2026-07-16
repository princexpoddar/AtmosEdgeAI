from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
from typing import List, Dict, Any
from backend.app.core.database import get_db, City, Ward, Reading, Forecast, Attribution, EnforcementTarget, Advisory
from backend.app.services.advisory import generate_chat_response, get_aqi_category
from backend.app.services.forecaster import calculate_pm25_aqi

router = APIRouter()

@router.get("/cities")
def get_cities(db: Session = Depends(get_db)):
    cities = db.query(City).all()
    return [{"id": c.id, "name": c.name, "latitude": c.latitude, "longitude": c.longitude, "ncap_target": c.ncap_target} for c in cities]

@router.get("/wards")
def get_wards(city_id: int, db: Session = Depends(get_db)):
    wards = db.query(Ward).filter(Ward.city_id == city_id).all()
    return [{
        "id": w.id,
        "name": w.name,
        "latitude": w.latitude,
        "longitude": w.longitude,
        "population": w.population,
        "boundary_geojson": w.boundary_geojson
    } for w in wards]

@router.get("/aqi/realtime")
def get_realtime_aqi(city_id: int, db: Session = Depends(get_db)):
    wards = db.query(Ward).filter(Ward.city_id == city_id).all()
    result = []
    for w in wards:
        latest = db.query(Reading).filter(
            Reading.ward_id == w.id
        ).order_by(Reading.timestamp.desc()).first()
        
        if latest:
            category = get_aqi_category(latest.pm25)
            aqi = calculate_pm25_aqi(latest.pm25)
            result.append({
                "ward_id": w.id,
                "ward_name": w.name,
                "latitude": w.latitude,
                "longitude": w.longitude,
                "timestamp": latest.timestamp,
                "pm25": latest.pm25,
                "pm10": latest.pm10,
                "no2": latest.no2,
                "so2": latest.so2,
                "o3": latest.o3,
                "co": latest.co,
                "aqi": round(aqi, 1),
                "category": category,
                "temp": latest.temp,
                "humidity": latest.humidity,
                "wind_speed": latest.wind_speed,
                "wind_deg": latest.wind_deg,
                "stagnation": latest.stagnation
            })
    return result

@router.get("/aqi/history")
def get_aqi_history(ward_id: int, hours: int = 24, db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    readings = db.query(Reading).filter(
        Reading.ward_id == ward_id,
        Reading.timestamp >= cutoff
    ).order_by(Reading.timestamp.asc()).all()
    
    result = []
    for r in readings:
        result.append({
            "timestamp": r.timestamp,
            "pm25": r.pm25,
            "pm10": r.pm10,
            "aqi": round(calculate_pm25_aqi(r.pm25), 1),
            "wind_speed": r.wind_speed,
            "stagnation": r.stagnation
        })
    return result

@router.post("/aqi/sync")
def sync_aqi_data(db: Session = Depends(get_db)):
    from backend.app.services.realtime_updater import update_db_realtime
    try:
        res = update_db_realtime(db)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecast")
def get_forecast(ward_id: int, db: Session = Depends(get_db)):
    # Fetch recent forecasts (rolling lead hours)
    latest_fc_time = db.query(Forecast.timestamp).filter(
        Forecast.ward_id == ward_id
    ).order_by(Forecast.timestamp.desc()).first()
    
    if not latest_fc_time:
        return []
        
    fcs = db.query(Forecast).filter(
        Forecast.ward_id == ward_id,
        Forecast.timestamp == latest_fc_time[0]
    ).order_by(Forecast.forecast_time.asc()).all()
    
    return [{
        "forecast_time": f.forecast_time,
        "predicted_pm25": f.predicted_pm25,
        "predicted_no2": f.predicted_no2,
        "predicted_aqi": f.predicted_aqi
    } for f in fcs]

@router.get("/attribution")
def get_attribution(ward_id: int, db: Session = Depends(get_db)):
    attrib = db.query(Attribution).filter(
        Attribution.ward_id == ward_id
    ).order_by(Attribution.timestamp.desc()).first()
    
    if not attrib:
        # Generate on-demand if missing
        from backend.app.services.attribution import run_source_attribution
        attrib = run_source_attribution(db, ward_id, datetime.utcnow())
        db.add(attrib)
        db.commit()
        
    return {
        "timestamp": attrib.timestamp,
        "vehicular": attrib.vehicular_pct,
        "industrial": attrib.industrial_pct,
        "biomass": attrib.biomass_pct,
        "waste_burning": attrib.waste_burning_pct,
        "dust": attrib.dust_pct,
        "confidence": attrib.confidence
    }

@router.get("/enforcement")
def get_enforcement_queue(city_id: int, db: Session = Depends(get_db)):
    targets = db.query(EnforcementTarget).join(Ward).filter(
        Ward.city_id == city_id
    ).order_by(EnforcementTarget.risk_score.desc()).all()
    
    result = []
    for t in targets:
        result.append({
            "id": t.id,
            "ward_name": t.ward.name,
            "name": t.name,
            "type": t.type,
            "latitude": t.latitude,
            "longitude": t.longitude,
            "risk_score": t.risk_score,
            "status": t.status,
            "evidence_packet": json.loads(t.evidence_packet) if t.evidence_packet else {},
            "created_at": t.created_at
        })
    return result

@router.post("/enforcement/inspect/{target_id}")
def inspect_target(target_id: int, status: str = "Inspected", db: Session = Depends(get_db)):
    target = db.query(EnforcementTarget).filter(EnforcementTarget.id == target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Inspection target not found")
    target.status = status
    db.commit()
    return {"message": f"Target {target_id} updated to {status}."}

@router.get("/advisory")
def get_ward_advisory(ward_id: int, db: Session = Depends(get_db)):
    adv = db.query(Advisory).filter(
        Advisory.ward_id == ward_id
    ).order_by(Advisory.timestamp.desc()).first()
    
    if not adv:
        return {}
        
    return {
        "level": adv.level,
        "message_en": adv.message_en,
        "message_hi": adv.message_hi,
        "message_local": adv.message_local
    }

# We handle JSON payloads for chat
from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    query: str
    ward_id: int
    gemini_api_key: Optional[str] = None

@router.post("/advisory/chat")
def advisory_chat(payload: ChatRequest, db: Session = Depends(get_db)):
    response = generate_chat_response(payload.query, payload.ward_id, db, payload.gemini_api_key)
    return {"response": response}
