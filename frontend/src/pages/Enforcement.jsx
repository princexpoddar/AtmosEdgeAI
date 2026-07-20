import { useState, useEffect } from "react";
import { useEnforcement } from "@/hooks/useEnforcement";
import { getComparativeAnalytics, getEnforcementDashboard } from "@/services/api";
import Spinner from "@/components/ui/Spinner";
import Navbar from "@/components/layout/Navbar";

export default function Enforcement() {
  const { data: globalData, loading, error, refetch } = useEnforcement();
  const [selectedStationId, setSelectedStationId] = useState("");
  const [stationData, setStationData] = useState(null);
  const [filterLoading, setFilterLoading] = useState(false);
  const [comparativeData, setComparativeData] = useState(null);
  const [activeTab, setActiveTab] = useState("dossier"); // "dossier" | "comparative"
  const [selectedNode, setSelectedNode] = useState("Now");

  // Fetch comparative analytics on mount
  useEffect(() => {
    getComparativeAnalytics()
      .then(setComparativeData)
      .catch((err) => console.error("Comparative analytics error:", err));
  }, []);

  // Fetch station-specific enforcement if selected
  useEffect(() => {
    if (!selectedStationId) {
      setStationData(null);
      return;
    }
    setFilterLoading(true);
    getEnforcementDashboard(selectedStationId)
      .then((res) => {
        setStationData(res);
        setFilterLoading(false);
      })
      .catch((err) => {
        console.error("Filter enforcement error:", err);
        setFilterLoading(false);
      });
  }, [selectedStationId]);

  /* ── Loading state ─────────────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="app-root">
        <Navbar />
        <div className="enforcement-page">
          <div className="enforcement-loading-shell">
            <Spinner size="lg" />
            <span className="enforcement-loading-text">
              Resolving Hyperlocal Station Intelligence & Command Telemetry…
            </span>
          </div>
        </div>
      </div>
    );
  }

  /* ── Error state ───────────────────────────────────────────────────── */
  if (error) {
    return (
      <div className="app-root">
        <Navbar />
        <div className="enforcement-page">
          <div className="enforcement-error-card">
            <div className="enforcement-error-icon">⚠️</div>
            <h3 className="enforcement-error-title">Unable to load Municipal Command Center</h3>
            <p className="enforcement-error-msg">{error}</p>
            {refetch && (
              <button className="btn btn-secondary" onClick={refetch} style={{ marginTop: 12 }}>
                Retry Telemetry Fetch
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  const activeData = stationData || globalData;
  if (!activeData) return null;

  const {
    executive_summary: es = {},
    priority_rankings = [],
    hotspots = { deteriorating: [], highest_priority: [], improving: [], stable: [] },
    resource_allocation = [],
    inspection_recommendations = [],
  } = activeData;

  const isCritical = (es.critical_count ?? 0) > 0;
  const selectedStationProfile = priority_rankings.find((s) => s.station_id === selectedStationId) || priority_rankings[0];

  return (
    <div className="app-root">
      <Navbar />
      <div className="enforcement-page">

        {/* Top Command Bar & Station Filter */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, flexWrap: "wrap", gap: 12 }}>
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: "var(--text-1)" }}>
              🏛️ Municipal Enforcement Command Center
            </h2>
            <p style={{ fontSize: 13, color: "var(--text-2)", margin: "2px 0 0 0" }}>
              Hyperlocal Evidence-Backed Directives, Station Land-Use Dossiers & Multi-City Benchmarks
            </p>
          </div>

          {/* Controls: Station Filter & View Switcher */}
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <select
              value={selectedStationId}
              onChange={(e) => setSelectedStationId(e.target.value)}
              style={{
                background: "rgba(15, 23, 42, 0.8)",
                border: "1px solid rgba(255, 255, 255, 0.15)",
                color: "#f8fafc",
                padding: "8px 14px",
                borderRadius: 8,
                fontSize: 13,
                outline: "none",
                cursor: "pointer"
              }}
            >
              <option value="">🌐 All Monitoring Stations (City Overview)</option>
              {globalData?.priority_rankings?.map((st) => (
                <option key={st.station_id} value={st.station_id}>
                  📍 {st.station_name} ({st.city}) — [{st.priority}]
                </option>
              ))}
            </select>

            <div style={{ display: "flex", background: "rgba(255,255,255,0.06)", padding: 3, borderRadius: 8 }}>
              <button
                onClick={() => setActiveTab("dossier")}
                className={`btn btn-xs ${activeTab === "dossier" ? "btn-primary" : "btn-ghost"}`}
                style={{ fontSize: 12, padding: "6px 12px" }}
              >
                🎯 Station Directives
              </button>
              <button
                onClick={() => setActiveTab("comparative")}
                className={`btn btn-xs ${activeTab === "comparative" ? "btn-primary" : "btn-ghost"}`}
                style={{ fontSize: 12, padding: "6px 12px" }}
              >
                📊 Multi-City Benchmarks
              </button>
            </div>
          </div>
        </div>

        {filterLoading && (
          <div style={{ padding: 12, background: "rgba(59, 130, 246, 0.1)", borderRadius: 8, color: "#60a5fa", fontSize: 13, marginBottom: 16 }}>
            ⚡ Refreshing station dossier for selected station...
          </div>
        )}

        {/* Tab 1: Station Directives & Command Dossiers */}
        {activeTab === "dossier" && (
          <>
            {/* Executive Summary Banner */}
            <div className={`enforcement-summary-banner ${isCritical ? "critical" : "normal"}`}>
              <div className="enforcement-summary-row">
                <h3 className={`enforcement-headline ${isCritical ? "critical" : "normal"}`}>
                  {es.headline ?? "Municipal Command Center"}
                </h3>
                <span className={`enforcement-status-badge ${isCritical ? "critical" : "normal"}`}>
                  {isCritical ? "ACTION REQUIRED" : "NORMAL OPERATIONS"}
                </span>
              </div>
              <p className="enforcement-summary-text">
                <strong>Summary of Alerts:</strong> Evaluated {es.total_evaluated ?? 0} regional wards.{" "}
                {es.critical_count ?? 0} wards are in Critical priority and {es.high_count ?? 0} are in High priority.
                <br />
                <strong>Statutory Order:</strong> {es.direct_orders ?? "No active directives."}
              </p>
            </div>

            {/* Station Land-Use & Receptor Dossier Card (if station selected or top station) */}
            {selectedStationProfile && (
              <div className="card" style={{ padding: "16px", marginBottom: "16px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
                  <div>
                    <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.5, color: "var(--accent)" }}>
                      STATION LAND-USE DOSSIER & CATCHMENT RECEPTORS
                    </span>
                    <h3 style={{ fontSize: 17, fontWeight: 700, margin: "4px 0", color: "var(--text-1)" }}>
                      📍 {selectedStationProfile.station_name} ({selectedStationProfile.city})
                    </h3>
                    <div style={{ display: "flex", gap: 8, marginTop: 8, flexWrap: "wrap" }}>
                      <span className="badge badge-outline" style={{ borderColor: "var(--accent)", color: "var(--accent)" }}>
                        🏢 {selectedStationProfile.land_use || "Mixed Zone"}
                      </span>
                      <span className="badge badge-outline" style={{ borderColor: "var(--purple)", color: "var(--purple)" }}>
                        ⚖️ {selectedStationProfile.spcb_authority || "SPCB"}
                      </span>
                      <span className="badge badge-outline" style={{ borderColor: "var(--yellow)", color: "var(--yellow)" }}>
                        🔥 Priority: {selectedStationProfile.priority} ({selectedStationProfile.score} pts)
                      </span>
                    </div>
                  </div>

                  {/* Receptor Summary Pills */}
                  {selectedStationProfile.receptors && (
                    <div style={{ display: "flex", gap: 16, alignItems: "center", background: "var(--bg-3)", padding: "10px 16px", borderRadius: "var(--radius-md)", border: "1px solid var(--border)" }}>
                      <div style={{ textAlign: "center" }}>
                        <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>{selectedStationProfile.receptors.schools || 0}</div>
                        <div style={{ fontSize: 10, color: "var(--text-3)", textTransform: "uppercase", fontWeight: 600 }}>🏫 Schools</div>
                      </div>
                      <div style={{ width: 1, height: 24, background: "var(--border)" }} />
                      <div style={{ textAlign: "center" }}>
                        <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>{selectedStationProfile.receptors.hospitals || 0}</div>
                        <div style={{ fontSize: 10, color: "var(--text-3)", textTransform: "uppercase", fontWeight: 600 }}>🏥 Hospitals</div>
                      </div>
                      <div style={{ width: 1, height: 24, background: "var(--border)" }} />
                      <div style={{ textAlign: "center" }}>
                        <div style={{ fontSize: 15, fontWeight: 700, color: "var(--red)" }}>{selectedStationProfile.receptors.vulnerability_level || "Medium"}</div>
                        <div style={{ fontSize: 10, color: "var(--text-3)", textTransform: "uppercase", fontWeight: 600 }}>Vulnerability</div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Local Hotspots */}
                {selectedStationProfile.registered_hotspots?.length > 0 && (
                  <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px dashed var(--border)", fontSize: 12, color: "var(--text-2)" }}>
                    <strong>🎯 Registered Catchment Hotspots:</strong>{" "}
                    {selectedStationProfile.registered_hotspots.map((h, i) => (
                      <span key={i} style={{ background: "var(--bg-3)", border: "1px solid var(--border)", padding: "2px 8px", borderRadius: 4, marginRight: 6, fontSize: 11, color: "var(--text-1)" }}>
                        • {h}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="enforcement-body-grid">
              {/* Left Column */}
              <div className="enforcement-left-col">
                {/* Priority Wards Queue */}
                <div className="card" style={{ padding: "16px" }}>
                  <h4 className="card-title">Priority Wards &amp; Stations Queue</h4>
                  {priority_rankings.length === 0 ? (
                    <p style={{ color: "var(--text-2)", fontSize: 13 }}>No priority wards at this time.</p>
                  ) : (
                    <div className="priority-ward-list">
                      {priority_rankings.map((st) => {
                        const pClass =
                          st.priority === "Critical" ? "critical" :
                          st.priority === "High" ? "high" : "medium";
                        const isSel = selectedStationId === st.station_id;
                        return (
                          <div
                            key={st.station_id}
                            className="priority-ward-row"
                            onClick={() => setSelectedStationId(st.station_id)}
                            style={{
                              cursor: "pointer",
                              borderLeft: isSel ? "3px solid #3b82f6" : "none",
                              background: isSel ? "rgba(59, 130, 246, 0.12)" : undefined,
                              padding: "8px 10px",
                              borderRadius: 6
                            }}
                          >
                            <div>
                              <span className="priority-ward-name">{st.station_name}</span>
                              <span className="priority-ward-delta">
                                {st.land_use || st.city} | Δ 24h:{" "}
                                {st.trend_delta > 0 ? `+${st.trend_delta.toFixed(1)}` : st.trend_delta.toFixed(1)} µg/m³
                              </span>
                            </div>
                            <div style={{ textAlign: "right" }}>
                              <span className={`priority-badge ${pClass}`}>{st.priority}</span>
                              <span className="priority-score">Score: {st.score.toFixed(0)}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Hotspot Classifications */}
                <div className="card" style={{ padding: "16px" }}>
                  <h4 className="card-title">Hotspot Classifications</h4>
                  <div className="hotspot-list">
                    <div className="hotspot-row">
                      <span>🔥 Deteriorating</span>
                      <strong>{hotspots.deteriorating?.[0]?.station_name ?? "None"}</strong>
                    </div>
                    <div className="hotspot-row">
                      <span>📈 Highest Priority</span>
                      <strong>{hotspots.highest_priority?.[0]?.station_name ?? "None"}</strong>
                    </div>
                    <div className="hotspot-row">
                      <span>🍃 Improving</span>
                      <strong>{hotspots.improving?.[0]?.station_name ?? "None"}</strong>
                    </div>
                    <div className="hotspot-row">
                      <span>⚖ Stable</span>
                      <strong>{hotspots.stable?.[0]?.station_name ?? "None"}</strong>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column */}
              <div className="enforcement-right-col">
                {/* Inspection Queue */}
                <div className="card" style={{ padding: "16px" }}>
                  <h4 className="card-title">Audit &amp; Inspection Dispatch Queue</h4>
                  {inspection_recommendations.length === 0 ? (
                    <p style={{ color: "var(--text-2)", fontSize: 13 }}>No inspections queued.</p>
                  ) : (
                    <div className="inspection-list">
                      {inspection_recommendations.map((insp, i) => (
                        <div key={i} className="inspection-row" style={{ flexDirection: "column", gap: 6 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", width: "100%" }}>
                            <span className="inspection-type">🔍 {insp.inspection_type}</span>
                            <span className="urgency-badge">{insp.urgency}</span>
                          </div>
                          <p style={{ fontSize: 12, color: "#cbd5e1", margin: 0, lineHeight: 1.4 }}>
                            {insp.reason}
                          </p>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
                            <span>📍 Hotspot: {insp.target_hotspot || insp.target_station}</span>
                            <span style={{ color: "#34d399" }}>Expected: {insp.expected_impact}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Resource Allocations */}
                <div className="card" style={{ padding: "16px" }}>
                  <h4 className="card-title">Targeted Asset Deployments &amp; Hardware</h4>
                  {resource_allocation.length === 0 ? (
                    <p style={{ color: "var(--text-2)", fontSize: 13 }}>No resources allocated.</p>
                  ) : (
                    <div className="resource-grid">
                      {resource_allocation.map((res, i) => {
                        const icon = res.resource?.includes("Sprinkler") ? "⛟"
                          : res.resource?.includes("Van") ? "🚐"
                          : res.resource?.includes("Gun") ? "🔫"
                          : "👮";
                        return (
                          <div key={i} className="resource-card">
                            <div className="resource-icon">{icon}</div>
                            <strong className="resource-name">
                              {res.quantity}x {res.resource}
                            </strong>
                            <span className="resource-target" style={{ fontSize: 11 }}>
                              Target: {res.target_hotspot || res.target_station}
                            </span>
                            {res.reason && (
                              <p style={{ fontSize: 11, color: "#94a3b8", marginTop: 4, lineHeight: 1.3 }}>
                                {res.reason}
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Interactive Command Timeline */}
                <div className="card" style={{ padding: "16px" }}>
                  <h4 className="timeline-section-title" style={{ margin: "0 0 12px 0" }}>Interactive Intervention Timeline</h4>
                  <div className="timeline-bar">
                    {["Now", "6h", "24h", "48h", "72h"].map((node) => {
                      const baseAqi = selectedStationProfile?.current_aqi ?? 80;
                      let val = baseAqi;
                      if (node === "24h") val = baseAqi * 1.1;
                      else if (node === "48h") val = baseAqi * 1.15;
                      else if (node === "72h") val = baseAqi * 1.12;
                      return (
                        <div
                          key={node}
                          className={`timeline-node${selectedNode === node ? " active" : ""}`}
                          onClick={() => setSelectedNode(node)}
                          role="button"
                          tabIndex={0}
                        >
                          <div className="timeline-node-label">{node}</div>
                          <div className="timeline-node-value">{val.toFixed(0)} AQI</div>
                        </div>
                      );
                    })}
                  </div>
                  <div className="timeline-insight" style={{ marginTop: 12 }}>
                    <strong>Command Insight ({selectedNode}):</strong>{" "}
                    Intervention Priority:{" "}
                    <span className="timeline-insight-critical">
                      {isCritical ? "Critical" : "Moderate"}
                    </span>
                    . Target Station: {selectedStationProfile?.station_name || "All Wards"}.
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Tab 2: Multi-City Comparative Benchmarks */}
        {activeTab === "comparative" && comparativeData && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Comparative Highlights */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
              <div className="card" style={{ padding: 16, background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)" }}>
                <span style={{ fontSize: 12, color: "#34d399", fontWeight: 700 }}>🏆 BEST PERFORMING CITY</span>
                <h3 style={{ fontSize: 22, fontWeight: 700, color: "#f8fafc", margin: "4px 0" }}>
                  {comparativeData.best_performing_city}
                </h3>
                <p style={{ fontSize: 12, color: "#94a3b8", margin: 0 }}>
                  Highest overall NCAP air quality compliance score across all monitoring stations.
                </p>
              </div>

              <div className="card" style={{ padding: 16, background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)" }}>
                <span style={{ fontSize: 12, color: "#f87171", fontWeight: 700 }}>⚠️ HIGHEST RISK URBAN CENTER</span>
                <h3 style={{ fontSize: 22, fontWeight: 700, color: "#f8fafc", margin: "4px 0" }}>
                  {comparativeData.highest_risk_city}
                </h3>
                <p style={{ fontSize: 12, color: "#94a3b8", margin: 0 }}>
                  Elevated particulate density requiring priority GRAP / NCAP intervention dispatches.
                </p>
              </div>
            </div>

            {/* City Rankings Table */}
            <div className="card" style={{ padding: 16 }}>
              <h4 className="card-title" style={{ marginBottom: 12 }}>Urban Center Air Quality &amp; NCAP Target Benchmark Table</h4>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, color: "#cbd5e1" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", textAlign: "left" }}>
                      <th style={{ padding: "10px" }}>City / State</th>
                      <th style={{ padding: "10px" }}>Stations</th>
                      <th style={{ padding: "10px" }}>Avg AQI</th>
                      <th style={{ padding: "10px" }}>PM2.5 (µg/m³)</th>
                      <th style={{ padding: "10px" }}>NCAP Target %</th>
                      <th style={{ padding: "10px" }}>Compliance Score</th>
                      <th style={{ padding: "10px" }}>Primary Local Threat</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparativeData.city_rankings?.map((c, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                        <td style={{ padding: "10px", fontWeight: 600, color: "#f8fafc" }}>{c.city} ({c.state})</td>
                        <td style={{ padding: "10px" }}>{c.station_count}</td>
                        <td style={{ padding: "10px" }}>
                          <span className="badge badge-outline" style={{ borderColor: c.avg_aqi > 200 ? "#ef4444" : "#38bdf8" }}>
                            {c.avg_aqi} AQI
                          </span>
                        </td>
                        <td style={{ padding: "10px" }}>{c.avg_pm25}</td>
                        <td style={{ padding: "10px" }}>{c.ncap_target_pct}%</td>
                        <td style={{ padding: "10px", fontWeight: 700, color: "#34d399" }}>{c.compliance_score} / 100</td>
                        <td style={{ padding: "10px", fontSize: 12, color: "#94a3b8" }}>{c.primary_threat}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Cross-City Transferable Insights */}
            <div className="card" style={{ padding: 16 }}>
              <h4 className="card-title">💡 What Worked in Comparable Cities (Transferable Policy Insights)</h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 14, marginTop: 12 }}>
                {comparativeData.cross_city_insights?.map((ins, i) => (
                  <div key={i} style={{ background: "rgba(15, 23, 42, 0.6)", padding: 14, borderRadius: 8, border: "1px solid rgba(255,255,255,0.08)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                      <span style={{ fontSize: 12, fontWeight: 700, color: "#60a5fa" }}>
                        {ins.source_city} ➔ {ins.target_city}
                      </span>
                      <span style={{ fontSize: 11, color: "#34d399" }}>Impact: {ins.measured_impact}</span>
                    </div>
                    <strong style={{ fontSize: 14, color: "#f8fafc", display: "block", marginBottom: 4 }}>
                      {ins.intervention}
                    </strong>
                    <p style={{ fontSize: 12, color: "#cbd5e1", margin: 0, lineHeight: 1.4 }}>
                      {ins.recommendation}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
