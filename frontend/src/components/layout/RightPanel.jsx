import { useState, useEffect } from "react";
import { getAqiSlug, getAqiLabel } from "@/constants/aqi";
import Analytics from "@/components/charts/Analytics";
import Explainability from "@/components/charts/Explainability";
import Comparison from "@/components/cards/Comparison";
import Skeleton from "@/components/ui/Skeleton";

function fmt(val, decimals = 1) {
  if (val === null || val === undefined) return "N/A";
  return typeof val === "number" ? val.toFixed(decimals) : val;
}

function ForecastCards({ forecasts }) {
  if (!forecasts || forecasts.length === 0) {
    return (
      <div className="forecast-row">
        {[0, 1, 2].map((i) => <Skeleton key={i} height="160px" />)}
      </div>
    );
  }
  return (
    <div className="forecast-row">
      {forecasts.slice(0, 3).map((fc, idx) => {
        const slug = getAqiSlug(fc.predicted_aqi);
        const label = getAqiLabel(fc.predicted_aqi);
        const horizonLabel = idx === 0 ? "24h Forecast" : idx === 1 ? "48h Forecast" : "72h Forecast";
        return (
          <div key={idx} className="forecast-card">
            <div className={`forecast-strip strip-${slug}`} />
            <div className="forecast-aqi-block">
              <span className={`forecast-aqi-num aqitxt-${slug}`}>{fc.predicted_aqi.toFixed(0)}</span>
              <span className="forecast-aqi-unit">AQI</span>
              <span className={`forecast-aqi-cat aqitxt-${slug}`}>{label}</span>
            </div>
            <div className="forecast-body">
              <div className="forecast-header">
                <span className="forecast-horizon-pill">{horizonLabel}</span>
              </div>
              <div className="forecast-chips">
                <div className="forecast-chip">
                  <span className="forecast-chip-label">PM2.5</span>
                  <span className="forecast-chip-val">{fmt(fc.predicted_pm25)}</span>
                  <span className="forecast-chip-unit">µg/m³</span>
                </div>
                <div className="forecast-chip">
                  <span className="forecast-chip-label">NO₂</span>
                  <span className="forecast-chip-val">{fmt(fc.predicted_no2)}</span>
                  <span className="forecast-chip-unit">µg/m³</span>
                </div>
              </div>
              <div className="forecast-catbar-track">
                <div
                  className={`forecast-catbar-fill catbar-${slug}`}
                  style={{ width: `${Math.min((fc.predicted_aqi / 500) * 100, 100)}%` }}
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function StationDetailHeader({ station, loading }) {
  if (loading) {
    return (
      <div className="card station-detail-header-card">
        <Skeleton height="80px" />
      </div>
    );
  }

  if (!station) {
    return (
      <div className="card station-detail-header-card" style={{ textAlign: "center", color: "var(--text-3)" }}>
        No station selected. Choose a station from the directory or map.
      </div>
    );
  }

  // Map backend status strings to clean, user-friendly labels
  let statusLabel = "Live Observation";
  let statusKey = station.quality_status || "LIVE";

  if (statusKey === "CACHED") {
    statusLabel = "Cached Observation";
  } else if (statusKey === "MODEL_ESTIMATE") {
    statusLabel = "Model Estimate";
  } else if (statusKey === "STALE") {
    statusLabel = "Stale Data";
  } else if (statusKey === "UNAVAILABLE") {
    statusLabel = "Data Unavailable";
  }

  // Get color configurations
  const getBadgeColors = (status) => {
    switch (status) {
      case "LIVE":
        return { bg: "rgba(34, 197, 94, 0.12)", fg: "#4ade80", dot: "#22c55e" };
      case "CACHED":
        return { bg: "rgba(59, 130, 246, 0.12)", fg: "#60a5fa", dot: "#3b82f6" };
      case "MODEL_ESTIMATE":
        return { bg: "rgba(234, 179, 8, 0.12)", fg: "#facc15", dot: "#eab308" };
      case "STALE":
        return { bg: "rgba(249, 115, 22, 0.12)", fg: "#fb923c", dot: "#f97316" };
      default:
        return { bg: "rgba(148, 163, 184, 0.12)", fg: "#cbd5e1", dot: "#94a6b8" };
    }
  };

  const colors = getBadgeColors(statusKey);
  const aqiSlug = getAqiSlug(station.aqi);

  return (
    <div className="card station-detail-header-card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", marginBottom: "16px" }}>
        <div>
          <h2 className="station-detail-name">{station.name}</h2>
          <p className="station-detail-location">
            {station.city}, {station.state} &bull; Elevation: {fmt(station.elevation, 0)}m
          </p>
        </div>
        <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "5px 12px",
              borderRadius: "20px",
              fontSize: "11px",
              fontWeight: "600",
              textTransform: "uppercase",
              backgroundColor: colors.bg,
              color: colors.fg
            }}
          >
            <span
              style={{
                display: "inline-block",
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                backgroundColor: colors.dot
              }}
            />
            <span>{statusLabel}</span>
          </div>
          <div style={{ textAlign: "right" }}>
            <span className={`forecast-aqi-cat aqitxt-${aqiSlug}`} style={{ fontSize: "12px", fontWeight: "600", display: "block" }}>
              {station.category}
            </span>
            <span className="station-detail-value" style={{ fontSize: "24px", fontWeight: "800", lineHeight: "1" }}>
              {station.aqi.toFixed(0)} <span className="station-detail-unit" style={{ fontSize: "12px" }}>AQI</span>
            </span>
          </div>
        </div>
      </div>

      <div className="station-detail-metrics-grid">
        <div className="station-detail-metric-item">
          <span className="station-detail-label">PM2.5</span>
          <strong className="station-detail-value">{fmt(station.pm25)} <span className="station-detail-unit">µg/m³</span></strong>
        </div>
        <div className="station-detail-metric-item">
          <span className="station-detail-label">NO₂</span>
          <strong className="station-detail-value">{fmt(station.no2)} <span className="station-detail-unit">µg/m³</span></strong>
        </div>
        <div className="station-detail-metric-item">
          <span className="station-detail-label">Temperature</span>
          <strong className="station-detail-value">{fmt(station.temp)} <span className="station-detail-unit">°C</span></strong>
        </div>
        <div className="station-detail-metric-item">
          <span className="station-detail-label">Humidity</span>
          <strong className="station-detail-value">{fmt(station.humidity, 0)} <span className="station-detail-unit">%</span></strong>
        </div>
        <div className="station-detail-metric-item">
          <span className="station-detail-label">Wind Speed</span>
          <strong className="station-detail-value">{fmt(station.wind_speed)} <span className="station-detail-unit">km/h</span></strong>
        </div>
      </div>

      <div className="station-detail-footer">
        <div>
          <span>Source: <strong style={{ color: "var(--text-2)" }}>{station.source || "Unknown"}</strong></span>
          <span style={{ margin: "0 8px" }}>&bull;</span>
          <span>Provider: <strong style={{ color: "var(--text-2)" }}>{station.provider || "Unknown"}</strong></span>
        </div>
        {station.last_updated && (
          <div>
            <span>Updated: <strong style={{ color: "var(--text-2)" }}>{station.last_updated}</strong> ({station.data_age_minutes || 0}m ago)</span>
          </div>
        )}
      </div>
    </div>
  );
}

function RegionalAdvisoryCard({ stationId }) {
  const [advisory, setAdvisory] = useState(null);
  const [lang, setLang] = useState("auto"); // "auto" or specific code
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!stationId) return;
    setLoading(true);
    const targetLang = lang === "auto" ? null : lang;
    import("@/services/api").then(({ getRegionalAdvisory }) => {
      getRegionalAdvisory(stationId, targetLang)
        .then((res) => {
          setAdvisory(res);
          setLoading(false);
        })
        .catch(() => setLoading(false));
    });
  }, [stationId, lang]);

  if (!stationId || (!advisory && !loading)) return null;

  const languages = [
    { code: "auto", label: "Auto (Native)" },
    { code: "kn", label: "ಕನ್ನಡ (Kannada)" },
    { code: "ta", label: "தமிழ் (Tamil)" },
    { code: "hi", label: "हिंदी (Hindi)" },
    { code: "mr", label: "மராठी (Marathi)" },
    { code: "bn", label: "বাংলা (Bengali)" },
    { code: "en", label: "English" },
  ];

  return (
    <div className="card" style={{ padding: 16, marginBottom: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: "var(--accent)", letterSpacing: 0.5, textTransform: "uppercase" }}>
          Citizen Health Advisory
        </span>

        {/* Language Switcher */}
        <select
          value={lang}
          onChange={(e) => setLang(e.target.value)}
          style={{
            background: "var(--bg-3)",
            border: "1px solid var(--border)",
            color: "var(--text-1)",
            padding: "4px 10px",
            borderRadius: 6,
            fontSize: 11,
            outline: "none",
            cursor: "pointer",
            fontWeight: 500
          }}
        >
          {languages.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <Skeleton height="60px" />
      ) : advisory ? (
        <>
          <div style={{ background: "var(--bg-3)", padding: 12, borderRadius: "var(--radius-md)", borderLeft: "4px solid var(--accent)", marginBottom: 10 }}>
            <p style={{ fontSize: 13.5, fontWeight: 600, color: "var(--text-1)", margin: 0, lineHeight: 1.5 }}>
              {advisory.advisory_message_regional}
            </p>
            {advisory.language !== "en" && (
              <p style={{ fontSize: 11, color: "var(--text-3)", margin: "6px 0 0 0", fontStyle: "italic", borderTop: "1px dashed var(--border)", paddingTop: 4 }}>
                Translation: {advisory.advisory_message_english}
              </p>
            )}
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11, color: "var(--text-2)", flexWrap: "wrap", gap: 8 }}>
            <span>Catchment Alert: <strong style={{ color: "var(--text-1)" }}>{advisory.sensitive_receptors_summary?.split("located")[0]?.trim()}</strong></span>
            <span className="badge badge-outline" style={{ borderColor: "var(--purple)", color: "var(--purple)", fontSize: 10 }}>
              {advisory.spcb_authority}
            </span>
          </div>
        </>
      ) : null}
    </div>
  );
}

