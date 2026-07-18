import { useEffect, useState } from "react";
import { getFeatureImportance } from "@/services/api";
import Skeleton from "@/components/ui/Skeleton";

export default function Explainability({ stationId }) {
  const [importance, setImportance] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    getFeatureImportance(controller.signal)
      .then((data) => setImportance(data.slice(0, 10)))
      .catch((err) => {
        if (err.name !== "AbortError") setImportance([]);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [stationId]);

  if (loading) {
    return (
      <div className="explainability-root">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} height="24px" />
        ))}
      </div>
    );
  }

  return (
    <div className="explainability-root">
      {/* Global Feature Importances */}
      <div>
        <h4 className="explainability-section-title">
          Global Model Feature Weights (XGBoost F-Scores)
        </h4>
        {importance.length === 0 ? (
          <p className="empty-state">Feature importance data unavailable.</p>
        ) : (
          <div className="fi-list">
            {importance.map((item, idx) => (
              <div key={idx} className="fi-row">
                <span className="fi-name">{item.feature}</span>
                <div className="fi-bar-track">
                  <div
                    className="fi-bar-fill"
                    style={{ width: `${item.importance * 100}%` }}
                  />
                </div>
                <span className="fi-pct">{(item.importance * 100).toFixed(1)}%</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
