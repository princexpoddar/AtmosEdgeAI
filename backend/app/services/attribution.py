import math
import random
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.core.database import Ward, Reading, Attribution
from backend.app.services.firms_processor import get_firms_processor

# Location of major external pollution hotspots
# Delhi NCR: industrial areas (Okhla, Sahibabad) and agricultural crop fires (Punjab/Haryana is North-West)
# Bengaluru: Peenya industrial area, transit hubs
SOURCE_HUBS = {
    "Delhi NCR": {
        "industrial": [
            {"name": "Okhla Industrial", "lat": 28.5355, "lng": 77.2639},
            {"name": "Sahibabad Industrial", "lat": 28.6750, "lng": 77.3450}
        ],
        "biomass": [
            {"name": "Haryana Farms", "lat": 29.5000, "lng": 76.2000},
            {"name": "Punjab Farms", "lat": 30.5000, "lng": 75.0000}
        ]
    },
    "Bengaluru": {
        "industrial": [
            {"name": "Peenya Industrial Hub", "lat": 13.0300, "lng": 77.5200},
            {"name": "Bommasandra Industrial", "lat": 12.8100, "lng": 77.6900}
        ],
        "biomass": [
            {"name": "Rural Outskirts", "lat": 13.2000, "lng": 77.8000}
        ]
    }
}

def calculate_bearing(lat1, lon1, lat2, lon2):
    """
    Calculates the compass bearing from point 1 to point 2
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dLon = lon2 - lon1
    y = math.sin(dLon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
    bearing = math.atan2(y, x)
    bearing = math.degrees(bearing)
    return (bearing + 360) % 360

def run_source_attribution(db: Session, ward_id: int, timestamp: datetime) -> Attribution:
    """
    Analyses wind, location, and temporal features to attribute PM2.5 sources.
    """
    ward = db.query(Ward).filter(Ward.id == ward_id).first()
    if not ward:
        raise ValueError(f"Ward with ID {ward_id} not found.")
        
    # Get latest reading at or before timestamp
    reading = db.query(Reading).filter(
        Reading.ward_id == ward_id,
        Reading.timestamp <= timestamp
    ).order_by(Reading.timestamp.desc()).first()
    
    if not reading:
        # Fallback reading
        reading = Reading(
            pm25=100.0, temp=20.0, humidity=50.0, wind_speed=3.0, wind_deg=270.0, stagnation=0.5
        )
        
    city_name = ward.city.name
    hubs = SOURCE_HUBS.get(city_name, SOURCE_HUBS["Delhi NCR"])
    
    # 1. Evaluate Upwind Industrial Influence
    industrial_influence = 0.0
    for ind_hub in hubs["industrial"]:
        bearing = calculate_bearing(ward.latitude, ward.longitude, ind_hub["lat"], ind_hub["lng"])
        # Wind is coming from reading.wind_deg. If difference between bearing and wind_deg is small, it's upwind.
        angle_diff = abs(bearing - reading.wind_deg)
        angle_diff = min(angle_diff, 360.0 - angle_diff)
        
        if angle_diff < 45.0: # Sector of 90 degrees upwind
            # Distance damping factor
            dist = math.sqrt((ward.latitude - ind_hub["lat"])**2 + (ward.longitude - ind_hub["lng"])**2)
            dist_factor = max(0.1, 1.0 / (dist * 100.0 + 1.0))
            # Wind speed increases dispersion, but also transports from far away if speed is moderate.
            speed_factor = min(2.0, reading.wind_speed / 4.0) if reading.wind_speed > 1.0 else 0.2
            industrial_influence += dist_factor * speed_factor * (1.0 - angle_diff / 45.0)

    # 2. Evaluate Upwind Agricultural Biomass Burning using NASA FIRMS fire alerts
    firms_proc = get_firms_processor()
    fire_metrics = firms_proc.get_upwind_fire_metrics(
        ward.latitude,
        ward.longitude,
        timestamp,
        reading.wind_speed,
        reading.wind_deg,
        city_name
    )
    # Scale upwind fire intensity (UFTI) to match contribution scores (UFTI is scaled by 0.08)
    biomass_influence = fire_metrics["upwind_fire_intensity"] * 0.08


    # 3. Traffic Density (Local vehicular emission)
    # Traffic peaks around 8-10 AM and 5-8 PM
    hour = timestamp.hour
    is_peak = (8 <= hour <= 10) or (17 <= hour <= 20)
    traffic_base = 0.45 if is_peak else 0.2
    
    # Specific ward multipliers
    if "Connaught" in ward.name or "Koramangala" in ward.name or "Indiranagar" in ward.name:
        traffic_base *= 1.5
    elif "Industrial" in ward.name:
        traffic_base *= 0.7
        
    vehicular_raw = traffic_base * (1.0 + reading.stagnation * 0.5)

    # 4. Construction Dust
    # Dry, high-wind conditions lead to re-suspended dust
    dust_raw = 0.15
    if reading.humidity < 40.0:
        dust_raw += (40.0 - reading.humidity) / 100.0
    if reading.wind_speed > 6.0:
        dust_raw += (reading.wind_speed - 6.0) * 0.05
    if "Dwarka" in ward.name or "Whitefield" in ward.name: # high construction zones
        dust_raw *= 1.6

    # 5. Local Waste Burning (mostly in winters, low boundary layer, calm winds)
    waste_raw = 0.1
    if reading.stagnation > 0.6: # trapped, local pockets
        waste_raw += (reading.stagnation - 0.6) * 0.4
    if reading.temp < 15.0: # heating fires in winter nights
        waste_raw += (15.0 - reading.temp) * 0.03

    # Normalize contributions
    scores = {
        "vehicular": vehicular_raw,
        "industrial": industrial_influence + (0.35 if "Industrial" in ward.name else 0.05),
        "biomass": biomass_influence,
        "waste_burning": waste_raw,
        "dust": dust_raw
    }
    
    total = sum(scores.values())
    for k in scores:
        scores[k] = round((scores[k] / total) * 100.0, 1)

    # Output Attribution db row
    attrib = Attribution(
        ward_id=ward_id,
        timestamp=timestamp,
        vehicular_pct=scores["vehicular"],
        industrial_pct=scores["industrial"],
        biomass_pct=scores["biomass"],
        waste_burning_pct=scores["waste_burning"],
        dust_pct=scores["dust"],
        confidence=round(0.85 - (0.15 * reading.stagnation) + random.uniform(-0.05, 0.05), 2)
    )
    return attrib

def run_attribution_for_all(db: Session):
    wards = db.query(Ward).all()
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    for w in wards:
        # Check if already attributed for this hour
        exists = db.query(Attribution).filter(
            Attribution.ward_id == w.id,
            Attribution.timestamp == now
        ).first()
        if not exists:
            attrib = run_source_attribution(db, w.id, now)
            db.add(attrib)
    db.commit()
    print("Source attribution completed for all wards.")
