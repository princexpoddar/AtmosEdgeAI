"""
AtmosEdgeAI — FastAPI Application Entry Point
==============================================
Run with:  uvicorn backend.app.main:app --host 127.0.0.1 --port 8001
"""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env from project root before any other imports that read env vars
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)

import json
from datetime import datetime, timedelta
import numpy as np

from backend.app.api.endpoints import router
from backend.app.core.database import City, SessionLocal, Ward, init_db, Station, StationReading

logger = logging.getLogger(__name__)


def _seed_initial_data() -> None:
    """Seed default Delhi city/ward and 40 CPCB monitoring stations if the database is empty."""
    db = SessionLocal()
    try:
        # Legacy ward/city seed
        if db.query(City).count() == 0:
            logger.info("Seeding initial city and ward data...")
            delhi = City(name="Delhi", latitude=28.6139, longitude=77.2090, ncap_target=40.0)
            db.add(delhi)
            db.flush()

            wards_data = [
                ("Anand Vihar",  28.6469, 77.3152, 250000),
                ("RK Puram",     28.5651, 77.1767, 180000),
                ("Rohini",       28.7495, 77.0664, 320000),
                ("Dwarka",       28.5823, 77.0500, 290000),
                ("Saket",        28.5244, 77.2167, 210000),
                ("Jahangirpuri", 28.7326, 77.1683, 270000),
                ("Okhla",        28.5384, 77.2768, 230000),
                ("Punjabi Bagh", 28.6742, 77.1311, 195000),
            ]
            for name, lat, lon, pop in wards_data:
                db.add(Ward(city_id=delhi.id, name=name, latitude=lat, longitude=lon, population=pop))
            db.commit()

        # Modern 40-station network seed from selected_stations.json
        if db.query(Station).count() == 0:
            stations_file = Path(__file__).resolve().parents[1] / "data" / "selected_stations.json"
            if stations_file.exists():
                logger.info("Auto-seeding 40 CPCB stations and 72h baseline readings from %s...", stations_file.name)
                with open(stations_file, "r", encoding="utf-8") as f:
                    stations_list = json.load(f)

                now = datetime.utcnow()
                timestamps = [now - timedelta(hours=i) for i in reversed(range(72))]

                for s_data in stations_list:
                    sid = str(s_data.get("id"))
                    st = Station(
                        id=sid,
                        name=s_data.get("name", f"Station {sid}"),
                        city=s_data.get("city", ""),
                        state=s_data.get("state", ""),
                        latitude=float(s_data.get("latitude", 0.0)),
                        longitude=float(s_data.get("longitude", 0.0)),
                        elevation=float(s_data.get("elevation", 200.0)),
                        station_type=s_data.get("station_type", "Continuous"),
                        available_pollutants=s_data.get("pollutants", "pm25,pm10,no2,so2,co,o3"),
                        quality_score=float(s_data.get("quality_score", 95.0)),
                    )
                    db.add(st)
                    db.flush()

                    city_lower = (s_data.get("city") or "").lower()
                    if any(c in city_lower for c in ["delhi", "ghaziabad", "noida", "faridabad"]):
                        base_pm25, base_no2 = 180.0, 45.0
                    elif any(c in city_lower for c in ["patna", "kanpur", "lucknow"]):
                        base_pm25, base_no2 = 130.0, 38.0
                    elif any(c in city_lower for c in ["mumbai", "kolkata"]):
                        base_pm25, base_no2 = 85.0, 32.0
                    else:
                        base_pm25, base_no2 = 38.0, 20.0

                    for t in timestamps:
                        diurn_pm = 1.0 + 0.15 * np.cos(2 * np.pi * (t.hour - 8) / 24.0)
                        diurn_no2 = 1.0 + 0.10 * np.cos(2 * np.pi * (t.hour - 9) / 24.0)
                        reading = StationReading(
                            station_id=sid,
                            timestamp=t,
                            pm25=round(base_pm25 * diurn_pm, 1),
                            pm10=round(base_pm25 * diurn_pm * 1.6, 1),
                            no2=round(base_no2 * diurn_no2, 1),
                            so2=14.5,
                            co=1.1,
                            o3=34.0,
                            temp=round(26.0 + 4.0 * np.sin(2 * np.pi * (t.hour - 14) / 24.0), 1),
                            humidity=round(55.0 - 15.0 * np.sin(2 * np.pi * (t.hour - 14) / 24.0), 1),
                            wind_speed=8.5,
                            wind_deg=180.0,
                            stagnation=0.52 if "delhi" in city_lower else 0.40,
                            upwind_fire_intensity=25.0 if "delhi" in city_lower else 0.0,
                            upwind_fire_count=8 if "delhi" in city_lower else 0,
                        )
                        db.add(reading)

                db.commit()
                logger.info("Successfully seeded 40 stations and 72h baseline readings.")
    except Exception:
        logger.exception("Error during startup seed")
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: init DB and verify env on startup."""
    logger.info("Initializing database...")
    init_db()
    _seed_initial_data()

    api_key = os.getenv("DATA_GOV_IN_API_KEY", "")
    if api_key:
        logger.info("DATA_GOV_IN_API_KEY loaded (len=%d)", len(api_key))
    else:
        logger.warning("DATA_GOV_IN_API_KEY is MISSING — live sync will not work")

    yield  # Application runs here
    logger.info("AtmosEdgeAI shutting down.")


app = FastAPI(
    title="AtmosEdgeAI API",
    version="2.1.0",
    description="Urban Air Quality Intelligence Platform — REST API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/", tags=["Health"])
def read_root():
    return {"message": "AtmosEdgeAI API v2.1. Visit /docs for documentation."}


@app.get("/api/health", tags=["Health"])
def health_check():
    """Quick health check endpoint for monitoring."""
    return {"status": "ok", "version": "2.1.0"}


@app.get("/api/debug/env", tags=["Debug"], include_in_schema=False)
def debug_env():
    """Internal endpoint to verify env variables are loaded at runtime."""
    return {
        "DATA_GOV_IN_API_KEY": "SET" if os.getenv("DATA_GOV_IN_API_KEY") else "MISSING",
        "OPENAQ_API_KEY":      "SET" if os.getenv("OPENAQ_API_KEY")      else "MISSING",
        "NASA_FIRMS_MAP_KEY":  "SET" if os.getenv("NASA_FIRMS_MAP_KEY")  else "MISSING",
    }
