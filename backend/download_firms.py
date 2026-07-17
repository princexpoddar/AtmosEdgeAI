"""
NASA FIRMS Fire Archive Downloader for India (2018-2022)
Uses 10-day chunk iteration over the FIRMS area CSV API.
API format: /api/area/csv/<KEY>/<PRODUCT>/<BBOX>/<DAYS>/<END_DATE>

Run:
    $env:FIRMS_MAP_KEY="your_key"
    .\venv\Scripts\python -u backend/download_firms.py
"""

import os, sys, time, csv, io, requests, logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [FIRMS] %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "firms"))
os.makedirs(BASE_DIR, exist_ok=True)

# India bounding box W,S,E,N
INDIA_BBOX = "68.0,8.0,98.0,38.0"
MAP_KEY = os.environ.get("FIRMS_MAP_KEY", "")

# Date range for archive
START_DATE = datetime(2018, 1, 1)
END_DATE   = datetime(2022, 12, 31)
CHUNK_DAYS = 10   # max allowed by FIRMS API

# FIRMS product names (Standard Processing = archive)
ARCHIVE_PRODUCTS = {
    "MODIS_ARCHIVE": {
        "source": "MODIS_SP",
        "filename": "fire_archive_M-C61_774045.csv",
        "conf_col": "confidence",
    },
    "VIIRS_ARCHIVE": {
        "source": "VIIRS_SNPP_SP",
        "filename": "fire_archive_SV-C2_774046.csv",
        "conf_col": "confidence",
    },
}
NRT_PRODUCTS = {
    "MODIS_NRT": {
        "source": "MODIS_NRT",
        "filename": "fire_nrt_M-C61_774045.csv",
        "days": 10
    },
    "VIIRS_NRT": {
        "source": "VIIRS_SNPP_NRT",
        "filename": "fire_nrt_SV-C2_774046.csv",
        "days": 10
    },
}
INDIA_BOUNDS = {"min_lat": 8.0, "max_lat": 38.0, "min_lon": 68.0, "max_lon": 98.0}


def download_archive_chunked(prod_name: str, prod: dict) -> None:
    """
    Downloads archive data in CHUNK_DAYS chunks from START_DATE to END_DATE.
    Merges all chunks into a single CSV file.
    """
    out_path = os.path.join(BASE_DIR, prod["filename"])
    if os.path.exists(out_path) and os.path.getsize(out_path) > 5000:
        logger.info(f"{prod_name}: already downloaded ({os.path.getsize(out_path)/1e6:.1f} MB). Skipping.")
        return

    source = prod["source"]
    logger.info(f"\n=== {prod_name} ({source}) — {START_DATE.date()} to {END_DATE.date()} ===")

    all_rows = []
    header = None

    # Generate end_dates for each chunk
    chunk_end = START_DATE + timedelta(days=CHUNK_DAYS - 1)
    total_days = (END_DATE - START_DATE).days + 1
    total_chunks = (total_days + CHUNK_DAYS - 1) // CHUNK_DAYS
    chunk_num = 0

    while chunk_end <= END_DATE + timedelta(days=CHUNK_DAYS):
        actual_end = min(chunk_end, END_DATE)
        date_str = actual_end.strftime("%Y-%m-%d")
        url = (f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
               f"{MAP_KEY}/{source}/{INDIA_BBOX}/{CHUNK_DAYS}/{date_str}")

        chunk_num += 1
        if chunk_num % 10 == 1:
            pct = 100.0 * chunk_num / total_chunks
            logger.info(f"  [{pct:5.1f}%] Chunk {chunk_num}/{total_chunks} ending {date_str} ...")

        try:
            resp = requests.get(url, timeout=60)
            if resp.status_code == 400:
                logger.debug(f"  Chunk {date_str}: 400 (no data for period). Skipping.")
                chunk_end += timedelta(days=CHUNK_DAYS)
                continue
            resp.raise_for_status()
            content = resp.text.strip()

            if content:
                reader = csv.DictReader(io.StringIO(content))
                rows = list(reader)
                if header is None and rows:
                    header = reader.fieldnames
                all_rows.extend(rows)

        except Exception as e:
            logger.warning(f"  Chunk {date_str} error: {e}")

        chunk_end += timedelta(days=CHUNK_DAYS)
        time.sleep(0.5)  # polite rate limiting

        if actual_end >= END_DATE:
            break

    if all_rows and header:
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            writer.writerows(all_rows)
        logger.info(f"Saved {len(all_rows):,} fire records -> {out_path} ({os.path.getsize(out_path)/1e6:.2f} MB)")
    else:
        logger.warning(f"No data collected for {prod_name}. Keeping existing stub.")


