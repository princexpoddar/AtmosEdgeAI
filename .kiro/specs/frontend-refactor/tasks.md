# Implementation Plan: AtmosEdgeAI Frontend Refactor

## Overview

Convert the monolithic Vite + React 19 application into a structured, production-quality frontend. Tasks proceed in dependency order: tooling first, then constants and services, then context and hooks, then UI primitives, then page decomposition, then component fixes, then performance, then testing. Each task builds directly on previous ones, with no orphaned code.

## Tasks

- [x] 1. Install dependencies and configure tooling
  - Add `react-router-dom`, `react-leaflet`, `leaflet`, `lucide-react`, `@fontsource/inter`, `@fontsource/jetbrains-mono` to `dependencies` in `package.json`
  - Add `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@fast-check/vitest`, `rollup-plugin-visualizer` to `devDependencies`
  - Add `test` script to `package.json`: `"test": "vitest --run"`
  - Update `vite.config.js`: add `@/` → `src/` path alias and `rollup-plugin-visualizer` plugin
  - Create `src/test/setup.js` importing `@testing-library/jest-dom`
  - Add `vitest` config block to `vite.config.js` with `environment: "jsdom"` and `setupFiles`
  - Create `.env.example` with `VITE_API_URL=http://127.0.0.1:8001`
  - _Requirements: 1.1, 1.2, 1.3, 1.6, 20.1_

  - [x]* 1.1 Write example test: package.json has required dependencies
    - Assert `dependencies` contains `react-router-dom`, `react-leaflet`, `leaflet`, `lucide-react`
    - Assert `devDependencies` contains `vitest`, `@testing-library/react`, `@fast-check/vitest`
    - Assert `.env.example` exists and contains `VITE_API_URL`
    - _Requirements: 1.1, 1.2, 1.6_

- [x] 2. Strip CDN tags and update index.html
  - Remove the Leaflet CDN `<link>` and `<script>` tags from `index.html`
  - Remove the FontAwesome CDN `<link>` tag from `index.html`
  - Add `<meta name="description">` and Open Graph `<meta>` tags (title, description, image, url)
  - _Requirements: 2.1, 2.5_

  - [x]* 2.1 Write example test: index.html has no CDN references and has meta tags
    - Parse `index.html` and assert zero occurrences of `unpkg.com`, `cdnjs.cloudflare.com`, `fonts.googleapis.com`
    - Assert presence of `<meta name="description">`, `<meta property="og:title">`, `<meta property="og:description">`
    - _Requirements: 2.1, 2.5_

- [x] 3. Create AQI constants module
  - Create `src/constants/aqi.js`
  - Define `AQI_THRESHOLDS` array with all six categories: good (≤50), satisfactory (≤100), moderate (≤200), poor (≤300), very-poor (≤400), severe (>400)
  - Each threshold entry contains `max`, `slug`, `label`, and `color` (hex string)
  - Export `getAqiSlug(aqi)`, `getAqiColor(aqi)`, `getAqiLabel(aqi)` functions
  - Export `AQI_HEAT_MAP` for heatmap color class lookup: `{ good: "heat-good", satisfactory: "heat-satisfactory", ... }`
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [ ]* 3.1 Write property test: AQI functions return well-formed outputs (Property 1)
    - **Property 1: AQI functions return well-formed outputs for all valid inputs**
    - Use `testProp` from `@fast-check/vitest` with `fc.integer({ min: 0, max: 600 })`
    - Assert `getAqiSlug` returns one of the six known slugs
    - Assert `getAqiColor` matches `/^#[0-9a-fA-F]{6}$/`
    - Assert `getAqiLabel` returns a non-empty string
    - Min 100 runs — `{ numRuns: 100 }`
    - **Validates: Requirements 8.2, 8.3, 8.4**

  - [ ]* 3.2 Write property test: AQI slug monotonicity (Property 2)
    - **Property 2: AQI functions are monotonically consistent with thresholds**
    - Use `fc.tuple(fc.integer({min:0,max:99}), fc.integer({min:100,max:600}))` to generate pairs that span a threshold boundary
    - Assert `getAqiSlug(a) !== getAqiSlug(b)` when `a` and `b` are on opposite sides of any threshold
    - Min 100 runs
    - **Validates: Requirements 8.2**

