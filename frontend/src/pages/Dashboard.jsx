import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { useStations } from "@/hooks/useStations";
import { useStationDetail } from "@/hooks/useStationDetail";
import { useSync } from "@/hooks/useSync";
import { useTheme } from "@/context/useTheme";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import RightPanel from "@/components/layout/RightPanel";
import Map from "@/components/map/Map";
import Banner from "@/components/ui/Banner";

export default function Dashboard() {
  const location = useLocation();
  const { theme } = useTheme();
  const [selectedStationId, setSelectedStationId] = useState("");
  const [activeMapLayer, setActiveMapLayer] = useState("aqi");
  const [showAlertPanel, setShowAlertPanel] = useState(false);
  const [countdown, setCountdown] = useState(300);

  const { stations, loading: stationsLoading, error: stationsError, lastUpdated, refresh } = useStations();
  const { history, forecasts, intelligence, alerts, loading: detailLoading } = useStationDetail(selectedStationId);
  const { syncing, syncOk, syncError, handleSync } = useSync(refresh);

  // Set first station as default once loaded
  useEffect(() => {
    if (stations.length > 0 && !selectedStationId) {
      setSelectedStationId(stations[0].id);
    }
  }, [stations, selectedStationId]);

  // Countdown timer — only runs on /dashboard
  useEffect(() => {
    if (location.pathname !== "/dashboard") return;
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          refresh();
          return 300;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [location.pathname, refresh]);

  // Sync countdown when data refreshes
  useEffect(() => {
    if (lastUpdated) setCountdown(300);
  }, [lastUpdated]);

  const error = stationsError || syncError;

  return (
    <div className="app-root">
      <Navbar
        syncing={syncing}
        syncOk={syncOk}
        onSync={handleSync}
        lastUpdated={lastUpdated}
        countdown={countdown}
        alerts={alerts}
        showAlertPanel={showAlertPanel}
        onToggleAlerts={() => setShowAlertPanel((v) => !v)}
      />

      {error && <Banner variant="error">⚠ {error}</Banner>}
      {syncOk && <Banner variant="success">✓ Updated CPCB live measurements. Refreshing…</Banner>}

      <div className="dashboard-grid">
        {/* Map column */}
        <div className="dashboard-map-col">
          <div className="card map-card">
            <div className="map-layer-controls">
              {[{ key: "aqi", label: "AQI" }, { key: "weather", label: "Temp" }, { key: "wind", label: "Wind" }].map((layer) => (
                <button
                  key={layer.key}
                  className={`map-layer-btn${activeMapLayer === layer.key ? " active" : " inactive"}`}
                  onClick={() => setActiveMapLayer(layer.key)}
                >
                  {layer.label}
                </button>
              ))}
            </div>
            <Map
              stations={stations}
              selectedStationId={selectedStationId}
              onSelectStation={setSelectedStationId}
              activeLayer={activeMapLayer}
              theme={theme}
            />
          </div>

          <Sidebar
            stations={stations}
            selectedStationId={selectedStationId}
            onSelectStation={setSelectedStationId}
            loading={stationsLoading}
          />
        </div>

        {/* Right column */}
        <RightPanel
          forecasts={forecasts}
          history={history}
          intelligence={intelligence}
          stationId={selectedStationId}
          stations={stations}
          loading={detailLoading}
        />
      </div>
    </div>
  );
}
