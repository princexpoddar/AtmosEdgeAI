import { useState } from "react";
import { getAqiSlug, getAqiLabel } from "@/constants/aqi";
import Analytics from "@/components/charts/Analytics";
import Explainability from "@/components/charts/Explainability";
import Comparison from "@/components/cards/Comparison";
import Skeleton from "@/components/ui/Skeleton";

function fmt(val, decimals = 1) {
  if (val === null || val === undefined) return "N/A";
  return typeof val === "number" ? val.toFixed(decimals) : val;
}

function ForecastCards({ forecasts }) {
  if (!forecasts || forecasts.length === 0) {
    return (
      <div className="forecast-row">
        {[0, 1, 2].map((i) => <Skeleton key={i} height="160px" />)}
      </div>
    );
  }
  return (
    <div className="forecast-row">
      {forecasts.slice(0, 3).map((fc, idx) => {
        const slug = getAqiSlug(fc.predicted_aqi);
        const label = getAqiLabel(fc.predicted_aqi);
        const horizonLabel = idx === 0 ? "24h Forecast" : idx === 1 ? "48h Forecast" : "72h Forecast";
        return (
          <div key={idx} className="forecast-card">
            <div className={`forecast-strip strip-${slug}`} />
            <div className="forecast-aqi-block">
              <span className={`forecast-aqi-num aqitxt-${slug}`}>{fc.predicted_aqi.toFixed(0)}</span>
              <span className="forecast-aqi-unit">AQI</span>
              <span className={`forecast-aqi-cat aqitxt-${slug}`}>{label}</span>
            </div>
            <div className="forecast-body">
              <div className="forecast-header">
                <span className="forecast-horizon-pill">{horizonLabel}</span>
              </div>
              <div className="forecast-chips">
                <div className="forecast-chip">
                  <span className="forecast-chip-label">PM2.5</span>
                  <span className="forecast-chip-val">{fmt(fc.pm25_24h)}</span>
                  <span className="forecast-chip-unit">µg/m³</span>
                </div>
                <div className="forecast-chip">
                  <span className="forecast-chip-label">NO₂</span>
                  <span className="forecast-chip-val">{fmt(fc.no2_24h)}</span>
                  <span className="forecast-chip-unit">µg/m³</span>
                </div>
              </div>
              <div className="forecast-catbar-track">
                <div
                  className={`forecast-catbar-fill catbar-${slug}`}
                  style={{ width: `${Math.min((fc.predicted_aqi / 500) * 100, 100)}%` }}
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function RightPanel({ forecasts, history, stationId, stations, loading }) {
  const [tab, setTab] = useState("analytics");

  const tabs = [
    { key: "analytics", label: "Analytics" },
    { key: "explainability", label: "Explainability" },
    { key: "comparison", label: "Comparison" },
  ];

  return (
    <div className="dashboard-content-col">
      <div className="panel-section">
        <div className="section-header">
          <span className="section-title">72h Forecast Outlook</span>
        </div>
        <ForecastCards forecasts={forecasts} />
      </div>

      <div className="card">
        <div className="tab-bar">
          {tabs.map((t) => (
            <button
              key={t.key}
              className={`tab-btn${tab === t.key ? " active" : ""}`}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="tab-panel">
          {tab === "analytics" && (
            loading
              ? <Skeleton height="200px" />
              : <Analytics history={history} forecasts={forecasts} />
          )}
          {tab === "explainability" && (
            <Explainability stationId={stationId} />
          )}
          {tab === "comparison" && (
            <Comparison stations={stations} />
          )}
        </div>
      </div>
    </div>
  );
}
