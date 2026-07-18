"""
AtmosEdgeAI — Full Data Quality Report
=======================================
Reads raw files directly (no DB required). Generates:
  • Console summary table
  • backend/models/data_quality_report.html  (rich HTML)
  • backend/models/data_quality_report.json  (machine-readable)

Run:
    .\venv\Scripts\python -u backend/data_quality_report.py
"""

import os, sys, json, glob, re, warnings
from datetime import datetime
from collections import defaultdict

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from io import BytesIO
import base64

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.ml.config import BASE_DIR, MODELS_DIR

# ── Paths ──────────────────────────────────────────────────────────────────────
OPENAQ_RAW  = os.path.join(BASE_DIR, "data", "raw", "openaq")
WEATHER_RAW = os.path.join(BASE_DIR, "data", "raw", "weather")
FIRMS_DIR   = os.path.join(BASE_DIR, "data", "firms")
STATIONS_JSON = os.path.join(BASE_DIR, "data", "selected_stations.json")
OUT_HTML    = os.path.join(MODELS_DIR, "data_quality_report.html")
OUT_JSON    = os.path.join(MODELS_DIR, "data_quality_report.json")
os.makedirs(MODELS_DIR, exist_ok=True)

POLLUTANTS  = ["pm25", "no2", "pm10", "so2", "co", "o3"]
WEATHER_VARS= ["temp", "humidity", "wind_speed", "pbl_height", "precipitation",
               "solar_radiation", "surface_pressure", "wind_deg", "cloud_cover", "dew_point"]

# ── Helpers ────────────────────────────────────────────────────────────────────
def fig_to_b64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()

def pct_bar(pct, width=20):
    filled = int(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)

def section(title):
    print(f"\n{'═'*65}")
    print(f"  {title}")
    print(f"{'═'*65}")

# ── 1. Load station metadata ──────────────────────────────────────────────────
def load_stations():
    if os.path.exists(STATIONS_JSON):
        with open(STATIONS_JSON) as f:
            return {str(s["id"]): s for s in json.load(f)}
    return {}

# ── 2. Parse OpenAQ raw JSON chunks for one station ──────────────────────────
def parse_openaq_station(sid):
    sdir = os.path.join(OPENAQ_RAW, str(sid))
    files = glob.glob(os.path.join(sdir, "*.json"))
    if not files:
        return pd.DataFrame()
    records = []
    for fp in files:
        try:
            with open(fp) as f:
                data = json.load(f)
            for item in data:
                param = item.get("parameter", {}).get("name", "").lower()
                val   = item.get("value")
                dt    = item.get("period", {}).get("datetimeTo", {})
                if isinstance(dt, dict):
                    dt = dt.get("utc") or dt.get("local")
                if param and val is not None and dt:
                    records.append({"timestamp": dt, "parameter": param, "value": float(val)})
        except Exception:
            pass
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce").dt.tz_localize(None)
    df = df.dropna(subset=["timestamp"])
    pivoted = df.pivot_table(index="timestamp", columns="parameter", values="value", aggfunc="mean")
    for col in POLLUTANTS:
        if col not in pivoted.columns:
            pivoted[col] = np.nan
    return pivoted

# ── 3. Parse weather CSVs for one station ─────────────────────────────────────
def parse_weather_station(sid):
    sdir = os.path.join(WEATHER_RAW, str(sid))
    files = glob.glob(os.path.join(sdir, "*.csv"))
    if not files:
        return pd.DataFrame()
    dfs = []
    for fp in files:
        try:
            df = pd.read_csv(fp)
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            dfs.append(df)
        except Exception:
            pass
    if not dfs:
        return pd.DataFrame()
    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.dropna(subset=["timestamp"]).sort_values("timestamp").drop_duplicates("timestamp")
    combined.set_index("timestamp", inplace=True)
    return combined

# ── 4. Parse FIRMS ────────────────────────────────────────────────────────────
def parse_firms():
    modis_files = sorted(glob.glob(os.path.join(FIRMS_DIR, "modis_*_India.csv")))
    viirs_files = sorted(glob.glob(os.path.join(FIRMS_DIR, "viirs-jpss1_*_India.csv")))
    all_files   = [(p, False) for p in modis_files] + [(p, True) for p in viirs_files]
    dfs = []
    for path, is_viirs in all_files:
        try:
            df = pd.read_csv(path, usecols=["latitude","longitude","acq_date","frp"], dtype={"frp": float}, low_memory=True)
            df["acq_date"] = pd.to_datetime(df["acq_date"], format="%Y-%m-%d", errors="coerce")
            df["sensor"]   = "VIIRS" if is_viirs else "MODIS"
            df["year"]     = df["acq_date"].dt.year
            dfs.append(df)
        except Exception as e:
            logger.error(f"Error parsing FIRMS file {os.path.basename(path)}: {e}")
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)

