import React from "react";

export default function LandingPage({ stations, onEnterApp }) {
  const totalStations = stations.length;
  const avgAqi = stations.length ? (stations.reduce((sum, st) => sum + st.aqi, 0) / stations.length) : 0;
  
  const getAqiCategoryText = (aqi) => {
    if (aqi <= 50) return "Good";
    if (aqi <= 100) return "Satisfactory";
    if (aqi <= 200) return "Moderate";
    if (aqi <= 300) return "Poor";
    if (aqi <= 400) return "Very Poor";
    return "Severe";
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
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "40px 20px", display: "flex", flexDirection: "column", gap: "60px" }}>
      
      {/* ── Hero Section ── */}
      <section style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "40px", alignItems: "center" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <span style={{ fontSize: "11px", fontWeight: "bold", textTransform: "uppercase", tracking: "0.15em", color: "#3b82f6" }}>
            ✨ Enterprise Air Quality Analytics
          </span>
          <h1 style={{ fontSize: "46px", fontWeight: "bold", lineHeight: "1.1", margin: 0, background: "linear-gradient(to right, #fff, #8b949e)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Spatiotemporal Environmental Intelligence at National Scale
          </h1>
          <p style={{ fontSize: "15px", color: "var(--text-2)", margin: 0, lineHeight: "1.5" }}>
            AtmosEdgeAI replaces disjoint single-station models with a unified multi-horizon deep learning engine.
            Predict PM2.5, NO₂ and Indian CPCB AQI up to 72 hours ahead across 36 active metropolitan stations in India.
          </p>
          <div style={{ display: "flex", gap: "12px", marginTop: "10px" }}>
            <button
              className="btn btn-primary"
              onClick={() => onEnterApp("dashboard")}
              style={{ height: "42px", borderRadius: "22px", padding: "0 24px", fontSize: "13.5px", fontWeight: "bold" }}
            >
              Explore Live Dashboard
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => onEnterApp("predictor")}
              style={{ height: "42px", borderRadius: "22px", padding: "0 24px", fontSize: "13.5px", fontWeight: "bold" }}
            >
              Interactive Predictor API
            </button>
          </div>
        </div>

        {/* Hero AQI Card Overlay */}
        <div style={{ display: "flex", justifyContent: "center" }}>
          <div
            style={{
              width: "100%",
              maxWidth: "360px",
              background: "linear-gradient(135deg, rgba(15, 23, 42, 0.7) 0%, rgba(3, 7, 18, 0.7) 100%)",
              border: "1px solid #1e2d4a",
              borderRadius: "16px",
              padding: "24px",
              boxShadow: "var(--shadow-lg)",
              backdropFilter: "blur(12px)",
              position: "relative",
              overflow: "hidden"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "20px" }}>
              <span style={{ fontSize: "11px", color: "var(--text-3)", fontWeight: "bold", textTransform: "uppercase" }}>
                National AQI Average
              </span>
              <span style={{ fontSize: "10px", color: "#10b981", background: "rgba(16, 185, 129, 0.12)", padding: "2px 8px", borderRadius: "10px", fontWeight: "bold" }}>
                ● Live Update
              </span>
            </div>
            
            <div style={{ display: "flex", alignItems: "baseline", gap: "10px", marginBottom: "16px" }}>
              <span style={{ fontSize: "64px", fontWeight: "bold", color: getAqiColor(avgAqi) }}>
                {avgAqi.toFixed(0)}
              </span>
              <span style={{ fontSize: "16px", color: "var(--text-2)", fontWeight: "500" }}>AQI</span>
              <span style={{ fontSize: "16px", fontWeight: "bold", color: getAqiColor(avgAqi), marginLeft: "auto" }}>
                {getAqiCategoryText(avgAqi)}
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", borderTop: "1px solid rgba(255,255,255,0.05)", paddingTop: "16px", fontSize: "12px", color: "var(--text-2)" }}>
              <div>
                Active Stations: <strong style={{ color: "#fff" }}>{totalStations}</strong>
              </div>
              <div>
                Ingestion Size: <strong style={{ color: "#fff" }}>2,068k rows</strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Core Feature Cards ── */}
      <section style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
        <h3 style={{ fontSize: "20px", fontWeight: "bold", textAlign: "center", margin: 0 }}>
          Advanced Architectural Capabilities
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "20px" }}>
          {[
            {
              icon: "fa-earth-asia",
              title: "Spatiotemporal Inversion",
              desc: "Embeds Latitude, Longitude, and Elevation to map transport vectors and pollution dispersion dynamically."
            },
            {
              icon: "fa-fire",
              title: "NASA FIRMS Fire Analytics",
              desc: "Calculates agricultural upwind transport vectors using regional fire intensities and wind directions."
            },
            {
              icon: "fa-chart-pie",
              title: "SHAP Explainability",
              desc: "Provides clear force contributions showing weather, fire activity, and autoregressive drivers."
            }
          ].map((feat, idx) => (
            <div
              key={idx}
              style={{
                background: "rgba(15, 23, 42, 0.4)",
                border: "1px solid #1e2d4a",
                borderRadius: "12px",
                padding: "20px",
                display: "flex",
                flexDirection: "column",
                gap: "12px"
              }}
            >
              <div style={{ width: "36px", height: "36px", borderRadius: "8px", background: "rgba(59,130,246,0.12)", color: "#3b82f6", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <i className={`fa ${feat.icon}`} style={{ fontSize: "16px" }}></i>
              </div>
              <h4 style={{ margin: 0, fontSize: "14.5px", fontWeight: "bold" }}>{feat.title}</h4>
              <p style={{ margin: 0, fontSize: "12px", color: "var(--text-2)", lineHeight: "1.4" }}>{feat.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── MLOps Telemetry Benchmarks ── */}
      <section style={{ background: "rgba(15, 23, 42, 0.55)", border: "1px solid #1e2d4a", borderRadius: "16px", padding: "30px", display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "40px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <h3 style={{ margin: 0, fontSize: "20px", fontWeight: "bold" }}>Production ML Engine Performance</h3>
          <p style={{ margin: 0, fontSize: "13px", color: "var(--text-2)", lineHeight: "1.5" }}>
            The global predictor evaluates on an untouched test set of **13,981 observations**.
            Linear Regression and XGBoost lead the leaderboard with extreme execution throughput.
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", borderTop: "1px solid rgba(255,255,255,0.05)", paddingTop: "20px" }}>
            <div>
              <span style={{ fontSize: "11px", color: "var(--text-3)", display: "block" }}>LR FORECAST MAE</span>
              <strong style={{ fontSize: "22px", color: "#10b981" }}>0.4880</strong>
            </div>
            <div>
              <span style={{ fontSize: "11px", color: "var(--text-3)", display: "block" }}>XGBOOST FORECAST MAE</span>
              <strong style={{ fontSize: "22px", color: "#3b82f6" }}>0.4965</strong>
            </div>
          </div>
        </div>

        {/* Diagnostic features checklist */}
        <div style={{ display: "flex", flexDirection: "column", gap: "10px", justifyContent: "center" }}>
          {[
            { label: "Temporal leakage constraints verified", status: "pass" },
            { label: "Chronological multi-horizon sequences shaped", status: "pass" },
            { label: "Single global Standard Scaler fitted", status: "pass" },
            { label: "Early Stopping and Cosine LR active", status: "pass" }
          ].map((item, idx) => (
            <div key={idx} style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "12px", color: "var(--text-2)" }}>
              <i className="fa fa-circle-check" style={{ color: "#10b981" }}></i>
              <span>{item.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ── Footer ── */}
      <footer style={{ borderTop: "1px solid var(--border)", paddingTop: "20px", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "11.5px", color: "var(--text-3)" }}>
        <span>&copy; {new Date().getFullYear()} AtmosEdgeAI Inc. All rights reserved.</span>
        <div style={{ display: "flex", gap: "20px" }}>
          <a href="#github" style={{ color: "var(--text-3)" }} onClick={e => e.preventDefault()}>GitHub</a>
          <a href="#docs" style={{ color: "var(--text-3)" }} onClick={e => e.preventDefault()}>Documentation</a>
          <a href="#benchmark" style={{ color: "var(--text-3)" }} onClick={e => e.preventDefault()}>Benchmarks</a>
        </div>
      </footer>

    </div>
  );
}
