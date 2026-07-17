import React, { useState } from "react";
import { submitPrediction } from "../services/api";

export default function Predictor({ stations }) {
  const [stationId, setStationId] = useState("");
  const [horizon, setHorizon] = useState(24);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  if (!stations || stations.length === 0) {
    return <p className="empty-state">No stations loaded for predictor.</p>;
  }

  const selectedId = stationId || stations[0].id;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await submitPrediction(selectedId, horizon);
      setResult(data);
    } catch (err) {
      setError(err.message || "Failed to generate prediction");
    } finally {
      setLoading(false);
    }
  };

  const getAqiColor = (aqi) => {
    if (aqi <= 50) return "#10b981";
    if (aqi <= 100) return "#3b82f6";
    if (aqi <= 200) return "#f59e0b";
    if (aqi <= 300) return "#ef4444";
    if (aqi <= 400) return "#8b5cf6";
    return "#7c2d12";
  };

  return (
    <div style={{ width: "100%", maxWidth: "800px", margin: "0 auto", background: "rgba(15, 23, 42, 0.55)", border: "1px solid var(--border)", borderRadius: "12px", padding: "24px", backdropFilter: "blur(12px)" }}>
      <h2 style={{ margin: "0 0 6px 0", fontSize: "18px", fontWeight: "bold" }}>Production ML Predictor Client</h2>
      <p style={{ margin: "0 0 20px 0", fontSize: "12px", color: "var(--text-3)", lineHeight: "1.4" }}>
        Triggers live inference using the deployed spatiotemporal Linear Regression baseline. The backend automatically gathers rolling lag observations, maps coordinates, and scales features on-the-fly.
      </p>
      
      {error && <div className="banner banner-error" style={{ marginBottom: "16px" }}>⚠ {error}</div>}

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: "16px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <label style={{ fontSize: "11px", color: "var(--text-3)" }}>Select Monitoring Station</label>
            <select
              className="select-control"
              value={stationId}
              onChange={(e) => setStationId(e.target.value)}
              style={{ width: "100%", height: "36px", background: "#0b1220", border: "1px solid var(--border)", color: "#fff", borderRadius: "6px", padding: "0 10px" }}
            >
              {stations.map(st => (
                <option key={st.id} value={st.id}>{st.name} ({st.city})</option>
              ))}
            </select>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <label style={{ fontSize: "11px", color: "var(--text-3)" }}>Forecast Horizon</label>
            <select
              className="select-control"
              value={horizon}
              onChange={(e) => setHorizon(e.target.value)}
              style={{ width: "100%", height: "36px", background: "#0b1220", border: "1px solid var(--border)", color: "#fff", borderRadius: "6px", padding: "0 10px" }}
            >
              <option value={24}>24 Hours ahead</option>
              <option value={48}>48 Hours ahead</option>
              <option value={72}>72 Hours ahead</option>
            </select>
          </div>
        </div>

        <button className="btn btn-primary" type="submit" style={{ alignSelf: "flex-start", marginTop: "10px" }} disabled={loading}>
          {loading ? "Triggering Inference..." : "Generate AI Prediction"}
        </button>
      </form>

      {result && (
        <div style={{ marginTop: "24px", background: "#080d16", border: "1px solid var(--border)", borderRadius: "10px", padding: "18px" }}>
          <h4 style={{ margin: "0 0 14px 0", fontSize: "14px", fontWeight: "bold" }}>Inference Results</h4>
          <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr", gap: "20px" }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: "6px" }}>
              <span style={{ fontSize: "42px", fontWeight: "bold", color: getAqiColor(result.aqi) }}>{result.aqi.toFixed(0)}</span>
              <span style={{ fontSize: "12px", color: "var(--text-3)" }}>AQI</span>
              <span style={{ fontSize: "14px", fontWeight: "bold", color: getAqiColor(result.aqi), marginLeft: "8px" }}>{result.category}</span>
            </div>
            <div>
              <span style={{ fontSize: "10px", color: "var(--text-3)", display: "block" }}>Predicted PM2.5</span>
              <strong style={{ fontSize: "18px" }}>{result.pm25_24h.toFixed(1)} µg/m³</strong>
            </div>
            <div>
              <span style={{ fontSize: "10px", color: "var(--text-3)", display: "block" }}>Predicted NO₂</span>
              <strong style={{ fontSize: "18px" }}>{result.no2_24h.toFixed(1)} µg/m³</strong>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
