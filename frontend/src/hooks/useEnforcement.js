import { useState, useEffect, useCallback } from "react";
import { getEnforcementDashboard } from "@/services/api";

export function useEnforcement() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true); // start true to avoid blank flash
  const [error, setError] = useState(null);

  const fetchData = useCallback(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    getEnforcementDashboard(controller.signal)
      .then((result) => {
        setData(result);
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          console.error("[useEnforcement] fetch failed:", err);
          setError("Failed to load Municipal Command Center. Is the backend running?");
        }
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, []);

  useEffect(() => {
    const cleanup = fetchData();
    return cleanup;
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}
