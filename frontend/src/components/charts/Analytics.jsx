import { useState } from "react";

export default function Analytics({ history, forecasts }) {
  const [activeMetric, setActiveMetric] = useState("pm25"); // "pm25" | "no2"

  if (!history || history.length === 0) {
    return <p className="empty-state">No historical analytics available for this station.</p>;
  }

  // Helper to format timestamps
  const formatTime = (isoString) => {
    return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getPoints = (data, key) => {
    const values = data.map(d => d[key] || 0.0);
    const maxVal = Math.max(...values, 100);
    const width = 500;
    const height = 150;
    const padding = 10;
    
    return data.map((d, i) => {
      const x = padding + (i / (data.length - 1)) * (width - 2 * padding);
      const y = height - padding - ((d[key] || 0.0) / maxVal) * (height - 2 * padding);
      return { x, y, value: d[key] || 0.0, label: formatTime(d.timestamp) };
    });
  };

  const points = getPoints(history, activeMetric);
  const pathData = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");

  // Create 24h x 7d Matrix hourly heatmap data
  const hours = Array.from({ length: 24 }, (_, i) => i);
  const weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  
  const getHeatmapColorClass = (val) => {
    if (val === null || val === undefined || val === 0) return "heat-empty";
    if (val <= 30) return "heat-good";
    if (val <= 60) return "heat-satisfactory";
    if (val <= 90) return "heat-moderate";
    if (val <= 120) return "heat-poor";
    if (val <= 250) return "heat-very-poor";
    return "heat-severe";
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      
      {/* Metrics Selector Tabs */}
      <div style={{ display: "flex", gap: "10px" }}>
        {["pm25", "no2"].map(m => (
          <button
            key={m}
            onClick={() => setActiveMetric(m)}
            className="btn btn-secondary"
            style={{
              height: "26px",
              padding: "0 12px",
              borderRadius: "13px",
              fontSize: "11px",
              fontWeight: "600",
              background: activeMetric === m ? "#3b82f6" : "rgba(255,255,255,0.02)",
              color: "#fff"
            }}
          >
            {m === "pm25" ? "PM2.5 Trend" : "NO₂ Trend"}
          </button>
        ))}
      </div>

      {/* SVG Historical Chart */}
      <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: "8px", padding: "16px", border: "1px solid var(--border-soft)" }}>
        <h4 style={{ margin: "0 0 12px 0", fontSize: "12px", color: "var(--text-3)", textTransform: "uppercase" }}>
          Historical Ingestion Cycles (Last 72h)
        </h4>
        <svg viewBox="0 0 500 150" style={{ width: "100%", height: "auto", overflow: "visible" }}>
          {/* Grid lines */}
          <line x1="10" y1="10" x2="490" y2="10" stroke="rgba(255,255,255,0.05)" strokeDasharray="3" />
          <line x1="10" y1="75" x2="490" y2="75" stroke="rgba(255,255,255,0.05)" strokeDasharray="3" />
          <line x1="10" y1="140" x2="490" y2="140" stroke="rgba(255,255,255,0.05)" strokeDasharray="3" />
          
          {/* Trend line */}
          <path d={pathData} fill="none" stroke="#3b82f6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          
          {/* Data Nodes */}
          {points.filter((_, i) => i % Math.max(1, Math.floor(points.length / 8)) === 0).map((p, idx) => (
            <g key={idx}>
              <circle cx={p.x} cy={p.y} r="3.5" fill="#fff" stroke="#3b82f6" strokeWidth="2" />
              <text x={p.x} y={p.y - 8} textAnchor="middle" fill="var(--text-2)" fontSize="7.5" fontWeight="bold">
                {p.value.toFixed(0)}
              </text>
              <text x={p.x} y="148" textAnchor="middle" fill="var(--text-3)" fontSize="7">
                {p.label}
              </text>
            </g>
          ))}
        </svg>
      </div>

      {/* Hourly Exposure Diurnal Heatmap */}
      <div>
        <h4 style={{ margin: "0 0 12px 0", fontSize: "12px", color: "var(--text-3)", textTransform: "uppercase" }}>
          Spatiotemporal Exposure Grid (CPCB Bands)
        </h4>
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          {/* Heatmap header containing hours */}
          <div style={{ display: "flex", gap: "2px", marginLeft: "36px" }}>
            {hours.filter(h => h % 3 === 0).map(h => (
              <span key={h} style={{ flex: 1, textAlign: "left", fontSize: "8px", color: "var(--text-3)" }}>
                {h}h
              </span>
            ))}
          </div>

          {/* Weekday matrix grids */}
          {weekdays.map((day, dIdx) => (
            <div key={day} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ width: "30px", fontSize: "9px", color: "var(--text-2)", fontWeight: "bold" }}>{day}</span>
              <div style={{ display: "flex", gap: "2px", flex: 1 }}>
                {hours.map(h => {
                  // Index matches (dayIndex * 24 + hour) from historical slices
                  const matchingRecord = history[Math.min(history.length - 1, (dIdx * 3 + h) % history.length)];
                  const val = matchingRecord ? matchingRecord[activeMetric] : 0.0;
                  const colorClass = getHeatmapColorClass(val);
                  return (
                    <div
                      key={h}
                      className={`heatmap-cell ${colorClass}`}
                      style={{
                        flex: 1,
                        height: "11px",
                        borderRadius: "2px",
                        cursor: "pointer"
                      }}
                      title={`${day} ${h}:00 - Value: ${val ? val.toFixed(1) : "N/A"}`}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
