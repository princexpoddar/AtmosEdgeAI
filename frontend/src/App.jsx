import { useState, useEffect, useRef } from "react";
import "./App.css";

const API_BASE = "http://127.0.0.1:8001/api";

/* ── AQI helpers ──────────────────────────────────────────────────────── */
function aqiClass(aqi) {
  if (aqi <= 50)  return "aqi-good";
  if (aqi <= 100) return "aqi-satisfactory";
  if (aqi <= 200) return "aqi-moderate";
  if (aqi <= 300) return "aqi-poor";
  if (aqi <= 400) return "aqi-very-poor";
  return "aqi-severe";
}

function aqiSlug(aqi) {
  if (aqi <= 50)  return "good";
  if (aqi <= 100) return "satisfactory";
  if (aqi <= 200) return "moderate";
  if (aqi <= 300) return "poor";
  if (aqi <= 400) return "very-poor";
  return "severe";
}

// AQI → 0–100% progress for category bar (buckets: 0-50, 50-100, 100-200, 200-300, 300-400, 400-500)
function aqiBarPct(aqi) {
  const stops = [0, 50, 100, 200, 300, 400, 500];
  const capped = Math.min(aqi, 500);
  for (let i = 0; i < stops.length - 1; i++) {
    if (capped <= stops[i + 1]) {
      const segPct = (capped - stops[i]) / (stops[i + 1] - stops[i]);
      return ((i + segPct) / (stops.length - 1)) * 100;
    }
  }
  return 100;
}

function aqiLabel(aqi) {
  if (aqi <= 50)  return "Good";
  if (aqi <= 100) return "Satisfactory";
  if (aqi <= 200) return "Moderate";
  if (aqi <= 300) return "Poor";
  if (aqi <= 400) return "Very Poor";
  return "Severe";
}

function advClass(level) {
  const map = {
    Good: "adv-good", Satisfactory: "adv-satisfactory",
    Moderate: "adv-moderate", Poor: "adv-poor",
    "Very Poor": "adv-very-poor", Severe: "adv-severe",
  };
  return map[level] || "adv-moderate";
}

function fmt(val, decimals = 1) {
  return val != null ? Number(val).toFixed(decimals) : "—";
}

/* ── Attribution source config ────────────────────────────────────────── */
const ATTR_SOURCES = [
  { key: "vehicular",     label: "Vehicular",        color: "#bc8cff" },
  { key: "industrial",    label: "Industrial",       color: "#388bfd" },
  { key: "biomass",       label: "Biomass / Fires",  color: "#db6d28" },
  { key: "waste_burning", label: "Waste Burning",    color: "#f85149" },
  { key: "dust",          label: "Dust",             color: "#d29922" },
];

