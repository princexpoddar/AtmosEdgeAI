const API_BASE = "http://127.0.0.1:8001/api";

export async function getStations() {
  const r = await fetch(`${API_BASE}/stations`);
  if (!r.ok) throw new Error("Failed to load CPCB stations");
  return r.json();
}

export async function getMonitoring() {
  const r = await fetch(`${API_BASE}/monitoring`);
  if (!r.ok) throw new Error("Failed to load MLOps telemetry stats");
  return r.json();
}

export async function getStationHistory(id, days = 7) {
  const r = await fetch(`${API_BASE}/stations/${id}/history?days=${days}`);
  if (!r.ok) throw new Error("Failed to load station history");
  return r.json();
}

export async function getStationForecast(id) {
  const r = await fetch(`${API_BASE}/stations/${id}/forecast`);
  if (!r.ok) throw new Error("Failed to load station forecasts");
  return r.json();
}

export async function getStationExplainability(id) {
  const r = await fetch(`${API_BASE}/stations/${id}/explainability`);
  if (!r.ok) throw new Error("Failed to load station explanation parameters");
  return r.json();
}

export async function getFeatureImportance() {
  const r = await fetch(`${API_BASE}/feature-importance`);
  if (!r.ok) throw new Error("Failed to load global feature weights");
  return r.json();
}

export async function submitPrediction(stationId, horizon = 24) {
  const r = await fetch(`${API_BASE}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      station_id: String(stationId),
      forecast_horizon: Number(horizon)
    })
  });
  
  if (!r.ok) {
    const errorData = await r.json().catch(() => ({}));
    throw new Error(errorData?.detail?.message || "Not enough observations to generate a reliable forecast.");
  }
  return r.json();
}

export async function syncCPCB() {
  const r = await fetch(`${API_BASE}/aqi/sync`, { method: "POST" });
  if (!r.ok) throw new Error("Failed database sync");
  return r.json();
}

export async function getStationIntelligence(id) {
  const r = await fetch(`${API_BASE}/v1/intelligence/${id}`);
  if (!r.ok) throw new Error("Failed to load AI intelligence reports");
  return r.json();
}

export async function getEnforcementDashboard() {
  const r = await fetch(`${API_BASE}/v1/enforcement`);
  if (!r.ok) throw new Error("Failed to load enforcement dashboard");
  return r.json();
}
