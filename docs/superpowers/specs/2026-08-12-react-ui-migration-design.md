# React UI Migration — Design Spec

**Date:** 2026-08-12
**Status:** Approved, not yet implemented

## Context

`app/index.html` is a ~900-line single-file vanilla JS + Leaflet app: global
mutable state (`selectedYear`, `selectedPair`, `selectedRegion`, etc.),
imperative DOM rebuilds on every filter change, and HTML built by string
concatenation for both popup builders. It works, but it's at its
architectural limit — the next planned features (competitor ranking
overlays beyond the existing popup section, voter-profile toggles, and a
storytelling/conclusions tab — see
[2026-08-11-vote-competitors-design.md](2026-08-11-vote-competitors-design.md)'s
sub-project list) don't fit cleanly into hand-rolled string templating.

This spec migrates the UI to React + Vite, keeping Leaflet as the map engine
via `react-leaflet`, with **zero behavior change** and **zero modification**
to the data pipeline (`scripts/01_download_tse.py` through
`scripts/07_top_competitors.py`). It is a pure feature-parity rewrite. The
three motivating features are explicitly **not** built here — they get their
own specs once this lands.

## Scope

### In scope
- Fresh Vite + React app in a new `app-web/` directory (parallel to the
  existing `app/`, not in-place) — plain JS/JSX, no TypeScript.
- `react-leaflet` replacing hand-rolled Leaflet calls; Leaflet becomes an
  npm dependency instead of a CDN `<script>` tag.
- All four existing marker layers (Hugo Leal, Felipe Peixoto, PSD, vote
  deltas), both popup builders (including the collapsible "Concorrência"
  competitor section), the compare panel, the stats panel, and every
  existing filter (year, delta pair, delta metric, region/bairro, layer
  toggles).
- `app/data.js` keeps being generated exactly as today — same Python call
  site, same output format, same file. `app-web/` consumes it via a
  lightweight sync (symlink), not a duplicated or reformatted copy.
- Vitest unit tests for all pure logic; React Testing Library component
  tests for rendering/interaction. See Testing Strategy below.
- Incremental migration with a working, checkable state at every step (see
  Execution Order).

### Out of scope (deferred)
- Competitor ranking overlays beyond the existing per-popup "Concorrência"
  section (e.g. a dedicated map-wide overlay/heatmap) — future spec.
- Voter-profile toggles (`scripts/04_voter_profile.py` data is generated
  but not surfaced in the UI today, and stays that way here) — future spec.
- Storytelling/conclusions tab — future spec, sub-project 3 from the prior
  design doc.
- Recharts — not installed in this migration. Nothing under feature-parity
  scope uses charts; it lands with whichever future spec needs it.
- Deploy/hosting config (Vercel project setup, build command wiring) —
  handled separately by the user, not part of this spec.
- Cutover mechanics (deleting `app/`, renaming `app-web/` → `app/` or
  repointing the deploy target at `app-web/dist/`) — noted as a followup,
  not designed in detail here since it depends on the deploy setup above.

## Design

### 1. Architecture

- **Location:** `app-web/` at repo root, scaffolded via
  `npm create vite@latest app-web -- --template react`. Plain JS/JSX,
  matching the untyped style of the rest of the codebase (Python has no
  type hints either) — not a decision to introduce TypeScript now.
- **Map:** `react-leaflet`, wrapping the same Leaflet 1.9.x behavior in use
  today.
- **Charts:** not installed (see Out of scope).
- **Styling:** the existing inline `<style>` block ports as a plain CSS
  file (or CSS Modules) with no behavior change — no CSS framework
  introduced.

### 2. Data Flow

The trickiest integration point, since the pipeline scripts must stay
untouched.

- **Generation (unchanged):** `scripts/06_build_vote_deltas.py` and
  `scripts/07_top_competitors.py` keep calling
  `rebuild_data_js(DATA_GEO, DATA_GEO.parent.parent / "app")` exactly as
  today, writing `app/data.js` as `const DATA = {...};`. Zero Python
  changes.
- **Consumption (new):** `app-web/` does not duplicate or reformat that
  logic. `app-web/public/data.js` is a symlink to `../../app/data.js`, set
  up once, so Vite serves the exact same generated file.
