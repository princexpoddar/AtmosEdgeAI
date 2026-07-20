import { useState, useMemo } from "react";
import { getHeatClass } from "@/constants/aqi";
import Skeleton from "@/components/ui/Skeleton";

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

function formatTime(isoString) {
  return new Date(isoString).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function getPoints(data, key) {
  const values = data.map((d) => d[key] || 0);
  const maxVal = Math.max(...values, 1);
  const W = 500, H = 150, P = 10;
  return data.map((d, i) => {
    const x = P + (i / Math.max(data.length - 1, 1)) * (W - 2 * P);
    const y = H - P - ((d[key] || 0) / maxVal) * (H - 2 * P);
    return { x, y, value: d[key] || 0, label: formatTime(d.timestamp) };
  });
}

export default function Analytics({ history, loading }) {
  const [activeMetric, setActiveMetric] = useState("pm25");

  // Build (dayOfWeek-hour) → value grid from real timestamps
  const heatmapData = useMemo(() => {
    const grid = {};
    if (!history) return grid;
    history.forEach((record) => {
      const d = new Date(record.timestamp);
      const key = `${d.getDay()}-${d.getHours()}`;
      grid[key] = record[activeMetric] ?? 0;
    });
    return grid;
  }, [history, activeMetric]);

  if (loading) {
    return (
      <div className="analytics-root">
        <Skeleton height="26px" width="200px" />
        <Skeleton height="150px" />
        <Skeleton height="120px" />
      </div>
    );
  }

  if (!history || history.length === 0) {
    return <p className="empty-state">No historical analytics available for this station.</p>;
  }

  const points = getPoints(history, activeMetric);
  const pathData = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  const sparsePoints = points.filter((_, i) => i % Math.max(1, Math.floor(points.length / 8)) === 0);

  return (
    <div className="analytics-root">
      {/* Metric selector */}
      <div className="analytics-tab-row">
        {["pm25", "no2"].map((m) => (
          <button
            key={m}
            onClick={() => setActiveMetric(m)}
            className={`analytics-tab-btn${activeMetric === m ? " active" : " inactive"}`}
          >
            {m === "pm25" ? "PM2.5 Trend" : "NO₂ Trend"}
          </button>
        ))}
      </div>

      {/* SVG trend chart */}
      <div className="analytics-chart-box">
        <h4 className="analytics-chart-title">Historical Ingestion Cycles (Last 72h)</h4>
        <svg viewBox="0 0 500 150" style={{ width: "100%", height: "auto", overflow: "visible" }}>
          <line x1="10" y1="10"  x2="490" y2="10"  stroke="var(--border-soft)" strokeDasharray="3" />
          <line x1="10" y1="75"  x2="490" y2="75"  stroke="var(--border-soft)" strokeDasharray="3" />
          <line x1="10" y1="140" x2="490" y2="140" stroke="var(--border-soft)" strokeDasharray="3" />
          <path d={pathData} fill="none" stroke="#3b82f6" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          {sparsePoints.map((p, idx) => (
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

      {/* Heatmap — real (day, hour) → value mapping */}
      <div className="analytics-heatmap-section">
        <h4 className="analytics-heatmap-title">Spatiotemporal Exposure Grid (CPCB Bands)</h4>
        <div className="heatmap-grid">
          {/* Hour header */}
          <div className="heatmap-hour-header">
            {HOURS.filter((h) => h % 3 === 0).map((h) => (
              <span key={h} className="heatmap-hour-label">{h}h</span>
            ))}
          </div>
          {/* Day rows */}
          {WEEKDAYS.map((day, dIdx) => (
            <div key={day} className="heatmap-day-row">
              <span className="heatmap-day-label">{day}</span>
              <div className="heatmap-cells-row">
                {HOURS.map((h) => {
                  const val = heatmapData[`${dIdx}-${h}`];
                  const colorClass = val !== undefined ? getHeatClass(val) : "heat-empty";
                  return (
                    <div
                      key={h}
                      className={`heatmap-cell ${colorClass}`}
                      title={`${day} ${h}:00 — ${val !== undefined ? val.toFixed(1) : "No data"}`}
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
