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

from backend.app.api.endpoints import router
from backend.app.core.database import City, SessionLocal, Ward, init_db

logger = logging.getLogger(__name__)


def _seed_initial_data() -> None:
    """Seed default Delhi city/ward data if the database is empty."""
    db = SessionLocal()
    try:
        if db.query(City).count() > 0:
            logger.info("Database already seeded — skipping.")
            return

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
        logger.info("Seed complete.")
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
    allow_origins=["*"],
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