export default function App() {
  /* ── state ── */
  const [cities, setCities]           = useState([]);
  const [selectedCityId, setCity]     = useState("");
  const [wards, setWards]             = useState([]);
  const [selectedWardId, setWard]     = useState("");
  const [realtime, setRealtime]       = useState(null);
  const [forecasts, setForecasts]     = useState([]);
  const [attribution, setAttribution] = useState(null);
  const [advisory, setAdvisory]       = useState(null);
  const [enforcements, setEnforcements] = useState([]);
  const [geminiKey, setGeminiKey]     = useState(() => localStorage.getItem("gk") || "");
  const [chatHistory, setChat]        = useState([
    { from: "bot", text: "Hello — I'm your AtmosEdgeAI health assistant. Ask me about mask usage, outdoor activity, or current air quality." },
  ]);
  const [chatInput, setChatInput]     = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [loading, setLoading]         = useState(false);
  const [syncing, setSyncing]         = useState(false);
  const [error, setError]             = useState(null);
  const [syncOk, setSyncOk]           = useState(false);
  const chatEndRef = useRef(null);

  /* ── fetch cities ── */
  useEffect(() => {
    fetch(`${API_BASE}/cities`)
      .then(r => r.json())
      .then(d => { setCities(d); if (d.length) setCity(d[0].id); })
      .catch(() => setError("Cannot reach backend. Is the server running on port 8001?"));
  }, []);

  /* ── fetch wards + enforcements when city changes ── */
  useEffect(() => {
    if (!selectedCityId) return;
    fetch(`${API_BASE}/wards?city_id=${selectedCityId}`)
      .then(r => r.json())
      .then(d => { setWards(d); if (d.length) setWard(d[0].id); })
      .catch(() => {});
    fetch(`${API_BASE}/enforcement?city_id=${selectedCityId}`)
      .then(r => r.json())
      .then(setEnforcements)
      .catch(() => {});
  }, [selectedCityId]);

  /* ── fetch ward data ── */
  useEffect(() => {
    if (!selectedWardId) return;
    setLoading(true);
    Promise.all([
      fetch(`${API_BASE}/aqi/realtime?city_id=${selectedCityId}`).then(r => r.json()),
      fetch(`${API_BASE}/forecast?ward_id=${selectedWardId}`).then(r => r.json()),
      fetch(`${API_BASE}/attribution?ward_id=${selectedWardId}`).then(r => r.json()),
      fetch(`${API_BASE}/advisory?ward_id=${selectedWardId}`).then(r => r.json()),
    ]).then(([rtList, fc, attr, adv]) => {
      setRealtime(rtList.find(x => x.ward_id === Number(selectedWardId)) || null);
      setForecasts(fc);
      setAttribution(attr);
      setAdvisory(adv);
      setError(null);
    }).catch(() => setError("Failed to load ward data."))
      .finally(() => setLoading(false));
  }, [selectedWardId, selectedCityId]);

  /* ── scroll chat ── */
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [chatHistory]);

  /* ── save gemini key ── */
  const onGeminiKey = e => {
    setGeminiKey(e.target.value);
    localStorage.setItem("gk", e.target.value);
  };

  /* ── sync ── */
  const handleSync = async () => {
    setSyncing(true); setError(null); setSyncOk(false);
    try {
      const r = await fetch(`${API_BASE}/aqi/sync`, { method: "POST" });
      if (r.ok) { setSyncOk(true); setTimeout(() => { setSyncOk(false); window.location.reload(); }, 2200); }
      else setError("Sync failed — check backend logs.");
    } catch { setError("Cannot reach sync endpoint."); }
    finally { setSyncing(false); }
  };

  /* ── chat ── */
  const handleChat = async e => {
    e.preventDefault();
    if (!chatInput.trim() || !selectedWardId) return;
    const q = chatInput;
    setChat(h => [...h, { from: "user", text: q }]);
    setChatInput(""); setChatLoading(true);
    try {
      const r = await fetch(`${API_BASE}/advisory/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q, ward_id: Number(selectedWardId), gemini_api_key: geminiKey || null }),
      });
      const d = await r.json();
      setChat(h => [...h, { from: "bot", text: d.response }]);
    } catch {
      setChat(h => [...h, { from: "bot", text: "Sorry, I couldn't reach the server." }]);
    } finally { setChatLoading(false); }
  };

  /* ── inspect enforcement ── */
  const handleInspect = async id => {
    await fetch(`${API_BASE}/enforcement/inspect/${id}?status=Inspected`, { method: "POST" });
    setEnforcements(p => p.map(x => x.id === id ? { ...x, status: "Inspected" } : x));
  };

  const aqi   = realtime?.aqi ?? null;
  const wardName = wards.find(w => w.id === Number(selectedWardId))?.name ?? "";

  return (
    <div className="app-root">

      {/* ── Topbar ── */}
      <header className="topbar">
        <div className="topbar-brand">
          <div className="brand-icon">🌬</div>
          <span className="brand-name">AtmosEdgeAI</span>
          <span className="brand-version">v1.1</span>
        </div>

        <span className="topbar-subtitle">
          Spatiotemporal Deep Learning · Air Quality Forecast &amp; Attribution Engine
        </span>

        <div className="topbar-actions">
          <div className="gemini-field">
            <label>Gemini Key</label>
            <input type="password" value={geminiKey} onChange={onGeminiKey} placeholder="Paste API key…" />
          </div>
          <button className="btn btn-secondary" onClick={handleSync} disabled={syncing}>
            {syncing ? "Syncing…" : "↻ Sync"}
          </button>
        </div>
      </header>

      {error   && <div className="banner banner-error">⚠ {error}</div>}
      {syncOk  && <div className="banner banner-success">✓ Live data synced — refreshing…</div>}

      {/* ── Main grid ── */}
      <div className="main-content">

        {/* ── Left sidebar ── */}
        <aside className="sidebar">

          {/* Location selectors */}
          <div className="sidebar-section">
            <div className="sidebar-label">Location</div>
            <div className="field">
              <span className="field-label">City</span>
              <select className="select-control" value={selectedCityId} onChange={e => setCity(e.target.value)}>
                {cities.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div className="field">
              <span className="field-label">Ward</span>
              <select className="select-control" value={selectedWardId} onChange={e => setWard(e.target.value)}>
                {wards.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
              </select>
            </div>
          </div>

          {/* AQI ring */}
          {realtime && (
            <div className="aqi-hero">
              <div className={`aqi-ring ${aqiClass(aqi)}`}>
                <span className="aqi-ring-value">{fmt(aqi, 0)}</span>
                <span className="aqi-ring-unit">AQI</span>
              </div>
              <span className={`aqi-category`} style={{ color: "var(--text-1)" }}>{aqiLabel(aqi)}</span>
              <span className="aqi-ward">{wardName}</span>
              <span className="aqi-time">
                {new Date(realtime.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>
          )}

          {/* Metrics grid */}
          {realtime && (
            <div className="metric-grid">
              {[
                { label: "PM2.5", value: fmt(realtime.pm25), unit: "µg/m³" },
                { label: "NO₂",   value: fmt(realtime.no2),  unit: "µg/m³" },
                { label: "SO₂",   value: fmt(realtime.so2),  unit: "µg/m³" },
                { label: "O₃",    value: fmt(realtime.o3),   unit: "µg/m³" },
                { label: "Wind",  value: fmt(realtime.wind_speed), unit: "km/h" },
                { label: "Temp",  value: fmt(realtime.temp), unit: "°C" },
                { label: "Humid", value: fmt(realtime.humidity), unit: "%" },
                { label: "Stag", value: fmt(realtime.stagnation, 2), unit: "0–1" },
              ].map(m => (
                <div className="metric-cell" key={m.label}>
                  <span className="metric-cell-label">{m.label}</span>
                  <span className="metric-cell-value">
                    {m.value} <span className="metric-cell-unit">{m.unit}</span>
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Advisory */}
          {advisory && advisory.level && (
            <div className="advisory-block">
              <div className="sidebar-label">Health Advisory</div>
              <span className={`advisory-tag ${advClass(advisory.level)}`}>
                {advisory.level}
              </span>
              <p className="advisory-text">{advisory.message_en}</p>
              <p className="advisory-text-hi">{advisory.message_hi}</p>
            </div>
          )}
        </aside>

        {/* ── Center panel ── */}
        <main className="center-panel">

          {/* Forecast section */}
          <div className="panel-section">
            <div className="section-header">
              <span className="section-title">CNN-LSTM Forecast Horizon</span>
              <span className="section-meta">24h · 48h · 72h prediction windows</span>
            </div>
            <div className="forecast-row">
              {forecasts.length > 0 ? forecasts.map((fc, i) => {
                const hrs  = Math.round((new Date(fc.forecast_time) - new Date()) / 3600000);
                const slug = aqiSlug(fc.predicted_aqi);
                const pct  = aqiBarPct(fc.predicted_aqi);
                const fcDate = new Date(fc.forecast_time);
                return (
                  <div className="forecast-card" key={i}>
                    <div className={`forecast-strip strip-${slug}`} />
                    <div className="forecast-aqi-block">
                      <span className={`forecast-aqi-num aqitxt-${slug}`}>{fmt(fc.predicted_aqi, 0)}</span>
                      <span className="forecast-aqi-unit">AQI</span>
                      <span className={`forecast-aqi-cat aqitxt-${slug}`}>{aqiLabel(fc.predicted_aqi)}</span>
                    </div>
                    <div className="forecast-body">
                      <div className="forecast-header">
                        <span className="forecast-horizon-pill">+{hrs}h</span>
                        <span className="forecast-datetime">
                          {fcDate.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" })}
                          &nbsp;·&nbsp;
                          {fcDate.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </div>
                      <div className="forecast-chips">
                        <div className="forecast-chip">
                          <span className="forecast-chip-label">PM2.5</span>
                          <span className="forecast-chip-val">{fmt(fc.predicted_pm25)} <span className="forecast-chip-unit">µg/m³</span></span>
                        </div>
                        <div className="forecast-chip-divider" />
                        <div className="forecast-chip">
                          <span className="forecast-chip-label">NO₂</span>
                          <span className="forecast-chip-val">{fmt(fc.predicted_no2)} <span className="forecast-chip-unit">µg/m³</span></span>
                        </div>
                      </div>
                      <div className="forecast-catbar-track">
                        <div className={`forecast-catbar-fill catbar-${slug}`} style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  </div>
                );
              }) : <p className="empty-state">No forecast data available.</p>}
            </div>
          </div>

          {/* Attribution section */}
          {attribution && (
            <div className="panel-section">
              <div className="section-header">
                <span className="section-title">PM2.5 Source Attribution</span>
                <div className="confidence-row">
                  <div className="confidence-dot"></div>
                  <span>Model confidence {fmt(attribution.confidence * 100, 0)}%</span>
                </div>
              </div>
              <div className="attribution-list">
                {ATTR_SOURCES.map(s => (
                  <div className="attr-row" key={s.key}>
                    <div className="attr-row-header">
                      <span className="attr-name">{s.label}</span>
                      <span className="attr-pct">{fmt(attribution[s.key], 1)}%</span>
                    </div>
                    <div className="attr-track">
                      <div className="attr-fill" style={{ width: `${attribution[s.key]}%`, background: s.color }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

        </main>

        {/* ── Right sidebar ── */}
        <aside className="right-sidebar">

          {/* Chat */}
          <div className="chat-wrapper">
            <div className="chat-title-row">
              <span className="chat-title">Health Advisor</span>
              {geminiKey
                ? <span className="ai-badge ai-badge-on">Gemini Active</span>
                : <span className="ai-badge ai-badge-off">Rule-based</span>
              }
            </div>
            <div className="chat-log">
              {chatHistory.map((m, i) => (
                <div className={`msg msg-${m.from}`} key={i}>
                  <span className="msg-sender">{m.from === "bot" ? "AtmosEdge" : "You"}</span>
                  <div className="msg-body">{m.text}</div>
                </div>
              ))}
              {chatLoading && (
                <div className="msg msg-bot">
                  <div className="msg-body">
                    <div className="typing-indicator">
                      <div className="typing-dot" />
                      <div className="typing-dot" />
                      <div className="typing-dot" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
            <form className="chat-form" onSubmit={handleChat}>
              <input
                className="chat-input"
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                placeholder="Ask about air safety…"
                disabled={chatLoading}
              />
              <button className="btn btn-primary" type="submit" disabled={chatLoading || !chatInput.trim()}>
                Send
              </button>
            </form>
          </div>

          {/* Enforcement */}
          <div className="enforcement-wrapper">
            <div className="enforcement-title-row">
              <span className="enforcement-title">Enforcement Queue</span>
              {enforcements.length > 0 && (
                <span className="enforcement-count">{enforcements.filter(x => x.status === "Pending").length} pending</span>
              )}
            </div>
            <div className="target-list">
              {enforcements.length > 0 ? enforcements.map((t, i) => (
                <div className="target-card" key={i}>
                  <div className="target-card-header">
                    <span className="target-type-tag">{t.type}</span>
                    <span className={`status-pill ${t.status.toLowerCase()}`}>{t.status}</span>
                  </div>
                  <div className="target-name">{t.name}</div>
                  <div className="target-evidence">
                    Risk {fmt(t.risk_score, 1)} · {t.ward_name} · PM {t.evidence_packet?.detected_pm25 ?? "—"} µg/m³
                  </div>
                  <div className="risk-bar-track">
                    <div className="risk-bar-fill" style={{ width: `${Math.min(t.risk_score, 100)}%` }} />
                  </div>
                  {t.status === "Pending" && (
                    <button className="btn btn-ghost" style={{ marginTop: 6, fontSize: 11, height: 26, padding: "0 10px" }} onClick={() => handleInspect(t.id)}>
                      Mark Inspected
                    </button>
                  )}
                </div>
              )) : <p className="empty-state">No violations in queue.</p>}
            </div>
          </div>

        </aside>
      </div>

      {loading && (
        <div className="loader-overlay">
          <div className="loader-spinner" />
          <span className="loader-text">Loading ward data…</span>
        </div>
      )}
    </div>
  );
}
