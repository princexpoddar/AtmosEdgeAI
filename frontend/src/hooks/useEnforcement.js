import { useState, useEffect } from "react";
import { getEnforcementDashboard } from "@/services/api";

export function useEnforcement() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tick, setTick] = useState(0); // increment to force a refetch

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(null);

    getEnforcementDashboard()
      .then((result) => {
        if (!cancelled) {
          setData(result);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          console.error("[useEnforcement] fetch failed:", err);
          setError("Failed to load Municipal Command Center. Is the backend running?");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [tick]);

  const refetch = () => setTick((t) => t + 1);

  return { data, loading, error, refetch };
}