- [x] 4. Centralize API service
  - Update `src/services/api.js` to read base URL from `import.meta.env.VITE_API_URL + "/api"`
  - Remove the hardcoded `const API_BASE = "http://127.0.0.1:8001/api"` line
  - Update every exported function to accept a `signal` parameter and pass it to `fetch`
  - Add `getSyncStatus(signal)` function for polling `/api/aqi/sync/status`
  - Ensure every function throws an `Error` with a human-readable message on non-OK responses
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6_

  - [ ]* 4.1 Write property test: API rejects non-OK responses (Property 3)
    - **Property 3: API Service rejects non-OK responses with an error**
    - Use `fc.constantFrom(...Object.keys(apiExports))` to pick any exported API function
    - Mock `fetch` to return `{ ok: false, status: fc.integer({min:400,max:599}), statusText: "Error" }`
    - Assert the function rejects with an `Error` instance with non-empty `message`
    - Min 100 runs
    - **Validates: Requirements 3.3**

  - [ ]* 4.2 Write property test: API attaches AbortSignal (Property 4)
    - **Property 4: API Service attaches AbortController signal to every fetch call**
    - For each exported API function, call it with a known `AbortSignal` instance
    - Spy on `fetch` and assert the `signal` option matches the provided signal
    - Min 100 runs (one per API function, plus random signal instances)
    - **Validates: Requirements 3.2**

- [x] 5. Create ThemeContext
  - Create `src/context/ThemeContext.jsx`
  - Implement `ThemeProvider` component that reads initial theme from `localStorage["theme"]`, defaults to `"dark"`
  - On theme change: write to `localStorage` and update `document.documentElement.dataset.theme`
  - Export `useTheme()` hook that returns `{ theme, toggleTheme }`
  - Wrap the `localStorage` access in a try/catch to handle private browsing
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 5.1 Write property test: ThemeContext round-trip (Property 5)
    - **Property 5: ThemeContext round-trip — toggle persists and initializes correctly**
    - Use `fc.constantFrom("dark", "light")` as arbitrary starting theme
    - Render `ThemeProvider`, call `toggleTheme`, assert `localStorage["theme"]` and `document.documentElement.dataset.theme` are updated
    - Unmount, set `localStorage["theme"]` to saved value, remount — assert theme initializes to that value
    - Min 100 runs
    - **Validates: Requirements 7.2, 7.3, 7.4**

- [x] 6. Implement custom data hooks
  - Create `src/hooks/useStations.js`:
    - Fetch stations with `AbortController`
    - Expose `useMemo`-memoized list sorted by AQI descending
    - Expose `{ stations, loading, error, refresh }`
  - Create `src/hooks/useStationDetail.js`:
    - Accept `stationId` parameter
    - Fetch history, forecast, and intelligence in parallel via `Promise.all`
    - Use `AbortController`; re-fetch when `stationId` changes
    - Expose `{ history, forecasts, intelligence, loading, error }`
  - Create `src/hooks/useEnforcement.js`:
    - Fetch enforcement dashboard data with `AbortController`
    - Expose `{ data, loading, error }`
  - Create `src/hooks/useSync.js`:
    - Call `syncCPCB()` on trigger; poll `getSyncStatus()` every 5s until done or 24 attempts
    - Use `AbortController` on cleanup; expose `{ syncing, syncOk, handleSync }`
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [ ]* 6.1 Write property test: useStations aborts on unmount (Property 6)
    - **Property 6: useStations hook aborts in-flight requests on unmount**
    - Use `renderHook` with a delayed mock fetch
    - Unmount the hook before fetch resolves
    - Assert `abortController.abort` was called
    - Min 100 runs (varying delay times)
    - **Validates: Requirements 6.5**

  - [ ]* 6.2 Write property test: useStationDetail aborts on unmount (Property 7)
    - **Property 7: useStationDetail hook aborts on unmount**
    - Same pattern as Property 6 but for `useStationDetail`
    - Use `fc.string()` as arbitrary station IDs
    - Min 100 runs
    - **Validates: Requirements 6.5**

  - [ ]* 6.3 Write property test: sorted station list is stable (Property 8)
    - **Property 8: Sorted station list is stable across re-renders**
    - Use `fc.array(fc.record({ id: fc.string(), aqi: fc.float({min:0,max:500}) }), {minLength:1})`
    - Render hook twice with the same input; assert the returned `stations` array is sorted by AQI descending
    - Assert referential identity is stable on re-render without input change
    - Min 100 runs
    - **Validates: Requirements 6.6, 17.1**

