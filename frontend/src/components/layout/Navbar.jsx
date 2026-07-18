import { useNavigate, useLocation } from "react-router-dom";
import { RefreshCw, Bell, Sun, Moon, X } from "lucide-react";
import { useTheme } from "@/context/useTheme";

export default function Navbar({
  syncing,
  onSync,
  lastUpdated,
  countdown,
  alerts,
  showAlertPanel,
  onToggleAlerts,
}) {
  const navigate = useNavigate();
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  const isActive = (path) => location.pathname === path;

  return (
    <header className="topbar">
      <div className="topbar-brand" onClick={() => navigate("/")} role="button" tabIndex={0} onKeyDown={(e) => e.key === "Enter" && navigate("/")}>
        <div className="brand-icon">🌬</div>
        <span className="brand-name">AtmosEdgeAI</span>
        <span className="brand-version">v2.1</span>
      </div>

      {location.pathname !== "/" && (
        <nav className="nav-links" aria-label="Main navigation">
          <button className={`nav-link${isActive("/dashboard") ? " active" : ""}`} onClick={() => navigate("/dashboard")}>
            Dashboard
          </button>
          <button className={`nav-link${isActive("/enforcement") ? " active" : ""}`} onClick={() => navigate("/enforcement")}>
            Municipal Command Center
          </button>
          <button className={`nav-link${isActive("/predictor") ? " active" : ""}`} onClick={() => navigate("/predictor")}>
            Predictor
          </button>
        </nav>
      )}

      <div className="topbar-actions">
        {onSync && (
          <button className="btn btn-secondary btn-sm" onClick={onSync} disabled={syncing}>
            <RefreshCw size={12} className={syncing ? "spin-icon" : ""} />
            <span>{syncing ? "Syncing…" : "Sync APIs"}</span>
          </button>
        )}

        {lastUpdated && (
          <div className="countdown-text">
            <span className="live-pulse" />
            <span>Updated {lastUpdated} (refresh {countdown}s)</span>
          </div>
        )}

        {alerts !== undefined && (
          <button
            className="btn btn-secondary btn-icon"
            onClick={onToggleAlerts}
            aria-label="Toggle alerts"
            style={{ position: "relative" }}
          >
            <Bell size={13} />
            {alerts.length > 0 && <span className="alert-badge" />}
          </button>
        )}

        <button className="btn btn-secondary btn-icon" onClick={toggleTheme} aria-label="Toggle theme">
          {theme === "dark" ? <Sun size={13} /> : <Moon size={13} />}
        </button>
      </div>

      {showAlertPanel && (
        <div className="alert-drawer">
          <div className="alert-drawer-header">
            <h4 className="alert-drawer-title">Alerts &amp; Advisories</h4>
            <button className="alert-drawer-close" onClick={onToggleAlerts} aria-label="Close alerts">
              <X size={14} />
            </button>
          </div>
          {(alerts || []).map((al, idx) => (
            <div key={idx} className={`alert-item ${al.type}`}>
              <strong>{al.title}</strong>
              <p>{al.desc}</p>
            </div>
          ))}
        </div>
      )}
    </header>
  );
}
