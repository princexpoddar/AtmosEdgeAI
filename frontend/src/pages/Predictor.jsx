import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { submitPrediction } from "@/services/api";
import { getAqiColor } from "@/constants/aqi";
import Navbar from "@/components/layout/Navbar";
import Banner from "@/components/ui/Banner";
import Spinner from "@/components/ui/Spinner";
import { useStations } from "@/hooks/useStations";

export default function Predictor({ stations: propStations }) {
  const { stations: hookStations } = useStations();
  const stations = propStations || hookStations || [];
  const navigate = useNavigate();
  const [stationId, setStationId] = useState("");
  const [horizon, setHorizon] = useState(24);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const selectedId = stationId || (stations[0]?.id ?? "");

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

  return (
    <div className="app-root">
      <Navbar />
      <div className="predictor-page">
        <div className="predictor-card">
          <h2 className="predictor-title">Production ML Predictor Client</h2>
          <p className="predictor-subtitle">
            Triggers live inference using the deployed spatiotemporal Linear Regression baseline.
            The backend automatically gathers rolling lag observations, maps coordinates, and
            scales features on-the-fly.
          </p>

          {error && <Banner variant="error">⚠ {error}</Banner>}

          {stations.length === 0 ? (
            <p className="empty-state">No stations loaded. <button className="btn btn-secondary btn-sm" onClick={() => navigate("/dashboard")}>Go to Dashboard</button></p>
          ) : (
            <form onSubmit={handleSubmit} className="predictor-form">
              <div className="predictor-fields-row">
                <div className="predictor-field">
                  <label className="predictor-field-label">Select Monitoring Station</label>
                  <select className="select-control" value={stationId} onChange={(e) => setStationId(e.target.value)}>
                    {stations.map((st) => (
                      <option key={st.id} value={st.id}>{st.name} ({st.city})</option>
                    ))}
                  </select>
                </div>
                <div className="predictor-field">
                  <label className="predictor-field-label">Forecast Horizon</label>
                  <select className="select-control" value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
                    <option value={24}>24 Hours ahead</option>
                    <option value={48}>48 Hours ahead</option>
                    <option value={72}>72 Hours ahead</option>
                  </select>
                </div>
              </div>
              <button className="btn btn-primary predictor-submit-btn" type="submit" disabled={loading}>
                {loading ? <><Spinner size="sm" /> Triggering Inference…</> : "Generate AI Prediction"}
              </button>
            </form>
          )}

          {result && (
            <div className="predictor-result">
              <h4 className="predictor-result-title">Inference Results</h4>
              <div className="predictor-result-grid">
                <div className="predictor-aqi-block">
                  <span className="predictor-aqi-num" style={{ color: getAqiColor(result.aqi) }}>
                    {result.aqi.toFixed(0)}
                  </span>
                  <span className="predictor-aqi-unit">AQI</span>
                  <span className="predictor-aqi-cat" style={{ color: getAqiColor(result.aqi) }}>
                    {result.category}
                  </span>
                </div>
                <div>
                  <span className="predictor-stat-label">Predicted PM2.5</span>
                  <strong className="predictor-stat-val">{result.pm25_24h.toFixed(1)} µg/m³</strong>
                </div>
                <div>
                  <span className="predictor-stat-label">Predicted NO₂</span>
                  <strong className="predictor-stat-val">{result.no2_24h.toFixed(1)} µg/m³</strong>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
