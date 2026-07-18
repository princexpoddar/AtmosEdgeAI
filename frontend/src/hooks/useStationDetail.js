import { useState, useEffect } from "react";
import {
  getStationHistory,
  getStationForecast,
  getStationIntelligence,
} from "@/services/api";

export function useStationDetail(stationId) {
  const [history,      setHistory]      = useState([]);
  const [forecasts,    setForecasts]    = useState([]);
  const [intelligence, setIntelligence] = useState(null);
  const [alerts,       setAlerts]       = useState([]);
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState(null);

  useEffect(() => {
    if (!stationId) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      getStationHistory(stationId, 3),
      getStationForecast(stationId),
      getStationIntelligence(stationId).catch(() => null),
    ])
      .then(([hist, fc, intel]) => {
        if (cancelled) return;
        setHistory(hist);
        setForecasts(fc);
        setIntelligence(intel);

        // Derive alerts from forecast
        const maxFc = fc.length > 0 ? Math.max(...fc.map((x) => x.predicted_aqi)) : 0;
        const newAlerts = [];
        if (maxFc > 200) {
          newAlerts.push({
            title: "High Pollution Alert",
            desc: `Forecast peaks at ${maxFc.toFixed(0)} AQI. Stay indoors and use air filters.`,
            type: "danger",
          });
        } else if (maxFc > 100) {
          newAlerts.push({
            title: "Moderate Exposure Advisory",
            desc: `AQI forecast reaches ${maxFc.toFixed(0)}. Close windows if sensitive.`,
            type: "warning",
          });
        } else {
          newAlerts.push({
            title: "Clean Air Forecasted",
            desc: "Low pollution levels predicted for the next 72 hours.",
            type: "success",
          });
        }
        setAlerts(newAlerts);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("[useStationDetail] fetch failed:", err);
        setError("Failed to load station details.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [stationId]);

  return { history, forecasts, intelligence, alerts, loading, error };
}
