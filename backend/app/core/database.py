import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, ForeignKey, Text, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATABASE_URL = f"sqlite:///{os.path.join(db_dir, 'geobreathe.db')}"

# Enable multi-threaded check exemption and a 30-second busy timeout
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False, "timeout": 30}
)

# Set WAL mode on SQLite connection to allow concurrent reads/writes
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class City(Base):
    __tablename__ = "cities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    ncap_target = Column(Float)  # Target reduction % (e.g. 40.0)
    wards = relationship("Ward", back_populates="city")

class Ward(Base):
    __tablename__ = "wards"
    id = Column(Integer, primary_key=True, index=True)
    city_id = Column(Integer, ForeignKey("cities.id"))
    name = Column(String, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    population = Column(Integer)
    boundary_geojson = Column(Text)  # GeoJSON string for mapping
    city = relationship("City", back_populates="wards")
    readings = relationship("Reading", back_populates="ward")
    forecasts = relationship("Forecast", back_populates="ward")
    attributions = relationship("Attribution", back_populates="ward")
    enforcements = relationship("EnforcementTarget", back_populates="ward")
    advisories = relationship("Advisory", back_populates="ward")

class Reading(Base):
    __tablename__ = "readings"
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"))
    timestamp = Column(DateTime, index=True, default=datetime.utcnow)
    pm25 = Column(Float)
    pm10 = Column(Float)
    no2 = Column(Float)
    so2 = Column(Float)
    o3 = Column(Float)
    co = Column(Float)
    temp = Column(Float)
    humidity = Column(Float)
    wind_speed = Column(Float)
    wind_deg = Column(Float)
    stagnation = Column(Float)
    
    ward = relationship("Ward", back_populates="readings")

class Forecast(Base):
    __tablename__ = "forecasts"
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"))
    timestamp = Column(DateTime, index=True)  # Forecast generation time
    forecast_time = Column(DateTime, index=True)  # Predicted time
    predicted_pm25 = Column(Float)
    predicted_no2 = Column(Float)
    predicted_aqi = Column(Float)
    
    ward = relationship("Ward", back_populates="forecasts")

class Attribution(Base):
    __tablename__ = "attributions"
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"))
    timestamp = Column(DateTime, index=True, default=datetime.utcnow)
    vehicular_pct = Column(Float)
    industrial_pct = Column(Float)
    biomass_pct = Column(Float)
    waste_burning_pct = Column(Float)
    dust_pct = Column(Float)
    confidence = Column(Float)
    
    ward = relationship("Ward", back_populates="attributions")

class EnforcementTarget(Base):
    __tablename__ = "enforcement_targets"
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"))
    name = Column(String)
    type = Column(String)  # Industrial, Traffic Corridor, Waste Burning, Construction
    latitude = Column(Float)
    longitude = Column(Float)
    risk_score = Column(Float)
    evidence_packet = Column(Text)  # JSON details (stagnation, PM levels)
    status = Column(String, default="Pending")  # Pending, Inspected, Resolved
    created_at = Column(DateTime, default=datetime.utcnow)
    
    ward = relationship("Ward", back_populates="enforcements")

class Advisory(Base):
    __tablename__ = "advisories"
    id = Column(Integer, primary_key=True, index=True)
    ward_id = Column(Integer, ForeignKey("wards.id"))
    timestamp = Column(DateTime, index=True, default=datetime.utcnow)
    level = Column(String)  # Good, Moderate, Poor, Severe
    message_en = Column(Text)
    message_hi = Column(Text)
    message_local = Column(Text)
    
    ward = relationship("Ward", back_populates="advisories")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
