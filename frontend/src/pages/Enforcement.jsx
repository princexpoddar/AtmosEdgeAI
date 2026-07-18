import { useState } from "react";
import { useEnforcement } from "@/hooks/useEnforcement";
import Spinner from "@/components/ui/Spinner";
import Banner from "@/components/ui/Banner";
import Navbar from "@/components/layout/Navbar";

export default function Enforcement() {
  const { data, loading, error } = useEnforcement();
  const [selectedNode, setSelectedNode] = useState("Now");

  if (loading) {
    return (
      <div className="app-root">
        <Navbar />
        <div className="enforcement-page">
          <div className="loader-overlay" style={{ position: "relative", minHeight: "400px", background: "transparent" }}>
            <Spinner size="lg" />
            <span className="loader-text">Resolving Municipal Command Center telemetry…</span>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app-root">
        <Navbar />
        <div className="enforcement-page">
          <Banner variant="error">⚠ {error}</Banner>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="app-root">
        <Navbar />
      </div>
    );
  }

  const { executive_summary: es, priority_rankings, hotspots, intervention_recommendations, resource_allocation, inspection_recommendations } = data;
  const isCritical = es.critical_count > 0;
  const topWard = priority_rankings[0];

  return (
    <div className="app-root">
      <Navbar />
      <div className="enforcement-page">
      {/* Executive Summary Banner */}
      <div className={`enforcement-summary-banner ${isCritical ? "critical" : "normal"}`}>
        <div className="enforcement-summary-row">
          <h3 className={`enforcement-headline ${isCritical ? "critical" : "normal"}`}>{es.headline}</h3>
          <span className={`enforcement-status-badge ${isCritical ? "critical" : "normal"}`}>
            {isCritical ? "ACTION REQUIRED" : "NORMAL OPERATIONS"}
          </span>
        </div>
        <p className="enforcement-summary-text">
          <strong>Summary of Alerts:</strong> Evaluated {es.total_evaluated} regional wards.{" "}
          {es.critical_count} wards are in Critical priority and {es.high_count} are in High priority.
          <br />
          <strong>Directives:</strong> {es.direct_orders}
        </p>
      </div>

      <div className="enforcement-body-grid">
        {/* Left Column */}
        <div className="enforcement-left-col">
          {/* Priority Wards Queue */}
          <div className="card" style={{ padding: "16px" }}>
            <h4 className="card-title">Priority Wards Queue</h4>
            <div className="priority-ward-list">
              {priority_rankings.map((st, i) => {
                const pClass = st.priority === "Critical" ? "critical" : st.priority === "High" ? "high" : "medium";
                return (
                  <div key={i} className="priority-ward-row">
                    <div>
                      <span className="priority-ward-name">{st.station_name}</span>
                      <span className="priority-ward-delta">
                        Trend Delta (24h): {st.trend_delta > 0 ? `+${st.trend_delta.toFixed(1)}` : st.trend_delta.toFixed(1)} µg/m³
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
          </div>

          {/* Hotspot Classifications */}
          <div className="card" style={{ padding: "16px" }}>
            <h4 className="card-title">Hotspot Classifications</h4>
            <div className="hotspot-list">
              <div className="hotspot-row">
                <span>🔥 Deteriorating (Worsening Delta)</span>
                <strong>{hotspots.deteriorating[0]?.station_name || "None"}</strong>
              </div>
              <div className="hotspot-row">
                <span>📈 Highest Priority Wards</span>
                <strong>{hotspots.highest_priority[0]?.station_name || "None"}</strong>
              </div>
              <div className="hotspot-row">
                <span>🍃 Improving (Clearing up)</span>
                <strong>{hotspots.improving[0]?.station_name || "None"}</strong>
              </div>
              <div className="hotspot-row">
                <span>⚖ Stable Wards</span>
                <strong>{hotspots.stable[0]?.station_name || "None"}</strong>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="enforcement-right-col">
          {/* Intervention Directives */}
          <div className="card" style={{ padding: "16px" }}>
            <h4 className="card-title">Recommended Intervention Directives</h4>
            <div className="intervention-grid">
              {intervention_recommendations.slice(0, 4).map((act, i) => (
                <div key={i} className="intervention-card">
                  <span className="intervention-category">{act.category} ({act.target_station.split(",")[0]})</span>
                  <p className="intervention-action">{act.action}</p>
                  <div className="intervention-meta">
                    <span>Difficulty: {act.implementation_difficulty}</span>
                    <span className="intervention-impact">Impact: {act.expected_impact}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Resource Allocations */}
          <div className="card" style={{ padding: "16px" }}>
            <h4 className="card-title">Resource Allocation &amp; Deployments</h4>
            <div className="resource-grid">
              {resource_allocation.slice(0, 6).map((res, i) => {
                const icon = res.resource.includes("Sprinkler") ? "⛟" : res.resource.includes("Van") ? "🚐" : "👮";
                return (
                  <div key={i} className="resource-card">
                    <div className="resource-icon">{icon}</div>
                    <strong className="resource-name">{res.quantity}x {res.resource}</strong>
                    <span className="resource-target">Target: {res.target_station.split(",")[0]}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Inspection Queue */}
          <div className="card" style={{ padding: "16px" }}>
            <h4 className="card-title">Inspection Dispatch Queue</h4>
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
          </div>

          {/* Timeline */}
          <div>
            <h4 className="timeline-section-title">Interactive Command Timeline</h4>
            <div className="timeline-bar">
              {["Now", "6h", "24h", "48h", "72h"].map((node) => {
                let val = topWard ? topWard.current_aqi : 80;
                if (node === "24h") val *= 1.1;
                else if (node === "48h") val *= 1.15;
                else if (node === "72h") val *= 1.12;
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
              Intervention Priority: <span className="timeline-insight-critical">Critical</span>.{" "}
              Deployments scheduled: Water sprinklers (Peenya Wards), Factory boiler log review patrols, and truck limits coordination.
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  );
}
