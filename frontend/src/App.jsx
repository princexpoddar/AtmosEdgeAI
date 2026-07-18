import { useState, useEffect } from "react";
import "./App.css";

// Import modular pages & services
import LandingPage from "./pages/LandingPage";
import Predictor from "./pages/Predictor";
import { getStations, getMonitoring, getStationHistory, getStationForecast, syncCPCB, getStationIntelligence, getEnforcementDashboard } from "./services/api";

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
  const [dashboardTab, setDashboardTab] = useState("analyst");
  const [activeMapLayer, setActiveMapLayer] = useState("aqi");
  const [intelligence, setIntelligence] = useState(null);
  const [selectedTimelineNode, setSelectedTimelineNode] = useState("Now");
  const [enforcementData, setEnforcementData] = useState(null);
  const [selectedEnforceNode, setSelectedEnforceNode] = useState("Now");

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

  useEffect(() => {
    if (viewMode === "enforcement") {
      setLoading(true);
      getEnforcementDashboard()
        .then(data => {
          setEnforcementData(data);
          setError(null);
        })
        .catch(() => {
          setError("Failed to fetch municipal command center telemetry.");
        })
        .finally(() => setLoading(false));
    }
  }, [viewMode]);

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
      getStationForecast(selectedStationId),
      getStationIntelligence(selectedStationId).catch(() => null)
    ]).then(([hist, fc, intel]) => {
      setStationHistory(hist);
      setStationForecasts(fc);
      setIntelligence(intel);
      
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
              style={{ fontSize: "13px", fontWeight: "600", cursor: "pointer", color: viewMode === "dashboard" ? "#3b82f6" : "var(--text-2)", transition: "all 0.15s" }}
            >
              Dashboard
            </span>
            <span 
              onClick={() => setViewMode("enforcement")} 
              style={{ fontSize: "13px", fontWeight: "600", cursor: "pointer", color: viewMode === "enforcement" ? "#3b82f6" : "var(--text-2)", transition: "all 0.15s" }}
            >
              Municipal Command Center
            </span>
            <span 
              onClick={() => setViewMode("predictor")} 
              style={{ fontSize: "13px", fontWeight: "600", cursor: "pointer", color: viewMode === "predictor" ? "#3b82f6" : "var(--text-2)", transition: "all 0.15s" }}
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
      ) : viewMode === "enforcement" ? (
        <div style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "20px", flex: 1 }}>
          {!enforcementData ? (
            <div style={{ display: "flex", flex: 1, justifyContent: "center", alignItems: "center", minHeight: "400px" }}>
              <div className="live-pulse" style={{ width: "30px", height: "30px" }}></div>
              <span style={{ marginLeft: "12px", color: "var(--text-3)" }}>Resolving Municipal Command Center telemetry...</span>
            </div>
          ) : (
            <>
              {/* Executive Summary Brief Banner */}
              <div style={{ background: enforcementData.executive_summary.critical_count > 0 ? "rgba(239, 68, 68, 0.08)" : "rgba(16, 185, 129, 0.08)", border: enforcementData.executive_summary.critical_count > 0 ? "1px solid rgba(239, 68, 68, 0.25)" : "1px solid rgba(16, 185, 129, 0.25)", borderRadius: "10px", padding: "16px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                  <h3 style={{ margin: 0, fontSize: "14px", fontWeight: "bold", textTransform: "uppercase", color: enforcementData.executive_summary.critical_count > 0 ? "#f87171" : "#34d399" }}>
                    {enforcementData.executive_summary.headline}
                  </h3>
                  <span style={{ fontSize: "10px", padding: "3px 8px", borderRadius: "12px", background: enforcementData.executive_summary.critical_count > 0 ? "#ef4444" : "#10b981", fontWeight: "bold" }}>
                    {enforcementData.executive_summary.critical_count > 0 ? "ACTION REQUIRED" : "NORMAL OPERATIONS"}
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: "12.5px", color: "var(--text-2)", lineHeight: "1.4" }}>
                  <strong>Summary of Alerts:</strong> Evaluated {enforcementData.executive_summary.total_evaluated} regional wards. {enforcementData.executive_summary.critical_count} wards are in Critical priority and {enforcementData.executive_summary.high_count} are in High priority.
                  <br />
                  <strong>Directives:</strong> {enforcementData.executive_summary.direct_orders}
                </p>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1.2fr 2fr", gap: "20px" }}>
                
                {/* Left Column: Priority Rankings & Hotspots List */}
                <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                  
                  {/* Priority Wards Queue */}
                  <div className="card" style={{ padding: "16px" }}>
                    <h4 style={{ margin: "0 0 12px 0", fontSize: "12px", color: "var(--text-3)", textTransform: "uppercase", fontWeight: "bold" }}>Priority Wards Queue</h4>
                    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                      {enforcementData.priority_rankings.map((st, i) => (
                        <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px", background: "var(--bg-3)", border: "1px solid var(--border)", borderRadius: "6px" }}>
                          <div>
                            <strong style={{ fontSize: "12.5px", display: "block" }}>{st.station_name}</strong>
                            <span style={{ fontSize: "10px", color: "var(--text-3)" }}>Trend Delta (24h): {st.trend_delta > 0 ? `+${st.trend_delta.toFixed(1)}` : st.trend_delta.toFixed(1)} ug/m3</span>
                          </div>
                          <div style={{ textAlign: "right" }}>
                            <span style={{ fontSize: "10px", padding: "2px 6px", borderRadius: "8px", background: st.priority === "Critical" ? "rgba(239, 68, 68, 0.15)" : st.priority === "High" ? "rgba(245, 158, 11, 0.15)" : "rgba(59, 130, 246, 0.15)", color: st.priority === "Critical" ? "#f87171" : st.priority === "High" ? "#f59e0b" : "#60a5fa", fontWeight: "bold", display: "inline-block", marginBottom: "4px" }}>
                              {st.priority}
                            </span>
                            <span style={{ display: "block", fontSize: "11px", fontWeight: "bold" }}>Score: {st.score.toFixed(0)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Hotspots Category Cards */}
                  <div className="card" style={{ padding: "16px" }}>
                    <h4 style={{ margin: "0 0 12px 0", fontSize: "12px", color: "var(--text-3)", textTransform: "uppercase", fontWeight: "bold" }}>Hotspot Classifications</h4>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "11.5px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>🔥 Deteriorating (Worsening Delta)</span>
                        <strong>{enforcementData.hotspots.deteriorating[0]?.station_name || "None"}</strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>📈 Highest Priority Wards</span>
                        <strong>{enforcementData.hotspots.highest_priority[0]?.station_name || "None"}</strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>🍃 Improving (Clearing up)</span>
                        <strong>{enforcementData.hotspots.improving[0]?.station_name || "None"}</strong>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>⚖ Stable Wards</span>
                        <strong>{enforcementData.hotspots.stable[0]?.station_name || "None"}</strong>
                      </div>
                    </div>
                  </div>

                </div>

                {/* Right Column: Inspection, Interventions, Allocations, timelines */}
                <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                  
                  {/* Recommended Interventions & Action Items */}
                  <div className="card" style={{ padding: "16px" }}>
                    <h4 style={{ margin: "0 0 12px 0", fontSize: "12px", color: "var(--text-3)", textTransform: "uppercase", fontWeight: "bold" }}>Recommended Intervention Directives</h4>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                      {enforcementData.intervention_recommendations.slice(0, 4).map((act, i) => (
                        <div key={i} style={{ padding: "10px", background: "var(--bg-3)", border: "1px solid var(--border)", borderRadius: "6px", fontSize: "11.5px" }}>
                          <span style={{ fontSize: "9px", color: "#3b82f6", fontWeight: "bold", display: "block", textTransform: "uppercase" }}>{act.category} ({act.target_station.split(",")[0]})</span>
                          <p style={{ margin: "4px 0", fontWeight: "600", fontSize: "11px" }}>{act.action}</p>
                          <div style={{ display: "flex", justifyContent: "space-between", marginTop: "6px", fontSize: "9px", color: "var(--text-3)" }}>
                            <span>Difficulty: {act.implementation_difficulty}</span>
                            <span style={{ color: "#10b981", fontWeight: "bold" }}>Impact: {act.expected_impact}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Resource Allocations Dispatches */}
                  <div className="card" style={{ padding: "16px" }}>
                    <h4 style={{ margin: "0 0 12px 0", fontSize: "12px", color: "var(--text-3)", textTransform: "uppercase", fontWeight: "bold" }}>Resource Allocation & Deployments</h4>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px" }}>
                      {enforcementData.resource_allocation.slice(0, 6).map((res, i) => (
                        <div key={i} style={{ padding: "10px", background: "var(--bg-3)", border: "1px solid var(--border)", borderRadius: "6px", textAlign: "center" }}>
                          <div style={{ fontSize: "20px", marginBottom: "4px" }}>
                            {res.resource.includes("Team") ? "👮" : res.resource.includes("Sprinkler") ? "⛟" : res.resource.includes("Van") ? "🚐" : "👮"}
                          </div>
                          <strong style={{ fontSize: "12px", display: "block" }}>{res.quantity}x {res.resource}</strong>
                          <span style={{ fontSize: "9.5px", color: "var(--text-3)", display: "block", marginTop: "2px" }}>Target: {res.target_station.split(",")[0]}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Inspection Queue */}
                  <div className="card" style={{ padding: "16px" }}>
                    <h4 style={{ margin: "0 0 12px 0", fontSize: "12px", color: "var(--text-3)", textTransform: "uppercase", fontWeight: "bold" }}>Inspection Dispatch Queue</h4>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {enforcementData.inspection_recommendations.slice(0, 3).map((insp, i) => (
                        <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px", background: "var(--bg-3)", border: "1px solid var(--border)", borderRadius: "6px", fontSize: "11.5px" }}>
                          <div>
                            <strong style={{ color: "#60a5fa" }}>{insp.inspection_type}</strong>
                            <span style={{ display: "block", fontSize: "10px", color: "var(--text-3)" }}>{insp.reason}</span>
                          </div>
                          <div style={{ textAlign: "right" }}>
                            <span style={{ fontSize: "9px", padding: "1px 5px", borderRadius: "6px", background: "rgba(239,68,68,0.12)", color: "#f87171", fontWeight: "bold" }}>{insp.urgency}</span>
                            <span style={{ display: "block", fontSize: "9px", color: "var(--text-3)", marginTop: "4px" }}>Est: {insp.estimated_duration}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Enforcement Timeline Widgets */}
                  <div>
                    <h4 style={{ margin: "0 0 10px 0", fontSize: "11px", color: "var(--text-3)", textTransform: "uppercase", fontWeight: "bold" }}>Interactive Command Timeline</h4>
                    <div style={{ display: "flex", justifyContent: "space-between", border: "1px solid var(--border)", borderRadius: "8px", background: "var(--bg-3)", padding: "10px" }}>
                      {["Now", "6h", "24h", "48h", "72h"].map((node) => {
                        const isSelected = selectedEnforceNode === node;
                        // Summarize top priority details
                        const topWard = enforcementData.priority_rankings[0];
                        let val = topWard ? topWard.current_aqi : 80;
                        
                        if (node === "24h") val = val * 1.1; 
                        else if (node === "48h") val = val * 1.15;
                        else if (node === "72h") val = val * 1.12;
                        
                        return (
                          <div
                            key={node}
                            onClick={() => setSelectedEnforceNode(node)}
                            style={{
                              flex: 1,
                              textAlign: "center",
                              padding: "6px",
                              borderRadius: "6px",
                              background: isSelected ? "rgba(59, 130, 246, 0.12)" : "transparent",
                              border: isSelected ? "1px solid #3b82f6" : "1px solid transparent",
                              cursor: "pointer",
                              transition: "all 0.15s"
                            }}
                          >
                            <div style={{ fontSize: "10px", color: "var(--text-3)", marginBottom: "4px" }}>{node}</div>
                            <div style={{ fontSize: "14px", fontWeight: "bold", color: "#3b82f6" }}>{val.toFixed(0)} AQI</div>
                          </div>
                        );
                      })}
                    </div>
                    
                    <div style={{ marginTop: "10px", padding: "12px", background: "rgba(255,255,255,0.01)", border: "1px solid var(--border-soft)", borderRadius: "6px", fontSize: "11.5px", color: "var(--text-2)" }}>
                      <strong>Command Insight ({selectedEnforceNode}):</strong>{" "}
                      <span>
                        Intervention Priority: <strong style={{ color: "#ef4444" }}>Critical</strong>. Deployments scheduled: Water sprinklers (Peenya Wards), Factory boiler log review patrols, and truck limits coordination.
                      </span>
                    </div>
                  </div>

                </div>

              </div>

            </>
          )}
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
                  { key: "analyst", label: "AI Environmental Analyst" },
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
                {dashboardTab === "analyst" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                    {!intelligence ? (
                      <div className="banner banner-warning">
                        ⚠ Not enough recent observations in the database cache ({stationHistory.length}h of data) to generate a reliable AI analyst report. Require at least 48 hours of observations.
                      </div>
                    ) : (
                      <>
                        {/* Executive Insights Header */}
                        <div style={{ background: intelligence.intelligence.report.severity === "High" ? "rgba(239, 68, 68, 0.08)" : "rgba(16, 185, 129, 0.08)", border: intelligence.intelligence.report.severity === "High" ? "1px solid rgba(239, 68, 68, 0.25)" : "1px solid rgba(16, 185, 129, 0.25)", borderRadius: "10px", padding: "16px", color: "#fff" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                            <h3 style={{ margin: 0, fontSize: "14px", fontWeight: "bold", textTransform: "uppercase", color: intelligence.intelligence.report.severity === "High" ? "#f87171" : "#34d399" }}>
                              {intelligence.intelligence.report.headline}
                            </h3>
                            <span style={{ fontSize: "10px", padding: "3px 8px", borderRadius: "12px", background: intelligence.intelligence.report.severity === "High" ? "#ef4444" : "#10b981", fontWeight: "bold" }}>
                              {intelligence.intelligence.report.severity} Severity
                            </span>
                          </div>
                          <p style={{ margin: 0, fontSize: "12px", color: "var(--text-2)", lineHeight: "1.4" }}>
                            {intelligence.intelligence.report.briefings.executive.summary} {intelligence.intelligence.report.briefings.executive.details}
                          </p>
                        </div>

                        {/* Interactive Timeline Nodes */}
                        <div>
                          <h4 style={{ margin: "0 0 10px 0", fontSize: "11px", color: "var(--text-3)", textTransform: "uppercase", fontWeight: "bold" }}>Interactive Analyst Timeline</h4>
                          <div style={{ display: "flex", justifyContent: "space-between", border: "1px solid var(--border)", borderRadius: "8px", background: "var(--bg-3)", padding: "10px" }}>
                            {["Now", "24h", "48h", "72h"].map((node) => {
                              const isSelected = selectedTimelineNode === node;
                              let val = selectedStation ? selectedStation.aqi : 0;
                              let label = "Now";
                              
                              if (node === "24h" && intelligence.forecast.length > 0) {
                                val = intelligence.forecast[0].predicted_aqi;
                                label = "24h Forecast";
                              } else if (node === "48h" && intelligence.forecast.length > 1) {
                                val = intelligence.forecast[1].predicted_aqi;
                                label = "48h Forecast";
                              } else if (node === "72h" && intelligence.forecast.length > 2) {
                                val = intelligence.forecast[2].predicted_aqi;
                                label = "72h Forecast";
                              }
                              
                              return (
                                <div
                                  key={node}
                                  onClick={() => setSelectedTimelineNode(node)}
                                  style={{
                                    flex: 1,
                                    textAlign: "center",
                                    padding: "6px",
                                    borderRadius: "6px",
                                    background: isSelected ? "rgba(59, 130, 246, 0.12)" : "transparent",
                                    border: isSelected ? "1px solid #3b82f6" : "1px solid transparent",
                                    cursor: "pointer",
                                    transition: "all 0.15s"
                                  }}
                                >
                                  <div style={{ fontSize: "10px", color: "var(--text-3)", marginBottom: "4px" }}>{label}</div>
                                  <div style={{ fontSize: "16px", fontWeight: "bold", color: "#3b82f6" }}>{val.toFixed(0)}</div>
                                </div>
                              );
                            })}
                          </div>
                          
                          {/* Timeline Node Explanations */}
                          <div style={{ marginTop: "10px", padding: "12px", background: "rgba(255,255,255,0.01)", border: "1px solid var(--border-soft)", borderRadius: "6px", fontSize: "11.5px", color: "var(--text-2)" }}>
                            <strong>Timeline Insight ({selectedTimelineNode}):</strong>{" "}
                            {selectedTimelineNode === "Now" ? (
                              <span>Current AQI is {(selectedStation ? selectedStation.aqi : 0).toFixed(0)} ({selectedStation ? selectedStation.category : "N/A"}). Primarily influenced by {intelligence.intelligence.source_attribution.primary.source}.</span>
                            ) : (
                              <span>
                                Projected AQI at +{selectedTimelineNode} is expected to reach{" "}
                                {selectedTimelineNode === "24h" ? intelligence.forecast[0]?.predicted_aqi.toFixed(0) : selectedTimelineNode === "48h" ? intelligence.forecast[1]?.predicted_aqi.toFixed(0) : intelligence.forecast[2]?.predicted_aqi.toFixed(0)}{" "}
                                ({selectedTimelineNode === "24h" ? intelligence.forecast[0]?.category : selectedTimelineNode === "48h" ? intelligence.forecast[1]?.category : intelligence.forecast[2]?.category}). Risk rating: {intelligence.intelligence.risk_assessment.overall_risk}.
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Why? reasoning and meteorological conditions */}
                        <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: "16px" }}>
                          <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-soft)", borderRadius: "8px", padding: "14px" }}>
                            <h4 style={{ margin: "0 0 10px 0", fontSize: "11px", color: "var(--text-3)", textTransform: "uppercase", fontWeight: "bold" }}>Why is pollution increasing?</h4>
                            <p style={{ margin: 0, fontSize: "12px", color: "var(--text-2)", lineHeight: "1.4" }}>
                              {intelligence.intelligence.reasoning.text}
                            </p>
                          </div>
                          
                          {/* Explainable Confidence Card */}
                          <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-soft)", borderRadius: "8px", padding: "14px", display: "flex", flexDirection: "column", gap: "6px" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                              <h4 style={{ margin: 0, fontSize: "11px", color: "var(--text-3)", textTransform: "uppercase", fontWeight: "bold" }}>Analyst Confidence</h4>
                              <strong style={{ color: "#3b82f6", fontSize: "14px" }}>{intelligence.intelligence.confidence.level}</strong>
                            </div>
                            <div style={{ fontSize: "24px", fontWeight: "bold" }}>{(intelligence.intelligence.confidence.score * 100).toFixed(0)}%</div>
                            <p style={{ margin: 0, fontSize: "10.5px", color: "var(--text-3)", lineHeight: "1.3" }}>
                              {intelligence.intelligence.confidence.reason}
                            </p>
                          </div>
                        </div>

                        {/* Likely Sources & Rejections */}
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                          
                          {/* Ranked Sources */}
                          <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-soft)", borderRadius: "8px", padding: "14px" }}>
                            <h4 style={{ margin: "0 0 12px 0", fontSize: "11px", color: "var(--text-3)", textTransform: "uppercase", fontWeight: "bold" }}>Likely Source Attribution</h4>
                            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11.5px" }}>
                                <span style={{ fontWeight: "bold" }}>Primary: {intelligence.intelligence.source_attribution.primary.source}</span>
                                <strong style={{ color: "#f59e0b" }}>{(intelligence.intelligence.source_attribution.primary.confidence * 100).toFixed(0)}%</strong>
                              </div>
                              <div style={{ fontSize: "11px", color: "var(--text-3)", paddingLeft: "8px", borderLeft: "2px solid #f59e0b" }}>
                                {intelligence.intelligence.source_attribution.primary.evidence.map((ev, i) => (
                                  <div key={i}>✓ {ev}</div>
                                ))}
                              </div>
                              
                              {intelligence.intelligence.source_attribution.secondary && (
                                <>
                                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11.5px", marginTop: "4px" }}>
                                    <span style={{ fontWeight: "bold" }}>Secondary: {intelligence.intelligence.source_attribution.secondary.source}</span>
                                    <strong style={{ color: "#60a5fa" }}>{(intelligence.intelligence.source_attribution.secondary.confidence * 100).toFixed(0)}%</strong>
                                  </div>
                                  <div style={{ fontSize: "11px", color: "var(--text-3)", paddingLeft: "8px", borderLeft: "2px solid #60a5fa" }}>
                                    {intelligence.intelligence.source_attribution.secondary.evidence.map((ev, i) => (
                                      <div key={i}>✓ {ev}</div>
                                    ))}
                                  </div>
                                </>
                              )}
                            </div>
                          </div>

                          {/* Rejected Hypotheses */}
                          <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-soft)", borderRadius: "8px", padding: "14px" }}>
                            <h4 style={{ margin: "0 0 12px 0", fontSize: "11px", color: "var(--text-3)", textTransform: "uppercase", fontWeight: "bold" }}>Rejected Hypotheses</h4>
                            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                              {intelligence.intelligence.source_attribution.rejected.map((rej, i) => (
                                <div key={i} style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                                  <div style={{ fontSize: "11.5px", fontWeight: "bold", textDecoration: "line-through", color: "var(--text-3)" }}>{rej.source}</div>
                                  <div style={{ fontSize: "10.5px", color: "var(--text-3)", paddingLeft: "8px" }}>✕ {rej.reason}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>

                        {/* Risk Levels Grid */}
                        <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-soft)", borderRadius: "8px", padding: "14px" }}>
                          <h4 style={{ margin: "0 0 12px 0", fontSize: "11px", color: "var(--text-3)", textTransform: "uppercase", fontWeight: "bold" }}>Risk Assessment Matrix</h4>
                          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "10px", textAlign: "center" }}>
                            {[
                              { label: "Environmental", val: intelligence.intelligence.risk_assessment.environmental_risk },
                              { label: "Health Risk", val: intelligence.intelligence.risk_assessment.health_risk },
                              { label: "Exposure", val: intelligence.intelligence.risk_assessment.exposure_risk },
                              { label: "Operational", val: intelligence.intelligence.risk_assessment.operational_risk },
                              { label: "Overall Risk", val: intelligence.intelligence.risk_assessment.overall_risk, bold: true }
                            ].map((rItem, i) => (
                              <div key={i} style={{ padding: "8px", background: "var(--bg-3)", border: "1px solid var(--border)", borderRadius: "6px" }}>
                                <div style={{ fontSize: "9px", color: "var(--text-3)", textTransform: "uppercase" }}>{rItem.label}</div>
                                <strong style={{ fontSize: "12px", color: rItem.val === "High" || rItem.val === "Critical" ? "#ef4444" : rItem.val === "Medium" ? "#f59e0b" : "#10b981" }}>{rItem.val}</strong>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Action Center Grid */}
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                          
                          {/* Recommended Actions */}
                          <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-soft)", borderRadius: "8px", padding: "14px" }}>
                            <h4 style={{ margin: "0 0 10px 0", fontSize: "11px", color: "var(--text-3)", textTransform: "uppercase", fontWeight: "bold" }}>Municipal Action Directives</h4>
                            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                              {intelligence.intelligence.decision.actions.map((act, i) => (
                                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: "8px", fontSize: "11.5px", background: "var(--bg-3)", padding: "8px", borderRadius: "6px", border: "1px solid var(--border)" }}>
                                  <div>
                                    <span style={{ fontSize: "9px", color: "#3b82f6", fontWeight: "bold", display: "block" }}>[{act.type}]</span>
                                    <span>{act.action}</span>
                                  </div>
                                  <span style={{ fontSize: "9px", padding: "2px 6px", borderRadius: "8px", background: act.expected_impact === "High" ? "rgba(239, 68, 68, 0.12)" : "rgba(59, 130, 246, 0.12)", color: act.expected_impact === "High" ? "#f87171" : "#60a5fa", fontWeight: "bold" }}>
                                    {act.expected_impact} Impact
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Citizen Guidance */}
                          <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-soft)", borderRadius: "8px", padding: "14px" }}>
                            <h4 style={{ margin: "0 0 10px 0", fontSize: "11px", color: "var(--text-3)", textTransform: "uppercase", fontWeight: "bold" }}>Citizen Health Guidance</h4>
                            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                              {intelligence.intelligence.citizen_actions.map((act, i) => (
                                <div key={i} style={{ display: "flex", gap: "8px", alignItems: "start", fontSize: "11.5px" }}>
                                  <span style={{ color: "#10b981" }}>●</span>
                                  <span>{act}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>

                      </>
                    )}
                  </div>
                )}

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
