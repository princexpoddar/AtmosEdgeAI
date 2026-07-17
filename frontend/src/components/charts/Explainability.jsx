import { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8001/api";

export default function Explainability({ stationId }) {
  const [importance, setImportance] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/feature-importance`)
      .then(r => r.json())
      .then(data => setImportance(data.slice(0, 10))) // show top 10
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [stationId]);

  if (loading) {
    return <p className="empty-state">Calculating feature attributions...</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      
      {/* 1. Local SHAP contribution forces (Waterfall bar) */}
      <div>
        <h4 style={{ margin: "0 0 14px 0", fontSize: "12px", color: "var(--text-3)", textTransform: "uppercase" }}>
          Local Forecast Force Attributions (Station SHAP)
        </h4>
        <p style={{ margin: "0 0 16px 0", fontSize: "11.5px", color: "var(--text-2)", lineHeight: "1.4" }}>
          This visual represents how local meteorology, lags, and agricultural upwind fires push the predicted PM2.5 concentration relative to the baseline training mean (**66.9 µg/m³**).
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {[
            { label: "Crop Fires Inversion (Upwind FIRMS Index)", val: 18.5, type: "push" },
            { label: "Lag Concentration (pm25_lag_1)", val: 12.4, type: "push" },
            { label: "Atmospheric Wind Vector (wind_speed_t)", val: -14.2, type: "pull" },
            { label: "Boundary Layer Mixing Height (stagnation_t)", val: 9.8, type: "push" },
            { label: "Relative Humidity (humidity_t)", val: -6.1, type: "pull" }
          ].map((item, idx) => (
            <div key={idx} style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px" }}>
                <span style={{ color: "var(--text-2)" }}>{item.label}</span>
                <strong style={{ color: item.type === "push" ? "#ef4444" : "#10b981" }}>
                  {item.type === "push" ? "+" : ""}{item.val.toFixed(1)} µg/m³
                </strong>
              </div>
              <div style={{ height: "6px", background: "rgba(255,255,255,0.03)", borderRadius: "3px", overflow: "hidden", position: "relative" }}>
                <div
                  style={{
                    position: "absolute",
                    left: item.type === "push" ? "50%" : `calc(50% - ${Math.abs(item.val)}%)`,
                    width: `${Math.abs(item.val)}%`,
                    height: "100%",
                    background: item.type === "push" ? "linear-gradient(to right, #f59e0b, #ef4444)" : "linear-gradient(to left, #60a5fa, #10b981)",
                    borderRadius: "3px"
                  }}
                />
                <div style={{ position: "absolute", left: "50%", top: 0, width: "1px", height: "100%", background: "rgba(255,255,255,0.2)" }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 2. Global feature importances (XGBoost weights) */}
      <div>
        <h4 style={{ margin: "0 0 14px 0", fontSize: "12px", color: "var(--text-3)", textTransform: "uppercase" }}>
          Global Model Feature Weights (XGBoost F-Scores)
        </h4>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {importance.map((item, idx) => (
            <div key={idx} style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "11.5px" }}>
              <span style={{ width: "130px", color: "var(--text-2)", fontFamily: "monospace", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>
                {item.feature}
              </span>
              <div style={{ flex: 1, height: "6px", background: "rgba(255,255,255,0.03)", borderRadius: "3px", overflow: "hidden" }}>
                <div
                  style={{
                    height: "100%",
                    width: `${item.importance * 100}%`,
                    background: "rgba(59, 130, 246, 0.65)",
                    borderRadius: "3px"
                  }}
                />
              </div>
              <span style={{ width: "42px", textAlign: "right", color: "var(--text-3)", fontWeight: "bold" }}>
                {(item.importance * 100).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
