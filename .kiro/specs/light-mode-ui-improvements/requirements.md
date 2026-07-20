# Requirements Document

## Introduction

The AtmosEdgeAI frontend currently supports dark and light themes via a `[data-theme="light"]` CSS override block and a `ThemeContext` toggle. Dark mode works correctly. Light mode has three categories of problems:

1. **Hardcoded dark colors in inline styles** — `RightPanel.jsx` and `LandingPage.jsx` use inline `style` props with literal dark hex values (`#f8fafc`, `rgba(17,24,39,0.7)`, `#0b1220`, etc.) that are never overridden by the light-mode CSS variables.
2. **Hardcoded dark colors in CSS classes** — Several CSS classes in `App.css` bypass design tokens (e.g., `.analytics-tab-btn.inactive`, `.aqi-hero-card`, `.landing-benchmarks`, `.predictor-result`, `.alert-drawer`, `.leaflet-tooltip-card`, `body` in `index.css`).
3. **Map tile and map pin readability** — In light mode the map tile layer correctly switches to CARTO Voyager, but the custom AQI marker pills use `var(--bg-2)` as their background which is acceptable but visually undistinguished. The Leaflet tooltip uses a hardcoded dark card style. Pin design can also be improved for both modes.

This spec covers all fixes plus a visual refresh of the map pins.

## Glossary

- **Design_Token**: A CSS custom property (variable) defined in `:root` or `[data-theme="light"]` in `App.css`, e.g. `var(--bg-2)`.
- **Inline_Style**: A React `style={{ }}` prop that directly embeds CSS values in JSX.
- **Light_Mode**: The theme state where `document.documentElement.dataset.theme === "light"`.
- **Dark_Mode**: The default theme state where no `data-theme` attribute or `data-theme="dark"` is set.
- **Map_Pin**: The custom Leaflet `divIcon` rendered by `buildIcon()` in `Map.jsx` that shows the AQI value on the map.
- **Leaflet_Tooltip**: The popup card shown on marker hover, rendered with class `.leaflet-tooltip-card`.
- **CARTO_Tile**: The map tile layer URL; dark mode uses `dark_all`, light mode uses `voyager`.
- **Theme_Variable**: Any CSS custom property whose value differs between `:root` and `[data-theme="light"]`.

## Requirements

### Requirement 1: Body and Root Background Follow Theme

**User Story:** As a user, I want the page background to always match the active theme, so that I never see a black background bleed-through in light mode.

#### Acceptance Criteria

1. THE `index.css` body rule SHALL use `var(--bg)` for both `background` and as a fallback, not a hardcoded hex value.
2. WHEN the theme is set to `"light"`, THE `body` element SHALL display with the light-mode `--bg` value (`#f6f8fa`).
3. WHEN the theme is set to `"dark"`, THE `body` element SHALL display with the dark-mode `--bg` value (`#000000`).

---

### Requirement 2: CSS Classes Use Design Tokens Instead of Hardcoded Dark Colors

**User Story:** As a user switching to light mode, I want all UI surfaces—cards, panels, charts, and overlays—to render with appropriate light colors, so that text and backgrounds are readable.

#### Acceptance Criteria

1. THE `.analytics-tab-btn.inactive` class SHALL use `var(--bg-3)` for background and `var(--text-1)` for color instead of `rgba(255,255,255,0.02)` and a hardcoded light color.
2. THE `.analytics-chart-box` class SHALL use `var(--bg-3)` for background instead of `rgba(0,0,0,0.2)`.
3. THE `.comparison-table` class SHALL use `var(--bg-3)` for background instead of `rgba(0,0,0,0.12)`.
4. THE `.comparison-table-header` class SHALL use `var(--bg-4)` for background instead of `rgba(255,255,255,0.02)`.
5. THE `.alert-drawer` class SHALL use `var(--bg-2)` for background and `var(--border)` for border color instead of hardcoded dark values.
6. THE `.shap-bar-track` and `.fi-bar-track` classes SHALL use `var(--bg-4)` for background instead of `rgba(255,255,255,0.03)`.
7. THE `.shap-bar-center` class SHALL use `var(--border)` instead of `rgba(255,255,255,0.2)`.
8. WHEN the theme is set to `"light"`, ALL CSS classes listed in criteria 1–7 SHALL render visibly distinct from their surrounding backgrounds.

---

### Requirement 3: Landing Page Uses Design Tokens

**User Story:** As a user viewing the landing page in light mode, I want the hero card, feature cards, benchmarks section, and footer to be readable and styled correctly.

#### Acceptance Criteria