def download_nrt_via_api():
    for p_name, p in NRT_PRODUCTS.items():
        out_path = os.path.join(BASE_DIR, p["filename"])
        if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
            logger.info(f"{p_name}: NRT already exists. Skipping.")
            continue
        url = (f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
               f"{MAP_KEY}/{p['source']}/{INDIA_BBOX}/{p['days']}")
        logger.info(f"Downloading {p_name} NRT ...")
        try:
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(resp.text)
            logger.info(f"  Saved {resp.text.count(chr(10)):,} lines -> {out_path}")
        except Exception as e:
            logger.error(f"  Error: {e}")


def download_public_nrt():
    PUBLIC = {
        "fire_nrt_M-C61_774045.csv": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_7d.csv",
        "fire_nrt_SV-C2_774046.csv": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_7d.csv",
    }
    for fname, url in PUBLIC.items():
        out_path = os.path.join(BASE_DIR, fname)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
            logger.info(f"{fname}: already exists. Skipping.")
            continue
        logger.info(f"Downloading public NRT: {url}")
        try:
            resp = requests.get(url, timeout=120)
            resp.raise_for_status()
            reader = csv.DictReader(io.StringIO(resp.text))
            rows = [r for r in reader if
                    INDIA_BOUNDS["min_lat"] <= float(r.get("latitude", 0)) <= INDIA_BOUNDS["max_lat"] and
                    INDIA_BOUNDS["min_lon"] <= float(r.get("longitude", 0)) <= INDIA_BOUNDS["max_lon"]]
            if rows:
                with open(out_path, "w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                    w.writeheader(); w.writerows(rows)
                logger.info(f"  Saved {len(rows):,} India rows -> {out_path}")
        except Exception as e:
            logger.error(f"  Error: {e}")


def create_stubs():
    stubs = {
        "fire_archive_M-C61_774045.csv": "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight",
        "fire_archive_SV-C2_774046.csv": "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight,type",
        "fire_nrt_M-C61_774045.csv":     "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight",
        "fire_nrt_SV-C2_774046.csv":     "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight,type",
    }
    for fname, header in stubs.items():
        path = os.path.join(BASE_DIR, fname)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(header + "\n")
            logger.info(f"Created stub: {fname}")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("NASA FIRMS Downloader  India Fire Archive 2018-2022")
    logger.info(f"Output : {BASE_DIR}")
    logger.info(f"Key    : {'SET (' + MAP_KEY[:6] + '...)' if MAP_KEY else 'NOT SET'}")
    logger.info("=" * 60)

    create_stubs()

    if MAP_KEY:
        logger.info("\n[Phase 1] Archive download (10-day chunks per product)...")
        for p_name, p in ARCHIVE_PRODUCTS.items():
            download_archive_chunked(p_name, p)
        logger.info("\n[Phase 2] NRT fires (last 10 days)...")
        download_nrt_via_api()
    else:
        logger.info("\nNo MAP_KEY set. Downloading public NRT CSVs only.")
        download_public_nrt()

    logger.info("\n=== Final Summary ===")
    for fname in ["fire_archive_M-C61_774045.csv", "fire_archive_SV-C2_774046.csv",
                  "fire_nrt_M-C61_774045.csv", "fire_nrt_SV-C2_774046.csv"]:
        path = os.path.join(BASE_DIR, fname)
        if os.path.exists(path):
            size = os.path.getsize(path)
            with open(path) as f:
                lines = sum(1 for _ in f)
            logger.info(f"  {fname}: {size/1e6:.2f} MB, {lines:,} lines")
        else:
            logger.info(f"  {fname}: NOT FOUND")

    logger.info("\nDone.")
