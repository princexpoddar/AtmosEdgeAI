import os
import sys
import json
from datetime import datetime

# Setup Python path to find the backend app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from backend.app.core.database import SessionLocal, Forecast, Attribution, Reading, Station, StationReading
from backend.app.services.forecaster import generate_forecasts_for_all
from backend.app.services.attribution import run_attribution_for_all

def verify_pipeline():
    print("--- Starting Pipeline Verification Run ---")
    db = SessionLocal()
    try:
        # Check current reading count
        readings_count = db.query(StationReading).count()
        print(f"Current Station Readings in database: {readings_count:,}")
        if readings_count == 0:
            print("ERROR: Database station_readings table is empty. Please run seeding script first.")
            return
            
        station_count = db.query(Station).count()
        print(f"Current Stations in database: {station_count}")
        
        # Calculate Average Quality Score
        stations = db.query(Station).all()
        if stations:
            avg_q = sum(s.quality_score for s in stations) / len(stations)
            print(f"Average Station Quality Score: {avg_q:.2f}/100")
            
        # 1. Test Forecasting pipeline (PyTorch CNN-LSTM training & prediction)
        print("\n1. Testing Forecasting Pipeline (Training PyTorch CNN-LSTM)...")
        # Clear old forecasts first to ensure clean execution
        db.query(Forecast).delete()
        db.commit()
        
        start_time = datetime.now()
        generate_forecasts_for_all(db, retrain=True)
        print(f"Forecasting complete in {datetime.now() - start_time}.")
        
        # Verify forecasts in database
        forecasts = db.query(Forecast).limit(10).all()
        print(f"Successfully generated forecasts. Saved count: {db.query(Forecast).count()}")
        print("Sample Forecast Rows (Aggregated to Wards via IDW):")
        for f in forecasts:
            print(f"  Ward {f.ward_id} | Time: {f.forecast_time} | Pred PM2.5: {f.predicted_pm25:.2f} | Pred NO2: {f.predicted_no2:.2f} | Pred AQI: {f.predicted_aqi:.1f}")
            
        # Verify reports and manifest existence
        print("\n2. Verifying Pipeline Ingestion Artifacts and Reports...")
        models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models"))
        
        manifest_path = os.path.join(models_dir, "download_manifest.json")
        version_path = os.path.join(models_dir, "dataset_version.json")
        readiness_path = os.path.join(models_dir, "ml_readiness_report.json")
        audit_path = os.path.join(models_dir, "dataset_audit.html")
        
        for name, path in [
            ("Download Manifest", manifest_path),
            ("Dataset Version", version_path),
            ("ML Readiness Report", readiness_path),
            ("Dataset Audit Report (HTML)", audit_path)
        ]:
            if os.path.exists(path):
                print(f"  [Artifact] {name} found at: {path}")
            else:
                print(f"  [Artifact] WARNING: {name} NOT found at: {path}")
                
        # 3. Test Source Attribution pipeline
        print("\n3. Testing Source Attribution Pipeline (Dynamic NASA FIRMS lookup)...")
        db.query(Attribution).delete()
        db.commit()
        
        start_time = datetime.now()
        run_attribution_for_all(db)
        print(f"Attribution complete in {datetime.now() - start_time}.")
        
        # Verify attributions in database
        attributions = db.query(Attribution).limit(10).all()
        print(f"Successfully generated attributions. Saved count: {db.query(Attribution).count()}")
        print("Sample Attribution Rows:")
        for a in attributions:
            print(f"  Ward {a.ward_id} | Vehicular: {a.vehicular_pct}% | Industrial: {a.industrial_pct}% | Biomass: {a.biomass_pct}% | Waste: {a.waste_burning_pct}% | Dust: {a.dust_pct}% | Confidence: {a.confidence:.2f}")
            
        print("\nPipeline Verification Successful!")
    except Exception as e:
        print(f"\nVerification Failed with error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_pipeline()