1. THE `.aqi-hero-card` class SHALL use `var(--bg-2)` for background and `var(--border)` for border instead of hardcoded dark values.
2. THE `.landing-headline` gradient SHALL render legibly in light mode by adapting to `var(--text-1)` as a fallback when `-webkit-text-fill-color` makes text invisible against a light background.
3. THE `.feature-card` class SHALL use `var(--bg-2)` for background and `var(--border)` for border instead of `rgba(15,23,42,0.4)` and `#1e2d4a`.
4. THE `.landing-benchmarks` class SHALL use `var(--bg-2)` for background and `var(--border)` for border instead of hardcoded dark values.
5. THE `.predictor-result` class SHALL use `var(--bg-3)` for background instead of `#080d16`.
6. WHEN the theme is set to `"light"`, THE landing page hero card AQI number and category label SHALL be readable against the card background.

---

### Requirement 4: RightPanel Inline Styles Replaced With CSS Classes

**User Story:** As a user in light mode, I want the station detail header and metric cells in the right panel to be readable, so that I can see station name, AQI, and pollutant values clearly.

#### Acceptance Criteria

1. THE `StationDetailHeader` component in `RightPanel.jsx` SHALL NOT use `Inline_Style` props for background colors, border colors, or text colors that bypass `Theme_Variable`s.
2. WHEN the theme is `"light"`, THE station name in `StationDetailHeader` SHALL render with `var(--text-1)` color.
3. WHEN the theme is `"light"`, THE metric cells grid (PM2.5, NO₂, Temperature, Humidity, Wind Speed) SHALL render with `var(--bg-3)` background and `var(--text-1)` values.
4. WHEN the theme is `"light"`, THE station detail source/provider/updated footer row SHALL render with `var(--text-3)` color.
5. THE CSS classes added for `StationDetailHeader` SHALL be defined in `App.css` using only `Theme_Variable`s.

---

### Requirement 5: Leaflet Tooltip Adapts to Theme

**User Story:** As a user in light mode, I want map marker tooltips to be readable with appropriate background and text colors, so that I can read station info on hover.

#### Acceptance Criteria

1. THE `.leaflet-tooltip-card` class SHALL use `var(--bg-2)` for background and `var(--border)` for border instead of hardcoded dark hex values.
2. THE `.leaflet-tooltip-card` class SHALL use `var(--text-1)` for its text color.
3. WHEN the theme is `"light"`, THE tooltip SHALL be visually distinguishable from the map tiles underneath it.

---

### Requirement 6: Map Tile Renders Correctly in Light Mode

**User Story:** As a user in light mode, I want the map to display a light-themed tile layer instead of a black map, so that I can see geography and station positions clearly.

#### Acceptance Criteria

1. WHEN the `theme` prop passed to the `Map` component is `"light"`, THE `TileTheme` component SHALL load the CARTO Voyager tile URL.
2. WHEN the `theme` prop passed to the `Map` component is `"dark"`, THE `TileTheme` component SHALL load the CARTO `dark_all` tile URL.
3. THE `Map` component in `Dashboard.jsx` SHALL receive the current theme value from `useTheme()` via a prop or context, so that tile switching is reactive to theme changes.
4. WHEN a user toggles the theme on the Dashboard page, THE map tile layer SHALL update without requiring a page reload.

---

### Requirement 7: Map Pin Design Improved for Both Themes

**User Story:** As a user, I want map pins to be visually clear and attractive in both dark and light mode, so that I can quickly identify AQI levels at each station.

#### Acceptance Criteria

1. THE `buildIcon()` function in `Map.jsx` SHALL produce pins that are visually readable against both dark map tiles and light map tiles.
2. WHEN a pin is in its default (unselected) state, THE pin SHALL display the AQI value with the AQI category color as the pill background with a contrasting white or dark text color, rather than the background using `var(--bg-2)`.
3. WHEN a pin is in its selected state, THE pin SHALL display a visually prominent indicator (e.g. increased size, distinct border or glow) that works in both themes.
4. THE pulsing ring animation on the selected pin SHALL use the AQI category color with appropriate opacity for both dark and light tile backgrounds.
5. THE pin design SHALL NOT rely on `var(--bg-2)` as the pill background since this creates a near-invisible pin against same-colored light mode surfaces.

---

### Requirement 8: Theme Toggle Propagates to All Themed Components

**User Story:** As a user toggling between dark and light mode, I want the entire page to update immediately and consistently, so that no component is left in the wrong theme.

#### Acceptance Criteria

1. THE `Dashboard` page SHALL pass the current `theme` value from `useTheme()` to the `Map` component as a prop.
2. WHEN `toggleTheme` is called, ALL components on the current page SHALL re-render reflecting the new theme within one React render cycle.
3. THE `ThemeProvider` SHALL set `document.documentElement.setAttribute("data-theme", theme)` synchronously within the same `useEffect` that updates `localStorage`.
