# Requirements Document

## Introduction

AtmosEdgeAI is a Vite + React 19 environmental intelligence dashboard for air quality monitoring across India. The current frontend is a monolithic application with a ~600-line god component (`App.jsx`) that handles all state, routing, and rendering. It relies on CDN-loaded dependencies (Leaflet, FontAwesome, Google Fonts), hardcodes the backend URL across multiple files, duplicates AQI logic in five or more places, has missing CSS class definitions, and contains broken data mappings in chart components.

This spec covers a full production-quality refactor of the frontend. The goal is to decompose the monolith into a well-structured, maintainable React application with proper routing, custom hooks, reusable UI primitives, a single source of truth for AQI constants, skeleton loading states, error boundaries, and a clean build with zero warnings and zero lint errors. The stack remains Vite + React 19 + JavaScript (no TypeScript migration).

## Glossary

- **App**: The root React application component (`App.jsx`) after refactoring — renders only providers and router.
- **Router**: The `react-router-dom` v6 router providing URL-based navigation.
- **Page**: A top-level routed component representing one full view (Landing, Dashboard, Predictor, Enforcement).
- **Hook**: A custom React hook in `src/hooks/` that encapsulates data fetching and derived state.
- **API_Service**: The centralized API layer in `src/services/api.js`.
- **ThemeContext**: A React context providing dark/light theme state and toggle function to the component tree.
- **AQI_Constants**: The single source of truth module at `src/constants/aqi.js` for AQI category thresholds, colors, slugs, and labels.
- **UI_Primitives**: Reusable presentational components in `src/components/ui/` (Button, Badge, Card, Skeleton, Spinner, Banner).
- **Layout_Components**: Shared structural components in `src/components/layout/` (Navbar, Sidebar, RightPanel).
- **ErrorBoundary**: A React class component that catches rendering errors and displays a fallback UI.
- **Skeleton**: A placeholder loading component that visually approximates the shape of the content being loaded.
- **AbortController**: The browser API used to cancel in-flight fetch requests when a component unmounts.
- **VITE_API_URL**: The environment variable that supplies the backend base URL at build time.

---

## Requirements

### Requirement 1: Dependency Installation and Tooling Setup

**User Story:** As a developer, I want all dependencies managed via npm so that the application has no runtime CDN dependencies and the build is reproducible.

#### Acceptance Criteria

1. THE App SHALL declare `react-router-dom`, `react-leaflet`, `leaflet`, `lucide-react`, `@fontsource/inter`, and `@fontsource/jetbrains-mono` as npm dependencies in `package.json`.
2. THE App SHALL declare `vitest`, `@testing-library/react`, and `@testing-library/jest-dom` as devDependencies in `package.json`.
3. THE App SHALL configure a `@/` path alias resolving to `src/` in `vite.config.js`.
4. WHEN `npm run build` is executed, THE App SHALL complete with zero warnings.
5. WHEN `npm run lint` is executed, THE App SHALL report zero errors across all source files.
6. THE App SHALL include a `.env.example` file defining the `VITE_API_URL` variable with a placeholder value.

---

### Requirement 2: CDN Removal

**User Story:** As a developer, I want all external CDN tags removed from `index.html` so that the application controls all its assets and works offline in a build environment.

#### Acceptance Criteria

1. THE `index.html` SHALL contain zero `<script>` or `<link>` tags referencing `unpkg.com`, `cdnjs.cloudflare.com`, or `fonts.googleapis.com`.
2. THE App SHALL import the Leaflet CSS from the `leaflet` npm package within the JavaScript module graph.
3. THE App SHALL import Inter and JetBrains Mono fonts from the `@fontsource` npm packages.
4. WHEN Leaflet functionality is initialized, THE Map component SHALL use the `leaflet` npm package import rather than `window.L`.
5. THE `index.html` SHALL include a `<meta name="description">` tag and Open Graph `<meta>` tags for the application.

---

### Requirement 3: API Service Centralization

**User Story:** As a developer, I want all HTTP calls to go through a single API service so that the backend URL is configured in one place and never hardcoded in component files.

#### Acceptance Criteria

