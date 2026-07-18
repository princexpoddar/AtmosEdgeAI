import { useState, useRef, useCallback } from "react";
import { syncCPCB, getSyncStatus } from "@/services/api";

export function useSync(onComplete) {
  const [syncing,  setSyncing]   = useState(false);
  const [syncOk,   setSyncOk]    = useState(false);
  const [error,    setSyncError] = useState(null);
  const pollRef = useRef(null);

  const handleSync = useCallback(async () => {
    // Clear any previous poll
    if (pollRef.current) clearInterval(pollRef.current);

    setSyncing(true);
    setSyncError(null);
    setSyncOk(false);

    try {
      await syncCPCB();

      let attempts   = 0;
      const maxAttempts = 24; // 24 × 5s = 2 minutes max

      pollRef.current = setInterval(async () => {
        try {
          const status = await getSyncStatus();
          attempts++;

          const done =
            status.status === "success"   ||
            status.status === "completed" ||
            status.status === "failed"    ||
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
        } catch {
          // poll errors are silent — keep retrying until maxAttempts
        }
      }, 5000);
    } catch (err) {
      setSyncError(err.message || "Failed to trigger live update.");
      setSyncing(false);
    }
  }, [onComplete]);

  return { syncing, syncOk, syncError: error, handleSync };
}