# ── 5. Build per-station AQ quality metrics ───────────────────────────────────
def audit_openaq(stations):
    section("OPENAQ AIR QUALITY DATA QUALITY")
    station_dirs = [d for d in os.listdir(OPENAQ_RAW)
                    if os.path.isdir(os.path.join(OPENAQ_RAW, d))] if os.path.exists(OPENAQ_RAW) else []

    rows = []
    print(f"\n  {'Station':<8} {'Name':<30} {'Records':>8} {'Yrs':>5} {'PM2.5%':>7} {'NO2%':>6} {'PM10%':>6} {'Gaps':>6}")
    print(f"  {'-'*8} {'-'*30} {'-'*8} {'-'*5} {'-'*7} {'-'*6} {'-'*6} {'-'*6}")

    for sid in sorted(station_dirs):
        df = parse_openaq_station(sid)
        meta = stations.get(str(sid), {})
        name = meta.get("name", f"Station {sid}")[:30]

        if df.empty:
            rows.append({"station_id": sid, "name": name, "records": 0,
                         "date_from": None, "date_to": None, "years_covered": 0,
                         **{f"{p}_pct": 0.0 for p in POLLUTANTS}, "large_gaps": 0})
            print(f"  {sid:<8} {name:<30} {'NO DATA':>8}")
            continue

        total   = len(df)
        dt_from = df.index.min()
        dt_to   = df.index.max()
        years   = round((dt_to - dt_from).days / 365.25, 1)

        pct = {}
        for p in POLLUTANTS:
            pct[p] = round(100 * df[p].notna().sum() / total, 1) if p in df.columns else 0.0

        # large gap detection (>24h)
        diffs = df.index.to_series().diff().dt.total_seconds() / 3600
        large_gaps = int((diffs > 24).sum())

        rows.append({
            "station_id": sid, "name": name, "records": total,
            "date_from": str(dt_from.date()), "date_to": str(dt_to.date()),
            "years_covered": years, "large_gaps": large_gaps,
            **{f"{p}_pct": pct[p] for p in POLLUTANTS}
        })
        print(f"  {sid:<8} {name:<30} {total:>8,} {years:>5.1f} "
              f"{pct['pm25']:>6.1f}% {pct['no2']:>5.1f}% {pct['pm10']:>5.1f}% {large_gaps:>6}")

    return rows

# ── 6. Build per-station weather quality metrics ──────────────────────────────
def audit_weather(stations):
    section("OPEN-METEO WEATHER DATA QUALITY")
    station_dirs = [d for d in os.listdir(WEATHER_RAW)
                    if os.path.isdir(os.path.join(WEATHER_RAW, d))] if os.path.exists(WEATHER_RAW) else []

    rows = []
    print(f"\n  {'Station':<8} {'Records':>8} {'Date From':<12} {'Date To':<12} {'Temp%':>6} {'Wind%':>6} {'PBL%':>6}")
    print(f"  {'-'*8} {'-'*8} {'-'*12} {'-'*12} {'-'*6} {'-'*6} {'-'*6}")

    for sid in sorted(station_dirs):
        df = parse_weather_station(sid)
        if df.empty:
            print(f"  {sid:<8} NO DATA")
            continue
        total   = len(df)
        dt_from = df.index.min()
        dt_to   = df.index.max()

        pct = {}
        for v in WEATHER_VARS:
            pct[v] = round(100 * df[v].notna().sum() / total, 1) if v in df.columns else 0.0

        rows.append({
            "station_id": sid, "records": total,
            "date_from": str(dt_from.date()), "date_to": str(dt_to.date()),
            **{f"{v}_pct": pct[v] for v in WEATHER_VARS}
        })
        print(f"  {sid:<8} {total:>8,} {str(dt_from.date()):<12} {str(dt_to.date()):<12} "
              f"{pct.get('temp', 0):>5.1f}% {pct.get('wind_speed', 0):>5.1f}% {pct.get('pbl_height', 0):>5.1f}%")

    return rows

