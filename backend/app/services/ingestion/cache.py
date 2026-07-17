import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from backend.app.core.database import StationReading, Station

logger = logging.getLogger(__name__)

def calculate_stagnation_index(wind_speed_kmh: float) -> float:
    """
    Stagnation index calculation helper.
    """
    wind_speed_ms = wind_speed_kmh / 3.6
    wind_factor = max(0.0, 1.0 - (wind_speed_ms / 6.0))
    pbl_factor = 0.65 # Assume moderate mixing height for live fallbacks
    return float(round(wind_factor * pbl_factor, 2))

def commit_normalized_observation(
    db: Session,
    station_id: str,
    timestamp: datetime,
    pm25: float,
    no2: float,
    temp: float,
    humidity: float,
    wind_speed: float,
    wind_deg: float,
    fire_intensity: float,
    fire_count: int,
    source: str = "LIVE",
    quality_flag: str = "LIVE"
) -> StationReading:
    """
    Inserts or updates a normalized station reading row in SQLite.
    Deduplicates based on station_id + timestamp.
    """
    # 1. Validation and bounds cleaning
    if pm25 is not None:
        pm25 = max(0.0, min(1000.0, pm25))
    if no2 is not None:
        no2 = max(0.0, min(500.0, no2))
        
    temp = max(-10.0, min(55.0, temp)) if temp is not None else 25.0
    humidity = max(0.0, min(100.0, humidity)) if humidity is not None else 60.0
    wind_speed = max(0.0, min(150.0, wind_speed)) if wind_speed is not None else 10.0
    wind_deg = max(0.0, min(360.0, wind_deg)) if wind_deg is not None else 180.0
    
    stagnation = calculate_stagnation_index(wind_speed)
    pm10 = pm25 * 1.6 if pm25 is not None else 0.0
    
    # 2. Find existing record to avoid duplicate key errors
    exists = db.query(StationReading).filter(
        and_(
            StationReading.station_id == station_id,
            StationReading.timestamp == timestamp
        )
    ).first()
    
    if exists:
        exists.pm25 = pm25
        exists.pm10 = pm10
        exists.no2 = no2
        exists.temp = temp
        exists.humidity = humidity
        exists.wind_speed = wind_speed
        exists.wind_deg = wind_deg
        exists.upwind_fire_intensity = fire_intensity
        exists.upwind_fire_count = fire_count
        exists.stagnation = stagnation
        db.commit()
        return exists
    else:
        reading = StationReading(
            station_id=station_id,
            timestamp=timestamp,
            pm25=pm25,
            pm10=pm10,
            no2=no2,
            temp=temp,
            humidity=humidity,
            wind_speed=wind_speed,
            wind_deg=wind_deg,
            upwind_fire_intensity=fire_intensity,
            upwind_fire_count=fire_count,
            stagnation=stagnation
        )
        db.add(reading)
        db.commit()
        return reading

def retrieve_station_lag_history(db: Session, station_id: str, count: int = 48) -> list:
    """
    Queries SQLite to retrieve the rolling cache of recent observations.
    Attempts to pull up to 48 hours.
    Returns a sorted list of dictionaries containing: pm25, no2, temp, humidity, wind_speed, wind_deg, stagnation, upwind_fire_intensity, upwind_fire_count, timestamp.
    """
    # Grab latest readings with non-null pm25 to ensure lag features can be constructed
    readings = db.query(StationReading).filter(
        StationReading.station_id == station_id
    ).order_by(StationReading.timestamp.desc()).limit(count).all()
    
    readings.reverse()
    return readings
