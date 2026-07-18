import { useState } from "react";
import { useEnforcement } from "@/hooks/useEnforcement";
import Spinner from "@/components/ui/Spinner";
import Navbar from "@/components/layout/Navbar";

export default function Enforcement() {
  const { data, loading, error, refetch } = useEnforcement();
  const [selectedNode, setSelectedNode] = useState("Now");

  /* ── Loading state ─────────────────────────────────────────────────── */
  if (loading) {
    return (
      <div className="app-root">
        <Navbar />
        <div className="enforcement-page">
          <div className="enforcement-loading-shell">
            <Spinner size="lg" />
            <span className="enforcement-loading-text">
              Resolving Municipal Command Center telemetry…
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
                Retry
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  /* ── No data (shouldn't happen, but guard anyway) ──────────────────── */
  if (!data) {
    return (
      <div className="app-root">
        <Navbar />
        <div className="enforcement-page">
          <div className="enforcement-error-card">
            <div className="enforcement-error-icon">📭</div>
            <h3 className="enforcement-error-title">No Command Center Data</h3>
            <p className="enforcement-error-msg">No enforcement data is currently available. Try triggering a data sync from the Dashboard.</p>
          </div>
        </div>
      </div>
    );
  }

  /* ── Destructure safely ─────────────────────────────────────────────── */
  const {
    executive_summary: es = {},
    priority_rankings = [],
    hotspots = { deteriorating: [], highest_priority: [], improving: [], stable: [] },
    intervention_recommendations = [],
    resource_allocation = [],
    inspection_recommendations = [],
  } = data;

  const isCritical = (es.critical_count ?? 0) > 0;
  const topWard = priority_rankings[0] ?? null;

  /* ── Full render ────────────────────────────────────────────────────── */
  return (
    <div className="app-root">
      <Navbar />
      <div className="enforcement-page">

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
            <strong>Directives:</strong> {es.direct_orders ?? "No active directives."}
          </p>
        </div>

        <div className="enforcement-body-grid">
          {/* Left Column */}
          <div className="enforcement-left-col">

            {/* Priority Wards Queue */}
            <div className="card" style={{ padding: "16px" }}>
              <h4 className="card-title">Priority Wards Queue</h4>
              {priority_rankings.length === 0 ? (
                <p style={{ color: "var(--text-2)", fontSize: 13 }}>No priority wards at this time.</p>
              ) : (
                <div className="priority-ward-list">
                  {priority_rankings.map((st, i) => {
                    const pClass =
                      st.priority === "Critical" ? "critical" :
                      st.priority === "High" ? "high" : "medium";
                    return (
                      <div key={i} className="priority-ward-row">
                        <div>
                          <span className="priority-ward-name">{st.station_name}</span>
                          <span className="priority-ward-delta">
                            Trend Δ 24h:{" "}
                            {st.trend_delta > 0
                              ? `+${st.trend_delta.toFixed(1)}`
                              : st.trend_delta.toFixed(1)}{" "}
                            µg/m³
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

            {/* Intervention Directives */}
            <div className="card" style={{ padding: "16px" }}>
              <h4 className="card-title">Recommended Intervention Directives</h4>
              {intervention_recommendations.length === 0 ? (
                <p style={{ color: "var(--text-2)", fontSize: 13 }}>No interventions currently recommended.</p>
              ) : (
                <div className="intervention-grid">
                  {intervention_recommendations.slice(0, 4).map((act, i) => (
                    <div key={i} className="intervention-card">
                      <span className="intervention-category">
                        {act.category} ({(act.target_station ?? "").split(",")[0]})
                      </span>
                      <p className="intervention-action">{act.action}</p>
                      <div className="intervention-meta">
                        <span>Difficulty: {act.implementation_difficulty}</span>
                        <span className="intervention-impact">Impact: {act.expected_impact}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Resource Allocations */}
            <div className="card" style={{ padding: "16px" }}>
              <h4 className="card-title">Resource Allocation &amp; Deployments</h4>
              {resource_allocation.length === 0 ? (
                <p style={{ color: "var(--text-2)", fontSize: 13 }}>No resources allocated.</p>
              ) : (
                <div className="resource-grid">
                  {resource_allocation.slice(0, 6).map((res, i) => {
                    const icon = res.resource?.includes("Sprinkler") ? "⛟"
                      : res.resource?.includes("Van") ? "🚐"
                      : "👮";
                    return (
                      <div key={i} className="resource-card">
                        <div className="resource-icon">{icon}</div>
                        <strong className="resource-name">
                          {res.quantity}x {res.resource}
                        </strong>
                        <span className="resource-target">
                          Target: {(res.target_station ?? "").split(",")[0]}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Inspection Queue */}
            <div className="card" style={{ padding: "16px" }}>
              <h4 className="card-title">Inspection Dispatch Queue</h4>
              {inspection_recommendations.length === 0 ? (
                <p style={{ color: "var(--text-2)", fontSize: 13 }}>No inspections queued.</p>
              ) : (
                <div className="inspection-list">
                  {inspection_recommendations.slice(0, 3).map((insp, i) => (
                    <div key={i} className="inspection-row">
                      <div>
                        <span className="inspection-type">{insp.inspection_type}</span>
                        <span className="inspection-reason">{insp.reason}</span>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <span className="urgency-badge">{insp.urgency}</span>
                        <span className="inspection-duration">Est: {insp.estimated_duration}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Interactive Timeline */}
            <div>
              <h4 className="timeline-section-title">Interactive Command Timeline</h4>
              <div className="timeline-bar">
                {["Now", "6h", "24h", "48h", "72h"].map((node) => {
                  const baseAqi = topWard?.current_aqi ?? 80;
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
                      onKeyDown={(e) => e.key === "Enter" && setSelectedNode(node)}
                    >
                      <div className="timeline-node-label">{node}</div>
                      <div className="timeline-node-value">{val.toFixed(0)} AQI</div>
                    </div>
                  );
                })}
              </div>
              <div className="timeline-insight">
                <strong>Command Insight ({selectedNode}):</strong>{" "}
                Intervention Priority:{" "}
                <span className="timeline-insight-critical">
                  {isCritical ? "Critical" : "Moderate"}
                </span>
                .{" "}
                {topWard
                  ? `Top ward: ${topWard.station_name} (AQI ${topWard.current_aqi.toFixed(0)}).`
                  : "All wards within normal parameters."}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