1. THE API_Service SHALL read the backend base URL exclusively from `import.meta.env.VITE_API_URL`.
2. WHEN a fetch call is initiated by the API_Service, THE API_Service SHALL attach an `AbortController` signal to the request.
3. IF a fetch request receives a non-OK HTTP status, THEN THE API_Service SHALL throw a typed error with a human-readable message.
4. THE codebase SHALL contain zero occurrences of the literal string `http://127.0.0.1:8001` outside of `.env` and `.env.example` files.
5. THE `Explainability` component SHALL call the API exclusively through the API_Service rather than calling `fetch` directly.
6. THE sync status polling in the dashboard SHALL call the API exclusively through the API_Service rather than calling `fetch` directly.

---

### Requirement 4: URL-Based Routing

**User Story:** As a user, I want the browser URL to reflect the current view so that I can bookmark pages, use browser back/forward, and share direct links.

#### Acceptance Criteria

1. THE Router SHALL define the route `/` rendering the Landing page.
2. THE Router SHALL define the route `/dashboard` rendering the Dashboard page.
3. THE Router SHALL define the route `/predictor` rendering the Predictor page.
4. THE Router SHALL define the route `/enforcement` rendering the Enforcement page.
5. WHEN a user navigates to an undefined route, THE Router SHALL redirect to `/`.
6. WHEN a user clicks a navigation link in the Navbar, THE Router SHALL update the browser URL and render the corresponding page without a full page reload.

---

### Requirement 5: App Component Decomposition

**User Story:** As a developer, I want `App.jsx` to be a thin root component so that view logic lives in page components and the file is easy to read at a glance.

#### Acceptance Criteria

1. THE App component SHALL be 100 lines or fewer.
2. THE App component SHALL render only providers (ThemeContext, Router) and route declarations.
3. THE App component SHALL contain zero inline `style={{...}}` props.
4. THE App component SHALL contain zero data-fetching logic or API calls.
5. THE Enforcement view (~200 lines) SHALL be extracted into `src/pages/Enforcement.jsx`.
6. THE Dashboard view logic SHALL reside in `src/pages/Dashboard.jsx`.

---

### Requirement 6: Custom Data Hooks

**User Story:** As a developer, I want all API calls abstracted into custom hooks so that components declare their data dependencies without managing fetch lifecycle details.

#### Acceptance Criteria

1. THE codebase SHALL define a `useStations` hook in `src/hooks/useStations.js` that fetches and returns the stations list along with loading and error state.
2. THE codebase SHALL define a `useStationDetail` hook that accepts a station ID and fetches history, forecast, and intelligence data for that station.
3. THE codebase SHALL define a `useEnforcement` hook that fetches and returns enforcement dashboard data.
4. THE codebase SHALL define a `useSync` hook that encapsulates the sync trigger and status-polling logic.
5. WHEN a hook's parent component unmounts, THE hook SHALL abort any in-flight fetch requests using `AbortController`.
6. THE `useStations` hook SHALL expose a memoized sorted station list computed with `useMemo`.
7. WHEN the `viewMode` is `"landing"`, THE auto-refresh timer SHALL NOT be active.

---

### Requirement 7: Theme Context

**User Story:** As a user, I want my dark/light theme preference persisted across sessions so that the interface always opens in my preferred mode.

#### Acceptance Criteria

1. THE codebase SHALL define a `ThemeContext` provider in `src/context/ThemeContext.jsx`.
2. WHEN the theme is toggled, THE ThemeContext SHALL persist the selection to `localStorage`.
3. WHEN the application loads, THE ThemeContext SHALL initialize the theme from `localStorage` if a value is stored, otherwise default to `"dark"`.
4. WHEN the theme changes, THE ThemeContext SHALL set the `data-theme` attribute on `document.documentElement`.
5. ALL components that read or set theme state SHALL consume `ThemeContext` rather than accepting theme as a prop.

---

### Requirement 8: AQI Constants Module

**User Story:** As a developer, I want AQI category logic defined in a single file so that adding a new category or changing a threshold propagates everywhere automatically.

#### Acceptance Criteria

