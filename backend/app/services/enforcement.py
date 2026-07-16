import json
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.core.database import Ward, Reading, EnforcementTarget

def prioritize_enforcements(db: Session):
    """
    Scans recent readings for stagnation, high PM2.5 hotspots, and high risk profiles.
    Identifies wards requiring enforcement actions and saves targets to the database.
    """
    wards = db.query(Ward).all()
    for w in wards:
        latest = db.query(Reading).filter(Reading.ward_id == w.id).order_by(Reading.timestamp.desc()).first()
        if not latest:
            continue
            
        pm25 = latest.pm25
        stagnation = latest.stagnation
        
        # Calculate risk score based on PM2.5 levels and atmospheric stagnation
        risk_score = pm25 * 0.7 + stagnation * 30.0
        
        # If risk is elevated, create an enforcement target entry if not already pending
        if risk_score > 50.0:
            exists = db.query(EnforcementTarget).filter(
                EnforcementTarget.ward_id == w.id,
                EnforcementTarget.status == "Pending"
            ).first()
            
            if not exists:
                evidence = {
                    "detected_pm25": pm25,
                    "stagnation": stagnation,
                    "wind_speed": latest.wind_speed,
                    "temp": latest.temp,
                    "timestamp": latest.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Determine mock source type based on ward metadata/name
                if "Industrial" in w.name or "Peenya" in w.name or "Okhla" in w.name:
                    source_type = "Industrial"
                    name = f"Industrial Facility Emissions - {w.name}"
                else:
                    source_type = "Traffic Corridor"
                    name = f"Vehicular Congestion Hotspot - {w.name}"
                    
                target = EnforcementTarget(
                    ward_id=w.id,
                    name=name,
                    type=source_type,
                    latitude=w.latitude,
                    longitude=w.longitude,
                    risk_score=float(round(risk_score, 2)),
                    evidence_packet=json.dumps(evidence),
                    status="Pending",
                    created_at=datetime.utcnow()
                )
                db.add(target)
    db.commit()
