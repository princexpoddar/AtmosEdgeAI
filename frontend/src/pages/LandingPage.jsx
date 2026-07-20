import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Globe, Flame, PieChart, CheckCircle2 } from "lucide-react";
import { getAqiColor, getAqiLabel } from "@/constants/aqi";
import { useStations } from "@/hooks/useStations";
import Navbar from "@/components/layout/Navbar";

const FEATURES = [
  {
    Icon: Globe,
    title: "Spatiotemporal Inversion",
    desc: "Embeds Latitude, Longitude, and Elevation to map transport vectors and pollution dispersion dynamically.",
  },
  {
    Icon: Flame,
    title: "NASA FIRMS Fire Analytics",
    desc: "Calculates agricultural upwind transport vectors using regional fire intensities and wind directions.",
  },
  {
    Icon: PieChart,
    title: "SHAP Explainability",
    desc: "Provides clear force contributions showing weather, fire activity, and autoregressive drivers.",
  },
];

const CHECKLIST = [
  "Temporal leakage constraints verified",
  "50-feature spatiotemporal sequences (seq_len=48)",
  "Separate scalers for inputs and targets (no leakage)",
  "Spatial K-NN neighbour context features included",
];

export default function LandingPage() {
  const navigate = useNavigate();
  const { stations } = useStations();

  const { totalStations, avgAqi } = useMemo(() => {
    const total = stations.length;
    const avg = total ? stations.reduce((sum, st) => sum + st.aqi, 0) / total : 0;
    return { totalStations: total, avgAqi: avg };
  }, [stations]);

  const avgColor = getAqiColor(avgAqi);
  const avgLabel = getAqiLabel(avgAqi);

  return (
    <div className="app-root">
      <Navbar />
      <div className="landing-root">
        {/* Hero */}
        <section className="landing-hero">
          <div className="landing-hero-content">
            <span className="landing-eyebrow">✨ Enterprise Air Quality Analytics</span>
            <h1 className="landing-headline">
              Spatiotemporal Environmental Intelligence at National Scale
            </h1>
            <p className="landing-subtext">
              AtmosEdgeAI replaces disjoint single-station models with a unified multi-horizon deep
              learning engine. Predict PM2.5, NO₂ and Indian CPCB AQI up to 72 hours ahead across
              36 active metropolitan stations in India.
            </p>
            <div className="landing-cta-row">
              <button className="btn btn-primary landing-cta-btn" onClick={() => navigate("/dashboard")}>
                Explore Live Dashboard
              </button>
              <button className="btn btn-secondary landing-cta-btn" onClick={() => navigate("/predictor")}>
                Interactive Predictor API
              </button>
            </div>
          </div>

          <div className="landing-hero-card">
            <div className="aqi-hero-card">
              <div className="aqi-hero-card-header">
                <span className="aqi-hero-card-label">National AQI Average</span>
                <span className="aqi-live-badge">● Live Update</span>
              </div>
              <div className="aqi-big-value">
                <span className="aqi-big-number" style={{ color: avgColor }}>{avgAqi.toFixed(0)}</span>
                <span className="aqi-big-unit">AQI</span>
                <span className="aqi-big-category" style={{ color: avgColor }}>{avgLabel}</span>
              </div>
              <div className="aqi-hero-card-stats">
                <div>Active Stations: <strong style={{ color: "var(--text-1)" }}>{totalStations || "—"}</strong></div>
                <div>Ingestion Size: <strong style={{ color: "var(--text-1)" }}>2,068k rows</strong></div>
              </div>
            </div>
          </div>
        </section>

        {/* Feature cards */}
        <section className="landing-features-section">
          <h3 className="landing-features-title">Advanced Architectural Capabilities</h3>
          <div className="landing-feature-grid">
            {FEATURES.map(({ Icon, title, desc }) => (
              <div key={title} className="feature-card">
                <div className="feature-icon-wrap">
                  <Icon size={16} />
                </div>
                <h4 className="feature-title">{title}</h4>
                <p className="feature-desc">{desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Benchmarks */}
        <section className="landing-benchmarks">
          <div className="landing-benchmarks-left">
            <h3 className="landing-benchmarks-title">Production ML Engine Performance</h3>
            <p className="landing-benchmarks-desc">
              The global predictor evaluates on an untouched test set of 13,572 observations.
              Ridge Regression leads the leaderboard with the best generalization on new temporal data.
            </p>
            <div className="landing-metric-grid">
              <div>
                <span className="landing-metric-label">RIDGE FORECAST MAE</span>
                <strong className="landing-metric-val-green">0.4832</strong>
              </div>
              <div>
                <span className="landing-metric-label">XGBOOST FORECAST MAE</span>
                <strong className="landing-metric-val-blue">0.4963</strong>
              </div>
            </div>
          </div>
          <div className="landing-checklist">
            {CHECKLIST.map((item) => (
              <div key={item} className="landing-check-row">
                <CheckCircle2 size={14} color="#10b981" />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Footer */}
        <footer className="landing-footer">
          <span>&copy; {new Date().getFullYear()} AtmosEdgeAI Inc. All rights reserved.</span>
          <div className="landing-footer-links">
            <a href="#github" className="landing-footer-link" onClick={(e) => e.preventDefault()}>GitHub</a>
            <a href="#docs"   className="landing-footer-link" onClick={(e) => e.preventDefault()}>Documentation</a>
            <a href="#bench"  className="landing-footer-link" onClick={(e) => e.preventDefault()}>Benchmarks</a>
          </div>
        </footer>
      </div>
    </div>
  );
}
