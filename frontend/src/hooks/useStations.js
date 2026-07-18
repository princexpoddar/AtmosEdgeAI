import { useState, useEffect, useMemo, useCallback } from "react";
import { getStations, getMonitoring } from "@/services/api";

export function useStations() {
  const [rawStations, setRawStations] = useState([]);
  const [monitoring, setMonitoring]   = useState(null);
  const [loading, setLoading]         = useState(true);   // start true – avoid blank flash
  const [error, setError]             = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [tick, setTick]               = useState(0);       // increment to force a refetch

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(null);

    Promise.all([getStations(), getMonitoring()])
      .then(([stList, monitor]) => {
        if (cancelled) return;
        setRawStations(stList);
        setMonitoring(monitor);
        setLastUpdated(new Date().toLocaleTimeString());
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("[useStations] fetch failed:", err);
        setError("Database server offline. Using locally cached datasets.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [tick]);

  // Memoised list sorted by AQI descending
  const stations = useMemo(
    () => [...rawStations].sort((a, b) => b.aqi - a.aqi),
    [rawStations]
  );

  const refresh = useCallback(() => setTick((t) => t + 1), []);

  return { stations, monitoring, loading, error, lastUpdated, refresh };
}
