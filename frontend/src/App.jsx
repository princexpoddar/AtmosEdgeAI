import React, { useState, useEffect, useRef } from "react";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000/api";

function App() {
  const [cities, setCities] = useState([]);
  const [selectedCityId, setSelectedCityId] = useState("");
  const [wards, setWards] = useState([]);
  const [selectedWardId, setSelectedWardId] = useState("");
  
  // Data States
  const [realtimeData, setRealtimeData] = useState(null);
  const [forecasts, setForecasts] = useState([]);
  const [attribution, setAttribution] = useState(null);
  const [advisory, setAdvisory] = useState(null);
  const [enforcements, setEnforcements] = useState([]);
  
  // Gemini Chat State
  const [geminiKey, setGeminiKey] = useState(() => localStorage.getItem("gemini_api_key") || "");
  const [chatQuery, setChatQuery] = useState("");
  const [chatHistory, setChatHistory] = useState([
    { sender: "bot", text: "Hello! I am your AtmosEdgeAI assistant. Ask me anything about local air safety, mask usage, or physical activity limits." }
  ]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const chatEndRef = useRef(null);

  // Loading & Error States
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [syncSuccess, setSyncSuccess] = useState(false);

  // Sync Live Data
  const handleSyncData = async () => {
    setSyncing(true);
    setError(null);
    setSyncSuccess(false);
    try {
      const response = await fetch(`${API_BASE}/aqi/sync`, {
        method: "POST"
      });
      if (response.ok) {
        setSyncSuccess(true);
        setTimeout(() => {
          setSyncSuccess(false);
          window.location.reload();
        }, 2200);
      } else {
        setError("Synchronization failed. Check backend console logs.");
      }
    } catch (err) {
      setError("Failed to connect to backend sync endpoint.");
    } finally {
      setSyncing(false);
    }
  };

  // Save Gemini Key to LocalStorage
  const handleSaveKey = (e) => {
    const key = e.target.value;
    setGeminiKey(key);
    localStorage.setItem("gemini_api_key", key);
  };

  // Fetch Cities on Load
  useEffect(() => {
    fetch(`${API_BASE}/cities`)
      .then((res) => res.json())
      .then((data) => {
        setCities(data);
        if (data.length > 0) setSelectedCityId(data[0].id);
      })
      .catch((err) => setError("Failed to connect to FastAPI backend. Make sure the backend server is running on port 8000."));
  }, []);

  // Fetch Wards when City changes
  useEffect(() => {
    if (!selectedCityId) return;
    fetch(`${API_BASE}/wards?city_id=${selectedCityId}`)
      .then((res) => res.json())
      .then((data) => {
        setWards(data);
        if (data.length > 0) setSelectedWardId(data[0].id);
      })
      .catch(() => setError("Failed to fetch wards."));

    // Fetch enforcement queue for this city
    fetch(`${API_BASE}/enforcement?city_id=${selectedCityId}`)
      .then((res) => res.json())
      .then((data) => setEnforcements(data))
      .catch(() => {});
  }, [selectedCityId]);

  // Fetch Ward-Specific Data (Realtime, Forecast, Attribution, Advisory)
  useEffect(() => {
    if (!selectedWardId) return;
    setLoading(true);
    
    // Fetch Realtime AQI list for city to pick the selected ward's reading
    const fetchRealtime = fetch(`${API_BASE}/aqi/realtime?city_id=${selectedCityId}`)
      .then((res) => res.json())
      .then((data) => {
        const wardRead = data.find((r) => r.ward_id === Number(selectedWardId));
        setRealtimeData(wardRead || null);
      });

    // Fetch Forecasts
    const fetchForecast = fetch(`${API_BASE}/forecast?ward_id=${selectedWardId}`)
      .then((res) => res.json())
      .then((data) => setForecasts(data));

    // Fetch Source Attribution
    const fetchAttr = fetch(`${API_BASE}/attribution?ward_id=${selectedWardId}`)
      .then((res) => res.json())
      .then((data) => setAttribution(data));

    // Fetch Advisory
    const fetchAdv = fetch(`${API_BASE}/advisory?ward_id=${selectedWardId}`)
      .then((res) => res.json())
      .then((data) => setAdvisory(data));

    Promise.all([fetchRealtime, fetchForecast, fetchAttr, fetchAdv])
      .then(() => {
        setLoading(false);
        setError(null);
      })
      .catch(() => {
        setLoading(false);
        setError("Error pulling metrics for the selected ward.");
      });
  }, [selectedWardId, selectedCityId]);

  // Scroll Chat to Bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // Send Message to Chatbot
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatQuery.trim() || !selectedWardId) return;

    const userMessage = chatQuery;
    setChatHistory((prev) => [...prev, { sender: "user", text: userMessage }]);
    setChatQuery("");
    setIsChatLoading(true);

    try {
      const response = await fetch(`${API_BASE}/advisory/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: userMessage,
          ward_id: Number(selectedWardId),
          gemini_api_key: geminiKey || null
        })
      });

      const resData = await response.json();
      setChatHistory((prev) => [...prev, { sender: "bot", text: resData.response }]);
    } catch (err) {
      setChatHistory((prev) => [...prev, { sender: "bot", text: "Sorry, I had trouble contacting the server. Please try again." }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  // Inspect Enforcement Target
  const handleInspect = async (targetId) => {
    try {
      const response = await fetch(`${API_BASE}/enforcement/inspect/${targetId}?status=Inspected`, {
        method: "POST"
      });
      if (response.ok) {
        // Refresh enforcements list
        setEnforcements((prev) =>
          prev.map((item) => (item.id === targetId ? { ...item, status: "Inspected" } : item))
        );
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Utility to map CPCB AQI class to color styles
  const getAqiColorStyle = (aqi) => {
    if (aqi <= 50) return { bg: "rgba(34, 197, 94, 0.15)", text: "#22c55e", label: "Good" };
    if (aqi <= 100) return { bg: "rgba(163, 230, 53, 0.15)", text: "#a3e635", label: "Satisfactory" };
    if (aqi <= 200) return { bg: "rgba(234, 179, 8, 0.15)", text: "#eab308", label: "Moderate" };
    if (aqi <= 300) return { bg: "rgba(249, 115, 22, 0.15)", text: "#f97316", label: "Poor" };
    if (aqi <= 400) return { bg: "rgba(239, 68, 68, 0.15)", text: "#ef4444", label: "Very Poor" };
    return { bg: "rgba(127, 29, 29, 0.25)", text: "#f87171", label: "Severe" };
  };

  return (
    <div className="app-container">
      {/* Background Orbs */}
      <div className="glow-orb orb-1"></div>
      <div className="glow-orb orb-2"></div>

      {/* Header Panel */}
      <header className="app-header">
        <div className="header-logo">
          <div className="logo-icon">💨</div>
          <h1>AtmosEdgeAI <span className="badge">v1.1</span></h1>
        </div>
        <p className="subtitle">Spatiotemporal Deep Learning Air Quality Forecast & Attribution Engine</p>

        <div className="header-actions">
          <button 
            onClick={handleSyncData} 
            className="sync-btn"
            disabled={syncing}
          >
            {syncing ? "🔄 Syncing..." : "🔄 Sync Live Data"}
          </button>

          {/* Global Key configuration */}
          <div className="key-config-box">
            <div className="key-label">🤖 Gemini AI Key:</div>
            <input
              type="password"
              value={geminiKey}
              onChange={handleSaveKey}
              placeholder="Paste your Gemini API Key for smart chat..."
              className="key-input"
            />
          </div>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}
      {syncSuccess && <div className="sync-success-banner">🟢 Live data synced successfully! Refreshing dashboard metrics...</div>}

      {/* Main Grid Content */}
      <main className="dashboard-grid">
        
        {/* Left Control & Realtime panel */}
        <section className="col-left">
          
          {/* selectors */}
          <div className="glass-card selectors-card">
            <h3>📍 Target Ward Settings</h3>
            <div className="select-group">
              <label>Select City</label>
              <select value={selectedCityId} onChange={(e) => setSelectedCityId(e.target.value)}>
                {cities.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div className="select-group">
              <label>Select Ward</label>
              <select value={selectedWardId} onChange={(e) => setSelectedWardId(e.target.value)}>
                {wards.map((w) => (
                  <option key={w.id} value={w.id}>{w.name}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Realtime Stats */}
          {realtimeData && (
            <div className="glass-card realtime-card">
              <div className="card-header-flex">
                <h3>⚡ Real-Time Reading</h3>
                <span className="timestamp-tag">
                  {new Date(realtimeData.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>

              {/* Large AQI display */}
              <div className="aqi-display-box" style={{ 
                background: getAqiColorStyle(realtimeData.aqi).bg,
                borderColor: getAqiColorStyle(realtimeData.aqi).text
              }}>
                <div className="aqi-val">{realtimeData.aqi}</div>
                <div className="aqi-lbl" style={{ color: getAqiColorStyle(realtimeData.aqi).text }}>
                  {getAqiColorStyle(realtimeData.aqi).label}
                </div>
              </div>

              {/* Grid of raw indicators */}
              <div className="stats-grid">
                <div className="stat-item">
                  <span className="lbl">PM2.5</span>
                  <span className="val">{realtimeData.pm25} <small>µg/m³</small></span>
                </div>
                <div className="stat-item">
                  <span className="lbl">NO₂</span>
                  <span className="val">{realtimeData.no2} <small>µg/m³</small></span>
                </div>
                <div className="stat-item">
                  <span className="lbl">Stagnation</span>
                  <span className="val">{realtimeData.stagnation} <small>(0-1)</small></span>
                </div>
                <div className="stat-item">
                  <span className="lbl">Wind</span>
                  <span className="val">{realtimeData.wind_speed} <small>km/h</small></span>
                </div>
                <div className="stat-item">
                  <span className="lbl">Temp</span>
                  <span className="val">{realtimeData.temp} <small>°C</small></span>
                </div>
                <div className="stat-item">
                  <span className="lbl">Humidity</span>
                  <span className="val">{realtimeData.humidity} <small>%</small></span>
                </div>
              </div>
            </div>
          )}

          {/* Health guidance alerts */}
          {advisory && (
            <div className="glass-card advisory-card">
              <h3>🚨 CPCB Citizen Advisories</h3>
              <div className="advisory-message">
                <p className="lang-header">🇬🇧 English Alert</p>
                <div className="msg-box en-box">{advisory.message_en}</div>
              </div>
              <div className="advisory-message">
                <p className="lang-header">🇮🇳 Hindi Alert</p>
                <div className="msg-box hi-box">{advisory.message_hi}</div>
              </div>
            </div>
          )}
        </section>

        {/* Center Forecasting & Attribution panel */}
        <section className="col-center">
          
          {/* Source Attribution Chart */}
          {attribution && (
            <div className="glass-card attribution-card">
              <h3>🔥 PM2.5 Source Attribution Analysis</h3>
              <p className="subtext">Real-time mapping via NASA MODIS/VIIRS crop fires upwind vector calculation.</p>
              
              <div className="bar-charts-list">
                {[
                  { name: "Vehicular Emissions", pct: attribution.vehicular, color: "#a855f7" },
                  { name: "Industrial Output", pct: attribution.industrial, color: "#3b82f6" },
                  { name: "Biomass Burning (Crop Fires)", pct: attribution.biomass, color: "#f97316" },
                  { name: "Waste Burning", pct: attribution.waste_burning, color: "#f43f5e" },
                  { name: "Soil & Road Dust", pct: attribution.dust, color: "#eab308" }
                ].map((item, index) => (
                  <div key={index} className="chart-item">
                    <div className="chart-info">
                      <span>{item.name}</span>
                      <strong>{item.pct.toFixed(1)}%</strong>
                    </div>
                    <div className="chart-track">
                      <div className="chart-fill" style={{ 
                        width: `${item.pct}%`, 
                        backgroundColor: item.color 
                      }}></div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="confidence-footer">
                Confidence Score: <strong>{(attribution.confidence * 100).toFixed(0)}%</strong>
              </div>
            </div>
          )}

          {/* CNN-LSTM forecasts */}
          <div className="glass-card forecast-card">
            <h3>🔮 Deep CNN-LSTM Forecast Horizon</h3>
            <p className="subtext">Spatiotemporal predictions trained dynamically over past 24h variables.</p>
            
            <div className="forecast-flex">
              {forecasts.map((fc, index) => {
                const hourDiff = Math.round((new Date(fc.forecast_time) - new Date()) / (1000 * 60 * 60));
                return (
                  <div key={index} className="forecast-col">
                    <div className="time-lbl">+{hourDiff}h Horizon</div>
                    <div className="date-sub">
                      {new Date(fc.forecast_time).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                    </div>
                    
                    <div className="fc-aqi-circle" style={{
                      borderColor: getAqiColorStyle(fc.predicted_aqi).text,
                      background: getAqiColorStyle(fc.predicted_aqi).bg
                    }}>
                      <div className="fc-val">{fc.predicted_aqi.toFixed(0)}</div>
                      <div className="fc-lbl">AQI</div>
                    </div>

                    <div className="fc-pollutants">
                      <div>PM2.5: <strong>{fc.predicted_pm25.toFixed(1)}</strong></div>
                      <div>NO₂: <strong>{fc.predicted_no2.toFixed(1)}</strong></div>
                    </div>
                  </div>
                );
              })}
              {forecasts.length === 0 && <p className="no-data">No active forecasting records found.</p>}
            </div>
          </div>
        </section>

        {/* Right side chatbot & enforcement panel */}
        <section className="col-right">
          
          {/* Chatbot Interface */}
          <div className="glass-card chat-card">
            <div className="card-header-flex">
              <h3>💬 Health Advisor AI Assistant</h3>
              {!geminiKey && <span className="key-warning-tag">Fallback Rule-based</span>}
              {geminiKey && <span className="key-active-tag">Gemini AI Active</span>}
            </div>

            <div className="chat-window">
              {chatHistory.map((msg, i) => (
                <div key={i} className={`chat-bubble ${msg.sender}-bubble`}>
                  <div className="bubble-sender">{msg.sender === "bot" ? "AtmosEdgeAI" : "You"}</div>
                  <div className="bubble-text">{msg.text}</div>
                </div>
              ))}
              {isChatLoading && (
                <div className="chat-bubble bot-bubble loading-bubble">
                  <div className="typing-dots">
                    <span>.</span><span>.</span><span>.</span>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            <form onSubmit={handleSendMessage} className="chat-input-row">
              <input
                type="text"
                value={chatQuery}
                onChange={(e) => setChatQuery(e.target.value)}
                placeholder="Ask e.g. Should I exercise outdoors?"
                disabled={isChatLoading}
              />
              <button type="submit" disabled={isChatLoading || !chatQuery.trim()}>
                Send
              </button>
            </form>
          </div>

          {/* Enforcement Queue panel */}
          <div className="glass-card enforcement-card">
            <h3>👮 Environmental Enforcement Queue</h3>
            <p className="subtext">Prioritized hotspots requiring pollution source suppression inspection.</p>
            
            <div className="target-list">
              {enforcements.map((item, index) => (
                <div key={index} className="target-item">
                  <div className="target-meta">
                    <span className="target-type">{item.type}</span>
                    <span className={`status-tag ${item.status.toLowerCase()}`}>{item.status}</span>
                  </div>
                  <h4>{item.name}</h4>
                  <div className="evidence-summary">
                    Risk Score: <strong>{item.risk_score}</strong> | PM2.5: {item.evidence_packet.detected_pm25} µg/m³
                  </div>
                  
                  {item.status === "Pending" && (
                    <button 
                      onClick={() => handleInspect(item.id)}
                      className="inspect-btn"
                    >
                      Mark as Inspected
                    </button>
                  )}
                </div>
              ))}
              {enforcements.length === 0 && <p className="no-data">No violations found in the queue.</p>}
            </div>
          </div>
        </section>

      </main>
      
      {loading && (
        <div className="loader-overlay">
          <div className="spinner"></div>
          <p>Processing spatiotemporal datasets...</p>
        </div>
      )}
    </div>
  );
}

export default App;
