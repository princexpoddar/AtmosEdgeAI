import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { submitPrediction } from "@/services/api";
import { getAqiColor, getAqiLabel, getAqiSlug } from "@/constants/aqi";
import Navbar from "@/components/layout/Navbar";
import Spinner from "@/components/ui/Spinner";
import { useStations } from "@/hooks/useStations";

const HEALTH_TIPS = {
  good:         "Air quality is excellent. Great day for outdoor activities.",
  satisfactory: "Air quality is acceptable. Sensitive individuals should limit prolonged exertion.",
  moderate:     "Sensitive groups may experience health effects. Limit outdoor exertion.",
  poor:         "Health effects may be felt. Avoid prolonged outdoor exertion.",
  "very-poor":  "High risk of health effects. Stay indoors and keep windows closed.",
  severe:       "Emergency conditions. Remain indoors, use air purifiers, wear N95 masks.",
};

const POLLUTANT_LIMITS = {
  pm25: { safe: 60,   label: "PM2.5", unit: "µg/m³", who: 15 },
  no2:  { safe: 80,   label: "NO₂",   unit: "µg/m³", who: 40 },
};

function GaugeRing({ aqi, size = 160 }) {
  const color    = getAqiColor(aqi);
  const maxAqi   = 500;
  const pct      = Math.min(aqi / maxAqi, 1);
  const r        = (size / 2) - 14;
  const circ     = 2 * Math.PI * r;
  const stroke   = circ * pct * 0.75; // 270° arc
  const gap      = circ - stroke;
  const offset   = circ * 0.125;      // start at 225°

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="gauge-svg">
      {/* Track */}
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke="var(--bg-4)" strokeWidth="12"
        strokeDasharray={`${circ * 0.75} ${circ}`}
        strokeDashoffset={-offset}
        strokeLinecap="round"
        transform={`rotate(135 ${size / 2} ${size / 2})`}
      />
      {/* Value arc */}
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke={color} strokeWidth="12"
        strokeDasharray={`${stroke} ${circ}`}
        strokeDashoffset={-offset}
        strokeLinecap="round"
        transform={`rotate(135 ${size / 2} ${size / 2})`}
        style={{ transition: "stroke-dasharray 0.8s cubic-bezier(.4,0,.2,1), stroke 0.4s" }}
      />
      {/* Center text */}
      <text x={size / 2} y={size / 2 - 8} textAnchor="middle" fill={color}
        fontSize="28" fontWeight="700" fontFamily="inherit">
        {Math.round(aqi)}
      </text>
      <text x={size / 2} y={size / 2 + 14} textAnchor="middle" fill="var(--text-3)"
        fontSize="10" fontWeight="600" letterSpacing="0.1em" fontFamily="inherit">
        AQI
      </text>
    </svg>
  );
}

function PollutantBar({ value, meta, label }) {
  const pct  = Math.min((value / (meta.safe * 2)) * 100, 100);
  const safe = Math.min((meta.safe / (meta.safe * 2)) * 100, 100);
  const who  = Math.min((meta.who  / (meta.safe * 2)) * 100, 100);
  const over = value > meta.safe;
  return (
    <div className="pred-pollutant-row">
      <div className="pred-poll-header">
        <span className="pred-poll-label">{meta.label}</span>
        <span className="pred-poll-value" style={{ color: over ? "var(--red)" : "var(--green)" }}>
          {value.toFixed(1)} <span className="pred-poll-unit">{meta.unit}</span>
        </span>
      </div>
      <div className="pred-poll-track">
        <div className="pred-poll-fill" style={{
          width: `${pct}%`,
          background: over
            ? "linear-gradient(90deg,var(--orange),var(--red))"
            : "linear-gradient(90deg,var(--green),var(--accent))",
          transition: "width 0.7s cubic-bezier(.4,0,.2,1)",
        }} />
        {/* WHO safe limit marker */}
        <div className="pred-poll-marker" style={{ left: `${who}%` }} title={`WHO limit: ${meta.who} ${meta.unit}`} />
        {/* CPCB safe limit marker */}
        <div className="pred-poll-marker pred-poll-marker-cpcb" style={{ left: `${safe}%` }} title={`CPCB limit: ${meta.safe} ${meta.unit}`} />
      </div>
      <div className="pred-poll-legend">
        <span>0</span>
        <span className="pred-poll-who-label">WHO {meta.who}</span>
        <span className="pred-poll-cpcb-label">CPCB {meta.safe}</span>
        <span>{meta.safe * 2}+</span>
      </div>
    </div>
  );
}