1. THE codebase SHALL define `src/constants/aqi.js` containing all AQI threshold values, category slugs, human-readable labels, and hex color values.
2. THE `aqi.js` module SHALL export a `getAqiSlug(aqi)` function that returns the category slug for a given numeric AQI value.
3. THE `aqi.js` module SHALL export a `getAqiColor(aqi)` function that returns the hex color string for a given numeric AQI value.
4. THE `aqi.js` module SHALL export a `getAqiLabel(aqi)` function that returns the human-readable category label for a given numeric AQI value.
5. ALL components and hooks that derive AQI category, color, or label SHALL import exclusively from `src/constants/aqi.js` rather than defining local equivalents.
6. THE `LandingPage` component SHALL use `AQI_Constants` functions for its national average AQI display.

---

### Requirement 9: UI Primitive Components

**User Story:** As a developer, I want a set of reusable UI components so that styling is consistent and duplicated markup is eliminated.

#### Acceptance Criteria

1. THE codebase SHALL provide a `Button` component in `src/components/ui/Button.jsx` accepting `variant` (`primary`, `secondary`, `ghost`), `size`, `disabled`, and `onClick` props.
2. THE codebase SHALL provide a `Badge` component in `src/components/ui/Badge.jsx` for status labels and AQI pills.
3. THE codebase SHALL provide a `Card` component in `src/components/ui/Card.jsx` as a styled container.
4. THE codebase SHALL provide a `Skeleton` component in `src/components/ui/Skeleton.jsx` that renders a shimmering placeholder.
5. THE codebase SHALL provide a `Spinner` component in `src/components/ui/Spinner.jsx` for inline loading indicators.
6. THE codebase SHALL provide a `Banner` component in `src/components/ui/Banner.jsx` for error and success messages.
7. WHERE a page or section is loading data, THE App SHALL render `Skeleton` components rather than a blank space or text-only spinner.

---

### Requirement 10: Layout Component Extraction

**User Story:** As a developer, I want the Navbar, Sidebar, and RightPanel extracted into layout components so that layout structure is reusable and testable in isolation.

#### Acceptance Criteria

1. THE codebase SHALL define a `Navbar` component in `src/components/layout/Navbar.jsx`.
2. THE codebase SHALL define a `Sidebar` component in `src/components/layout/Sidebar.jsx`.
3. THE codebase SHALL define a `RightPanel` component in `src/components/layout/RightPanel.jsx`.
4. THE `Navbar` component SHALL use `lucide-react` icon components in place of all FontAwesome `<i className="fa ...">` elements.
5. ALL layout components SHALL use CSS classes exclusively; they SHALL contain zero inline `style={{...}}` props.

---

### Requirement 11: Inline Style Elimination

**User Story:** As a developer, I want all inline style props removed and replaced with CSS classes so that styling is maintainable, overridable via themes, and consistent across components.

#### Acceptance Criteria

1. WHEN a component renders HTML elements, THE component SHALL use `className` attributes referencing defined CSS classes rather than `style={{...}}` props.
2. THE CSS SHALL define all classes referenced in JSX; zero undefined CSS classes SHALL exist in the rendered output.
3. THE CSS SHALL define the `aqi-indicator-pill` class along with its AQI-category modifier classes (`aqi-indicator-pill.good`, `aqi-indicator-pill.satisfactory`, etc.).
4. THE CSS SHALL define heatmap cell classes: `heatmap-cell`, `heat-good`, `heat-satisfactory`, `heat-moderate`, `heat-poor`, `heat-very-poor`, `heat-severe`, `heat-empty`.
5. ALL page components SHALL contain zero inline `style={{...}}` props after the refactor.

---

### Requirement 12: Analytics Chart Fixes

**User Story:** As a developer, I want the Analytics chart component to display correct data so that the heatmap reflects actual historical observations rather than random array indices.

#### Acceptance Criteria

1. THE `Analytics` component SHALL map heatmap cells using the actual hour-of-day and day-of-week derived from each observation's timestamp rather than random array indices.
2. WHEN the `history` array contains insufficient data for a given (day, hour) slot, THE `Analytics` component SHALL render the cell with the `heat-empty` CSS class.
3. THE `Analytics` component SHALL use CSS classes from `src/constants/aqi.js` conventions for all heatmap color states.
4. WHEN `history` is loading, THE `Analytics` component SHALL render skeleton placeholder rows.

---

### Requirement 13: Explainability Component Fix

**User Story:** As a developer, I want the Explainability component to display real API data so that users see actual SHAP attributions rather than hardcoded fake values.

#### Acceptance Criteria

