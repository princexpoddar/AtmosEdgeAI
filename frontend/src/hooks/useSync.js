import { useState, useRef, useCallback } from "react";
import { syncCPCB, getSyncStatus } from "@/services/api";

export function useSync(onComplete) {
  const [syncing, setSyncing] = useState(false);
  const [syncOk, setSyncOk] = useState(false);
  const [error, setSyncError] = useState(null);
  const pollRef = useRef(null);
  const controllerRef = useRef(null);

  const handleSync = useCallback(async () => {
    setSyncing(true);
    setSyncError(null);
    setSyncOk(false);

    // Clean up any previous poll
    if (pollRef.current) clearInterval(pollRef.current);
    if (controllerRef.current) controllerRef.current.abort();

    controllerRef.current = new AbortController();
    const { signal } = controllerRef.current;

    try {
      await syncCPCB(signal);

      let attempts = 0;
      const maxAttempts = 24;

      pollRef.current = setInterval(async () => {
        try {
          const status = await getSyncStatus(signal);
          attempts++;
          const done =
            status.status === "completed" ||
            status.status === "failed" ||
            attempts >= maxAttempts;

          if (done) {
            clearInterval(pollRef.current);
            setSyncing(false);
            if (status.status === "failed") {
              setSyncError("Sync failed: " + JSON.stringify(status.last_result));
            } else {
              setSyncOk(true);
              setTimeout(() => {
                setSyncOk(false);
                onComplete?.();
              }, 2000);
            }
          }
        } catch (err) {
          if (err.name !== "AbortError") {
            // poll errors are silent — keep retrying until maxAttempts
          }
        }
      }, 5000);
    } catch (err) {
      if (err.name !== "AbortError") {
        setSyncError(err.message || "Failed to trigger live update.");
      }
      setSyncing(false);
    }
  }, [onComplete]);

  // Cleanup on unmount
  const cleanup = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (controllerRef.current) controllerRef.current.abort();
  }, []);

  return { syncing, syncOk, syncError: error, handleSync, cleanup };
}