# ── 7. FIRMS summary ──────────────────────────────────────────────────────────
def audit_firms():
    section("NASA FIRMS FIRE DATA QUALITY")
    df = parse_firms()
    if df.empty:
        print("  No FIRMS data found.")
        return {}

    total   = len(df)
    by_year = df.groupby(["year","sensor"]).size().reset_index(name="count")
    dt_from = df["acq_date"].min().date()
    dt_to   = df["acq_date"].max().date()
    avg_frp = round(df["frp"].mean(), 2)

    print(f"\n  Total fire detections : {total:,}")
    print(f"  Date range            : {dt_from}  →  {dt_to}")
    print(f"  Average FRP           : {avg_frp} MW")
    print(f"\n  {'Year':<6} {'MODIS':>10} {'VIIRS':>10}")
    print(f"  {'-'*6} {'-'*10} {'-'*10}")

    summary_by_year = {}
    for year in sorted(df["year"].dropna().unique()):
        yr = int(year)
        m  = int(by_year.query("year==@yr and sensor=='MODIS'")["count"].sum()) if "MODIS" in by_year["sensor"].values else 0
        v  = int(by_year.query("year==@yr and sensor=='VIIRS'")["count"].sum()) if "VIIRS" in by_year["sensor"].values else 0
        summary_by_year[yr] = {"modis": m, "viirs": v}
        print(f"  {yr:<6} {m:>10,} {v:>10,}")

    return {
        "total": total, "date_from": str(dt_from), "date_to": str(dt_to),
        "avg_frp_mw": avg_frp, "by_year": summary_by_year
    }

