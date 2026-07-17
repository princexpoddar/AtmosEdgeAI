"""
Pipeline Verification & Data Audit Script.
Verifies the full training dataset integrity and generates a console audit report.

Run:
    .\venv\Scripts\python -u backend/app/tests/verify_pipeline.py
"""
import os, sys, json
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

from backend.app.core.database import SessionLocal, Forecast, Attribution, StationReading, Station
from backend.app.services.forecaster import generate_forecasts_for_all
from backend.app.services.attribution import run_attribution_for_all
from backend.app.services.ml.config import MODELS_DIR

# ─────────────────────────────────────────────
# 0. SECTION HEADER HELPER
# ─────────────────────────────────────────────
def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ─────────────────────────────────────────────
# 1. DATABASE AUDIT
# ─────────────────────────────────────────────
def audit_database(db) -> bool:
    section("DATABASE AUDIT")

    station_count = db.query(Station).count()
    readings_count = db.query(StationReading).count()
    print(f"  Stations in DB         : {station_count}")
    print(f"  Station Readings in DB : {readings_count:,}")

    if readings_count == 0:
        print("\n  [ERROR] Database is empty. Run seeding script first.")
        return False

    # Per-station breakdown
    stations = db.query(Station).all()
    print(f"\n  {'Station':<35} {'City':<20} {'Readings':>10} {'Quality':>9}")
    print(f"  {'-'*35} {'-'*20} {'-'*10} {'-'*9}")
    total_q = 0.0
    for s in stations:
        rc = db.query(StationReading).filter(StationReading.station_id == s.id).count()
        q = s.quality_score or 0.0
        total_q += q
        print(f"  {s.name[:34]:<35} {(s.city or 'Unknown')[:19]:<20} {rc:>10,} {q:>8.1f}")

    avg_q = total_q / len(stations) if stations else 0.0
    print(f"\n  Average Quality Score  : {avg_q:.2f}/100")

    # Date range
    from sqlalchemy import func
    row = db.query(
        func.min(StationReading.timestamp),
        func.max(StationReading.timestamp)
    ).one()
    print(f"  Date Range             : {row[0]} → {row[1]}")

    # Missing data summary
    total = readings_count
    pm25_null = db.query(StationReading).filter(StationReading.pm25 == None).count()
    no2_null  = db.query(StationReading).filter(StationReading.no2  == None).count()
    print(f"\n  PM2.5 missing          : {pm25_null:,} / {total:,} ({100*pm25_null/total:.1f}%)")
    print(f"  NO2   missing          : {no2_null:,} / {total:,} ({100*no2_null/total:.1f}%)")

    return True

# ─────────────────────────────────────────────
# 2. ARTIFACT AUDIT
# ─────────────────────────────────────────────
def audit_artifacts():
    section("PIPELINE ARTIFACTS")
    artifacts = {
        "Download Manifest"     : os.path.join(MODELS_DIR, "download_manifest.json"),
        "Dataset Version"       : os.path.join(MODELS_DIR, "dataset_version.json"),
        "ML Readiness Report"   : os.path.join(MODELS_DIR, "ml_readiness_report.json"),
        "Dataset Audit HTML"    : os.path.join(MODELS_DIR, "dataset_audit.html"),
        "Feature Cache (Parquet)": os.path.join(os.path.dirname(MODELS_DIR), "data", "feature_cache.parquet"),
    }
    all_ok = True
    for name, path in artifacts.items():
        exists = os.path.exists(path)
        size = f"{os.path.getsize(path)/1e3:.1f} KB" if exists else "--"
        status = "OK" if exists else "MISSING"
        print(f"  [{status:^7}] {name:<30} {size}")
        if not exists:
            all_ok = False

    # Load & display dataset_version.json if present
    vpath = os.path.join(MODELS_DIR, "dataset_version.json")
    if os.path.exists(vpath):
        with open(vpath) as f:
            v = json.load(f)
        print(f"\n  Dataset Version : {v.get('dataset_version')}")
        print(f"  Generated At    : {v.get('generated_at')}")
        print(f"  Stations        : {v.get('stations')}")
        print(f"  Rows            : {v.get('rows', 0):,}")
        split = v.get("training_split", {})
        print(f"  Train/Val/Test  : {split.get('train')}/{split.get('validation')}/{split.get('test')}")

    return all_ok

# ─────────────────────────────────────────────
# 3. FORECASTING PIPELINE
# ─────────────────────────────────────────────
def run_forecast_test(db):
    section("FORECASTING PIPELINE (CNN-LSTM)")
    db.query(Forecast).delete()
    db.commit()
    t0 = datetime.now()
    generate_forecasts_for_all(db, retrain=True)
    elapsed = datetime.now() - t0
    count = db.query(Forecast).count()
    print(f"  Forecasts generated : {count:,}  (took {elapsed})")
    sample = db.query(Forecast).limit(5).all()
    print(f"\n  {'Ward':<8} {'Time':<22} {'PM2.5':>8} {'NO2':>8} {'AQI':>8}")
    print(f"  {'-'*8} {'-'*22} {'-'*8} {'-'*8} {'-'*8}")
    for f in sample:
        print(f"  {f.ward_id:<8} {str(f.forecast_time)[:22]:<22} {f.predicted_pm25:>8.2f} {f.predicted_no2:>8.2f} {f.predicted_aqi:>8.1f}")
    return count > 0

# ─────────────────────────────────────────────
# 4. ATTRIBUTION PIPELINE
# ─────────────────────────────────────────────
def run_attribution_test(db):
    section("SOURCE ATTRIBUTION PIPELINE")
    db.query(Attribution).delete()
    db.commit()
    t0 = datetime.now()
    run_attribution_for_all(db)
    elapsed = datetime.now() - t0
    count = db.query(Attribution).count()
    print(f"  Attributions generated : {count:,}  (took {elapsed})")
    sample = db.query(Attribution).limit(5).all()
    print(f"\n  {'Ward':<8} {'Vehicular':>10} {'Industrial':>11} {'Biomass':>8} {'Waste':>7} {'Dust':>6} {'Conf':>6}")
    print(f"  {'-'*8} {'-'*10} {'-'*11} {'-'*8} {'-'*7} {'-'*6} {'-'*6}")
    for a in sample:
        print(f"  {a.ward_id:<8} {a.vehicular_pct:>9.1f}% {a.industrial_pct:>10.1f}% "
              f"{a.biomass_pct:>7.1f}% {a.waste_burning_pct:>6.1f}% {a.dust_pct:>5.1f}% {a.confidence:>6.2f}")
    return count > 0

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def verify_pipeline():
    print("\n" + "="*60)
    print("  AtmosEdgeAI — Pipeline Verification & Audit")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    db = SessionLocal()
    results = {}
    try:
        results["db_ok"]          = audit_database(db)
        results["artifacts_ok"]   = audit_artifacts()

        if results["db_ok"]:
            results["forecast_ok"]    = run_forecast_test(db)
            results["attribution_ok"] = run_attribution_test(db)
        else:
            print("\n[SKIP] Skipping forecast & attribution — DB empty.")
            results["forecast_ok"]    = False
            results["attribution_ok"] = False

        section("VERIFICATION SUMMARY")
        all_pass = True
        for check, passed in results.items():
            icon = "PASS" if passed else "FAIL"
            print(f"  [{icon}] {check}")
            if not passed:
                all_pass = False

        if all_pass:
            print("\n  All checks PASSED. Pipeline is ready for production.")
        else:
            print("\n  Some checks FAILED. Review above output for details.")

    except Exception as e:
        import traceback
        print(f"\n[ERROR] Verification crashed: {e}")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_pipeline()
