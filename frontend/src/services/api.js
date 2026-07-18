const API_BASE = (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8001") + "/api";

async function apiFetch(url, options = {}) {
  const r = await fetch(url, options);
  if (!r.ok) throw new Error(`API ${r.status}: ${url}`);
  return r.json();
}

export async function getStations() {
  return apiFetch(`${API_BASE}/stations`);
}

export async function getMonitoring() {
  return apiFetch(`${API_BASE}/monitoring`);
}

export async function getStationHistory(id, days = 7) {
  return apiFetch(`${API_BASE}/stations/${id}/history?days=${days}`);
}

export async function getStationForecast(id) {
  return apiFetch(`${API_BASE}/stations/${id}/forecast`);
}

export async function getStationExplainability(id) {
  return apiFetch(`${API_BASE}/stations/${id}/explainability`);
}

export async function getFeatureImportance() {
  return apiFetch(`${API_BASE}/feature-importance`);
}

export async function submitPrediction(stationId, horizon = 24) {
  const r = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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

export async function syncCPCB() {
  return apiFetch(`${API_BASE}/aqi/sync`, { method: "POST" });
}

export async function getSyncStatus() {
  return apiFetch(`${API_BASE}/aqi/sync/status`);
}

export async function getStationIntelligence(id) {
  return apiFetch(`${API_BASE}/v1/intelligence/${id}`);
}

export async function getEnforcementDashboard() {
  return apiFetch(`${API_BASE}/v1/enforcement`);
}

export async function getProviderDiagnostics() {
  return apiFetch(`${API_BASE}/v1/diagnostics/providers`);
}
