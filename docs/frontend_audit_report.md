# AtmosEdgeAI Frontend Dependency & Usage Audit Report

This report presents a thorough audit of the Vite-React frontend directory, checking routing, component tree imports, assets usage, and npm package dependencies.

---

## 1. Routing & Reachability
* **Routing Mechanism**: State-based view routing inside `App.jsx` using `viewMode` state.
* **Reachable Routes**:
  * `viewMode === "landing"` (Renders `<LandingPage />`) → **REACHABLE** (Default viewport on load)
  * `viewMode === "dashboard"` (Renders live metrics, map overlays, forecasts, and attributions) → **REACHABLE** (Via header link or main CTAs)
  * `viewMode === "predictor"` (Renders Custom Predictor REST testing pane) → **REACHABLE** (Via header link or CTAs)

---

## 2. Component Directory Audit

| Component | File Path | Imported By | Usage / Role | Status |
|---|---|---|---|---|
| **App** | `src/App.jsx` | `src/main.jsx` | Main application shell, state management, timer loops | **ACTIVE** |
| **LandingPage** | `src/components/LandingPage.jsx` | `src/App.jsx` | Product intro page, live average AQI, MLOps benchmarks | **ACTIVE** |
| **Map** | `src/components/Map.jsx` | `src/App.jsx` | Leaflet spatial station map plot | **ACTIVE** |
| **Analytics** | `src/components/Analytics.jsx` | `src/App.jsx` | Grafana SVG lines trend, weekly diurnal heatmap grid | **ACTIVE** |
| **Explainability**| `src/components/Explainability.jsx`| `src/App.jsx` | Local SHAP force pushes and global feature weight charts | **ACTIVE** |
| **Comparison** | `src/components/Comparison.jsx` | `src/App.jsx` | Station side-by-side comparators | **ACTIVE** |
| **Predictor** | `src/components/Predictor.jsx` | `src/App.jsx` | Custom REST API predict query runner | **ACTIVE** |

* **Unimported Components**: None. Every `.jsx` file under `src/components` is actively imported in `App.jsx`.

---

## 3. Hooks & Context Providers
* **Custom Hooks**: None defined. The project relies strictly on built-in React hooks (`useState`, `useEffect`, `useRef`).
* **Context / Providers**: None defined. Application state (theme, selected station, lists) is stored globally in `App.jsx` and passed down via props.

---

## 4. REST API Integration Audit

| Endpoint | Called By Component | Trigger event | Role |
|---|---|---|---|
| `GET /api/stations` | `App.jsx` | Mount & Auto-Refresh | Feeds Map and Station Lists |
| `GET /api/monitoring` | `App.jsx` | Mount & Auto-Refresh | Feeds MLOps telemetry indicator |
| `GET /api/feature-importance`| `Explainability.jsx` | Mount | Feeds global feature weight bar charts |
| `GET /api/stations/{id}/history`| `App.jsx` | selectedStationId changes | Feeds Grafana Analytics and trends |
| `GET /api/stations/{id}/forecast`| `App.jsx` | selectedStationId changes | Feeds forecast horizons card |
| `GET /api/stations/{id}/explainability`| `App.jsx` | selectedStationId changes | Feeds physical attributions bars |
| `POST /api/predict` | `App.jsx` / `Predictor.jsx` | Form submit | Computes predictions for custom payloads |
| `POST /api/aqi/sync` | `App.jsx` | Click sync button | Syncs live CPCB database observations |

---

## 5. Assets Audit (Images, Icons & Fonts)

| Asset File | Path | Referenced In Code? | Status | Action |
|---|---|---|---|---|
| `favicon.svg` | `public/favicon.svg` | `index.html` (Shortcut icon) | **ACTIVE** | Keep |
| `icons.svg` | `public/icons.svg` | None | **DEAD** | **Delete** |
| `hero.png` | `src/assets/hero.png` | None | **DEAD** | **Delete** |
| `react.svg` | `src/assets/react.svg` | None | **DEAD** | **Delete** |
| `vite.svg` | `src/assets/vite.svg` | None | **DEAD** | **Delete** |

---

## 6. npm Dependencies Audit
* **Dependencies in `package.json`**:
  * `react`: **Used** (Base virtual DOM library)
  * `react-dom`: **Used** (App root injection wrapper in `main.jsx`)
* **Dev Dependencies**:
  * `vite`: **Used** (Vite bundler and dev server runner)
  * `@vitejs/plugin-react`: **Used** (Vite react compilation middleware)
  * `oxlint`: **Used** (Linter configuration)
  * `@types/react` / `@types/react-dom`: **Used** (React typing parameters)
* **Unused Packages**: None. The `package.json` is extremely clean.

---

## 7. Cleanup Targets (Safely Deletable Files)
1. **`frontend/src/components/common/`** (Empty directory)
2. **`frontend/src/assets/hero.png`** (Unreferenced image)
3. **`frontend/src/assets/react.svg`** (Unreferenced SVG icon)
4. **`frontend/src/assets/vite.svg`** (Unreferenced SVG icon)
5. **`frontend/public/icons.svg`** (Unreferenced SVG asset file)
