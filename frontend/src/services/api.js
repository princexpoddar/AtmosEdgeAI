const API_BASE = (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8001") + "/api";

export async function getStations(signal) {
  const r = await fetch(`${API_BASE}/stations`, { signal });
  if (!r.ok) throw new Error(`Failed to load CPCB stations: ${r.status}`);
  return r.json();
}

export async function getMonitoring(signal) {
  const r = await fetch(`${API_BASE}/monitoring`, { signal });
  if (!r.ok) throw new Error(`Failed to load MLOps telemetry stats: ${r.status}`);
  return r.json();
}

export async function getStationHistory(id, days = 7, signal) {
  const r = await fetch(`${API_BASE}/stations/${id}/history?days=${days}`, { signal });
  if (!r.ok) throw new Error(`Failed to load station history: ${r.status}`);
  return r.json();
}

export async function getStationForecast(id, signal) {
  const r = await fetch(`${API_BASE}/stations/${id}/forecast`, { signal });
  if (!r.ok) throw new Error(`Failed to load station forecasts: ${r.status}`);
  return r.json();
}

export async function getStationExplainability(id, signal) {
  const r = await fetch(`${API_BASE}/stations/${id}/explainability`, { signal });
  if (!r.ok) throw new Error(`Failed to load station explanation parameters: ${r.status}`);
  return r.json();
}

export async function getFeatureImportance(signal) {
  const r = await fetch(`${API_BASE}/feature-importance`, { signal });
  if (!r.ok) throw new Error(`Failed to load global feature weights: ${r.status}`);
  return r.json();
}

export async function submitPrediction(stationId, horizon = 24, signal) {
  const r = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    signal,
    body: JSON.stringify({
      station_id: String(stationId),
      forecast_horizon: Number(horizon),
    }),
  });
  if (!r.ok) {
    const errorData = await r.json().catch(() => ({}));
    throw new Error(errorData?.detail?.message || `Prediction failed: ${r.status}`);
  }
  return r.json();
}

export async function syncCPCB(signal) {
  const r = await fetch(`${API_BASE}/aqi/sync`, { method: "POST", signal });
  if (!r.ok) throw new Error(`Failed database sync: ${r.status}`);
  return r.json();
}

export async function getSyncStatus(signal) {
  const r = await fetch(`${API_BASE}/aqi/sync/status`, { signal });
  if (!r.ok) throw new Error(`Failed to load sync status: ${r.status}`);
  return r.json();
}

export async function getStationIntelligence(id, signal) {
  const r = await fetch(`${API_BASE}/v1/intelligence/${id}`, { signal });
  if (!r.ok) throw new Error(`Failed to load AI intelligence reports: ${r.status}`);
  return r.json();
}

export async function getEnforcementDashboard(signal) {
  const r = await fetch(`${API_BASE}/v1/enforcement`, { signal });
  if (!r.ok) throw new Error(`Failed to load enforcement dashboard: ${r.status}`);
  return r.json();
}