- [x] 7. Checkpoint — ensure all existing tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Build UI primitive components
  - Create `src/components/ui/Button.jsx` — accepts `variant` (primary/secondary/ghost), `size` (sm/md), `disabled`, `onClick`, `children`; uses only CSS classes
  - Create `src/components/ui/Badge.jsx` — accepts `variant` (aqi slug or status), `children`; uses CSS class `badge badge-{variant}`
  - Create `src/components/ui/Card.jsx` — wrapper div with `card` CSS class, accepts `className` and `children`
  - Create `src/components/ui/Skeleton.jsx` — shimmer placeholder; accepts `width`, `height`, `className` as CSS custom properties or class names
  - Create `src/components/ui/Spinner.jsx` — spinning loader; accepts `size` (sm/md/lg)
  - Create `src/components/ui/Banner.jsx` — full-width banner; accepts `variant` (error/success/warning), `children`
  - Add any missing CSS class definitions for these components to `App.css`
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [ ]* 8.1 Write smoke tests for all UI primitives
    - Render each component with valid props and assert it mounts without throwing
    - _Requirements: 9.1–9.6_

- [x] 9. Add missing CSS class definitions
  - Add `aqi-indicator-pill` class to `App.css` plus modifier classes: `.aqi-indicator-pill.good`, `.aqi-indicator-pill.satisfactory`, `.aqi-indicator-pill.moderate`, `.aqi-indicator-pill.poor`, `.aqi-indicator-pill.very-poor`, `.aqi-indicator-pill.severe`
  - Add heatmap cell classes: `heatmap-cell`, `heat-good`, `heat-satisfactory`, `heat-moderate`, `heat-poor`, `heat-very-poor`, `heat-severe`, `heat-empty`
  - Add `error-boundary-fallback` class for ErrorBoundary fallback UI
  - Add skeleton shimmer keyframe animation and `.skeleton` base class
  - Replace `@import url('https://fonts.googleapis.com/...')` at top of `App.css` with npm `@fontsource` imports in `main.jsx`
  - _Requirements: 11.2, 11.3, 11.4_

  - [ ]* 9.1 Write example tests: CSS classes are defined
    - Read `App.css` text and assert it contains `aqi-indicator-pill`, `heatmap-cell`, `heat-good`, `heat-moderate`, `heat-severe`, `heat-empty`
    - _Requirements: 11.3, 11.4_

- [x] 10. Create ErrorBoundary component
  - Create `src/components/ErrorBoundary.jsx` as a class component
  - Implement `getDerivedStateFromError` to set `hasError: true`
  - Implement `componentDidCatch` to log error and `info.componentStack` to console
  - Render fallback div with class `error-boundary-fallback` containing a heading and description — no stack trace in the UI
  - _Requirements: 15.1, 15.2, 15.3, 15.4_

  - [ ]* 10.1 Write property test: ErrorBoundary shows fallback and hides stack trace (Property 10)
    - **Property 10: ErrorBoundary shows fallback and hides stack trace**
    - Use `fc.string()` as arbitrary error messages thrown by a child component
    - Wrap a throwing component in `ErrorBoundary`; assert rendered output contains "Something went wrong"
    - Assert rendered output does NOT contain the thrown error message string or any stack trace content
    - Min 100 runs
    - **Validates: Requirements 15.2, 15.4**

