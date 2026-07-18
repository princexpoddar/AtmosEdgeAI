import { useState, useEffect, useMemo, useCallback } from "react";
import { getStations, getMonitoring } from "@/services/api";

export function useStations() {
  const [rawStations, setRawStations] = useState([]);
  const [monitoring, setMonitoring] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const load = useCallback((signal) => {
    setLoading(true);
    setError(null);
    return Promise.all([getStations(signal), getMonitoring(signal)])
      .then(([stList, monitor]) => {
        setRawStations(stList);
        setMonitoring(monitor);
        setLastUpdated(new Date().toLocaleTimeString());
        return stList;
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          setError("Database server offline. Using locally cached datasets.");
        }
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  // Memoized list sorted by AQI descending
  const stations = useMemo(
    () => [...rawStations].sort((a, b) => b.aqi - a.aqi),
    [rawStations]
  );

  const refresh = useCallback(() => {
    const controller = new AbortController();
    load(controller.signal);
  }, [load]);

  return { stations, monitoring, loading, error, lastUpdated, refresh };
}
