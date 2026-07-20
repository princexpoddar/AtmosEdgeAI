# Implementation Plan: Light Mode UI Improvements

## Overview

Fix all light mode rendering issues across the AtmosEdgeAI frontend by replacing hardcoded dark colors with design tokens, wiring the map theme prop, and refreshing the map pin design. Work is split into four focused areas: CSS token fixes, JSX inline style removal, map tile/tooltip theming, and pin redesign.

## Tasks

- [x] 1. Fix body background in `index.css` to use design tokens
  - Replace the hardcoded `background: #000000` on `body` with `background: var(--bg)`
  - Replace the hardcoded `color: #e6edf3` with `color: var(--text-1)`
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Fix hardcoded dark colors in `App.css` CSS classes
  - [x] 2.1 Fix analytics and chart classes
    - `.analytics-tab-btn.inactive`: change `background: rgba(255,255,255,0.02)` to `var(--bg-3)` and set `color: var(--text-1)`
    - `.analytics-chart-box`: change `background: rgba(0,0,0,0.2)` to `var(--bg-3)`
    - _Requirements: 2.1, 2.2_

  - [x] 2.2 Fix comparison table classes
    - `.comparison-table`: change `background: rgba(0,0,0,0.12)` to `var(--bg-3)`
    - `.comparison-table-header`: change `background: rgba(255,255,255,0.02)` to `var(--bg-4)`
    - _Requirements: 2.3, 2.4_

  - [x] 2.3 Fix alert drawer and SHAP/FI bar classes
    - `.alert-drawer`: replace `background: rgba(15,23,42,0.95)` with `var(--bg-2)` and `border: 1px solid #1e2d4a` with `border: 1px solid var(--border)`
    - `.shap-bar-track` and `.fi-bar-track`: change `background: rgba(255,255,255,0.03)` to `var(--bg-4)`
    - `.shap-bar-center`: change `background: rgba(255,255,255,0.2)` to `var(--border)`
    - _Requirements: 2.5, 2.6, 2.7_

  - [x] 2.4 Fix landing page CSS classes
    - `.aqi-hero-card`: replace `background: linear-gradient(135deg, rgba(15,23,42,0.7)...)` with `var(--bg-2)` and `border: 1px solid #1e2d4a` with `var(--border)`
    - `.feature-card`: replace `background: rgba(15,23,42,0.4)` with `var(--bg-2)` and `border: 1px solid #1e2d4a` with `var(--border)`
    - `.landing-benchmarks`: replace `background: rgba(15,23,42,0.55)` with `var(--bg-2)` and `border: 1px solid #1e2d4a` with `var(--border)`
    - `.landing-headline`: add a `[data-theme="light"] .landing-headline` override that sets `-webkit-text-fill-color: var(--text-1)` and `background: none` so the gradient does not make text invisible
    - `.predictor-result`: change `background: #080d16` to `var(--bg-3)`
    - `.predictor-card`: change `background: rgba(15,23,42,0.55)` to `var(--bg-2)`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Replace inline styles in `RightPanel.jsx` with CSS classes
  - [x] 3.1 Add themed CSS classes to `App.css` for `StationDetailHeader`
    - Add `.station-detail-header-card` — uses `var(--bg-2)` background, `var(--border)` border
    - Add `.station-detail-metrics-grid` — uses `var(--bg-3)` background
    - Add `.station-detail-metric-item` — layout for each metric cell
    - Add `.station-detail-label` — uses `var(--text-3)` color
    - Add `.station-detail-value` — uses `var(--text-1)` color
    - Add `.station-detail-unit` — uses `var(--text-3)` color
    - Add `.station-detail-footer` — uses `var(--text-3)` color, `var(--border-soft)` border-top
    - Add `.station-detail-name` — uses `var(--text-1)` color
    - Add `.station-detail-location` — uses `var(--text-2)` color
    - _Requirements: 4.1, 4.5_

  - [x] 3.2 Refactor `StationDetailHeader` in `RightPanel.jsx` to use new CSS classes
    - Remove all `style={{ background: "rgba(17,24,39,0.7)", ... }}` inline props from the card wrapper — use `.station-detail-header-card` class instead
    - Remove hardcoded `color: "#f8fafc"` from station name — use `.station-detail-name` class
    - Remove hardcoded `color: "#94a3b8"` from location paragraph — use `.station-detail-location` class
    - Remove inline `style` from the metrics wrapper div — use `.station-detail-metrics-grid` class
    - Replace each metric `div` inline styles with `.station-detail-metric-item`, `.station-detail-label`, `.station-detail-value`, `.station-detail-unit`
    - Replace inline styles on the footer row with `.station-detail-footer`
    - Keep the `getBadgeColors` status badge using inline styles (status colors are dynamic, not themeable via static classes)
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 4. Checkpoint — verify CSS and JSX changes visually
  - Ensure all tests pass. Toggle between dark and light mode and confirm no component renders with a black/invisible background. Ask the user if any questions arise.

- [x] 5. Fix Leaflet tooltip to use design tokens
  - In `App.css`, update `.leaflet-tooltip-card`:
    - Change `color: #fff` to `color: var(--text-1)`
    - Change `background: #0b1220` to `background: var(--bg-2)`
    - Change `border: 1px solid #1e2d4a` to `border: 1px solid var(--border)`
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 6. Wire `theme` prop from `Dashboard.jsx` to `Map` component
  - In `Dashboard.jsx`, import `useTheme` from `@/context/useTheme`
  - Destructure `theme` from `useTheme()`
  - Pass `theme={theme}` as a prop to the `<Map>` component
  - This makes `TileTheme` inside `Map.jsx` react to live toggles without a page reload
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 8.1, 8.2_

- [x] 7. Improve map pin design in `Map.jsx` and `App.css`
  - [x] 7.1 Update `buildIcon()` in `Map.jsx` to use AQI color as pill background
    - Change the pill so its `background-color` is the AQI `color` value (not `var(--bg-2)`)
    - Set pill text `color` to `#fff` (white text on colored background for all AQI levels)
    - Keep `border-color` as the AQI color for the selected state ring
    - Remove the `style="border-color:${color};color:${color}"` pattern — replace with `style="background-color:${color};color:#fff"`
    - _Requirements: 7.1, 7.2, 7.5_

  - [x] 7.2 Update `.custom-marker-pill` and `.custom-marker-pill.selected` in `App.css`
    - Remove `background: var(--bg-2)` from `.custom-marker-pill` (background is now set inline per AQI color)
    - `.custom-marker-pill.selected`: increase `transform: scale(1.3)`, update box-shadow to use `currentColor` or a stronger glow
    - Add a subtle `box-shadow: 0 2px 8px rgba(0,0,0,0.35)` to the base pill for legibility on both tile types
    - _Requirements: 7.1, 7.3_

  - [x] 7.3 Update pulsing ring animation in `Map.jsx` and `App.css`
    - In `buildIcon()`, give the pulsing div `style="background-color:${color};opacity:0.45"` so the ring uses the AQI color
    - In `.custom-marker-pulsing.active`, adjust animation to scale from `0.85` to `2.4` with opacity fading from `0.6` to `0`
    - _Requirements: 7.4_

- [x] 8. Final checkpoint — end-to-end theme consistency
  - Ensure all tests pass and that toggling theme on Dashboard updates the map tile, all panels, the landing page, and the predictor page correctly. Ask the user if any questions arise.
