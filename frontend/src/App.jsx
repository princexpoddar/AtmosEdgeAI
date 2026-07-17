import { useState, useEffect } from "react";
import "./App.css";

// Import modular pages & services
import LandingPage from "./pages/LandingPage";
import Predictor from "./pages/Predictor";
import { getStations, getMonitoring, getStationHistory, getStationForecast, syncCPCB } from "./services/api";

// Import components
import Map from "./components/map/Map";
import Analytics from "./components/charts/Analytics";
import Explainability from "./components/charts/Explainability";
import Comparison from "./components/cards/Comparison";

function aqiSlug(aqi) {
  if (aqi <= 50)  return "good";
  if (aqi <= 100) return "satisfactory";
  if (aqi <= 200) return "moderate";
  if (aqi <= 300) return "poor";
  if (aqi <= 400) return "very-poor";
  return "severe";
}

function fmt(val, decimals = 1) {
  if (val === null || val === undefined) return "N/A";
  return typeof val === "number" ? val.toFixed(decimals) : val;
}

export default function App() {
  const [viewMode, setViewMode] = useState("landing"); // "landing" | "dashboard" | "predictor"
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "dark");
  const [dashboardTab, setDashboardTab] = useState("forecast");
  const [activeMapLayer, setActiveMapLayer] = useState("aqi");

  // Core Data
  const [stations, setStations] = useState([]);
  const [selectedStationId, setSelectedStationId] = useState("");
  const [stationHistory, setStationHistory] = useState([]);
  const [stationForecasts, setStationForecasts] = useState([]);
  const [monitoring, setMonitoring] = useState(null);
  
  // Refresh & Ingestion state
  const [lastUpdated, setLastUpdated] = useState(null);
  const [countdown, setCountdown] = useState(300);
  const [syncing, setSyncing] = useState(false);
  const [syncOk, setSyncOk] = useState(false);

  // Alerts & Warnings
  const [alerts, setAlerts] = useState([]);
  const [showAlertPanel, setShowAlertPanel] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Toggle Theme
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  // Request notifications
  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);

  // Fetch initial telemetry & stations
  const loadData = () => {
    return Promise.all([getStations(), getMonitoring()])
      .then(([stList, monitor]) => {
        setStations(stList);
        setMonitoring(monitor);
        setLastUpdated(new Date().toLocaleTimeString());
        setCountdown(300);
        setError(null);
        return stList;
      })
      .catch(() => {
        setError("Database server offline. Using locally cached datasets.");
      });
  };

  useEffect(() => {
    setLoading(true);
    loadData()
      .then((stList) => {
        if (stList && stList.length) setSelectedStationId(stList[0].id);
      })
      .finally(() => setLoading(false));
  }, []);

  // Count down loop
  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          loadData().catch(() => {});
          return 300;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // Fetch individual station details when selection changes
  useEffect(() => {
    if (!selectedStationId) return;
    Promise.all([
      getStationHistory(selectedStationId, 3),
      getStationForecast(selectedStationId)
    ]).then(([hist, fc]) => {
      setStationHistory(hist);
      setStationForecasts(fc);
      
      const maxFc = Math.max(...fc.map(x => x.predicted_aqi), 0);
      const newAlerts = [];
      if (maxFc > 200) {
        newAlerts.push({
          title: "High Pollution Alert!",
          desc: `Forecast peaks at ${maxFc.toFixed(0)} AQI. Stay indoors and use air filters.`,
          type: "danger"
        });
      } else if (maxFc > 100) {
        newAlerts.push({
          title: "Moderate Exposure Advisory",
          desc: `AQI forecast reaches ${maxFc.toFixed(0)}. Close windows if sensitive.`,
          type: "warning"
        });
      } else {
        newAlerts.push({
          title: "Clean Air Forecasted",
          desc: "Low pollution levels predicted for the next 72 hours.",
          type: "success"
        });
      }
      setAlerts(newAlerts);
    }).catch(() => {});
  }, [selectedStationId]);

  // Ingestion database sync
  const handleSync = async () => {
    setSyncing(true);
    setError(null);
    setSyncOk(false);
    try {
      await syncCPCB();
      setSyncOk(true);
      setTimeout(() => {
        setSyncOk(false);
        loadData().catch(() => {});
      }, 2000);
    } catch (err) {
      setError(err.message || "Failed to trigger live update.");
    } finally {
      setSyncing(false);
    }
  };

  const selectedStation = stations.find(s => s.id === selectedStationId);

  // Determine current data source depending on quality flags
  const getDataSourceText = () => {
    if (!selectedStation) return "Historical Data";
    if (selectedStation.pm25 === 0.0) return "Cached (Offline Fallback)";
    return "Live Observation API";
  };

  return (
    <div className="app-root">
      
      {/* ── Navbar ── */}
      <header className="topbar">
        <div className="topbar-brand" onClick={() => setViewMode("landing")} style={{ cursor: "pointer" }}>
          <div className="brand-icon">🌬</div>
          <span className="brand-name">AtmosEdgeAI</span>
          <span className="brand-version">v2.1</span>
        </div>

        {viewMode !== "landing" && (
          <div style={{ display: "flex", gap: "16px", marginLeft: "20px" }}>
            <span 
              onClick={() => setViewMode("dashboard")} 
              style={{ fontSize: "13px", fontWeight: "600", cursor: "pointer", color: viewMode === "dashboard" ? "#3b82f6" : "var(--text-2)" }}
            >
              Dashboard
            </span>
            <span 
              onClick={() => setViewMode("predictor")} 
              style={{ fontSize: "13px", fontWeight: "600", cursor: "pointer", color: viewMode === "predictor" ? "#3b82f6" : "var(--text-2)" }}
            >
              Predictor
            </span>
          </div>
        )}

        <div className="topbar-actions">
          {/* Database Ingest sync trigger */}
          <button 
            className="btn btn-secondary" 
            onClick={handleSync}
            disabled={syncing}
            style={{ fontSize: "11px", height: "30px", borderRadius: "15px", display: "flex", gap: "6px", alignItems: "center" }}
          >
            <i className={`fa fa-arrows-rotate ${syncing ? "fa-spin" : ""}`}></i>
            <span>{syncing ? "Syncing..." : "Sync APIs"}</span>
          </button>

          {/* Refresh Countdown */}
          {lastUpdated && (
            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", color: "var(--text-3)", marginRight: "10px" }}>
              <span className="live-pulse"></span>
              <span>Updated {lastUpdated} (refresh {countdown}s)</span>
            </div>
          )}

          {/* Alert Center Trigger */}
          <button 
            className="btn btn-secondary" 
            onClick={() => setShowAlertPanel(!showAlertPanel)}
            style={{ width: "32px", height: "32px", padding: 0, justifyContent: "center", position: "relative" }}
          >
            <i className="fa fa-bell" style={{ fontSize: "12px" }}></i>
            {alerts.length > 0 && <span className="alert-badge"></span>}
          </button>

          {/* Theme Toggle */}
          <button 
            className="btn btn-secondary" 
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            style={{ width: "32px", height: "32px", padding: 0, justifyContent: "center" }}
          >
            <i className={`fa ${theme === "dark" ? "fa-sun" : "fa-moon"}`} style={{ fontSize: "12px" }}></i>
          </button>
        </div>
      </header>

      {/* Alert Overlay Drawer */}
      {showAlertPanel && (
        <div className="alert-drawer">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
            <h4 style={{ margin: 0, fontSize: "13.5px", fontWeight: "bold" }}>Alerts & Advisories</h4>
            <i className="fa fa-times" style={{ cursor: "pointer" }} onClick={() => setShowAlertPanel(false)}></i>
          </div>
          {alerts.map((al, idx) => (
            <div key={idx} className={`alert-item ${al.type}`} style={{ padding: "10px 12px", borderRadius: "6px", fontSize: "11.5px", marginBottom: "8px" }}>
              <strong>{al.title}</strong>
              <p style={{ margin: "4px 0 0 0", color: "var(--text-2)", lineHeight: "1.4" }}>{al.desc}</p>
            </div>
          ))}
        </div>
      )}

      {error  && <div className="banner banner-error">⚠ {error}</div>}
      {syncOk && <div className="banner banner-success">✓ Updated CPCB live measurements. Refreshing...</div>}

      {/* ── View Routing ── */}
      {viewMode === "landing" ? (
        <LandingPage 
          stations={stations} 
          onEnterApp={(mode) => setViewMode(mode)} 
        />
      ) : viewMode === "predictor" ? (
        <div style={{ padding: "40px 20px" }}>
          <Predictor stations={stations} />
        </div>
      ) : (
        /* ── Full Dashboard View ── */
        <div className="main-content" style={{ display: "grid", gridTemplateColumns: "1.4fr 2fr", gap: "20px", padding: "20px", flex: 1 }}>
          
          {/* Map Column */}
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            
            {/* Interactive Leaflet Map */}
            <div className="card" style={{ flex: 1.2, minHeight: "440px", overflow: "hidden", position: "relative" }}>
              <div style={{ position: "absolute", top: "15px", right: "15px", zIndex: 1000, display: "flex", gap: "6px" }}>
                {[
                  { key: "aqi", label: "AQI" },
                  { key: "weather", label: "Temp" },
                  { key: "wind", label: "Wind" }
                ].map(layer => (
                  <button
                    key={layer.key}
                    onClick={() => setActiveMapLayer(layer.key)}
                    style={{
                      height: "26px",
                      padding: "0 10px",
                      borderRadius: "13px",
                      fontSize: "10.5px",
                      fontWeight: "bold",
                      border: "1px solid var(--border)",
                      background: activeMapLayer === layer.key ? "#3b82f6" : "var(--bg-3)",
                      color: "#fff",
                      cursor: "pointer",
                      boxShadow: "var(--shadow-sm)"
                    }}
                  >
                    {layer.label}
                  </button>
                ))}
              </div>
              <Map
                stations={stations}
                selectedStationId={selectedStationId}
                onSelectStation={(id) => setSelectedStationId(id)}
                theme={theme}
                activeLayer={activeMapLayer}
              />
            </div>

            {/* List directory of stations */}
            <div className="card" style={{ flex: 1, display: "flex", flexDirection: "column", padding: "16px" }}>
              <h3 style={{ margin: "0 0 12px 0", fontSize: "14px", fontWeight: "bold" }}>CPCB Station Directory</h3>
              <div style={{ flex: 1, overflowY: "auto", maxHeight: "250px", display: "flex", flexDirection: "column", gap: "6px" }}>
                {stations.map(st => {
                  const isSelected = st.id === selectedStationId;
                  const slug = aqiSlug(st.aqi);
                  return (
                    <div
                      key={st.id}
                      onClick={() => setSelectedStationId(st.id)}
                      className={`station-list-row ${isSelected ? "active" : ""}`}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "10px 12px",
                        borderRadius: "8px",
                        background: isSelected ? "rgba(59, 130, 246, 0.12)" : "var(--bg-3)",
                        border: isSelected ? "1px solid #3b82f6" : "1px solid var(--border)",
                        cursor: "pointer"
                      }}
                    >
                      <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                        <span style={{ fontSize: "12.5px", fontWeight: isSelected ? "bold" : "500", color: isSelected ? "#3b82f6" : "var(--text-1)" }}>{st.name}</span>
                        <span style={{ fontSize: "10px", color: "var(--text-3)" }}>{st.city}, {st.state}</span>
                      </div>
                      <span className={`aqi-indicator-pill ${slug}`}>{st.aqi.toFixed(0)}</span>
                    </div>
                  );
                })}
              </div>
            </div>

          </div>

          {/* Right Metrics & Analytics column */}
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            
            {/* Header info */}
            {selectedStation && (
              <div className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 20px" }}>
                <div>
                  <h2 style={{ margin: 0, fontSize: "17px", fontWeight: "bold" }}>{selectedStation.name}</h2>
                  <span style={{ fontSize: "11px", color: "var(--text-3)" }}>Source: <strong style={{ color: "#3b82f6" }}>{getDataSourceText()}</strong></span>
                </div>
                <div style={{ textAlign: "right" }}>
                  <span style={{ fontSize: "22px", fontWeight: "bold", color: "#3b82f6" }}>{selectedStation.aqi.toFixed(0)}</span>
                  <span style={{ fontSize: "10px", color: "var(--text-3)", display: "block" }}>AQI</span>
                </div>
              </div>
            )}

            {/* Metrics cards row */}
            {selectedStation && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "10px" }}>
                {[
                  { l: "PM2.5", v: selectedStation.pm25, u: "µg/m³" },
                  { l: "NO₂", v: selectedStation.no2, u: "µg/m³" },
                  { l: "Temp", v: selectedStation.temp, u: "°C" },
                  { l: "Humid", v: selectedStation.humidity, u: "%" },
                  { l: "Wind", v: selectedStation.wind_speed, u: "km/h" }
                ].map((m, idx) => (
                  <div key={idx} className="card" style={{ padding: "10px", display: "flex", flexDirection: "column", gap: "3px", textAlign: "center" }}>
                    <span style={{ fontSize: "10px", color: "var(--text-3)" }}>{m.l}</span>
                    <strong style={{ fontSize: "14.5px" }}>{fmt(m.v)} <span style={{ fontSize: "9px", color: "var(--text-3)" }}>{m.u}</span></strong>
                  </div>
                ))}
              </div>
            )}

            {/* Dashboard Sub-tabs */}
            <div className="card" style={{ flex: 1, padding: "16px", display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ display: "flex", gap: "14px", borderBottom: "1px solid var(--border)", paddingBottom: "10px" }}>
                {[
                  { key: "forecast", label: "Model Predictions" },
                  { key: "analytics", label: "Historical Records" },
                  { key: "shap", label: "SHAP Explainability" },
                  { key: "comparison", label: "Compare Stations" }
                ].map(tab => (
                  <span
                    key={tab.key}
                    onClick={() => setDashboardTab(tab.key)}
                    style={{
                      fontSize: "13px",
                      fontWeight: "600",
                      cursor: "pointer",
                      paddingBottom: "8px",
                      borderBottom: dashboardTab === tab.key ? "2px solid #3b82f6" : "2px solid transparent",
                      color: dashboardTab === tab.key ? "var(--text-1)" : "var(--text-3)",
                      transition: "all 0.15s"
                    }}
                  >
                    {tab.label}
                  </span>
                ))}
              </div>

              {/* Tab panels */}
              <div style={{ flex: 1 }}>
                {dashboardTab === "forecast" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                    {stationForecasts.map((fc, i) => {
                      const fTime = new Date(fc.forecast_time);
                      const slug = aqiSlug(fc.predicted_aqi);
                      return (
                        <div key={i} className="forecast-card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "var(--bg-3)", border: "1px solid var(--border)", borderRadius: "8px" }}>
                          <div>
                            <span style={{ fontSize: "11px", color: "#3b82f6", fontWeight: "bold" }}>+{24 * (i+1)}h Forecast Horizon</span>
                            <h4 style={{ margin: "2px 0", fontSize: "13px" }}>{fTime.toLocaleDateString([], { weekday: "long", month: "short", day: "numeric" })}</h4>
                            <span style={{ fontSize: "10px", color: "var(--text-3)" }}>Uncertainty: {fc.pm25_lower.toFixed(0)} – {fc.pm25_upper.toFixed(0)} µg/m³</span>
                          </div>
                          <div style={{ textAlign: "right" }}>
                            <strong style={{ fontSize: "20px", color: `var(--${slug === 'very-poor' ? 'purple' : slug === 'satisfactory' ? 'accent' : slug})` }}>{fc.predicted_aqi.toFixed(0)} AQI</strong>
                            <span style={{ display: "block", fontSize: "10px", color: "var(--text-3)" }}>{fc.category}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {dashboardTab === "analytics" && (
                  <Analytics 
                    history={stationHistory} 
                    forecasts={stationForecasts} 
                  />
                )}

                {dashboardTab === "shap" && (
                  <Explainability 
                    stationId={selectedStationId} 
                  />
                )}

                {dashboardTab === "comparison" && (
                  <Comparison 
                    stations={stations} 
                  />
                )}
              </div>
            </div>

            {/* MLOps health monitoring telemetry */}
            {monitoring && (
              <div className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 18px", fontSize: "11px" }}>
                <div style={{ display: "flex", gap: "20px", color: "var(--text-2)" }}>
                  <span>MAE: <strong>{monitoring.current_mae.toFixed(4)}</strong></span>
                  <span>RMSE: <strong>{monitoring.current_rmse.toFixed(4)}</strong></span>
                  <span>Prediction Drift: <strong style={{ color: "#10b981" }}>{monitoring.prediction_drift.toFixed(4)}</strong></span>
                </div>
                <span style={{ color: "#10b981", fontWeight: "bold" }}>● system healthy</span>
              </div>
            )}

          </div>

        </div>
      )}

      {loading && (
        <div className="loader-overlay">
          <div className="loader-spinner"></div>
          <span style={{ marginLeft: "14px", fontSize: "13px" }}>Loading AtmosEdgeAI metrics...</span>
        </div>
      )}
    </div>
  );
}
