# Design Document: Light Mode UI Improvements

## Overview

This document covers the technical approach for fixing light mode across the AtmosEdgeAI frontend. The app uses a CSS custom-property (design token) system with a `[data-theme="light"]` block in `App.css` that overrides `:root` values. Dark mode works because the entire codebase was initially written with dark mode as the default. Light mode breaks wherever code bypasses the token system — using hardcoded hex values or `rgba()` literals instead of `var(--*)` references.

There are three categories of work:
1. **CSS fixes** — replace hardcoded colors in `App.css` and `index.css` with design tokens
2. **JSX fixes** — replace inline `style` props in `RightPanel.jsx` and other components with CSS classes
3. **Map improvements** — fix tile theming propagation, fix tooltip styling, redesign pins

No new dependencies are needed. No architectural changes are required.

---

## Architecture

The existing theme architecture is sound and does not change:

```
ThemeProvider (context/ThemeContext.jsx)
  └─ useState("dark" | "light")
  └─ useEffect → document.documentElement.setAttribute("data-theme", theme)
  └─ useEffect → localStorage.setItem("theme", theme)

App.css
  └─ :root { --bg: #000000; ... }          ← dark default
  └─ [data-theme="light"] { --bg: #f6f8fa; ... }  ← light overrides

index.css
  └─ body { background: var(--bg); }       ← must use token, not hardcoded
```

The `Map` component needs the `theme` value passed as a prop from `Dashboard` via `useTheme()` so `TileTheme` can react to live toggles. This is already partially wired — `Map` accepts a `theme` prop — but `Dashboard.jsx` doesn't pass it.

---

## Components and Interfaces

### Files Modified

| File | Change Category |
|---|---|
| `frontend/src/index.css` | Fix body background to use `var(--bg)` |
| `frontend/src/App.css` | Replace all hardcoded dark colors with design tokens |
| `frontend/src/components/layout/RightPanel.jsx` | Replace inline styles with CSS classes |
| `frontend/src/components/m