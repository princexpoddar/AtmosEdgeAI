import logging
from sqlalchemy.orm import Session
from backend.app.core.database import Station, StationReading

logger = logging.getLogger(__name__)

def upsert_stations(session: Session, stations_data: list, engine_type: str = "sqlite") -> None:
    """
    Upserts station records into the database.
    Prevents duplicate primary keys and updates changing metadata dynamically.
    """
    if not stations_data:
        return
    
    try:
        if engine_type == "sqlite":
            from sqlalchemy.dialects.sqlite import insert
            for data in stations_data:
                stmt = insert(Station).values(data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "name": stmt.excluded.name,
                        "city": stmt.excluded.city,
                        "state": stmt.excluded.state,
                        "latitude": stmt.excluded.latitude,
                        "longitude": stmt.excluded.longitude,
                        "elevation": stmt.excluded.elevation,
                        "station_type": stmt.excluded.station_type,
                        "installation_date": stmt.excluded.installation_date,
                        "available_pollutants": stmt.excluded.available_pollutants,
                        "quality_score": stmt.excluded.quality_score
                    }
                )
                session.execute(stmt)
        elif engine_type == "postgresql":
            from sqlalchemy.dialects.postgresql import insert
            for data in stations_data:
                stmt = insert(Station).values(data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "name": stmt.excluded.name,
                        "city": stmt.excluded.city,
                        "state": stmt.excluded.state,
                        "latitude": stmt.excluded.latitude,
                        "longitude": stmt.excluded.longitude,
                        "elevation": stmt.excluded.elevation,
                        "station_type": stmt.excluded.station_type,
                        "installation_date": stmt.excluded.installation_date,
                        "available_pollutants": stmt.excluded.available_pollutants,
                        "quality_score": stmt.excluded.quality_score
                    }
                )
                session.execute(stmt)
        else:
            # Fallback standard merge
            for data in stations_data:
                session.merge(Station(**data))
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error performing station upsert: {e}")
        raise e

def upsert_station_readings(session: Session, readings_data: list, engine_type: str = "sqlite") -> None:
    """
    Upserts station readings in batches to scale to millions of records.
    Prevents duplicate (station_id, timestamp) rows and updates existing records.
    """
    if not readings_data:
        return
        
    batch_size = 1000
    total = len(readings_data)
    
    try:
        for start in range(0, total, batch_size):
            batch = readings_data[start : start + batch_size]
            
            if engine_type == "sqlite":
                from sqlalchemy.dialects.sqlite import insert
                for data in batch:
                    stmt = insert(StationReading).values(data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["station_id", "timestamp"],
                        set_={
                            "pm25": stmt.excluded.pm25,
                            "pm10": stmt.excluded.pm10,
                            "no2": stmt.excluded.no2,
                            "so2": stmt.excluded.so2,
                            "o3": stmt.excluded.o3,
                            "co": stmt.excluded.co,
                            "temp": stmt.excluded.temp,
                            "humidity": stmt.excluded.humidity,
                            "surface_pressure": stmt.excluded.surface_pressure,
                            "wind_speed": stmt.excluded.wind_speed,
                            "wind_deg": stmt.excluded.wind_deg,
                            "wind_u": stmt.excluded.wind_u,
                            "wind_v": stmt.excluded.wind_v,
                            "precipitation": stmt.excluded.precipitation,
                            "pbl_height": stmt.excluded.pbl_height,
                            "solar_radiation": stmt.excluded.solar_radiation,
                            "cloud_cover": stmt.excluded.cloud_cover,
                            "dew_point": stmt.excluded.dew_point,
                            "visibility": stmt.excluded.visibility,
                            "upwind_fire_intensity": stmt.excluded.upwind_fire_intensity,
                            "upwind_fire_count": stmt.excluded.upwind_fire_count,
                            "stagnation": stmt.excluded.stagnation
                        }
                    )
                    session.execute(stmt)
            elif engine_type == "postgresql":
                from sqlalchemy.dialects.postgresql import insert
                for data in batch:
                    stmt = insert(StationReading).values(data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["station_id", "timestamp"],
                        set_={
                            "pm25": stmt.excluded.pm25,
                            "pm10": stmt.excluded.pm10,
                            "no2": stmt.excluded.no2,
                            "so2": stmt.excluded.so2,
                            "o3": stmt.excluded.o3,
                            "co": stmt.excluded.co,
                            "temp": stmt.excluded.temp,
                            "humidity": stmt.excluded.humidity,
                            "surface_pressure": stmt.excluded.surface_pressure,
                            "wind_speed": stmt.excluded.wind_speed,
                            "wind_deg": stmt.excluded.wind_deg,
                            "wind_u": stmt.excluded.wind_u,
                            "wind_v": stmt.excluded.wind_v,
                            "precipitation": stmt.excluded.precipitation,
                            "pbl_height": stmt.excluded.pbl_height,
                            "solar_radiation": stmt.excluded.solar_radiation,
                            "cloud_cover": stmt.excluded.cloud_cover,
                            "dew_point": stmt.excluded.dew_point,
                            "visibility": stmt.excluded.visibility,
                            "upwind_fire_intensity": stmt.excluded.upwind_fire_intensity,
                            "upwind_fire_count": stmt.excluded.upwind_fire_count,
                            "stagnation": stmt.excluded.stagnation
                        }
                    )
                    session.execute(stmt)
            else:
                for data in batch:
                    session.merge(StationReading(**data))
            
            session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Error performing batch readings upsert: {e}")
        raise e