export default function RightPanel({ forecasts, history, stationId, stations, loading }) {
  const [tab, setTab] = useState("analytics");
  const selectedStation = (stations || []).find((s) => s.id === stationId);

  const tabs = [
    { key: "analytics", label: "Analytics" },
    { key: "explainability", label: "Explainability" },
    { key: "comparison", label: "Comparison" },
  ];

  return (
    <div className="dashboard-content-col">
      {/* Active Station Ingestion Details Header */}
      <StationDetailHeader station={selectedStation} loading={loading} />

      {/* Multi-Lingual Citizen Advisory Card */}
      <RegionalAdvisoryCard stationId={stationId} />

      <div className="panel-section">
        <div className="section-header">
          <span className="section-title">72h Forecast Outlook</span>
        </div>
        <ForecastCards forecasts={forecasts} />
      </div>

      <div className="card">
        <div className="tab-bar">
          {tabs.map((t) => (
            <button
              key={t.key}
              className={`tab-btn${tab === t.key ? " active" : ""}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="tab-panel">
          {tab === "analytics" && (
            loading
              ? <Skeleton height="200px" />
              : <Analytics history={history} forecasts={forecasts} />
          )}
          {tab === "explainability" && (
            <Explainability stationId={stationId} />
          )}
          {tab === "comparison" && (
            <Comparison stations={stations} />
          )}
        </div>
      </div>
    </div>
  );
}
