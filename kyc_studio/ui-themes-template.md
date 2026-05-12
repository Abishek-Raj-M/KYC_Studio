# AI Evaluation Engine — UI themes & layout template

This document captures the **look and feel** of the AI Evaluation Platform React UI so a separate project (for example KYC) can **match colors, typography, glass surfaces, dark/light toggle**, and **layout conventions** before any merge or iframe integration.

**Analyzed codebase:** `C:\AIIA\ai_evaluation_engine\ai_evaluation_engine\ui\react\`  
**Stack:** React 18, React Router 6, Vite 5, Tailwind CSS 3.4 (`darkMode: 'class'`), Lucide icons, Recharts.

---

## 1. Pages and routes

Top-level routes live in `src/App.tsx` and render inside `AppLayout` (sidebar + header + `<Outlet />`).

| URL path | Component | Notes |
|----------|-----------|--------|
| `/` | redirect | → `/evaluation/artifacts` |
| `/dashboard` | `pages/Dashboard.tsx` | Charts, mock pipeline strip |
| `/recent` | `pages/SavedReports.tsx` | Recent evaluations |
| `/saved` | redirect | → `/recent` |
| `/settings` | `pages/Settings.tsx` | |
| `/observability` | `pages/Observability.tsx` | Under “Roadmap” in nav |
| `/evaluation/*` | `pages/NewEvaluation.tsx` + `EvaluationProvider` | Multi-step wizard |
| `/dataset-generation/*` | `pages/DatasetGeneration.tsx` | Separate wizard |
| `/compare` | `evaluation/ComparisonView.tsx` | Compare view |

### 1.1 New evaluation wizard (`/evaluation/*`)

Defined in `src/pages/NewEvaluation.tsx`:

| Step path | Label | Component |
|-----------|--------|-------------|
| `artifacts` | Artifacts | `evaluation/ArtifactsStep.tsx` |
| `solution-analyzer` | Solution Analyzer | `evaluation/SolutionAnalyzerStep.tsx` |
| `evaluation-planner` | Evaluation Planner | `evaluation/EvaluationPlannerStep.tsx` |
| `dataset-review` | Upload Dataset | `evaluation/DatasetReviewStep.tsx` |
| `report` | AI evaluation | `evaluation/QualityReportStep.tsx` |

Base path for stepper links: `/evaluation`. Index `/evaluation` redirects to `artifacts`.

### 1.2 Dataset generation (`/dataset-generation/*`)

Defined in `src/pages/DatasetGeneration.tsx` (comment block at top of file documents intent):

| Step path | Label |
|-----------|--------|
| `seed` | Seed Dataset |
| `api-specs` | API Specs |
| `preview` | Preview |
| `done` | Done |

Base path for `PipelineSteps`: `/dataset-generation`.

---

## 2. Navigation model

**File:** `src/layouts/AppLayout.tsx`

### 2.1 Structure

- **Left sidebar:** fixed width `w-56` (14rem), column flex, `bg-raised surface-glass border-r border-border shadow-panel`.
- **Right main:** `flex-1`, column; **header** bar then **content** `p-6 min-h-[60vh] overflow-auto` wrapping `<Outlet />` inside `ErrorBoundary`.

### 2.2 Primary nav items

```ts
const primaryNavItems: NavItem[] = [
  { to: '/evaluation/artifacts', label: 'New evaluation', Icon: ClipboardList, activePrefix: '/evaluation' },
  { to: '/recent', label: 'Recent evaluation', Icon: FileText },
  { to: '/dashboard', label: 'Dashboard', Icon: LayoutGrid },
  { to: '/dataset-generation', label: 'Dataset generation', Icon: Database, activePrefix: '/dataset-generation' },
]
```

`activePrefix` means “active” when `location.pathname.startsWith(prefix)` (needed for nested routes).

### 2.3 Roadmap section

Second group with uppercase section label `Roadmap` (`text-[10px] uppercase tracking-[0.2em] font-bold text-fg-muted mb-2 px-1`):

```ts
const roadmapNavItems: NavItem[] = [
  { to: '/observability', label: 'Observability monitoring', Icon: Activity },
  { to: '/settings', label: 'Settings', Icon: Settings },
]
```

### 2.4 Nav link styling

Active: `bg-accent-soft text-fg border-l-2 border-link`  
Inactive: `text-fg-muted hover:bg-nav-hover hover:text-fg border-l-2 border-transparent`  
Shared: `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150`

Chevron: `ChevronRight` with `ml-auto opacity-50`.

### 2.5 Header (right pane top bar)

- `bg-raised surface-glass border-b border-border px-6 py-4 flex items-center justify-between shadow-panel`
- Breadcrumb: `text-sm text-fg-muted font-mono` from `getBreadcrumb(pathname)` / `breadcrumbByPath`.
- **Conditional CTA:** On `/dashboard` or `/recent`, a “New Evaluation” button links to `/evaluation/artifacts` with `bg-brand text-btn-primary`, `shadow-brand-glow-strong`, `Plus` icon.

### 2.6 Adding a future “another project” menu item

To mirror this app when you integrate another project:

1. Add a `NavItem` to `primaryNavItems` or `roadmapNavItems` (or a new section) with `to`, `label`, `Icon`, and optional `activePrefix`.
2. In `App.tsx`, add a `<Route>` sibling under the layout route with your page component.
3. Extend `breadcrumbByPath` and `getBreadcrumb()` in `AppLayout.tsx` so the header shows a sensible trail.
4. If the new app is a **separate SPA**, typical options are: **reverse proxy + path prefix**, **iframe** in a wrapper route, or **module federation** — theme tokens below still apply if you copy `index.css` + Tailwind config + `ThemeProvider` / blocking script.

---

## 3. Theme system (dark / light)

### 3.1 Mechanism

- **Tailwind:** `darkMode: 'class'` in `tailwind.config.js` — dark styles use the `dark:` variant when `<html>` has class `dark`.
- **CSS variables:** Almost all colors live in `src/index.css` on `:root` and `.dark`.
- **React:** `src/context/ThemeContext.tsx` exposes `theme`, `setTheme`, `toggleTheme`; `useLayoutEffect` calls `applyThemeClass` + `persistTheme`.
- **Storage key:** `THEME_STORAGE_KEY = 'ai-eval-theme'` (values `'light'` | `'dark'`).
- **FOUC prevention:** `index.html` inline script runs **before** paint and sets `document.documentElement.classList` from `localStorage.getItem('ai-eval-theme')`; default is **dark** if missing or error.

```html
<script>
  (function () {
    try {
      var t = localStorage.getItem('ai-eval-theme')
      if (t === 'light') document.documentElement.classList.remove('dark')
      else document.documentElement.classList.add('dark')
    } catch (e) {
      document.documentElement.classList.add('dark')
    }
  })()
</script>
```

### 3.2 Provider wiring

`src/main.tsx`:

```tsx
<ThemeProvider>
  <BrowserRouter>
    <App />
  </BrowserRouter>
</ThemeProvider>
```

### 3.3 Toggle control

`src/components/ThemeToggle.tsx` — icon button (Sun in dark mode, Moon in light), uses semantic tokens: `border-border`, `bg-panel-muted/50`, `hover:bg-nav-hover`, `dark:border-transparent dark:bg-transparent`, focus ring `ring-focus` with `ring-offset-page` / `ring-offset-raised` patterns used elsewhere.

---

## 4. Layout, z-index, and page background

### 4.1 Full-page mesh (ambient background)

In `index.css` `body::before`:

- `position: fixed; inset: -12%; z-index: 0; pointer-events: none`
- `background: var(--page-mesh)` — layered **radial gradients** (different for `:root` vs `.dark`)
- `filter: blur(var(--page-mesh-blur))`
- `opacity: var(--page-mesh-opacity)`
- `transform: scale(var(--page-mesh-scale))`

`#root` is `position: relative; z-index: 1; min-height: 100vh` so UI sits above the mesh.

### 4.2 HTML / body

- `html`: `min-height: 100%`, `background-color: var(--color-page)`
- `body`: transparent bg (mesh shows through), `font-family: var(--font-body)`, `color: var(--color-fg)`

### 4.3 Typography

From `index.css` + `tailwind.config.js`:

| Role | Font |
|------|------|
| Body | Plus Jakarta Sans (`--font-body`) |
| Headings `h1–h3` | Outfit (`--font-heading`) |
| `.font-mono` / `font-mono` in Tailwind | IBM Plex Mono |

Google Fonts link is in `index.html` (weights 400–700 for Outfit / Plus Jakarta Sans; mono 400–600).

---

## 5. Glass, transparency, and backdrop

### 5.1 Core tokens

| Token | Light (`:root`) | Dark (`.dark`) |
|-------|-----------------|----------------|
| `--surface-glass-blur` | `14px` | `18px` |
| `--surface-backdrop` | `saturate(165%) blur(var(--surface-glass-blur))` | `saturate(150%) blur(var(--surface-glass-blur))` |

### 5.2 Utility class `.surface-glass`

```css
.surface-glass {
  -webkit-backdrop-filter: var(--surface-backdrop);
  backdrop-filter: var(--surface-backdrop);
}
```

**Usage pattern:** combine **semi-transparent background** tokens (`bg-raised`, `bg-panel`, `bg-panel-muted`) **with** `surface-glass` on sidebars, headers, cards, and the stepper strip. Example from `PipelineSteps.tsx`:

`bg-panel surface-glass border border-border rounded-2xl p-4 shadow-card`

### 5.3 Tailwind `backgroundImage.glass-gradient`

In `tailwind.config.js`:

```js
'glass-gradient': 'linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0) 100%)',
```

(Use with `bg-glass-gradient` if needed for subtle highlights.)

### 5.4 `prefers-reduced-transparency: reduce`

Under `@media (prefers-reduced-transparency: reduce)`:

- Light theme: panels become **opaque** (`#ffffff`, `#f5f5f5`, etc.), `--surface-backdrop: none`
- `.dark`: `--surface-backdrop: none` as well

So glass **degrades to solid** for accessibility.

### 5.5 `prefers-reduced-motion: reduce`

`body::before` uses fixed `blur(48px)` and `opacity: calc(var(--page-mesh-opacity) * 0.75)` to soften motion-heavy background.

---

## 6. Opacity levels (reference)

These appear across the design system; use the same ranges for consistency.

| Use | Typical values |
|-----|----------------|
| Page mesh | `--page-mesh-opacity`: light `1`, dark `0.72` |
| Nav chevron | `opacity-50` (Tailwind) |
| Theme toggle surface | `bg-panel-muted/50` |
| Muted helper text / icon buttons in modals | `opacity-70`, `opacity-75`, `opacity-80` |
| Hover on semi-transparent controls | e.g. `hover:opacity-100` from `opacity-70` |
| Disabled controls | `disabled:opacity-45` |
| Chart / link hovers | `hover:opacity-80`, `dark:hover:opacity-90` |
| Dark scrim overlays | e.g. `bg-black/55`, `dark:bg-black/80` |
| Color-mix accents | badges use `color-mix(in srgb, <color> 14–16%, transparent)` |

---

## 7. Color tokens (CSS variables)

### 7.1 Semantic surfaces and text (light)

| Variable | Value (light) |
|----------|----------------|
| `--color-page` | `#eef1f8` |
| `--color-raised` | `rgba(255, 255, 255, 0.55)` |
| `--color-panel` | `rgba(255, 255, 255, 0.46)` |
| `--color-panel-muted` | `rgba(255, 255, 255, 0.36)` |
| `--color-border` | `rgb(0 0 0 / 0.09)` |
| `--color-border-subtle` | `rgb(0 0 0 / 0.06)` |
| `--color-border-strong` | `rgb(0 0 0 / 0.14)` |
| `--color-fg` | `#050505` |
| `--color-fg-muted` | `#4d4d4d` |
| `--color-fg-subtle` | `#898989` |
| `--color-input` | `rgba(255, 255, 255, 0.62)` |
| `--color-nav-hover` | `rgba(255, 255, 255, 0.68)` |
| `--color-accent-soft` | `color-mix(in srgb, #0078c2 12%, #ffffff)` |

### 7.2 Semantic surfaces and text (dark)

| Variable | Value (dark) |
|----------|----------------|
| `--color-page` | `#050505` |
| `--color-raised` | `rgba(255, 255, 255, 0.04)` |
| `--color-panel` | `rgba(255, 255, 255, 0.05)` |
| `--color-panel-muted` | `rgba(255, 255, 255, 0.07)` |
| `--color-border` | `rgba(255, 255, 255, 0.12)` |
| `--color-fg` | `#ffffff` |
| `--color-fg-muted` | `#dedede` |
| `--color-fg-subtle` | `#8a8a8a` |
| `--color-input` | `rgba(255, 255, 255, 0.06)` |
| `--color-nav-hover` | `rgba(255, 255, 255, 0.08)` |
| `--color-accent-soft` | `color-mix(in srgb, #00f6ff 14%, #050505)` |

### 7.3 Brand / links / focus

**Light**

- `--brand-gradient`: `linear-gradient(60deg, #0078c2 0%, #0047ff 50%, #8453d2 100%)`
- `--link-color`: `#0078c2`
- `--focus-ring-outer`: `rgb(0 120 194 / 0.45)`

**Dark**

- `--brand-gradient`: `linear-gradient(20deg, #00f6ff 0%, #00fff0 50%, #b895ff 100%)`
- `--link-color`: `#00f6ff`
- `--focus-ring-outer`: `rgb(0 246 255 / 0.4)`

Primary buttons use `bg-brand` (maps to `--brand-gradient` via Tailwind) and `text-btn-primary` (`--btn-primary-text`: white in light, `#050505` in dark).

### 7.4 Status / evaluation colors

Shared labels:

- `--eval-high`: `#00a705`, `--eval-mid`: `#e06c00`, `--eval-low`: `#e80202`
- `--step-done` / `--step-idle` for pipeline dots; Tailwind `bg-eval-high`, `bg-brand`, `bg-[var(--color-step-idle)]` in `PipelineSteps.tsx`

### 7.5 Dialog-specific (opaque modals)

Independent of frosted panels:

- Light: `--color-dialog-scrim`, `--color-dialog-surface`, `--color-dialog-inset`, `--color-dialog-border`, `--color-dialog-shadow`
- Dark: scrim `rgb(0 0 0 / 0.72)`, surfaces `#0c0c0f` / `#141418`, etc.

### 7.6 Charts (Recharts)

`index.css` sets `.recharts-wrapper` background to `var(--color-panel-muted)` and aligns tooltip colors in `.dark`. Grid/tick colors use `--color-chart-grid`, `--color-chart-tick`, `--color-gauge-track`.

---

## 8. Tailwind color / shadow mapping

**File:** `tailwind.config.js`

Semantic colors reference `var(--color-*)` etc. Key names used in JSX:

`page`, `raised`, `panel`, `panel-muted`, `border`, `border-subtle`, `border-strong`, `fg`, `fg-muted`, `fg-subtle`, `input`, `nav-hover`, `accent-soft`, `link`, `btn-primary`, `eval-high` / `eval-mid` / `eval-low`, `focus` (ring), `chart-*`, `so-coded` / `so-llm`, `rw-*` (risk widgets), …

Shadows: `shadow-panel`, `shadow-card`, `shadow-brand-glow`, `shadow-brand-glow-strong` → CSS vars in `index.css`.

---

## 9. Recurring UI patterns (for a sibling project)

1. **Cards / panels:** `bg-panel surface-glass border border-border rounded-2xl` (+ optional `hover:border-border-strong`, `shadow-card`, `transition-all duration-300`).
2. **Inset fields:** `rounded-lg border border-border bg-panel px-3 py-2 text-sm text-fg placeholder:text-fg-muted` with `focus:border-link focus:ring-1 focus:ring-link`.
3. **Stepper:** `PipelineSteps` component — glass container, dots: completed `bg-eval-high`, current `bg-brand ring-4 ring-focus animate-pulse`, idle `bg-[var(--color-step-idle)]`.
4. **Focus rings:** `focus-visible:ring-2 focus-visible:ring-focus focus-visible:ring-offset-2` with `ring-offset-page` or `ring-offset-raised` matching surface.

---

## 10. Minimal integration checklist (another repo)

1. Copy **`tailwind.config.js`** (`darkMode: 'class'`, `extend.colors`, `boxShadow`, `fontFamily`, `backgroundImage`).
2. Copy **`src/index.css`** (or merge tokens into your global CSS).
3. Copy **`ThemeContext.tsx`**, **`ThemeToggle.tsx`**, wire **`ThemeProvider`** in entry, replicate **`index.html`** blocking script (adjust `localStorage` key if you want isolation).
4. Replicate **font** links in HTML.
5. For **layout parity:** flex shell, `aside` `w-56` + `main` with glass header and padded `Outlet`.
6. Run through **`prefers-reduced-transparency`** and **`prefers-reduced-motion`** in a browser.

---

## 11. File index (source of truth)

| Concern | Path |
|---------|------|
| Design tokens + mesh + glass + Recharts tweaks | `ui/react/src/index.css` |
| Tailwind mapping | `ui/react/tailwind.config.js` |
| Theme state | `ui/react/src/context/ThemeContext.tsx` |
| Theme toggle UI | `ui/react/src/components/ThemeToggle.tsx` |
| Shell + nav + breadcrumbs | `ui/react/src/layouts/AppLayout.tsx` |
| Routes | `ui/react/src/App.tsx` |
| Entry + provider order | `ui/react/src/main.tsx` |
| FOUC theme script | `ui/react/index.html` |
| Stepper chrome | `ui/react/src/components/PipelineSteps.tsx` |

---

*Generated from analysis of the AI Evaluation Engine UI. Adjust storage keys and product copy when forking for KYC or other apps.*
