/**
 * AQI Constants — single source of truth for AQI thresholds, slugs, labels, and colors.
 * All components and hooks that derive AQI category, color, or label must import from here.
 */

export const AQI_THRESHOLDS = [
  { max: 50,       slug: "good",         label: "Good",         color: "#10b981" },
  { max: 100,      slug: "satisfactory", label: "Satisfactory", color: "#3b82f6" },
  { max: 200,      slug: "moderate",     label: "Moderate",     color: "#f59e0b" },
  { max: 300,      slug: "poor",         label: "Poor",         color: "#ef4444" },
  { max: 400,      slug: "very-poor",    label: "Very Poor",    color: "#8b5cf6" },
  { max: Infinity, slug: "severe",       label: "Severe",       color: "#7c2d12" },
];

/**
 * Returns the CPCB category slug for a given AQI value.
 * @param {number} aqi
 * @returns {string} One of: "good" | "satisfactory" | "moderate" | "poor" | "very-poor" | "severe"
 */
export function getAqiSlug(aqi) {
  const threshold = AQI_THRESHOLDS.find((t) => aqi <= t.max);
  return threshold ? threshold.slug : "severe";
}

/**
 * Returns the hex color string for a given AQI value.
 * @param {number} aqi
 * @returns {string} A hex color string, e.g. "#10b981"
 */
export function getAqiColor(aqi) {
  const threshold = AQI_THRESHOLDS.find((t) => aqi <= t.max);
  return threshold ? threshold.color : AQI_THRESHOLDS[AQI_THRESHOLDS.length - 1].color;
}

/**
 * Returns the human-readable label for a given AQI value.
 * @param {number} aqi
 * @returns {string} e.g. "Good", "Satisfactory", "Moderate", etc.
 */
export function getAqiLabel(aqi) {
  const threshold = AQI_THRESHOLDS.find((t) => aqi <= t.max);
  return threshold ? threshold.label : AQI_THRESHOLDS[AQI_THRESHOLDS.length - 1].label;
}

/**
 * Maps AQI category slugs to CSS heatmap class names.
 */
export const AQI_HEAT_MAP = {
  good:         "heat-good",
  satisfactory: "heat-satisfactory",
  moderate:     "heat-moderate",
  poor:         "heat-poor",
  "very-poor":  "heat-very-poor",
  severe:       "heat-severe",
};

/**
 * Returns the CSS heat class for a numeric value.
 * Returns "heat-empty" if val is null, undefined, or 0.
 * @param {number|null|undefined} val
 * @returns {string} A CSS class name
 */
export function getHeatClass(val) {
  if (val === null || val === undefined || val === 0) {
    return "heat-empty";
  }
  const slug = getAqiSlug(val);
  return AQI_HEAT_MAP[slug] ?? "heat-empty";
}