- [x] 11. Extract layout components (Navbar, Sidebar, RightPanel)
  - Create `src/components/layout/Navbar.jsx`:
    - Extract the `<header className="topbar">` block from `App.jsx`
    - Replace all `<i className="fa ...">` icons with lucide-react equivalents: `RefreshCw` for sync, `Bell` for alerts, `Sun`/`Moon` for theme toggle
    - Use `useNavigate` and `useLocation` from `react-router-dom` for nav link active states
    - Consume `useTheme()` from ThemeContext for theme toggle
    - Use `useSync` hook for sync button state
    - Zero inline `style={{...}}` props — all CSS classes
  - Create `src/components/layout/Sidebar.jsx`:
    - Extract the left panel (station list, AQI ring, metrics grid) from the Dashboard view
    - Accept `stations`, `selectedStationId`, `onSelectStation` as props
    - Use `Badge` and `Card` primitives; zero inline styles
  - Create `src/components/layout/RightPanel.jsx`:
    - Extract the right analytics panel (forecast cards, tabs) from the Dashboard view
    - Accept `forecasts`, `intelligence`, `stationHistory` as props; zero inline styles
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [ ]* 11.1 Write property test: no inline style attributes in layout components (Property 11)
    - **Property 11: Components render without inline style attributes**
    - Render `Navbar`, `Sidebar`, `RightPanel` with minimal valid props
    - Query all DOM elements and assert none have a `style` attribute set
    - Min 100 runs (vary prop values using fast-check)
    - **Validates: Requirements 10.5, 11.1**

- [x] 12. Create Enforcement page
  - Create `src/pages/Enforcement.jsx`
  - Move all ~200 lines of the `viewMode === "enforcement"` block from `App.jsx` into this file
  - Wire to `useEnforcement` hook instead of inline state/fetch
  - Replace all inline `style={{...}}` props with CSS classes; add any new classes needed to `App.css`
  - Add `Skeleton` placeholders for the loading state instead of the pulse spinner
  - _Requirements: 5.5, 11.1_

- [ ] 13. Create Dashboard page
  - Create `src/pages/Dashboard.jsx`
  - Compose `Navbar`, `Sidebar`, `Map`, `Analytics`, `Explainability`, `Comparison`, `RightPanel` inside a layout grid using CSS classes (no inline styles)
  - Wire `useStations` and `useStationDetail(selectedStationId)` hooks
  - Wire `useSync` for the sync button
  - Manage `selectedStationId`, `activeMapLayer`, `dashboardTab` state locally in this component
  - Stop the countdown timer when the current route is not `/dashboard` (use `useLocation`)
  - Add loading skeleton for the station list section while `useStations` loading is true
  - _Requirements: 5.6, 6.7, 9.7_

  - [ ]* 13.1 Write property test: no inline styles in Dashboard page (Property 11 extension)
    - Render `Dashboard` with mocked hooks and assert zero style attributes in the DOM
    - **Validates: Requirements 11.5**

