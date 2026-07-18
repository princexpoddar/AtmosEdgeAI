import { useState, useEffect } from "react";
import { getEnforcementDashboard } from "@/services/api";

export function useEnforcement() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    getEnforcementDashboard(controller.signal)
      .then(setData)
      .catch((err) => {
        if (err.name !== "AbortError") {
          setError("Failed to fetch municipal command center telemetry.");
        }
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, []);

  return { data, loading, error };
}
