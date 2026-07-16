from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.endpoints import router
from backend.app.core.database import init_db, SessionLocal

app = FastAPI(title="AtmosEdgeAI API", version="1.0.0")

# Enable CORS for frontend dashboard connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.on_event("startup")
def startup_event():
    print("Initializing database...")
    init_db()

    db = SessionLocal()
    try:
        from backend.app.core.database import City, Ward
        # Seed Delhi if no cities exist
        if db.query(City).count() == 0:
            print("Seeding initial city and ward data...")
            delhi = City(name="Delhi", latitude=28.6139, longitude=77.2090, ncap_target=40.0)
            db.add(delhi)
            db.flush()

            wards_data = [
                ("Anand Vihar",       28.6469, 77.3152, 250000),
                ("RK Puram",          28.5651, 77.1767, 180000),
                ("Rohini",            28.7495, 77.0664, 320000),
                ("Dwarka",            28.5823, 77.0500, 290000),
                ("Saket",             28.5244, 77.2167, 210000),
                ("Jahangirpuri",      28.7326, 77.1683, 270000),
                ("Okhla",             28.5384, 77.2768, 230000),
                ("Punjabi Bagh",      28.6742, 77.1311, 195000),
            ]
            for name, lat, lon, pop in wards_data:
                db.add(Ward(city_id=delhi.id, name=name, latitude=lat, longitude=lon, population=pop))
            db.commit()
            print("Seed complete.")
        else:
            print("Data already exists, skipping seed.")
    except Exception as e:
        print(f"Startup error: {e}")
        db.rollback()
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Welcome to the AtmosEdgeAI API. Visit /docs for documentation."}