1. THE `Explainability` component SHALL fetch SHAP data exclusively via the `useStationDetail` hook or through the API_Service rather than with a local hardcoded `fetch` call.
2. THE `Explainability` component SHALL display the feature importance data returned by the API rather than hardcoded static values.
3. WHEN the station ID changes, THE `Explainability` component SHALL re-fetch and display updated data for the new station.
4. WHEN feature importance data is loading, THE `Explainability` component SHALL render skeleton placeholders.

---

### Requirement 14: Map Component Marker Optimization

**User Story:** As a developer, I want the map to update markers in-place so that the map does not flicker or lose state on every data refresh.

#### Acceptance Criteria

1. THE `Map` component SHALL use the `react-leaflet` npm package rather than the CDN-based `window.L` global.
2. WHEN station data is updated, THE `Map` component SHALL update existing marker icons without removing and re-adding markers to the map.
3. THE `Map` component SHALL use `useRef` to track marker instances and update them in-place.
4. THE `Map` component SHALL replace the FontAwesome search icon with a `lucide-react` `Search` icon component.
5. WHEN the map is loading, THE `Map` component SHALL render a `Skeleton` placeholder of the same dimensions.

---

### Requirement 15: Error Boundaries

**User Story:** As a user, I want rendering errors to be caught at the page level so that a crash in one section does not take down the entire application.

#### Acceptance Criteria

1. THE codebase SHALL define an `ErrorBoundary` component in `src/components/ErrorBoundary.jsx`.
2. THE `ErrorBoundary` SHALL display a human-readable fallback message when a child component throws during rendering.
3. WHEN rendering any Page component, THE Router SHALL wrap it with an `ErrorBoundary`.
4. THE `ErrorBoundary` SHALL log the caught error to the console without exposing internal stack traces in the UI.

---

### Requirement 16: Code Splitting

**User Story:** As a user, I want the initial page load to be fast so that I do not have to wait for dashboard or enforcement bundle code to load when I am only viewing the landing page.

#### Acceptance Criteria

1. THE Dashboard page SHALL be loaded using `React.lazy` and `Suspense`.
2. THE Predictor page SHALL be loaded using `React.lazy` and `Suspense`.
3. THE Enforcement page SHALL be loaded using `React.lazy` and `Suspense`.
4. WHILE a lazy page chunk is loading, THE App SHALL render a full-page `Skeleton` or `Spinner` fallback via the `Suspense` boundary.

---

### Requirement 17: Performance Memoization

**User Story:** As a developer, I want expensive list computations memoized so that the station list and national average do not recompute on every unrelated render.

#### Acceptance Criteria

1. THE `useStations` hook SHALL memoize the sorted and filtered station list using `useMemo`, recomputing only when the raw station array or filter parameters change.
2. THE `LandingPage` component SHALL compute the national AQI average using `useMemo`, recomputing only when the stations array changes.

---

### Requirement 18: Smoke Tests

**User Story:** As a developer, I want render smoke tests for key components so that regressions in component mounting are caught automatically.

#### Acceptance Criteria

1. THE codebase SHALL include a smoke test that renders `LandingPage` without throwing.
2. THE codebase SHALL include a smoke test that renders the `Predictor` page without throwing.
3. THE codebase SHALL include a smoke test that renders the `Navbar` component without throwing.
4. WHEN `npm test` is executed, THE test runner SHALL run all smoke tests and report results.

---

### Requirement 19: Folder Structure

**User Story:** As a developer, I want a clear and conventional folder structure so that any developer can locate files predictably without reading a guide.

#### Acceptance Criteria

1. THE `src/` directory SHALL contain subfolders: `hooks/`, `context/`, `components/ui/`, `components/layout/`, `constants/`, `utils/`, `pages/`.
2. THE `src/hooks/` folder SHALL contain only custom hook files named with the `use` prefix.
3. THE `src/constants/` folder SHALL contain `aqi.js` and any other application-wide constant modules.
4. THE `src/utils/` folder SHALL contain pure utility functions with no side effects.

---

### Requirement 20: Bundle Analysis

**User Story:** As a developer, I want bundle size visibility so that I can identify and address bloat before shipping to production.

#### Acceptance Criteria

1. THE `vite.config.js` SHALL include the `rollup-plugin-visualizer` plugin configured to emit a `stats.html` file on `npm run build`.