- **Runtime access:** `app-web/index.html` loads `data.js` via a plain
  `<script>` tag before the React bundle mounts, preserving the existing
  `window.DATA` global-variable contract (not an ES import) — so the
  pipeline's output format (`const DATA = ...`, not `export const DATA =
  ...`) never needs to change. A `useMapData()` hook reads `window.DATA` on
  mount.
- **Live external fetches** (Niterói ArcGIS region/bairro boundaries, CARTO
  basemap tiles) — same URLs, same behavior, re-homed into a
  `useBoundaries()` hook.
- **Cutover note:** when `app-web/` eventually replaces `app/`, the symlink
  target changes accordingly. Flagged here so it isn't a surprise during
  cutover; not designed further since cutover itself is out of scope.

### 3. Components & State Management

**Map layer:**
- `<MapView>` — map + tile layer shell (replaces `init()`'s map setup)
- `<MarkerLayer type="hugo_leal" | "felipe_peixoto" | "psd">` — one
  reusable component instead of the loop in `buildLayers()`, parameterized
  by color/radius formula
- `<DeltaLayer>` — diverging-color delta markers (`buildDeltaLayer()`)
- `<BoundaryLayer type="region" | "bairro">` — polygon overlays
  (`buildBoundaryLayers()`)
- `<PopupContent>` / `<DeltaPopupContent>` — JSX replacing the HTML-string
  builders (`buildPopup`, `buildDeltaPopup`); `<CompetitorSection>` as its
  own piece (`buildCompetitorSection`/`competitorRows`)
- `<CompareTable>` — click-to-compare panel (`showCompare`)

**Sidebar:**
- `<LayerToggles>`, `<YearFilter>`, `<DeltaPairFilter>`,
  `<DeltaMetricFilter>`, `<GeoFilter>` (region/bairro selects),
  `<StatsPanel>`

**Pure logic → `src/lib/`** (no React, independently testable):
`aggregateByLocal`, `passesGeoFilter`, `pointInGeometry`/`pointInRing`,
`getDivergingColor`/`interpolateColor`, `getRadius`/`getDeltaRadius`,
`electionType`/`electionPairLabel`, `formatSigned`/`formatPct`,
`normalizeText`, `featureName`

**State:** plain `useState` in top-level `<App>` — `selectedYear`,
`selectedPair`, `selectedDeltaMetric`, `selectedRegion`, `selectedBairro`,
plus the six layer-visibility toggles (currently read ad-hoc from DOM
checkboxes on every rebuild; becomes explicit state, same behavior). No
reducer/Context — five-ish pieces of filter state don't need it. Revisit
only if a future feature spec makes prop-drilling genuinely painful.
Compare-panel selection is its own `useState`, colocated with
`<CompareTable>` rather than lifted to `<App>`.

**Derived data** (`ALL_YEARS`, `DELTA_PAIRS`, filtered/aggregated feature
lists, geo-annotated boundary lookups) — `useMemo`, recomputed from
`window.DATA` + current filter state, replacing the imperative
rebuild-everything-on-every-change pattern.

### 4. Error Handling

Same behavior as today, plus one small hardening:

- **Boundary fetch failure** (ArcGIS down/CORS) — `useBoundaries()` catches,
  logs a warning, region/bairro filters stay empty/disabled. Rest of the
  app keeps working, same as today.
- **Missing/stale `window.DATA`** — new guard. Today this isn't handled at
  all (blank page, "DATA is not defined"). `useMapData()` checks for
  `window.DATA` on mount; `<App>` renders a plain "data not loaded" message
  instead of crashing. One guard, one fallback, nothing speculative beyond
  it.
- **Missing competitor data** (`top1_nome` absent) — same "Sem dados"
  fallback as today, ported directly into `<CompetitorSection>`.
- **Feature-name/geometry edge cases** in boundary matching — unchanged,
  no new handling.

### 5. Testing Strategy

Unit + component tests. No E2E/browser automation — manual Chrome
verification covers that, same method used to verify the vanilla app this
session.

**Vitest — `src/lib/` unit tests:**
- `aggregateByLocal` — sums votes across years per local, preserves geometry
- `passesGeoFilter` — region/bairro match logic incl. the `'all'` bypass
- `pointInGeometry`/`pointInRing` — Polygon and MultiPolygon cases
- `getDivergingColor`/`interpolateColor` — gain vs. loss direction,
  magnitude scaling
- `getRadius`/`getDeltaRadius` — hugo-vs-others radius formula difference,
  zero-delta floor
- `electionType`/`electionPairLabel` — municipal/federal year math (gets a
  real regression test this time — the source of an actual bug found
  earlier in the prior spec's implementation)
- `formatSigned`/`formatPct` — sign prefixing, pt-BR number formatting

**React Testing Library — component tests:**
- `<PopupContent>` — correct fields from mock props; "Sem dados" when no
  `top1_nome`; competitor section present for hugo/felipe, absent for PSD;
  absent in aggregated (`_years`) mode
- `<DeltaPopupContent>` — two competitor sections for hugo/felipe metric,
  none for PSD metric
- Filter components — reflect selected state, fire correct callback on
  click, show correct municipal/federal indicator
- `<StatsPanel>` — correct totals given a mock `window.DATA` fixture

**Data-contract regression check:** one Vitest test asserting the shape of
a real (or fixture) `data.js` output matches what components expect — e.g.
every hugo_leal/felipe_peixoto feature has `ano`/`nr_local`/`QT_VOTOS` —
catching silent drift from the Python side without touching Python.

**Manual Chrome verification** (not automated): actual map rendering,
marker placement, popup open/close, layer toggle visuals.

### 6. Migration Execution Order

Incremental — each step lands in a working, checkable state:

1. **Scaffold** — Vite+React app in `app-web/`, data.js symlink wired up,
   bare Leaflet map + tile layer, no markers. *Check: app boots, map
   renders, tiles load.*
2. **Pure logic port** — all `src/lib/` functions + full Vitest coverage,
   no UI consuming them yet. *Check: unit suite green.*
3. **First marker layer** — `<MarkerLayer type="hugo_leal">` +
   `<PopupContent>` + year filter wired up. *Check: component tests pass,
   manual browser check shows real markers/popups.*
4. **Remaining marker layers** — felipe, psd, delta layer + delta popup,
   delta pair/metric filters. *Check: same, plus competitor-section
   PSD-hidden / aggregated-mode-hidden cases.*
5. **Compare panel + stats panel.** *Check: component tests, manual
   click-through.*
6. **Boundary layers + geo filters** — ArcGIS live-fetch, point-in-polygon
   annotation, region/bairro selects. *Check: manual verification against
   live ArcGIS data, error-path check (simulate fetch failure).*
7. **Full parity pass** — same filters, same location, side-by-side against
   the still-live vanilla `app/`, confirming visual and data equivalence.
   This is the spec's exit criterion.