# ── 8. Completeness chart ─────────────────────────────────────────────────────
def make_completeness_chart(aq_rows):
    sids  = [r["station_id"] for r in aq_rows if r["records"] > 0]
    pm25s = [r.get("pm25_pct", 0) for r in aq_rows if r["records"] > 0]
    no2s  = [r.get("no2_pct", 0) for r in aq_rows if r["records"] > 0]

    if not sids:
        return ""

    fig, ax = plt.subplots(figsize=(14, max(5, len(sids) * 0.35)))
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#1e293b")
    y = np.arange(len(sids))
    h = 0.35
    bars1 = ax.barh(y + h/2, pm25s, h, label="PM2.5", color="#3b82f6", alpha=0.9)
    bars2 = ax.barh(y - h/2, no2s,  h, label="NO2",   color="#f59e0b", alpha=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels(sids, fontsize=8, color="#94a3b8")
    ax.set_xlabel("Completeness %", color="#94a3b8")
    ax.set_xlim(0, 110)
    ax.axvline(80, color="#ef4444", linestyle="--", linewidth=0.8, label="80% threshold")
    ax.tick_params(colors="#94a3b8")
    ax.spines["bottom"].set_color("#475569")
    ax.spines["left"].set_color("#475569")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(facecolor="#1e293b", labelcolor="#e2e8f0", fontsize=9)
    ax.set_title("PM2.5 & NO2 Data Completeness by Station", color="#e2e8f0", fontsize=12, pad=10)
    fig.tight_layout()
    return fig_to_b64(fig)

# ── 9. FIRMS fire timeline chart ──────────────────────────────────────────────
def make_firms_chart(firms_summary):
    if not firms_summary or "by_year" not in firms_summary:
        return ""
    years = sorted(firms_summary["by_year"].keys())
    modis = [firms_summary["by_year"][y]["modis"] for y in years]
    viirs = [firms_summary["by_year"][y]["viirs"] for y in years]

    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor("#0f172a")
    ax.set_facecolor("#1e293b")
    x = np.arange(len(years))
    ax.bar(x - 0.2, modis, 0.4, label="MODIS", color="#f97316", alpha=0.9)
    ax.bar(x + 0.2, viirs, 0.4, label="VIIRS JPSS-1", color="#a78bfa", alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels(years, color="#94a3b8")
    ax.tick_params(colors="#94a3b8")
    ax.set_ylabel("Fire Detections", color="#94a3b8")
    ax.set_title("NASA FIRMS Fire Detections — India by Year", color="#e2e8f0", fontsize=12, pad=10)
    ax.legend(facecolor="#1e293b", labelcolor="#e2e8f0")
    for sp in ["top", "right"]:
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color("#475569")
    ax.spines["left"].set_color("#475569")
    fig.tight_layout()
    return fig_to_b64(fig)

# ── 10. HTML report generator ─────────────────────────────────────────────────
def build_html(aq_rows, wx_rows, firms_summary, completeness_b64, firms_b64, generated_at):
    total_aq_records = sum(r["records"] for r in aq_rows)
    total_wx_records = sum(r["records"] for r in wx_rows)
    aq_stations = len([r for r in aq_rows if r["records"] > 0])
    wx_stations = len(wx_rows)
    fires_total = firms_summary.get("total", 0)

    def quality_badge(pct):
        if pct >= 80:  return f'<span class="badge green">{pct:.1f}%</span>'
        if pct >= 50:  return f'<span class="badge yellow">{pct:.1f}%</span>'
        return         f'<span class="badge red">{pct:.1f}%</span>'

    aq_rows_html = ""
    for r in aq_rows:
        if r["records"] == 0:
            aq_rows_html += f'<tr><td>{r["station_id"]}</td><td>{r["name"]}</td><td colspan="7" style="color:#ef4444">No data</td></tr>'
            continue
        aq_rows_html += (
            f'<tr><td>{r["station_id"]}</td><td>{r["name"]}</td>'
            f'<td>{r["records"]:,}</td><td>{r.get("years_covered","?")}</td>'
            f'<td>{r.get("date_from","?")}</td><td>{r.get("date_to","?")}</td>'
            f'<td>{quality_badge(r.get("pm25_pct",0))}</td>'
            f'<td>{quality_badge(r.get("no2_pct",0))}</td>'
            f'<td>{quality_badge(r.get("pm10_pct",0))}</td>'
            f'<td>{"⚠️" if r.get("large_gaps",0) > 10 else "✅"} {r.get("large_gaps",0)}</td></tr>'
        )

    wx_rows_html = ""
    for r in wx_rows:
        wx_rows_html += (
            f'<tr><td>{r["station_id"]}</td><td>{r["records"]:,}</td>'
            f'<td>{r.get("date_from","?")}</td><td>{r.get("date_to","?")}</td>'
            f'<td>{quality_badge(r.get("temp_pct",0))}</td>'
            f'<td>{quality_badge(r.get("wind_speed_pct",0))}</td>'
            f'<td>{quality_badge(r.get("pbl_height_pct",0))}</td>'
            f'<td>{quality_badge(r.get("precipitation_pct",0))}</td></tr>'
        )

    firms_years_html = ""
    for yr, cnts in sorted(firms_summary.get("by_year", {}).items()):
        firms_years_html += f'<tr><td>{yr}</td><td>{cnts["modis"]:,}</td><td>{cnts["viirs"]:,}</td><td>{cnts["modis"]+cnts["viirs"]:,}</td></tr>'

    completeness_img = f'<img src="data:image/png;base64,{completeness_b64}" style="width:100%;border-radius:8px">' if completeness_b64 else ""
    firms_img = f'<img src="data:image/png;base64,{firms_b64}" style="width:100%;border-radius:8px">' if firms_b64 else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AtmosEdgeAI — Data Quality Report</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:"Segoe UI",system-ui,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}}
  .header{{background:linear-gradient(135deg,#1e3a5f,#0f172a);padding:40px 48px;border-bottom:1px solid #1e293b}}
  .header h1{{font-size:2rem;font-weight:700;background:linear-gradient(90deg,#38bdf8,#818cf8);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
  .header p{{color:#94a3b8;margin-top:6px;font-size:.95rem}}
  .body{{padding:32px 48px;max-width:1400px;margin:0 auto}}
  .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin-bottom:36px}}
  .kpi{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:22px 26px}}
  .kpi .label{{font-size:.8rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em}}
  .kpi .value{{font-size:2rem;font-weight:700;color:#38bdf8;margin-top:4px}}
  .kpi .sub{{font-size:.8rem;color:#64748b;margin-top:2px}}
  .section{{margin-bottom:44px}}
  .section h2{{font-size:1.1rem;font-weight:600;color:#cbd5e1;padding-bottom:10px;border-bottom:1px solid #1e293b;margin-bottom:18px}}
  table{{width:100%;border-collapse:collapse;font-size:.82rem}}
  th{{background:#1e293b;color:#94a3b8;padding:10px 12px;text-align:left;font-weight:600;border-bottom:1px solid #334155}}
  td{{padding:9px 12px;border-bottom:1px solid #1e293b;color:#cbd5e1}}
  tr:hover td{{background:#1e293b}}
  .badge{{padding:2px 8px;border-radius:12px;font-size:.76rem;font-weight:600}}
  .badge.green{{background:#14532d;color:#4ade80}}
  .badge.yellow{{background:#451a03;color:#fbbf24}}
  .badge.red{{background:#450a0a;color:#f87171}}
  .chart-box{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:20px;margin-bottom:24px}}
  footer{{text-align:center;color:#334155;padding:24px;font-size:.8rem}}
</style>
</head>
<body>
<div class="header">
  <h1>⚡ AtmosEdgeAI — Data Quality Report</h1>
  <p>Generated: {generated_at} &nbsp;|&nbsp; Pre-training dataset audit across all raw data sources</p>
</div>
<div class="body">
  <div class="kpi-grid">
    <div class="kpi"><div class="label">AQ Stations</div><div class="value">{aq_stations}</div><div class="sub">with OpenAQ data</div></div>
    <div class="kpi"><div class="label">AQ Records</div><div class="value">{total_aq_records/1e6:.1f}M</div><div class="sub">hourly observations</div></div>
    <div class="kpi"><div class="label">Weather Stations</div><div class="value">{wx_stations}</div><div class="sub">Open-Meteo coverage</div></div>
    <div class="kpi"><div class="label">Weather Records</div><div class="value">{total_wx_records/1e6:.2f}M</div><div class="sub">hourly meteorology</div></div>
    <div class="kpi"><div class="label">Fire Detections</div><div class="value">{fires_total/1e6:.2f}M</div><div class="sub">MODIS + VIIRS JPSS-1</div></div>
    <div class="kpi"><div class="label">FIRMS Range</div><div class="value">2018–2024</div><div class="sub">{firms_summary.get("date_from","?")} → {firms_summary.get("date_to","?")}</div></div>
  </div>

  <div class="section">
    <h2>📡 OpenAQ Air Quality — Per-Station Completeness</h2>
    <div class="chart-box">{completeness_img}</div>
    <table>
      <tr><th>Station ID</th><th>Name</th><th>Records</th><th>Yrs</th><th>From</th><th>To</th><th>PM2.5</th><th>NO2</th><th>PM10</th><th>Gaps&gt;24h</th></tr>
      {aq_rows_html}
    </table>
  </div>

  <div class="section">
    <h2>🌤 Open-Meteo Weather — Per-Station Coverage</h2>
    <table>
      <tr><th>Station ID</th><th>Records</th><th>From</th><th>To</th><th>Temp</th><th>Wind Speed</th><th>PBL Height</th><th>Precipitation</th></tr>
      {wx_rows_html}
    </table>
  </div>

  <div class="section">
    <h2>🔥 NASA FIRMS Fire Attribution Data</h2>
    <div class="chart-box">{firms_img}</div>
    <table>
      <tr><th>Year</th><th>MODIS</th><th>VIIRS JPSS-1</th><th>Total</th></tr>
      {firms_years_html}
    </table>
  </div>
</div>
<footer>AtmosEdgeAI Data Quality Report &nbsp;|&nbsp; {generated_at}</footer>
</body>
</html>"""

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "█"*65)
    print("  AtmosEdgeAI — Full Data Quality Report")
    print(f"  {generated_at}")
    print("█"*65)

    stations   = load_stations()
    aq_rows    = audit_openaq(stations)
    wx_rows    = audit_weather(stations)
    firms_summ = audit_firms()

    # Summary stats
    section("SUMMARY")
    aq_with_data = [r for r in aq_rows if r["records"] > 0]
    if aq_with_data:
        avg_pm25 = np.mean([r.get("pm25_pct",0) for r in aq_with_data])
        avg_no2  = np.mean([r.get("no2_pct",0)  for r in aq_with_data])
        total_r  = sum(r["records"] for r in aq_with_data)
        print(f"\n  AQ Stations with data  : {len(aq_with_data)}/{len(aq_rows)}")
        print(f"  Total AQ records       : {total_r:,}")
        print(f"  Avg PM2.5 completeness : {avg_pm25:.1f}%")
        print(f"  Avg NO2  completeness  : {avg_no2:.1f}%")
        print(f"  Weather stations       : {len(wx_rows)}")
        print(f"  FIRMS fire records     : {firms_summ.get('total',0):,}")

    # Charts
    print("\nGenerating charts...")
    completeness_b64 = make_completeness_chart(aq_rows)
    firms_b64        = make_firms_chart(firms_summ)

    # HTML
    html = build_html(aq_rows, wx_rows, firms_summ, completeness_b64, firms_b64, generated_at)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n  HTML report saved: {OUT_HTML}")

    # JSON
    report_json = {
        "generated_at": generated_at,
        "openaq":  {"stations": len(aq_rows), "with_data": len(aq_with_data) if aq_with_data else 0,
                    "total_records": sum(r["records"] for r in aq_rows), "per_station": aq_rows},
        "weather": {"stations": len(wx_rows), "total_records": sum(r["records"] for r in wx_rows), "per_station": wx_rows},
        "firms":   firms_summ,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(report_json, f, indent=2, default=str)
    print(f"  JSON summary saved: {OUT_JSON}")

    print(f"\n  Open the HTML report:\n  file:///{OUT_HTML.replace(chr(92), '/')}")
    print("\nDone.\n")