- [x] 14. Refactor App.jsx to ≤100 lines
  - Rewrite `App.jsx` to import and render only: `ThemeProvider`, `BrowserRouter`, `ErrorBoundary`, `Suspense`, and route definitions
  - Use `React.lazy` for `Dashboard`, `Predictor`, and `Enforcement` pages
  - Use `Suspense` with a `Spinner` fallback wrapping all lazy routes
  - Wrap all routes in `ErrorBoundary`
  - Add `<Navigate to="/" replace />` for unmatched routes
  - Zero inline styles, zero data fetching, zero local state
  - Import `@fontsource/inter` and `@fontsource/jetbrains-mono` in `main.jsx`
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 15.3, 16.1, 16.2, 16.3, 16.4_

  - [ ]* 14.1 Write example test: App.jsx is ≤100 lines
    - Read `src/App.jsx` with `fs.readFileSync`, count non-empty lines, assert ≤100
    - _Requirements: 5.1_

  - [ ]* 14.2 Write example test: routes render correct pages
    - Use `MemoryRouter` to navigate to `/`, `/dashboard`, `/predictor`, `/enforcement`
    - Assert each route renders the correct page component (by heading text or test id)
    - Assert unknown route redirects to `/`
    - _Requirements: 4.1–4.5_

  - [ ]* 14.3 Write example test: lazy pages are loaded with React.lazy
    - Import `App.jsx` and inspect that Dashboard, Predictor, Enforcement are lazy components
    - Assert each is an object with `$$typeof === Symbol(react.lazy)`
    - _Requirements: 16.1, 16.2, 16.3_

- [x] 15. Checkpoint — ensure all tests pass and build succeeds
  - Ensure all tests pass, ask the user if questions arise.

- [x] 16. Fix Analytics component
  - Update `src/components/charts/Analytics.jsx`
  - Replace the bogus heatmap index arithmetic with a `useMemo`-computed `(dayOfWeek × 24 + hour)` → value grid built from actual record timestamps using `new Date(record.timestamp)`
  - Import `getAqiSlug` from `src/constants/aqi.js` and use `AQI_HEAT_MAP` for color classes
  - Replace all inline `style={{...}}` props with CSS classes
  - Add `Skeleton` rows (using the `Skeleton` primitive) for the loading state
  - _Requirements: 8.5, 11.1, 12.1, 12.2, 12.3, 12.4_

  - [ ]* 16.1 Write property test: Analytics heatmap slot correctness (Property 9)
    - **Property 9: Analytics heatmap maps cells to correct (day, hour) slots**
    - Use `fc.array(fc.record({ timestamp: fc.date(), pm25: fc.float({min:0,max:500}) }), {minLength:1})`
    - Render `Analytics` with the generated history; for each record, assert the cell at `(dayOfWeek, hour)` position has the correct class
    - Assert cells with no matching record have the `heat-empty` class
    - Min 100 runs
    - **Validates: Requirements 12.1, 12.2**

- [x] 17. Fix Explainability component
  - Update `src/components/charts/Explainability.jsx`
  - Remove the local `const API_BASE = "http://127.0.0.1:8001/api"` constant and the direct `fetch` call
  - Replace with `getFeatureImportance(signal)` from `api.js` called with an `AbortController` signal (or accept data from the parent `useStationDetail` hook via props)
  - Remove all hardcoded static SHAP data arrays — display only real API-returned data
  - Replace all inline `style={{...}}` props with CSS classes
  - Add `Skeleton` rows for the loading state
  - _Requirements: 3.4, 3.5, 13.1, 13.2, 13.3, 13.4_

  - [ ]* 17.1 Write property test: Explainability renders API data (Property 12)
    - **Property 12: Explainability renders API data for any station ID**
    - Use `fc.array(fc.record({ feature: fc.string({minLength:1}), importance: fc.float({min:0,max:1}) }), {minLength:1,maxLength:10})`
    - Mock `getFeatureImportance` to resolve with the generated data
    - Assert each feature name appears in the rendered output
    - Use `fc.string()` as arbitrary station IDs and assert re-fetch is triggered on change
    - Min 100 runs
    - **Validates: Requirements 13.2, 13.3**