export default function Predictor({ stations: propStations }) {
  const { stations: hookStations, loading: stLoading } = useStations();
  const stations  = propStations || hookStations || [];
  const navigate  = useNavigate();

  const [stationId, setStationId] = useState("");
  const [horizon,   setHorizon]   = useState(24);
  const [loading,   setLoading]   = useState(false);
  const [result,    setResult]    = useState(null);
  const [error,     setError]     = useState(null);
  const [hovered,   setHovered]   = useState(null);

  const selectedId  = stationId || (stations[0]?.id ?? "");
  const selectedSt  = stations.find((s) => s.id === selectedId) || stations[0];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await submitPrediction(selectedId, horizon);
      setResult(data);
    } catch (err) {
      setError(err.message || "Failed to generate prediction");
    } finally {
      setLoading(false);
    }
  };

  const slug    = result ? getAqiSlug(result.aqi) : null;
  const color   = result ? getAqiColor(result.aqi) : "var(--accent)";
  const tip     = result ? HEALTH_TIPS[slug] : null;

  return (
    <div className="app-root">
      <Navbar />

      <div className="pred-page">

        {/* ── Header ──────────────────────────────────────────────────── */}
        <div className="pred-header">
          <div>
            <div className="pred-header-eyebrow">⚗ Spatiotemporal ML Engine</div>
            <h1 className="pred-header-title">AI Pollution Predictor</h1>
            <p className="pred-header-sub">
              Live inference using the deployed Ridge Regression model with 50-feature
              spatiotemporal sequences, K-NN spatial context, and scaler-corrected targets.
            </p>
          </div>
          {/* Live station current reading pill */}
          {selectedSt && (
            <div className="pred-live-pill">
              <span className="pred-live-dot" />
              <div>
                <div className="pred-live-station">{selectedSt.name?.split(",")[0]}</div>
                <div className="pred-live-reading">
                  Current AQI: <strong style={{ color: getAqiColor(selectedSt.aqi ?? 0) }}>
                    {(selectedSt.aqi ?? 0).toFixed(0)}
                  </strong>
                  {" · "}PM2.5: <strong>{(selectedSt.pm25 ?? 0).toFixed(0)} µg/m³</strong>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Main grid ───────────────────────────────────────────────── */}
        <div className="pred-grid">

          {/* Left: config + result ───────────────────────────────────── */}
          <div className="pred-left">

            {/* Config card */}
            <div className="pred-config-card">
              <div className="pred-config-header">
                <span className="pred-config-icon">🎯</span>
                <div>
                  <h3 className="pred-config-title">Configure Prediction</h3>
                  <p className="pred-config-sub">Select a monitoring station and forecast window</p>
                </div>
              </div>

              {error && (
                <div className="pred-error-banner">
                  ⚠ {error}
                </div>
              )}

              {stLoading ? (
                <div className="pred-stations-loading">
                  <Spinner size="sm" />
                  <span>Loading stations…</span>
                </div>
              ) : stations.length === 0 ? (
                <div className="pred-empty-state">
                  <span className="pred-empty-icon">📡</span>
                  <p>No monitoring stations found.</p>
                  <button className="btn btn-secondary btn-sm" onClick={() => navigate("/dashboard")}>
                    Go to Dashboard
                  </button>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="pred-form">
                  <div className="pred-field">
                    <label className="pred-label">Monitoring Station</label>
                    <div className="pred-select-wrap">
                      <select
                        className="pred-select"
                        value={stationId}
                        onChange={(e) => { setStationId(e.target.value); setResult(null); }}
                      >
                        {stations.map((st) => (
                          <option key={st.id} value={st.id}>
                            {st.name} ({st.city})
                          </option>
                        ))}
                      </select>
                      <span className="pred-select-arrow">▾</span>
                    </div>
                  </div>

                  <div className="pred-field">
                    <label className="pred-label">Forecast Horizon</label>
                    <div className="pred-horizon-group">
                      {[24, 48, 72].map((h) => (
                        <button
                          key={h}
                          type="button"
                          className={`pred-horizon-btn${horizon === h ? " active" : ""}`}
                          onClick={() => { setHorizon(h); setResult(null); }}
                        >
                          {h}h
                          <span className="pred-horizon-sub">
                            {h === 24 ? "tomorrow" : h === 48 ? "day after" : "3 days"}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <button
                    className={`pred-submit${loading ? " loading" : ""}`}
                    type="submit"
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <Spinner size="sm" />
                        <span>Running ML Inference…</span>
                      </>
                    ) : (
                      <>
                        <span className="pred-submit-icon">⚡</span>
                        <span>Generate AI Prediction</span>
                      </>
                    )}
                  </button>
                </form>
              )}
            </div>

            {/* Result card */}
            {result && (
              <div className="pred-result-card" style={{ "--result-color": color }}>
                <div className="pred-result-header">
                  <div>
                    <div className="pred-result-eyebrow">INFERENCE COMPLETE · {horizon}h OUTLOOK</div>
                    <div className="pred-result-station">{selectedSt?.name}</div>
                  </div>
                  <div className="pred-category-badge" style={{ background: color + "22", color, border: `1px solid ${color}44` }}>
                    {getAqiLabel(result.aqi)}
                  </div>
                </div>

                {/* Gauge + pollutants */}
                <div className="pred-result-body">
                  <div className="pred-gauge-col">
                    <GaugeRing aqi={result.aqi} size={160} />
                    <div className="pred-gauge-label">Predicted AQI</div>
                  </div>
                  <div className="pred-pollutants-col">
                    <PollutantBar value={result.pm25_24h} meta={POLLUTANT_LIMITS.pm25} />
                    <PollutantBar value={result.no2_24h}  meta={POLLUTANT_LIMITS.no2} />
                  </div>
                </div>

                {/* Health advisory */}
                <div className="pred-advisory" style={{ borderColor: color + "44", background: color + "0d" }}>
                  <span className="pred-advisory-icon">💡</span>
                  <p>{tip}</p>
                </div>
              </div>
            )}
          </div>

          {/* Right: info panels ──────────────────────────────────────── */}
          <div className="pred-right">

            {/* Model info */}
            <div className="pred-info-card">
              <h4 className="pred-info-title">🧠 Model Architecture</h4>
              <div className="pred-info-rows">
                {[
                  { k: "Algorithm",      v: "Ridge Regression (50-feature spatial)" },
                  { k: "Feature Set",    v: "48-step lags, rolling stats, K-NN neighbours" },
                  { k: "Training Data",  v: "CPCB historical observations (SQLite)" },
                  { k: "Scaling",        v: "Separate scalers for inputs and targets" },
                  { k: "Forecast Type",  v: "PM2.5 / NO₂ → AQI (CPCB formula)" },
                ].map(({ k, v }) => (
                  <div key={k} className="pred-info-row">
                    <span className="pred-info-key">{k}</span>
                    <span className="pred-info-val">{v}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* AQI scale legend */}
            <div className="pred-info-card">
              <h4 className="pred-info-title">📊 CPCB AQI Scale Reference</h4>
              <div className="pred-aqi-scale">
                {[
                  { range: "0–50",   label: "Good",         color: "#10b981", bg: "rgba(16,185,129,0.1)" },
                  { range: "51–100", label: "Satisfactory", color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
                  { range: "101–200",label: "Moderate",     color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
                  { range: "201–300",label: "Poor",         color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
                  { range: "301–400",label: "Very Poor",    color: "#8b5cf6", bg: "rgba(139,92,246,0.1)" },
                  { range: "401+",   label: "Severe",       color: "#7c2d12", bg: "rgba(124,45,18,0.15)" },
                ].map(({ range, label, color, bg }) => (
                  <div
                    key={range}
                    className={`pred-scale-row${slug === label.toLowerCase().replace(" ","-") ? " active" : ""}`}
                    style={{ "--sc": color, background: slug && getAqiLabel(result?.aqi) === label ? bg : "transparent" }}
                  >
                    <div className="pred-scale-dot" style={{ background: color }} />
                    <span className="pred-scale-label">{label}</span>
                    <span className="pred-scale-range">{range}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Data source pills */}
            <div className="pred-info-card">
              <h4 className="pred-info-title">🔗 Data Pipeline</h4>
              <div className="pred-pipeline">
                {[
                  { icon: "🏛", label: "CPCB data.gov.in API",   sub: "Live PM2.5 / NO₂" },
                  { icon: "🌤", label: "Open-Meteo",              sub: "Weather features" },
                  { icon: "🛰", label: "NASA FIRMS",              sub: "Fire hotspot data" },
                  { icon: "🗄", label: "SQLite Store",            sub: "Hourly ingestion cache" },
                ].map(({ icon, label, sub }) => (
                  <div key={label} className="pred-pipeline-item">
                    <div className="pred-pipeline-icon">{icon}</div>
                    <div>
                      <div className="pred-pipeline-label">{label}</div>
                      <div className="pred-pipeline-sub">{sub}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
