import { useState } from "react";
import { getAqiSlug } from "@/constants/aqi";

export default function Comparison({ stations }) {
  const [stationIdA, setStationIdA] = useState("");
  const [stationIdB, setStationIdB] = useState("");

  if (!stations || stations.length < 2) {
    return <p className="empty-state">Not enough stations registered to compare.</p>;
  }

  const stationA = stations.find((s) => s.id === stationIdA) || stations[0];
  const stationB = stations.find((s) => s.id === stationIdB) || stations[1];

  const rows = [
    { label: "State Location",           valA: stationA.state,       valB: stationB.state,       type: "text" },
    { label: "City Metropolitan",         valA: stationA.city,        valB: stationB.city,        type: "text" },
    { label: "Spatiotemporal AQI",        valA: stationA.aqi,         valB: stationB.aqi,         type: "aqi"  },
    { label: "PM2.5 Concentration (µg/m³)", valA: stationA.pm25,     valB: stationB.pm25,        type: "num"  },
    { label: "NO₂ Concentration (µg/m³)", valA: stationA.no2,        valB: stationB.no2,         type: "num"  },
    { label: "Station Temperature (°C)", valA: stationA.temp,        valB: stationB.temp,        type: "num"  },
    { label: "Relative Humidity (%)",     valA: stationA.humidity,    valB: stationB.humidity,    type: "num"  },
    { label: "Wind Velocity (km/h)",      valA: stationA.wind_speed,  valB: stationB.wind_speed,  type: "num"  },
  ];

  return (
    <div className="comparison-root">
      <div className="comparison-selector-row">
        <div className="comparison-selector">
          <label className="comparison-selector-label">Compare Station A</label>
          <select className="select-control" value={stationIdA} onChange={(e) => setStationIdA(e.target.value)}>
            {stations.map((st) => <option key={st.id} value={st.id}>{st.name} ({st.city})</option>)}
          </select>
        </div>
        <div className="comparison-selector">
          <label className="comparison-selector-label">Compare Station B</label>
          <select className="select-control" value={stationIdB} onChange={(e) => setStationIdB(e.target.value)}>
            {stations.map((st) => <option key={st.id} value={st.id}>{st.name} ({st.city})</option>)}
          </select>
        </div>
      </div>

      <div className="comparison-table">
        <div className="comparison-table-header">
          <span>Metric</span><span>Station A</span><span>Station B</span>
        </div>
        {rows.map((row, idx) => (
          <div key={idx} className="comparison-table-row">
            <span className="comparison-row-label">{row.label}</span>
            {row.type === "aqi" ? (
              <span className={`aqi-indicator-pill ${getAqiSlug(row.valA)}`}>{row.valA?.toFixed(0)} ({stationA.category})</span>
            ) : row.type === "num" ? (
              <span className="comparison-row-val">{row.valA?.toFixed(1)}</span>
            ) : (
              <span>{row.valA}</span>
            )}
            {row.type === "aqi" ? (
              <span className={`aqi-indicator-pill ${getAqiSlug(row.valB)}`}>{row.valB?.toFixed(0)} ({stationB.category})</span>
            ) : row.type === "num" ? (
              <span className="comparison-row-val">{row.valB?.toFixed(1)}</span>
            ) : (
              <span>{row.valB}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
