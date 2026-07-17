import { useState } from "react";

export default function Comparison({ stations }) {
  const [stationIdA, setStationIdA] = useState("");
  const [stationIdB, setStationIdB] = useState("");

  if (!stations || stations.length < 2) {
    return <p className="empty-state">Not enough stations registered to compare.</p>;
  }

  // Initialize dropdown selections
  const defaultA = stationIdA || stations[0].id;
  const defaultB = stationIdB || stations[1].id;
  
  const stationA = stations.find(s => s.id === defaultA) || stations[0];
  const stationB = stations.find(s => s.id === defaultB) || stations[1];

  const getAqiClass = (aqi) => {
    if (aqi <= 50) return "good";
    if (aqi <= 100) return "satisfactory";
    if (aqi <= 200) return "moderate";
    if (aqi <= 300) return "poor";
    if (aqi <= 400) return "very-poor";
    return "severe";
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      
      {/* Selector dropdown row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ fontSize: "10.5px", color: "var(--text-3)", fontWeight: "bold", textTransform: "uppercase" }}>
            Compare Station A
          </label>
          <select
            className="select-control"
            value={stationIdA}
            onChange={(e) => setStationIdA(e.target.value)}
            style={{ width: "100%", height: "34px", background: "var(--bg-3)", border: "1px solid var(--border)", color: "#fff", borderRadius: "6px", padding: "0 10px" }}
          >
            {stations.map(st => (
              <option key={st.id} value={st.id}>{st.name} ({st.city})</option>
            ))}
          </select>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label style={{ fontSize: "10.5px", color: "var(--text-3)", fontWeight: "bold", textTransform: "uppercase" }}>
            Compare Station B
          </label>
          <select
            className="select-control"
            value={stationIdB}
            onChange={(e) => setStationIdB(e.target.value)}
            style={{ width: "100%", height: "34px", background: "var(--bg-3)", border: "1px solid var(--border)", color: "#fff", borderRadius: "6px", padding: "0 10px" }}
          >
            {stations.map(st => (
              <option key={st.id} value={st.id}>{st.name} ({st.city})</option>
            ))}
          </select>
        </div>
      </div>

      {/* Comparison table */}
      <div style={{ background: "rgba(0,0,0,0.12)", border: "1px solid var(--border-soft)", borderRadius: "8px", overflow: "hidden" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr", borderBottom: "1px solid var(--border)", background: "rgba(255,255,255,0.02)", padding: "10px 14px", fontSize: "11px", fontWeight: "bold", color: "var(--text-3)", textTransform: "uppercase" }}>
          <span>Metric parameter</span>
          <span>Station A</span>
          <span>Station B</span>
        </div>

        {[
          { label: "State Location", valA: stationA.state, valB: stationB.state, type: "text" },
          { label: "City Metropolitan", valA: stationA.city, valB: stationB.city, type: "text" },
          { label: "Spatiotemporal AQI", valA: stationA.aqi, valB: stationB.aqi, type: "aqi" },
          { label: "PM2.5 Concentration (µg/m³)", valA: stationA.pm25, valB: stationB.pm25, type: "num" },
          { label: "NO₂ Concentration (µg/m³)", valA: stationA.no2, valB: stationB.no2, type: "num" },
          { label: "Station Temperature (°C)", valA: stationA.temp, valB: stationB.temp, type: "num" },
          { label: "Relative Humidity (%)", valA: stationA.humidity, valB: stationB.humidity, type: "num" },
          { label: "Wind Velocity (km/h)", valA: stationA.wind_speed, valB: stationB.wind_speed, type: "num" }
        ].map((row, idx) => (
          <div
            key={idx}
            style={{
              display: "grid",
              gridTemplateColumns: "1.2fr 1fr 1fr",
              borderBottom: idx === 7 ? "none" : "1px solid var(--border-soft)",
              padding: "12px 14px",
              fontSize: "12px",
              alignItems: "center"
            }}
          >
            <span style={{ color: "var(--text-2)", fontWeight: "500" }}>{row.label}</span>
            
            {row.type === "aqi" ? (
              <span className={`aqi-indicator-pill ${getAqiClass(row.valA)}`} style={{ alignSelf: "start", justifySelf: "start" }}>
                {row.valA.toFixed(0)} ({stationA.category})
              </span>
            ) : row.type === "num" ? (
              <span style={{ fontWeight: "bold" }}>{row.valA.toFixed(1)}</span>
            ) : (
              <span>{row.valA}</span>
            )}

            {row.type === "aqi" ? (
              <span className={`aqi-indicator-pill ${getAqiClass(row.valB)}`} style={{ alignSelf: "start", justifySelf: "start" }}>
                {row.valB.toFixed(0)} ({stationB.category})
              </span>
            ) : row.type === "num" ? (
              <span style={{ fontWeight: "bold" }}>{row.valB.toFixed(1)}</span>
            ) : (
              <span>{row.valB}</span>
            )}
          </div>
        ))}
      </div>

    </div>
  );
}