- [x] 18. Fix Map component
  - Update `src/components/map/Map.jsx`
  - Remove all `window.L` references and the CDN-loaded Leaflet polling logic
  - Import from `react-leaflet` (`MapContainer`, `TileLayer`, `Marker`) and `import L from "leaflet"` with `import "leaflet/dist/leaflet.css"`
  - Use `useRef` to store a `{ [stationId]: markerRef }` map
  - On stations update: iterate and call `markerRef.current[id].setIcon(buildIcon(st))` instead of removing/re-adding markers
  - Replace the `<i className="fa fa-search">` with `<Search size={14} />` from `lucide-react`
  - Replace the loading state with a `Skeleton` component of the same dimensions
  - Replace all inline `style={{...}}` props with CSS classes
  - _Requirements: 2.4, 14.1, 14.2, 14.3, 14.4, 14.5_

  - [ ]* 18.1 Write property test: Map marker count equals station count (Property 14)
    - **Property 14: Map marker count equals station count after updates**
    - Use `fc.array(fc.record({ id: fc.uuid(), latitude: fc.float({min:8,max:37}), longitude: fc.float({min:68,max:97}), aqi: fc.integer({min:0,max:500}) }), {minLength:1,maxLength:30})`
    - Render `Map` with generated stations; assert number of markers equals station count
    - Update the stations array (different AQI values, same IDs); assert marker count is unchanged
    - Min 100 runs
    - **Validates: Requirements 14.2**

- [x] 19. Migrate Comparison, LandingPage, and Predictor to use AQI constants and CSS classes
  - Update `src/components/cards/Comparison.jsx`:
    - Replace local `getAqiClass` function with `getAqiSlug` from `src/constants/aqi.js`
    - Replace all inline `style={{...}}` props with CSS classes
  - Update `src/pages/LandingPage.jsx`:
    - Replace local `getAqiCategoryText` and `getAqiColor` functions with imports from `src/constants/aqi.js`
    - Wrap the national AQI average calculation in `useMemo`
    - Replace `<i className="fa ...">` icons with lucide-react equivalents (`Globe`, `Flame`, `PieChart`, `CheckCircle2`)
    - Replace all inline `style={{...}}` props with CSS classes
  - Update `src/pages/Predictor.jsx`:
    - Replace local `getAqiColor` with import from `src/constants/aqi.js`
    - Replace all inline `style={{...}}` props with CSS classes
  - _Requirements: 8.5, 8.6, 11.1, 17.2_

  - [ ]* 19.1 Write property test: LandingPage average is memoization-stable (Property 13)
    - **Property 13: LandingPage national average is stable across re-renders**
    - Use `fc.array(fc.record({ aqi: fc.float({min:0,max:500}) }), {minLength:1})`
    - Render `LandingPage` with generated stations; trigger a re-render without changing stations input
    - Assert the displayed average value is stable (no spurious recalculation)
    - Min 100 runs
    - **Validates: Requirements 17.2**

  - [ ]* 19.2 Write property test: no inline styles in page components (Property 11 extension)
    - Render `LandingPage`, `Predictor`, and `Comparison` with minimal props
    - Assert zero DOM elements have a `style` attribute
    - **Validates: Requirements 11.1, 11.5**

- [x] 20. Write smoke tests for key components
  - Create `src/test/smoke.test.jsx`
  - Render `LandingPage` with an empty stations array; assert no errors thrown
  - Render `Predictor` with a minimal stations array; assert no errors thrown
  - Render `Navbar` wrapped in `MemoryRouter` and `ThemeProvider`; assert no errors thrown
  - Assert the `Navbar` rendered output contains zero `<i>` elements with a class beginning with `fa`
  - _Requirements: 10.4, 18.1, 18.2, 18.3_

- [x] 21. Final checkpoint — full test suite and build
  - Ensure all tests pass (`npm run test`)
  - Ensure `npm run build` completes with zero warnings
  - Ensure `npm run lint` reports zero errors
  - Ask the user if any questions arise.
  - _Requirements: 1.4, 1.5_

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP delivery
- Each task references specific requirements for traceability
- Property tests use `@fast-check/vitest` with minimum 100 runs each
- Unit/example tests use `@testing-library/react` and vitest
- Checkpoints at tasks 7, 15, and 21 ensure incremental validation
- The `@/` path alias should be used in all new imports after task 1 is complete
