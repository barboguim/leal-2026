# React UI Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `app/index.html` (vanilla JS + Leaflet, ~900 lines) as a React + Vite app in a new `app-web/` directory, with zero behavior change and zero modification to the data pipeline.

**Architecture:** `react-leaflet` wraps the same Leaflet map engine; all filter state is plain `useState` in a top-level `App` component (no reducer — too few state pieces to need one); pure logic (aggregation, geo-filtering, color interpolation, formatting) lives in standalone `src/lib/` modules, independently unit-tested. `app/data.js` keeps being generated exactly as today by the unchanged Python pipeline; `app-web/` consumes it via a copy script (not a symlink — Windows dev environments here don't reliably support true symlinks without Developer Mode, verified this session), run before `dev`/`build`.

**Tech Stack:** React 18, Vite, react-leaflet, Vitest, React Testing Library, plain JS/JSX (no TypeScript).

## Global Constraints

- Feature-parity only. No new features (competitor overlays beyond the existing popup section, voter-profile toggles, storytelling tab are explicitly out of scope — see design spec).
- Zero modification to `scripts/01_download_tse.py` through `scripts/07_top_competitors.py`. `rebuild_data_js(DATA_GEO, DATA_GEO.parent.parent / "app")` keeps writing `app/data.js` exactly as today.
- New app lives in `app-web/`, parallel to the existing `app/` — not in-place. `app/` stays untouched and deployable throughout.
- No TypeScript. No CSS framework. No state management library (plain `useState`).
- Recharts is NOT installed in this migration — nothing under feature-parity scope uses it.
- No E2E/browser automation in the test suite — Vitest (unit) + React Testing Library (component) only. Manual Chrome verification covers rendering.
- `window.DATA` stays a plain global set by a `<script>` tag (not an ES import) — the pipeline's output format never changes.

Full design: [`docs/superpowers/specs/2026-08-12-react-ui-migration-design.md`](../specs/2026-08-12-react-ui-migration-design.md)

---

### Task 1: Scaffold Vite + React app and data sync

**Files:**
- Create: `app-web/package.json`, `app-web/vite.config.js`, `app-web/index.html`, `app-web/src/main.jsx`, `app-web/src/index.css`, `app-web/scripts/sync-data.mjs`, `app-web/src/test-setup.js`
- Create: `app-web/.gitignore`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: a running `npm run dev` dev server serving a blank page at `app-web/`, `npm test` running an empty Vitest suite successfully, `npm run build` producing `app-web/dist/`. `app-web/public/data.js` populated by the sync script — consumed by Task 2's `useMapData`.

- [ ] **Step 1: Create the directory and initialize the Vite project**

Run from the repo root (`LEAL/`):

```bash
npm create vite@latest app-web -- --template react
cd app-web
npm install
npm install leaflet react-leaflet
npm install -D vitest jsdom @testing-library/react @testing-library/jest-dom
```

- [ ] **Step 2: Write the data sync script**

Create `app-web/scripts/sync-data.mjs`:

```js
import { copyFileSync, existsSync, mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const src = path.resolve(__dirname, '../../app/data.js');
const destDir = path.resolve(__dirname, '../public');
const dest = path.join(destDir, 'data.js');

if (!existsSync(src)) {
  console.error(`Missing ${src} — run scripts/06_build_vote_deltas.py and scripts/07_top_competitors.py from the repo root first.`);
  process.exit(1);
}
if (!existsSync(destDir)) mkdirSync(destDir, { recursive: true });
copyFileSync(src, dest);
console.log(`Synced data.js -> ${dest}`);
```

This replaces the design doc's symlink example — verified this session that `ln -s` on this Windows dev environment silently falls back to a plain file copy rather than a real symlink (no Developer Mode enabled), so a copy script is the portable equivalent. Same intent: `app-web/` never duplicates or reformats the generation logic, it only ever reads the file the unchanged Python pipeline already produces.

- [ ] **Step 3: Wire the sync script into package.json**

Edit `app-web/package.json`, replace the `"scripts"` block:

```json
{
  "scripts": {
    "predev": "node scripts/sync-data.mjs",
    "dev": "vite",
    "prebuild": "node scripts/sync-data.mjs",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run"
  }
}
```

- [ ] **Step 4: Run the sync script and verify it works**

Run: `node scripts/sync-data.mjs` (from `app-web/`)
Expected: `Synced data.js -> .../app-web/public/data.js` printed, and `app-web/public/data.js` exists with the same content as `app/data.js`.

If it errors with the "Missing" message, run `python scripts/06_build_vote_deltas.py && python scripts/07_top_competitors.py` from the repo root first (both already ran successfully earlier this session, so `app/data.js` should already exist).

- [ ] **Step 5: Replace Vite's default index.html**

Replace `app-web/index.html`:

```html
<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>LEAL — Mapa Eleitoral Niterói</title>
  </head>
  <body>
    <div id="root"></div>
    <script src="/data.js"></script>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 6: Port the CSS**

Create `app-web/src/index.css` (ported verbatim from `app/index.html`'s `<style>` block, no behavior change):

```css
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #1a1a2e; color: #e0e0e0; }

#map { position: absolute; top: 0; left: 0; right: 0; bottom: 0; z-index: 1; }

#panel {
  position: absolute; top: 12px; left: 12px; z-index: 1000;
  background: rgba(20, 20, 40, 0.92); backdrop-filter: blur(8px);
  border-radius: 10px; padding: 16px; width: 320px;
  border: 1px solid rgba(255,255,255,0.08);
  max-height: calc(100vh - 24px); overflow-y: auto;
}

#panel h1 { font-size: 18px; font-weight: 700; margin-bottom: 2px; color: #fff; }
#panel .subtitle { font-size: 11px; color: #888; margin-bottom: 14px; }

.section-title { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #666; margin: 14px 0 6px; }

.layer-row {
  display: flex; align-items: center; gap: 8px; padding: 6px 8px;
  border-radius: 6px; cursor: pointer; transition: background 0.15s;
  margin-bottom: 2px;
}
.layer-row:hover { background: rgba(255,255,255,0.06); }
.layer-row input { cursor: pointer; }
.layer-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
.delta-dot { background: linear-gradient(90deg, #d94a4a, #d8d8ce, #55b96a); }
.layer-label { font-size: 13px; flex: 1; }
.layer-count { font-size: 12px; color: #888; font-variant-numeric: tabular-nums; }
.control-grid { display: grid; gap: 6px; }
.control-row { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.control-select {
  width: 100%;
  padding: 6px 8px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,0.14);
  background: rgba(255,255,255,0.04);
  color: #e0e0e0;
  font-size: 12px;
}
.control-select:focus { outline: none; border-color: rgba(255,255,255,0.32); }
.control-select option { background: #1a1a2e; color: #e0e0e0; }
.control-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 2px 0;
  font-size: 12px;
  color: #c9c9d1;
}
.control-note { font-size: 11px; color: #888; line-height: 1.45; margin-top: 4px; }

.year-bar { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 4px; }
.year-btn {
  padding: 4px 10px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.15);
  background: transparent; color: #aaa; font-size: 12px; cursor: pointer;
  transition: all 0.15s;
}
.year-btn:hover { border-color: rgba(255,255,255,0.3); color: #fff; }
.year-btn.active { background: rgba(255,255,255,0.15); color: #fff; border-color: rgba(255,255,255,0.3); font-weight: 600; }
.year-btn.municipal::before, .year-btn.federal::before {
  content: ''; display: inline-block; width: 6px; height: 6px; border-radius: 50%;
  margin-right: 5px; vertical-align: middle;
}
.year-btn.municipal::before { background: #2dd4bf; }
.year-btn.federal::before { background: #a78bfa; }
.year-type-legend { display: flex; align-items: center; gap: 12px; margin-top: 4px; font-size: 10px; color: #888; }
.year-type-legend .dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }

#stats {
  margin-top: 14px; padding: 10px; background: rgba(255,255,255,0.04);
  border-radius: 6px; font-size: 12px; line-height: 1.6;
}
#stats .stat-val { font-weight: 600; color: #fff; font-variant-numeric: tabular-nums; }
.delta-legend { display: flex; align-items: center; gap: 8px; margin-top: 8px; color: #888; font-size: 11px; }
.delta-scale { height: 6px; flex: 1; border-radius: 999px; background: linear-gradient(90deg, #d94a4a, #d8d8ce, #55b96a); }

.leaflet-popup-content-wrapper {
  background: rgba(20, 20, 40, 0.95) !important;
  color: #e0e0e0 !important; border-radius: 8px !important;
  border: 1px solid rgba(255,255,255,0.1) !important;
}
.leaflet-popup-tip { background: rgba(20, 20, 40, 0.95) !important; }
.leaflet-popup-content { font-size: 13px !important; line-height: 1.5 !important; }
.popup-title { font-weight: 700; font-size: 14px; margin-bottom: 4px; color: #fff; }
.popup-bairro { font-size: 11px; color: #888; margin-bottom: 8px; }
.popup-row { display: flex; justify-content: space-between; padding: 2px 0; }
.popup-label { color: #aaa; }
.popup-val { font-weight: 600; font-variant-numeric: tabular-nums; }
.popup-competitors { margin-top: 6px; padding-top: 4px; border-top: 1px solid rgba(255,255,255,0.1); }
.popup-competitors summary { cursor: pointer; color: #aaa; font-size: 12px; outline: none; }
.popup-competitors[open] summary { margin-bottom: 4px; }

#compare-panel {
  position: absolute; bottom: 24px; left: 50%; transform: translateX(-50%);
  z-index: 1000; background: rgba(20, 20, 40, 0.92); backdrop-filter: blur(8px);
  border-radius: 10px; padding: 12px 20px; border: 1px solid rgba(255,255,255,0.08);
  font-size: 13px; text-align: center;
}

@media (max-width: 640px) {
  #panel { width: calc(100vw - 24px); max-height: 52vh; }
  #compare-panel { left: 12px; right: 12px; bottom: 12px; transform: none; overflow-x: auto; }
}
```

Note: `#compare-panel`'s `display: none` default is dropped since React conditionally renders it (`CompareTable` returns `null` when nothing is selected — Task 8).

- [ ] **Step 7: Write the entry point**

Create `app-web/src/main.jsx`:

```jsx
import { createRoot } from 'react-dom/client';
import 'leaflet/dist/leaflet.css';
import App from './App.jsx';
import './index.css';

createRoot(document.getElementById('root')).render(<App />);
```

Create a placeholder `app-web/src/App.jsx` (replaced fully in Task 2):

```jsx
export default function App() {
  return <div>LEAL</div>;
}
```

- [ ] **Step 8: Configure Vitest**

Create `app-web/src/test-setup.js`:

```js
import '@testing-library/jest-dom/vitest';
```

Edit `app-web/vite.config.js`:

```js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test-setup.js',
  },
});
```

- [ ] **Step 9: Verify the dev server and test runner both work**

Run: `npm run dev` (from `app-web/`), open the printed local URL.
Expected: blank page showing "LEAL", no console errors. Stop the server (Ctrl+C).

Run: `npm test`
Expected: "No test files found" or similar — passes with 0 tests (none written yet).

- [ ] **Step 10: Ignore build/data artifacts**

Create `app-web/.gitignore`:

```
node_modules
dist
public/data.js
```

`public/data.js` is generated by the sync script, not source — same treatment as `app/data.js` itself.

- [ ] **Step 11: Commit**

```bash
git add app-web/package.json app-web/package-lock.json app-web/vite.config.js app-web/index.html app-web/src app-web/scripts app-web/.gitignore
git commit -m "chore: scaffold Vite+React app in app-web/"
```

---

### Task 2: Data loading — `useMapData` hook and bare map

**Files:**
- Create: `app-web/src/lib/useMapData.js`, `app-web/src/lib/useMapData.test.js`
- Create: `app-web/src/components/MapView.jsx`
- Modify: `app-web/src/App.jsx`

**Interfaces:**
- Consumes: `app-web/public/data.js` (from Task 1's sync script) setting `window.DATA`.
- Produces: `useMapData(): object | null` — reads `window.DATA`, returns `null` if absent. Consumed by every later task that needs `window.DATA`. `<MapView>` — consumed by Tasks 6, 7, 10 as the layer-hosting map shell.

- [ ] **Step 1: Write the failing test for `useMapData`**

Create `app-web/src/lib/useMapData.test.js`:

```js
import { describe, it, expect, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useMapData } from './useMapData';

describe('useMapData', () => {
  afterEach(() => {
    delete window.DATA;
  });

  it('returns window.DATA when present', () => {
    window.DATA = { hugo_leal: { type: 'FeatureCollection', features: [] } };
    const { result } = renderHook(() => useMapData());
    expect(result.current).toBe(window.DATA);
  });

  it('returns null when window.DATA is missing', () => {
    delete window.DATA;
    const { result } = renderHook(() => useMapData());
    expect(result.current).toBeNull();
  });

  it('reflects the real generated data.js shape', async () => {
    const raw = await import('../../public/data.js?raw');
    // eslint-disable-next-line no-eval
    window.DATA = undefined;
    (0, eval)(raw.default.replace('const DATA', 'window.DATA'));
    const { result } = renderHook(() => useMapData());
    expect(result.current).toHaveProperty('hugo_leal.features');
    expect(result.current).toHaveProperty('felipe_peixoto.features');
    const sample = result.current.hugo_leal.features[0].properties;
    expect(sample).toHaveProperty('ano');
    expect(sample).toHaveProperty('nr_local');
    expect(sample).toHaveProperty('QT_VOTOS');
  });
});
```

The third test is the data-contract regression check from the design spec: it loads the **real** generated `app-web/public/data.js` (synced from the actual pipeline output) and asserts the property shape components rely on, catching any silent drift from the Python side without touching Python. Requires `npm run predev` (or the sync script) to have run at least once — already true from Task 1.

`@testing-library/react`'s `renderHook` needs `react-dom/test-utils` peer support, already satisfied by the `react`/`react-dom` versions installed in Task 1.

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test` (from `app-web/`)
Expected: FAIL — `useMapData.js` doesn't exist yet (`Cannot find module`).

- [ ] **Step 3: Write `useMapData`**

Create `app-web/src/lib/useMapData.js`:

```js
export function useMapData() {
  return typeof window !== 'undefined' && window.DATA ? window.DATA : null;
}
```

No `useState`/`useEffect` needed — `data.js`'s `<script>` tag runs before the React bundle mounts (Task 1, `index.html`), so `window.DATA` is already set by the time any component first calls this hook.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test`
Expected: PASS (3 tests)

- [ ] **Step 5: Write `MapView`**

Create `app-web/src/components/MapView.jsx`:

```jsx
import { MapContainer, TileLayer, ZoomControl } from 'react-leaflet';

export default function MapView({ children }) {
  return (
    <MapContainer
      center={[-22.9017, -43.0783]}
      zoom={13}
      zoomControl={false}
      style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1 }}
    >
      <ZoomControl position="topright" />
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
        maxZoom={19}
      />
      {children}
    </MapContainer>
  );
}
```

- [ ] **Step 6: Wire `App.jsx` to render the bare map with a missing-data guard**

Replace `app-web/src/App.jsx`:

```jsx
import MapView from './components/MapView.jsx';
import { useMapData } from './lib/useMapData.js';

export default function App() {
  const data = useMapData();

  if (!data) {
    return <div style={{ padding: 24, color: '#e0e0e0' }}>Dados nao carregados.</div>;
  }

  return <MapView />;
}
```

- [ ] **Step 7: Manual browser check**

Run: `npm run dev` (from `app-web/`)
Expected: dark-tiled Leaflet map fills the screen, centered on Niterói, zoom controls top-right. No console errors. Stop the server.

- [ ] **Step 8: Commit**

```bash
git add app-web/src/lib/useMapData.js app-web/src/lib/useMapData.test.js app-web/src/components/MapView.jsx app-web/src/App.jsx
git commit -m "feat: load window.DATA and render bare map"
```

---

### Task 3: Pure logic — geo, filtering, and boundary annotation

**Files:**
- Create: `app-web/src/lib/geo.js`, `app-web/src/lib/geo.test.js`

**Interfaces:**
- Consumes: nothing from other tasks (pure logic, no I/O).
- Produces: `pointInRing(point: [number, number], ring: [number, number][]): boolean`, `pointInGeometry(point: [number, number], geometry: {type: string, coordinates: any}): boolean`, `normalizeText(value: string): string`, `featureName(feature: object): string`, `passesGeoFilter(props: object, selectedRegion: string, selectedBairro: string): boolean`, `annotateFeatureCollection(fc: object, regionFeatures: object[], bairroFeatures: object[]): object` — consumed by Task 4's App wiring, Task 9's `StatsPanel`, and Task 10's boundary/geo-filter components.

Note the signature change from the vanilla source: `passesGeoFilter` originally read `selectedRegion`/`selectedBairro` from global variables via closure. Here they're explicit parameters — there's no global state in the React version, so this is a necessary and deliberate adaptation, not a behavior change.

- [ ] **Step 1: Write the failing tests**

Create `app-web/src/lib/geo.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { pointInRing, pointInGeometry, normalizeText, featureName, passesGeoFilter, annotateFeatureCollection } from './geo';

describe('pointInRing', () => {
  const square = [[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]];

  it('returns true for a point inside the ring', () => {
    expect(pointInRing([5, 5], square)).toBe(true);
  });

  it('returns false for a point outside the ring', () => {
    expect(pointInRing([15, 15], square)).toBe(false);
  });
});

describe('pointInGeometry', () => {
  it('handles a Polygon with an outer ring only', () => {
    const geometry = { type: 'Polygon', coordinates: [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]] };
    expect(pointInGeometry([5, 5], geometry)).toBe(true);
    expect(pointInGeometry([50, 50], geometry)).toBe(false);
  });

  it('excludes points inside a hole (second ring)', () => {
    const geometry = {
      type: 'Polygon',
      coordinates: [
        [[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]],
        [[4, 4], [4, 6], [6, 6], [6, 4], [4, 4]],
      ],
    };
    expect(pointInGeometry([5, 5], geometry)).toBe(false);
    expect(pointInGeometry([1, 1], geometry)).toBe(true);
  });

  it('handles a MultiPolygon by checking each polygon', () => {
    const geometry = {
      type: 'MultiPolygon',
      coordinates: [
        [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]],
        [[[20, 20], [20, 30], [30, 30], [30, 20], [20, 20]]],
      ],
    };
    expect(pointInGeometry([25, 25], geometry)).toBe(true);
    expect(pointInGeometry([50, 50], geometry)).toBe(false);
  });

  it('returns false for missing or unsupported geometry', () => {
    expect(pointInGeometry([1, 1], null)).toBe(false);
    expect(pointInGeometry([1, 1], { type: 'Point', coordinates: [1, 1] })).toBe(false);
  });
});

describe('normalizeText', () => {
  it('strips accents and uppercases', () => {
    expect(normalizeText('Niterói')).toBe('NITEROI');
    expect(normalizeText('  são gonçalo  ')).toBe('SAO GONCALO');
  });

  it('handles null/undefined as empty string', () => {
    expect(normalizeText(null)).toBe('');
    expect(normalizeText(undefined)).toBe('');
  });
});

describe('featureName', () => {
  it('reads the first available name field', () => {
    expect(featureName({ properties: { tx_nome: 'Centro' } })).toBe('Centro');
    expect(featureName({ properties: { si_nome: 'Icarai' } })).toBe('Icarai');
    expect(featureName({ properties: {} })).toBe('');
    expect(featureName({})).toBe('');
  });
});

describe('passesGeoFilter', () => {
  const props = { __region: 'Regiao Oceanica', __bairro_geo: 'Icarai' };

  it('passes everything when both filters are "all"', () => {
    expect(passesGeoFilter(props, 'all', 'all')).toBe(true);
  });

  it('filters by region', () => {
    expect(passesGeoFilter(props, 'Regiao Oceanica', 'all')).toBe(true);
    expect(passesGeoFilter(props, 'Regiao Norte', 'all')).toBe(false);
  });

  it('filters by bairro, falling back to props.bairro when __bairro_geo is absent', () => {
    expect(passesGeoFilter(props, 'all', 'Icarai')).toBe(true);
    expect(passesGeoFilter({ bairro: 'Icarai' }, 'all', 'Icarai')).toBe(true);
    expect(passesGeoFilter({ bairro: 'Centro' }, 'all', 'Icarai')).toBe(false);
  });
});

describe('annotateFeatureCollection', () => {
  const regionFeatures = [{
    properties: { tx_nome: 'Regiao Oceanica' },
    geometry: { type: 'Polygon', coordinates: [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]] },
  }];
  const bairroFeatures = [{
    properties: { tx_nome: 'Icarai' },
    geometry: { type: 'Polygon', coordinates: [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]] },
  }];

  it('tags each feature with __region and __bairro_geo without mutating the input', () => {
    const fc = {
      type: 'FeatureCollection',
      features: [{ type: 'Feature', geometry: { type: 'Point', coordinates: [5, 5] }, properties: { nr_local: '1' } }],
    };
    const result = annotateFeatureCollection(fc, regionFeatures, bairroFeatures);
    expect(result.features[0].properties.__region).toBe('REGIAO OCEANICA');
    expect(result.features[0].properties.__bairro_geo).toBe('ICARAI');
    expect(fc.features[0].properties.__region).toBeUndefined();
  });

  it('returns empty tags for a point outside all boundaries', () => {
    const fc = {
      type: 'FeatureCollection',
      features: [{ type: 'Feature', geometry: { type: 'Point', coordinates: [500, 500] }, properties: {} }],
    };
    const result = annotateFeatureCollection(fc, regionFeatures, bairroFeatures);
    expect(result.features[0].properties.__region).toBe('');
    expect(result.features[0].properties.__bairro_geo).toBe('');
  });

  it('passes through a falsy collection unchanged', () => {
    expect(annotateFeatureCollection(null, regionFeatures, bairroFeatures)).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test` (from `app-web/`)
Expected: FAIL — `geo.js` doesn't exist.

- [ ] **Step 3: Write `geo.js`**

Create `app-web/src/lib/geo.js`:

```js
export function pointInRing(point, ring) {
  const x = point[0];
  const y = point[1];
  let inside = false;

  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    const intersect = ((yi > y) !== (yj > y)) &&
      (x < ((xj - xi) * (y - yi)) / ((yj - yi) || 1e-12) + xi);
    if (intersect) inside = !inside;
  }

  return inside;
}

export function pointInGeometry(point, geometry) {
  if (!geometry) return false;
  if (geometry.type === 'Polygon') {
    const rings = geometry.coordinates || [];
    if (!rings.length) return false;
    if (!pointInRing(point, rings[0])) return false;
    for (let i = 1; i < rings.length; i++) {
      if (pointInRing(point, rings[i])) return false;
    }
    return true;
  }

  if (geometry.type === 'MultiPolygon') {
    return (geometry.coordinates || []).some(poly => pointInGeometry(point, { type: 'Polygon', coordinates: poly }));
  }

  return false;
}

export function normalizeText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toUpperCase()
    .trim();
}

export function featureName(feature) {
  const props = feature?.properties || {};
  return props.tx_nome || props.si_nome || props.Nome_Ecid || props.nome || props.name || '';
}

export function passesGeoFilter(props, selectedRegion, selectedBairro) {
  const region = normalizeText(selectedRegion);
  const bairro = normalizeText(selectedBairro);
  const featureRegion = normalizeText(props.__region || '');
  const featureBairro = normalizeText(props.__bairro_geo || props.bairro || '');

  if (region !== 'ALL' && featureRegion !== region) return false;
  if (bairro !== 'ALL' && featureBairro !== bairro) return false;
  return true;
}

function findContainingName(point, features) {
  for (const feature of features) {
    if (pointInGeometry(point, feature.geometry)) {
      return normalizeText(featureName(feature));
    }
  }
  return '';
}

export function annotateFeatureCollection(fc, regionFeatures, bairroFeatures) {
  if (!fc) return fc;
  return {
    ...fc,
    features: fc.features.map(f => {
      if (!f.geometry) return f;
      const point = f.geometry.coordinates;
      return {
        ...f,
        properties: {
          ...f.properties,
          __region: findContainingName(point, regionFeatures),
          __bairro_geo: findContainingName(point, bairroFeatures),
        },
      };
    }),
  };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test`
Expected: PASS (all `geo.test.js` cases plus the 3 from Task 2)

- [ ] **Step 5: Commit**

```bash
git add app-web/src/lib/geo.js app-web/src/lib/geo.test.js
git commit -m "feat: port geo, filtering, and boundary-annotation logic"
```

---

### Task 4: Pure logic — vote aggregation and visual formulas

**Files:**
- Create: `app-web/src/lib/aggregate.js`, `app-web/src/lib/aggregate.test.js`
- Create: `app-web/src/lib/visual.js`, `app-web/src/lib/visual.test.js`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `aggregateByLocal(features: Feature[]): Feature[]`, `interpolateChannel(a: number, b: number, t: number): number`, `interpolateColor(start: [number,number,number], end: [number,number,number], t: number): string`, `getDivergingColor(value: number, maxAbs: number): string`, `getRadius(votes: number, key: string): number`, `getDeltaRadius(delta: number): number` — consumed by Task 6's `MarkerLayer`, Task 7's `DeltaLayer`.

- [ ] **Step 1: Write the failing tests**

Create `app-web/src/lib/aggregate.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { aggregateByLocal } from './aggregate';

describe('aggregateByLocal', () => {
  it('sums votes across years for the same local', () => {
    const features = [
      { type: 'Feature', geometry: { type: 'Point', coordinates: [1, 2] }, properties: { nr_local: '10', ano: 2018, QT_VOTOS: 100, n_secoes: 5 } },
      { type: 'Feature', geometry: { type: 'Point', coordinates: [1, 2] }, properties: { nr_local: '10', ano: 2022, QT_VOTOS: 150, n_secoes: 6 } },
    ];
    const result = aggregateByLocal(features);
    expect(result).toHaveLength(1);
    expect(result[0].properties.QT_VOTOS).toBe(250);
    expect(result[0].properties.n_secoes).toBe(6);
    expect(result[0].properties._years).toEqual({ 2018: 100, 2022: 150 });
    expect(result[0].geometry).toEqual(features[0].geometry);
  });

  it('keeps different locals separate', () => {
    const features = [
      { type: 'Feature', geometry: { type: 'Point', coordinates: [1, 2] }, properties: { nr_local: '10', ano: 2022, QT_VOTOS: 100, n_secoes: 5 } },
      { type: 'Feature', geometry: { type: 'Point', coordinates: [3, 4] }, properties: { nr_local: '20', ano: 2022, QT_VOTOS: 200, n_secoes: 3 } },
    ];
    expect(aggregateByLocal(features)).toHaveLength(2);
  });

  it('returns an empty array for no features', () => {
    expect(aggregateByLocal([])).toEqual([]);
  });
});
```

Create `app-web/src/lib/visual.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { interpolateChannel, interpolateColor, getDivergingColor, getRadius, getDeltaRadius } from './visual';

describe('interpolateChannel', () => {
  it('interpolates linearly and rounds', () => {
    expect(interpolateChannel(0, 100, 0)).toBe(0);
    expect(interpolateChannel(0, 100, 1)).toBe(100);
    expect(interpolateChannel(0, 100, 0.5)).toBe(50);
  });
});

describe('interpolateColor', () => {
  it('produces an rgb() string between two colors', () => {
    expect(interpolateColor([0, 0, 0], [100, 100, 100], 0.5)).toBe('rgb(50, 50, 50)');
  });
});

describe('getDivergingColor', () => {
  it('trends toward the gain color for positive values', () => {
    const color = getDivergingColor(100, 100);
    expect(color).toBe('rgb(85, 185, 106)');
  });

  it('trends toward the loss color for negative values', () => {
    const color = getDivergingColor(-100, 100);
    expect(color).toBe('rgb(217, 74, 74)');
  });

  it('returns the neutral color at zero', () => {
    expect(getDivergingColor(0, 100)).toBe('rgb(216, 216, 206)');
  });
});

describe('getRadius', () => {
  it('uses a larger multiplier for hugo_leal than other layers', () => {
    expect(getRadius(100, 'hugo_leal')).toBeGreaterThan(getRadius(100, 'felipe_peixoto'));
    expect(getRadius(100, 'hugo_leal')).toBeGreaterThan(getRadius(100, 'psd'));
  });

  it('floors at 4', () => {
    expect(getRadius(0, 'hugo_leal')).toBe(4);
    expect(getRadius(0, 'psd')).toBe(4);
  });
});

describe('getDeltaRadius', () => {
  it('returns 4 for a zero delta', () => {
    expect(getDeltaRadius(0)).toBe(4);
  });

  it('scales with the magnitude of the delta, clamped between 5 and 28', () => {
    expect(getDeltaRadius(1)).toBeGreaterThanOrEqual(5);
    expect(getDeltaRadius(100000)).toBeLessThanOrEqual(28);
  });

  it('treats gains and losses symmetrically', () => {
    expect(getDeltaRadius(50)).toBe(getDeltaRadius(-50));
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test`
Expected: FAIL — `aggregate.js` and `visual.js` don't exist.

- [ ] **Step 3: Write `aggregate.js`**

Create `app-web/src/lib/aggregate.js`:

```js
export function aggregateByLocal(features) {
  const byLocal = {};
  features.forEach(f => {
    const key = f.properties.nr_local;
    if (!byLocal[key]) {
      byLocal[key] = {
        type: 'Feature',
        geometry: f.geometry,
        properties: {
          ...f.properties,
          QT_VOTOS: 0,
          n_secoes: 0,
          _years: {},
        },
      };
    }
    byLocal[key].properties.QT_VOTOS += f.properties.QT_VOTOS;
    byLocal[key].properties.n_secoes = Math.max(byLocal[key].properties.n_secoes, f.properties.n_secoes);
    byLocal[key].properties._years[f.properties.ano] = f.properties.QT_VOTOS;
  });
  return Object.values(byLocal);
}
```

- [ ] **Step 4: Write `visual.js`**

Create `app-web/src/lib/visual.js`:

```js
export function interpolateChannel(a, b, t) {
  return Math.round(a + (b - a) * t);
}

export function interpolateColor(start, end, t) {
  return `rgb(${interpolateChannel(start[0], end[0], t)}, ${interpolateChannel(start[1], end[1], t)}, ${interpolateChannel(start[2], end[2], t)})`;
}

export function getDivergingColor(value, maxAbs) {
  const neutral = [216, 216, 206];
  const gain = [85, 185, 106];
  const loss = [217, 74, 74];
  const t = Math.min(1, Math.sqrt(Math.abs(value) / Math.max(maxAbs, 1)));
  return value >= 0 ? interpolateColor(neutral, gain, t) : interpolateColor(neutral, loss, t);
}

export function getRadius(votes, key) {
  if (key === 'hugo_leal') return Math.max(4, Math.sqrt(votes) * 2.5);
  return Math.max(4, Math.sqrt(votes) * 0.8);
}

export function getDeltaRadius(delta) {
  const absDelta = Math.abs(Number(delta) || 0);
  if (absDelta === 0) return 4;
  return Math.max(5, Math.min(28, Math.sqrt(absDelta) * 0.72));
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npm test`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app-web/src/lib/aggregate.js app-web/src/lib/aggregate.test.js app-web/src/lib/visual.js app-web/src/lib/visual.test.js
git commit -m "feat: port vote-aggregation and visual-formula logic"
```

---

### Task 5: Pure logic — formatting and election-type math

**Files:**
- Create: `app-web/src/lib/format.js`, `app-web/src/lib/format.test.js`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `electionType(year: number): 'Municipal' | 'Federal'`, `electionPairLabel(startYear: number, endYear: number): string`, `formatSigned(value: number): string`, `formatPct(value: number): string` — consumed by Task 6's `YearFilter`, Task 7's `DeltaPopupContent`/`DeltaPairFilter`, Task 9's `StatsPanel`.

- [ ] **Step 1: Write the failing tests**

Create `app-web/src/lib/format.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { electionType, electionPairLabel, formatSigned, formatPct } from './format';

describe('electionType', () => {
  it('classifies years divisible by 4 as Municipal', () => {
    expect(electionType(2012)).toBe('Municipal');
    expect(electionType(2016)).toBe('Municipal');
    expect(electionType(2020)).toBe('Municipal');
    expect(electionType(2024)).toBe('Municipal');
  });

  it('classifies years not divisible by 4 as Federal', () => {
    expect(electionType(2010)).toBe('Federal');
    expect(electionType(2014)).toBe('Federal');
    expect(electionType(2018)).toBe('Federal');
    expect(electionType(2022)).toBe('Federal');
  });
});

describe('electionPairLabel', () => {
  it('labels a municipal-to-federal pair correctly', () => {
    // Regression case: 2012 is Municipal, 2014 is Federal — this exact pair
    // exposed a fixture bug in the Python-side test suite for the same
    // election-type math earlier in this project; covering it here too.
    expect(electionPairLabel(2012, 2014)).toBe('Municipal -> Federal');
  });

  it('labels a federal-to-federal pair correctly', () => {
    expect(electionPairLabel(2010, 2014)).toBe('Federal -> Federal');
  });

  it('labels a municipal-to-municipal pair correctly', () => {
    expect(electionPairLabel(2020, 2024)).toBe('Municipal -> Municipal');
  });
});

describe('formatSigned', () => {
  it('prefixes positive values with +', () => {
    expect(formatSigned(42)).toBe('+42');
  });

  it('leaves negative values as-is', () => {
    expect(formatSigned(-42)).toBe('-42');
  });

  it('formats zero without a sign', () => {
    expect(formatSigned(0)).toBe('0');
  });

  it('formats large numbers with pt-BR thousands separators', () => {
    expect(formatSigned(12345)).toBe('+12.345');
  });

  it('treats non-numeric input as zero', () => {
    expect(formatSigned(undefined)).toBe('0');
    expect(formatSigned(null)).toBe('0');
  });
});

describe('formatPct', () => {
  it('prefixes positive percentages with +', () => {
    expect(formatPct(12.3)).toBe('+12,3%');
  });

  it('leaves negative percentages as-is', () => {
    expect(formatPct(-5)).toBe('-5%');
  });

  it('returns a dash for non-finite input', () => {
    expect(formatPct(NaN)).toBe('-');
    expect(formatPct(undefined)).toBe('-');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test`
Expected: FAIL — `format.js` doesn't exist.

- [ ] **Step 3: Write `format.js`**

Create `app-web/src/lib/format.js`:

```js
export function electionType(year) {
  return Number(year) % 4 === 0 ? 'Municipal' : 'Federal';
}

export function electionPairLabel(startYear, endYear) {
  return `${electionType(startYear)} -> ${electionType(endYear)}`;
}

export function formatSigned(value) {
  const n = Math.round(Number(value) || 0);
  return `${n > 0 ? '+' : ''}${n.toLocaleString('pt-BR')}`;
}

export function formatPct(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '-';
  return `${n > 0 ? '+' : ''}${n.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app-web/src/lib/format.js app-web/src/lib/format.test.js
git commit -m "feat: port formatting and election-type math"
```

---

### Task 6: First marker layer — Hugo Leal, popup, competitor section, year filter

**Files:**
- Create: `app-web/src/lib/constants.js`
- Create: `app-web/src/components/CompetitorSection.jsx`, `app-web/src/components/CompetitorSection.test.jsx`
- Create: `app-web/src/components/PopupContent.jsx`, `app-web/src/components/PopupContent.test.jsx`
- Create: `app-web/src/components/MarkerLayer.jsx`
- Create: `app-web/src/components/YearFilter.jsx`, `app-web/src/components/YearFilter.test.jsx`
- Modify: `app-web/src/App.jsx`

**Interfaces:**
- Consumes: `getRadius` (Task 4), `electionType` (Task 5), `useMapData` (Task 2), `MapView` (Task 2).
- Produces: `COLORS`, `LABELS`, `BASE_KEYS`, `DELTA_METRICS`, `COMPETITOR_LAYER_BY_METRIC` (all in `constants.js`) — consumed by every remaining component task. `<MarkerLayer layerKey features onSelect>`, `<PopupContent p layerKey>`, `<CompetitorSection title props>`, `<YearFilter years selectedYear onChange>` — consumed by Task 7 (more layers) and Task 10 (final App wiring).

- [ ] **Step 1: Write the constants module**

Create `app-web/src/lib/constants.js`:

```js
export const COLORS = {
  hugo_leal: '#4a90d9',
  felipe_peixoto: '#50c878',
  psd: '#e8a838',
  deltaLoss: '#d94a4a',
  deltaNeutral: '#d8d8ce',
  deltaGain: '#55b96a',
};

export const LABELS = {
  hugo_leal: 'Hugo Leal',
  felipe_peixoto: 'Felipe Peixoto',
  psd: 'PSD',
};

export const BASE_KEYS = ['hugo_leal', 'felipe_peixoto', 'psd'];

export const DELTA_METRICS = {
  hugo: { label: 'Hugo', field: 'delta_hugo' },
  felipe: { label: 'Felipe', field: 'delta_felipe' },
  psd: { label: 'PSD', field: 'delta_psd' },
};

export const COMPETITOR_LAYER_BY_METRIC = { hugo: 'hugo_leal', felipe: 'felipe_peixoto' };
```

No test file — this is static data, not logic; the components consuming it are what get tested.

- [ ] **Step 2: Write the failing test for `CompetitorSection`**

Create `app-web/src/components/CompetitorSection.test.jsx`:

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CompetitorSection from './CompetitorSection';

describe('CompetitorSection', () => {
  it('renders up to 3 ranked rows with name, party, and votes', () => {
    render(<CompetitorSection title="Concorrencia" props={{
      top1_nome: 'FULANO', top1_partido: 'PSD', top1_votos: 100,
      top2_nome: 'BELTRANO', top2_partido: 'PT', top2_votos: 80,
    }} />);
    expect(screen.getByText('Concorrencia')).toBeInTheDocument();
    expect(screen.getByText(/FULANO \(PSD\) — 100/)).toBeInTheDocument();
    expect(screen.getByText(/BELTRANO \(PT\) — 80/)).toBeInTheDocument();
  });

  it('shows "Sem dados" when no competitor fields are present', () => {
    render(<CompetitorSection title="Concorrencia" props={{}} />);
    expect(screen.getByText('Sem dados')).toBeInTheDocument();
  });

  it('is collapsed by default (a native <details> element)', () => {
    render(<CompetitorSection title="Concorrencia" props={{ top1_nome: 'FULANO', top1_partido: 'PSD', top1_votos: 1 }} />);
    const details = screen.getByText('Concorrencia').closest('details');
    expect(details).not.toHaveAttribute('open');
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `npm test`
Expected: FAIL — `CompetitorSection.jsx` doesn't exist.

- [ ] **Step 4: Write `CompetitorSection`**

Create `app-web/src/components/CompetitorSection.jsx`:

```jsx
function competitorRows(props) {
  const rows = [];
  for (let i = 1; i <= 3; i++) {
    const nome = props[`top${i}_nome`];
    if (!nome) continue;
    const partido = props[`top${i}_partido`] || '-';
    const votos = Number(props[`top${i}_votos`] || 0).toLocaleString('pt-BR');
    rows.push(
      <div className="popup-row" key={i}>
        <span className="popup-label">{i}º</span>
        <span className="popup-val">{nome} ({partido}) — {votos}</span>
      </div>
    );
  }
  return rows.length ? rows : (
    <div className="popup-row"><span className="popup-label">Sem dados</span></div>
  );
}

export default function CompetitorSection({ title, props }) {
  return (
    <details className="popup-competitors">
      <summary>{title}</summary>
      {competitorRows(props)}
    </details>
  );
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test`
Expected: PASS

- [ ] **Step 6: Write the failing test for `PopupContent`**

Create `app-web/src/components/PopupContent.test.jsx`:

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PopupContent from './PopupContent';

const baseProps = { nm_local: 'Escola Teste', bairro: 'Icarai', ano: 2022, QT_VOTOS: 50, n_secoes: 3 };

describe('PopupContent', () => {
  it('renders local name, bairro, year, votes, and secoes for a single-year feature', () => {
    render(<PopupContent p={baseProps} layerKey="hugo_leal" />);
    expect(screen.getByText('Escola Teste')).toBeInTheDocument();
    expect(screen.getByText('Icarai')).toBeInTheDocument();
    expect(screen.getByText('2022')).toBeInTheDocument();
    expect(screen.getByText('50')).toBeInTheDocument();
  });

  it('shows the competitor section for hugo_leal and felipe_peixoto', () => {
    render(<PopupContent p={baseProps} layerKey="hugo_leal" />);
    expect(screen.getByText('Concorrencia')).toBeInTheDocument();
  });

  it('hides the competitor section for psd', () => {
    render(<PopupContent p={baseProps} layerKey="psd" />);
    expect(screen.queryByText('Concorrencia')).not.toBeInTheDocument();
  });

  it('hides the competitor section in aggregated ("Todos" years) mode, showing a yearly breakdown instead', () => {
    const aggregated = { ...baseProps, _years: { 2018: 20, 2022: 30 }, QT_VOTOS: 50 };
    render(<PopupContent p={aggregated} layerKey="hugo_leal" />);
    expect(screen.queryByText('Concorrencia')).not.toBeInTheDocument();
    expect(screen.getByText('2018')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
    expect(screen.getByText('Total')).toBeInTheDocument();
  });
});
```

- [ ] **Step 7: Run test to verify it fails**

Run: `npm test`
Expected: FAIL — `PopupContent.jsx` doesn't exist.

- [ ] **Step 8: Write `PopupContent`**

Create `app-web/src/components/PopupContent.jsx`:

```jsx
import CompetitorSection from './CompetitorSection';
import { COLORS, LABELS, COMPETITOR_LAYER_BY_METRIC } from '../lib/constants';

export default function PopupContent({ p, layerKey }) {
  const hasCompetitorData = Object.values(COMPETITOR_LAYER_BY_METRIC).includes(layerKey);

  return (
    <div>
      <div className="popup-title">{p.nm_local || `Local ${p.nr_local}`}</div>
      <div className="popup-bairro">{p.bairro || ''}</div>
      <div className="popup-row">
        <span className="popup-label">Candidato/Partido</span>
        <span className="popup-val" style={{ color: COLORS[layerKey] }}>{LABELS[layerKey]}</span>
      </div>
      {p._years ? (
        <>
          {Object.entries(p._years).sort((a, b) => a[0] - b[0]).map(([y, v]) => (
            <div className="popup-row" key={y}>
              <span className="popup-label">{y}</span>
              <span className="popup-val">{v.toLocaleString('pt-BR')}</span>
            </div>
          ))}
          <div className="popup-row" style={{ borderTop: '1px solid rgba(255,255,255,0.1)', marginTop: 4, paddingTop: 4 }}>
            <span className="popup-label">Total</span>
            <span className="popup-val">{p.QT_VOTOS.toLocaleString('pt-BR')}</span>
          </div>
        </>
      ) : (
        <>
          <div className="popup-row"><span className="popup-label">Ano</span><span className="popup-val">{p.ano}</span></div>
          <div className="popup-row"><span className="popup-label">Votos</span><span className="popup-val">{p.QT_VOTOS.toLocaleString('pt-BR')}</span></div>
          <div className="popup-row"><span className="popup-label">Secoes</span><span className="popup-val">{p.n_secoes}</span></div>
          {hasCompetitorData && <CompetitorSection title="Concorrencia" props={p} />}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 9: Run test to verify it passes**

Run: `npm test`
Expected: PASS

- [ ] **Step 10: Write `MarkerLayer` (no separate test — covered end-to-end by manual browser check in Step 13)**

Create `app-web/src/components/MarkerLayer.jsx`:

```jsx
import { CircleMarker, Popup } from 'react-leaflet';
import PopupContent from './PopupContent';
import { COLORS } from '../lib/constants';
import { getRadius } from '../lib/visual';

export default function MarkerLayer({ layerKey, features, onSelect }) {
  return (
    <>
      {features.map(f => {
        const p = f.properties;
        const [lng, lat] = f.geometry.coordinates;
        return (
          <CircleMarker
            key={`${layerKey}-${p.nr_local}-${p.ano ?? 'all'}`}
            center={[lat, lng]}
            radius={getRadius(p.QT_VOTOS, layerKey)}
            pathOptions={{ fillColor: COLORS[layerKey], fillOpacity: 0.55, color: COLORS[layerKey], weight: 1, opacity: 0.8 }}
            eventHandlers={{
              mouseover: (e) => e.target.setStyle({ fillOpacity: 0.85, weight: 2 }),
              mouseout: (e) => e.target.setStyle({ fillOpacity: 0.55, weight: 1 }),
              click: () => onSelect?.(p, f.geometry.coordinates),
            }}
          >
            <Popup>
              <PopupContent p={p} layerKey={layerKey} />
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}
```

- [ ] **Step 11: Write the failing test for `YearFilter`**

Create `app-web/src/components/YearFilter.test.jsx`:

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import YearFilter from './YearFilter';

describe('YearFilter', () => {
  it('renders a "Todos" button plus one per year', () => {
    render(<YearFilter years={[2018, 2022]} selectedYear={2022} onChange={() => {}} />);
    expect(screen.getByText('Todos')).toBeInTheDocument();
    expect(screen.getByText('2018')).toBeInTheDocument();
    expect(screen.getByText('2022')).toBeInTheDocument();
  });

  it('marks the selected year active', () => {
    render(<YearFilter years={[2018, 2022]} selectedYear={2022} onChange={() => {}} />);
    expect(screen.getByText('2022')).toHaveClass('active');
    expect(screen.getByText('2018')).not.toHaveClass('active');
  });

  it('shows the municipal/federal indicator class per year', () => {
    render(<YearFilter years={[2020, 2022]} selectedYear={2022} onChange={() => {}} />);
    expect(screen.getByText('2020')).toHaveClass('municipal');
    expect(screen.getByText('2022')).toHaveClass('federal');
  });

  it('fires onChange with the clicked year, or null for "Todos"', () => {
    const onChange = vi.fn();
    render(<YearFilter years={[2018, 2022]} selectedYear={2022} onChange={onChange} />);
    fireEvent.click(screen.getByText('2018'));
    expect(onChange).toHaveBeenCalledWith(2018);
    fireEvent.click(screen.getByText('Todos'));
    expect(onChange).toHaveBeenCalledWith(null);
  });
});
```

- [ ] **Step 12: Run test to verify it fails, then write `YearFilter`**

Run: `npm test` — expect FAIL (`YearFilter.jsx` doesn't exist).

Create `app-web/src/components/YearFilter.jsx`:

```jsx
import { electionType } from '../lib/format';

export default function YearFilter({ years, selectedYear, onChange }) {
  return (
    <>
      <div className="year-bar">
        <button className={'year-btn' + (selectedYear === null ? ' active' : '')} onClick={() => onChange(null)}>
          Todos
        </button>
        {years.map(y => (
          <button
            key={y}
            className={'year-btn' + (selectedYear === y ? ' active' : '') + ' ' + electionType(y).toLowerCase()}
            title={electionType(y)}
            onClick={() => onChange(y)}
          >
            {y}
          </button>
        ))}
      </div>
      <div className="year-type-legend">
        <span><span className="dot" style={{ background: '#2dd4bf' }} /> Municipal</span>
        <span><span className="dot" style={{ background: '#a78bfa' }} /> Federal</span>
      </div>
    </>
  );
}
```

Run: `npm test` — expect PASS.

- [ ] **Step 13: Wire it all into `App.jsx`**

Replace `app-web/src/App.jsx`:

```jsx
import { useState, useMemo } from 'react';
import MapView from './components/MapView.jsx';
import MarkerLayer from './components/MarkerLayer.jsx';
import YearFilter from './components/YearFilter.jsx';
import { useMapData } from './lib/useMapData.js';
import { BASE_KEYS } from './lib/constants.js';

export default function App() {
  const data = useMapData();

  const allYears = useMemo(() => {
    if (!data) return [];
    return [...new Set(
      BASE_KEYS.flatMap(key => (data[key]?.features || []).map(f => Number(f.properties.ano)).filter(Number.isFinite))
    )].sort((a, b) => a - b);
  }, [data]);

  const [selectedYear, setSelectedYear] = useState(() => (allYears.includes(2022) ? 2022 : (allYears[allYears.length - 1] ?? null)));
  const [compareSelection, setCompareSelection] = useState(null);

  if (!data) {
    return <div style={{ padding: 24, color: '#e0e0e0' }}>Dados nao carregados.</div>;
  }

  const year = selectedYear;
  const hugoFeatures = (data.hugo_leal?.features || []).filter(f => f.properties.ano === year);

  return (
    <>
      <MapView>
        <MarkerLayer
          layerKey="hugo_leal"
          features={hugoFeatures}
          onSelect={(p, coords) => setCompareSelection({ props: p, coords })}
        />
      </MapView>

      <div id="panel">
        <h1>LEAL</h1>
        <div className="subtitle">Mapa Eleitoral — Niterói</div>
        <div className="section-title">Ano</div>
        <YearFilter years={allYears} selectedYear={year} onChange={setSelectedYear} />
      </div>
    </>
  );
}
```

`compareSelection` state is introduced now (unused until Task 8's `CompareTable` exists) so `MarkerLayer`'s `onSelect` has a real destination from the start, rather than reworking the click handler later.

- [ ] **Step 14: Manual browser check**

Run: `npm run dev` (from `app-web/`)
Expected: real Hugo Leal markers appear on the map for 2022 (compare against the vanilla `app/` — same locations, same approximate sizes). Click a marker — popup shows local name, bairro, candidate, year, votes, seções, and a collapsed "▸ Concorrência" line. Expand it — shows real top-3 competitor rows matching what the vanilla app shows for the same location. Click a different year button — markers update, dot color matches Municipal/Federal. Stop the server.

- [ ] **Step 15: Commit**

```bash
git add app-web/src/lib/constants.js app-web/src/components/CompetitorSection.jsx app-web/src/components/CompetitorSection.test.jsx app-web/src/components/PopupContent.jsx app-web/src/components/PopupContent.test.jsx app-web/src/components/MarkerLayer.jsx app-web/src/components/YearFilter.jsx app-web/src/components/YearFilter.test.jsx app-web/src/App.jsx
git commit -m "feat: render Hugo Leal marker layer with popup and year filter"
```

---

### Task 7: Remaining marker layers, delta layer, delta popup, and layer/metric filters

**Files:**
- Create: `app-web/src/lib/findFeature.js`, `app-web/src/lib/findFeature.test.js`
- Create: `app-web/src/components/DeltaPopupContent.jsx`, `app-web/src/components/DeltaPopupContent.test.jsx`
- Create: `app-web/src/components/DeltaLayer.jsx`
- Create: `app-web/src/components/LayerToggles.jsx`, `app-web/src/components/DeltaPairFilter.jsx`, `app-web/src/components/DeltaMetricFilter.jsx`
- Modify: `app-web/src/App.jsx`

**Interfaces:**
- Consumes: `getDivergingColor`/`getDeltaRadius` (Task 4), `formatSigned`/`formatPct`/`electionPairLabel` (Task 5), `CompetitorSection`/`MarkerLayer`/`COLORS`/`LABELS`/`DELTA_METRICS`/`COMPETITOR_LAYER_BY_METRIC` (Task 6).
- Produces: `findYearLocalFeature(data: object, layerKey: string, ano: number, nrLocal: string): Feature | null`, `<DeltaLayer features metric selectedDeltaMetric data>`, `<LayerToggles toggles counts onToggle>`, `<DeltaPairFilter pairs selectedPair onChange>`, `<DeltaMetricFilter metrics selectedMetric onChange>` — consumed by Task 10's final App wiring.

- [ ] **Step 1: Write the failing test for `findYearLocalFeature`**

Create `app-web/src/lib/findFeature.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { findYearLocalFeature } from './findFeature';

const data = {
  hugo_leal: {
    features: [
      { properties: { ano: 2022, nr_local: '10' } },
      { properties: { ano: 2018, nr_local: '10' } },
    ],
  },
};

describe('findYearLocalFeature', () => {
  it('finds the matching feature by year and local, coercing nr_local to string', () => {
    const result = findYearLocalFeature(data, 'hugo_leal', 2022, 10);
    expect(result).toBe(data.hugo_leal.features[0]);
  });

  it('returns null when the layer does not exist', () => {
    expect(findYearLocalFeature(data, 'nonexistent', 2022, '10')).toBeNull();
  });

  it('returns null when no feature matches', () => {
    expect(findYearLocalFeature(data, 'hugo_leal', 1999, '10')).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails, then write `findFeature.js`**

Run: `npm test` — expect FAIL.

Create `app-web/src/lib/findFeature.js`:

```js
export function findYearLocalFeature(data, layerKey, ano, nrLocal) {
  const fc = data[layerKey];
  if (!fc) return null;
  return fc.features.find(
    f => f.properties.ano === ano && String(f.properties.nr_local) === String(nrLocal)
  ) || null;
}
```

Run: `npm test` — expect PASS.

- [ ] **Step 3: Write the failing test for `DeltaPopupContent`**

Create `app-web/src/components/DeltaPopupContent.test.jsx`:

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import DeltaPopupContent from './DeltaPopupContent';

const p = {
  nm_local: 'Escola Teste', bairro: 'Icarai', pair: '2022-2024', nr_local: '10',
  ano_inicio: 2022, ano_fim: 2024, tipo_par: 'Federal -> Municipal',
  delta_hugo: -10, delta_felipe: 20, delta_psd: 5,
  votos_hugo_inicio: 50, votos_hugo_fim: 40,
  votos_felipe_inicio: 30, votos_felipe_fim: 50,
  votos_psd_inicio: 100, votos_psd_fim: 105,
  secoes_inicio: 3, secoes_fim: 4, secao_churn: 0.1,
};
const metric = { label: 'Hugo', field: 'delta_hugo' };
const noopFind = () => null;

describe('DeltaPopupContent', () => {
  it('renders the local name and delta fields', () => {
    render(<DeltaPopupContent p={p} metric={metric} color="#fff" selectedDeltaMetric="hugo" findYearLocalFeature={noopFind} />);
    expect(screen.getByText('Escola Teste')).toBeInTheDocument();
    expect(screen.getByText('Delta Hugo')).toBeInTheDocument();
    expect(screen.getByText('-10')).toBeInTheDocument();
  });

  it('shows two competitor sections (start and end year) for the hugo metric', () => {
    render(<DeltaPopupContent p={p} metric={metric} color="#fff" selectedDeltaMetric="hugo" findYearLocalFeature={noopFind} />);
    expect(screen.getByText('Concorrencia 2022')).toBeInTheDocument();
    expect(screen.getByText('Concorrencia 2024')).toBeInTheDocument();
  });

  it('shows no competitor sections for the psd metric', () => {
    render(<DeltaPopupContent p={p} metric={{ label: 'PSD', field: 'delta_psd' }} color="#fff" selectedDeltaMetric="psd" findYearLocalFeature={noopFind} />);
    expect(screen.queryByText(/Concorrencia/)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run test to verify it fails, then write `DeltaPopupContent`**

Run: `npm test` — expect FAIL.

Create `app-web/src/components/DeltaPopupContent.jsx`:

```jsx
import CompetitorSection from './CompetitorSection';
import { formatSigned, formatPct, electionPairLabel } from '../lib/format';
import { COMPETITOR_LAYER_BY_METRIC } from '../lib/constants';

function PopupRow({ label, value, color }) {
  return (
    <div className="popup-row">
      <span className="popup-label">{label}</span>
      <span className="popup-val" style={color ? { color } : undefined}>{value}</span>
    </div>
  );
}

export default function DeltaPopupContent({ p, metric, color, selectedDeltaMetric, findYearLocalFeature }) {
  const moved = (Number(p.secoes_movidas_in) || 0) + (Number(p.secoes_movidas_out) || 0);
  const competitorLayer = COMPETITOR_LAYER_BY_METRIC[selectedDeltaMetric];
  const startFeat = competitorLayer ? findYearLocalFeature(competitorLayer, p.ano_inicio, p.nr_local) : null;
  const endFeat = competitorLayer ? findYearLocalFeature(competitorLayer, p.ano_fim, p.nr_local) : null;

  return (
    <div>
      <div className="popup-title">{p.nm_local || `Local ${p.nr_local}`}</div>
      <div className="popup-bairro">{p.bairro || ''}</div>
      <PopupRow label="Par" value={p.pair} />
      <PopupRow label="Tipo de eleicao" value={p.tipo_par || electionPairLabel(p.ano_inicio, p.ano_fim)} />
      <PopupRow label={`Delta ${metric.label}`} value={formatSigned(p[metric.field])} color={color} />
      <PopupRow label="Hugo" value={`${p.votos_hugo_inicio} -> ${p.votos_hugo_fim} (${formatSigned(p.delta_hugo)})`} />
      <PopupRow label="Felipe" value={`${p.votos_felipe_inicio} -> ${p.votos_felipe_fim} (${formatSigned(p.delta_felipe)})`} />
      <PopupRow label="PSD" value={`${p.votos_psd_inicio} -> ${p.votos_psd_fim} (${formatSigned(p.delta_psd)})`} />
      <PopupRow label="Secoes" value={`${p.secoes_inicio || 0} -> ${p.secoes_fim || 0}`} />
      <PopupRow label="Troca de secoes" value={formatPct((Number(p.secao_churn) || 0) * 100)} />
      {moved > 0 && <PopupRow label="Secoes com troca" value={`+${p.secoes_movidas_in || 0} / -${p.secoes_movidas_out || 0}`} />}
      {competitorLayer && (
        <>
          <CompetitorSection title={`Concorrencia ${p.ano_inicio}`} props={startFeat ? startFeat.properties : {}} />
          <CompetitorSection title={`Concorrencia ${p.ano_fim}`} props={endFeat ? endFeat.properties : {}} />
        </>
      )}
    </div>
  );
}
```

Run: `npm test` — expect PASS.

- [ ] **Step 5: Write `DeltaLayer` (no separate test — covered by manual browser check)**

Create `app-web/src/components/DeltaLayer.jsx`:

```jsx
import { CircleMarker, Popup } from 'react-leaflet';
import DeltaPopupContent from './DeltaPopupContent';
import { getDivergingColor, getDeltaRadius } from '../lib/visual';
import { findYearLocalFeature } from '../lib/findFeature';

export default function DeltaLayer({ features, metric, selectedDeltaMetric, data }) {
  const maxAbs = Math.max(1, ...features.map(f => Math.abs(Number(f.properties[metric.field]) || 0)));

  return (
    <>
      {features.map(f => {
        const p = f.properties;
        const [lng, lat] = f.geometry.coordinates;
        const delta = Number(p[metric.field]) || 0;
        const color = getDivergingColor(delta, maxAbs);

        return (
          <CircleMarker
            key={`delta-${p.nr_local}-${p.pair}`}
            center={[lat, lng]}
            radius={getDeltaRadius(delta)}
            pathOptions={{ fillColor: color, fillOpacity: 0.78, color, weight: delta === 0 ? 1 : 2, opacity: 0.95 }}
            eventHandlers={{
              mouseover: (e) => e.target.setStyle({ fillOpacity: 0.95, weight: 3 }),
              mouseout: (e) => e.target.setStyle({ fillOpacity: 0.78, weight: delta === 0 ? 1 : 2 }),
            }}
          >
            <Popup>
              <DeltaPopupContent
                p={p}
                metric={metric}
                color={color}
                selectedDeltaMetric={selectedDeltaMetric}
                findYearLocalFeature={(layerKey, ano, nrLocal) => findYearLocalFeature(data, layerKey, ano, nrLocal)}
              />
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}
```

- [ ] **Step 6: Write `LayerToggles`, `DeltaPairFilter`, `DeltaMetricFilter`**

Create `app-web/src/components/LayerToggles.jsx`:

```jsx
const ROWS = [
  { id: 'hugo', label: 'Hugo Leal', color: '#4a90d9' },
  { id: 'felipe', label: 'Felipe Peixoto', color: '#50c878' },
  { id: 'psd', label: 'PSD (total)', color: '#e8a838' },
];

export default function LayerToggles({ toggles, counts, onToggle }) {
  return (
    <>
      {ROWS.map(row => (
        <label className="layer-row" key={row.id}>
          <input type="checkbox" checked={toggles[row.id]} onChange={() => onToggle(row.id)} />
          <span className="layer-dot" style={{ background: row.color }} />
          <span className="layer-label">{row.label}</span>
          <span className="layer-count">{counts[row.id] ?? '—'}</span>
        </label>
      ))}
    </>
  );
}
```

Create `app-web/src/components/DeltaPairFilter.jsx`:

```jsx
export default function DeltaPairFilter({ pairs, selectedPair, onChange }) {
  return (
    <div className="year-bar">
      {pairs.map(pair => (
        <button
          key={pair}
          className={'year-btn' + (selectedPair === pair ? ' active' : '')}
          onClick={() => onChange(pair)}
        >
          {pair}
        </button>
      ))}
    </div>
  );
}
```

Create `app-web/src/components/DeltaMetricFilter.jsx`:

```jsx
export default function DeltaMetricFilter({ metrics, selectedMetric, onChange }) {
  return (
    <div className="year-bar">
      {Object.entries(metrics).map(([key, metric]) => (
        <button
          key={key}
          className={'year-btn' + (selectedMetric === key ? ' active' : '')}
          onClick={() => onChange(key)}
        >
          {metric.label}
        </button>
      ))}
    </div>
  );
}
```

These three are thin, presentational, and structurally identical to `YearFilter`'s tested click/active-class behavior — not re-tested individually here; their behavior is exercised by the manual browser check in Step 8 and would be worth a regression test only if a future bug is found in one of them (YAGNI).

- [ ] **Step 7: Wire everything into `App.jsx`**

Replace `app-web/src/App.jsx`:

```jsx
import { useState, useMemo } from 'react';
import MapView from './components/MapView.jsx';
import MarkerLayer from './components/MarkerLayer.jsx';
import DeltaLayer from './components/DeltaLayer.jsx';
import YearFilter from './components/YearFilter.jsx';
import LayerToggles from './components/LayerToggles.jsx';
import DeltaPairFilter from './components/DeltaPairFilter.jsx';
import DeltaMetricFilter from './components/DeltaMetricFilter.jsx';
import { useMapData } from './lib/useMapData.js';
import { aggregateByLocal } from './lib/aggregate.js';
import { BASE_KEYS, DELTA_METRICS } from './lib/constants.js';

const LAYER_ORDER = ['psd', 'felipe_peixoto', 'hugo_leal'];
const TOGGLE_ID_BY_LAYER_KEY = { psd: 'psd', felipe_peixoto: 'felipe', hugo_leal: 'hugo' };

export default function App() {
  const data = useMapData();

  const allYears = useMemo(() => {
    if (!data) return [];
    return [...new Set(
      BASE_KEYS.flatMap(key => (data[key]?.features || []).map(f => Number(f.properties.ano)).filter(Number.isFinite))
    )].sort((a, b) => a - b);
  }, [data]);

  const deltaPairs = useMemo(() => {
    if (!data?.vote_deltas) return [];
    return [...new Set(data.vote_deltas.features.map(f => f.properties.pair))]
      .sort((a, b) => Number(a.slice(0, 4)) - Number(b.slice(0, 4)));
  }, [data]);

  const [selectedYear, setSelectedYear] = useState(() => (allYears.includes(2022) ? 2022 : (allYears[allYears.length - 1] ?? null)));
  const [selectedPair, setSelectedPair] = useState(() => (deltaPairs.includes('2022-2024') ? '2022-2024' : (deltaPairs[deltaPairs.length - 1] ?? null)));
  const [selectedDeltaMetric, setSelectedDeltaMetric] = useState('hugo');
  const [toggles, setToggles] = useState({ hugo: true, felipe: true, psd: false, delta: true });
  const [compareSelection, setCompareSelection] = useState(null);

  if (!data) {
    return <div style={{ padding: 24, color: '#e0e0e0' }}>Dados nao carregados.</div>;
  }

  const year = selectedYear;
  const pair = selectedPair;

  const counts = {};
  const markerLayers = LAYER_ORDER
    .filter(key => toggles[TOGGLE_ID_BY_LAYER_KEY[key]])
    .map(key => {
      const fc = data[key];
      if (!fc) return null;
      const filtered = year ? fc.features.filter(f => f.properties.ano === year) : fc.features;
      const points = year ? filtered : aggregateByLocal(filtered);
      const id = TOGGLE_ID_BY_LAYER_KEY[key];
      counts[id] = points.reduce((s, f) => s + f.properties.QT_VOTOS, 0).toLocaleString('pt-BR');
      return { key, features: points };
    })
    .filter(Boolean);

  const deltaFeats = data.vote_deltas && pair
    ? data.vote_deltas.features.filter(f => f.properties.pair === pair)
    : [];
  if (data.vote_deltas && pair && toggles.delta) {
    const metric = DELTA_METRICS[selectedDeltaMetric];
    const total = deltaFeats.reduce((s, f) => s + (Number(f.properties[metric.field]) || 0), 0);
    counts.delta = `${total > 0 ? '+' : ''}${Math.round(total).toLocaleString('pt-BR')}`;
  }

  return (
    <>
      <MapView>
        {markerLayers.map(({ key, features }) => (
          <MarkerLayer
            key={key}
            layerKey={key}
            features={features}
            onSelect={(p, coords) => setCompareSelection({ props: p, coords })}
          />
        ))}
        {toggles.delta && pair && (
          <DeltaLayer features={deltaFeats} metric={DELTA_METRICS[selectedDeltaMetric]} selectedDeltaMetric={selectedDeltaMetric} data={data} />
        )}
      </MapView>

      <div id="panel">
        <h1>LEAL</h1>
        <div className="subtitle">Mapa Eleitoral — Niterói</div>

        <div className="section-title">Camadas</div>
        <LayerToggles
          toggles={toggles}
          counts={counts}
          onToggle={(id) => setToggles(t => ({ ...t, [id]: !t[id] }))}
        />

        <div className="section-title">Ano</div>
        <YearFilter years={allYears} selectedYear={year} onChange={setSelectedYear} />

        <div className="section-title">Deltas</div>
        <label className="layer-row">
          <input type="checkbox" checked={toggles.delta} onChange={() => setToggles(t => ({ ...t, delta: !t.delta }))} />
          <span className="layer-dot delta-dot" />
          <span className="layer-label">Variacao por local</span>
          <span className="layer-count">{counts.delta ?? '-'}</span>
        </label>
        <DeltaPairFilter pairs={deltaPairs} selectedPair={pair} onChange={setSelectedPair} />
        <DeltaMetricFilter metrics={DELTA_METRICS} selectedMetric={selectedDeltaMetric} onChange={setSelectedDeltaMetric} />
        <div className="delta-legend"><span>perdeu</span><span className="delta-scale" /><span>ganhou</span></div>
      </div>
    </>
  );
}
```

- [ ] **Step 8: Manual browser check**

Run: `npm run dev`
Expected: all three base layers (toggle PSD on to see it) plus the delta layer render with correct colors. Click a Felipe Peixoto marker — popup shows competitor section. Click a PSD marker — no competitor section (matches vanilla behavior). Switch delta metric to PSD — delta popups show no competitor sections; switch to Hugo or Felipe — two sections appear. Toggle each layer checkbox off/on — markers appear/disappear, counts update. Stop the server.

- [ ] **Step 9: Commit**

```bash
git add app-web/src/lib/findFeature.js app-web/src/lib/findFeature.test.js app-web/src/components/DeltaPopupContent.jsx app-web/src/components/DeltaPopupContent.test.jsx app-web/src/components/DeltaLayer.jsx app-web/src/components/LayerToggles.jsx app-web/src/components/DeltaPairFilter.jsx app-web/src/components/DeltaMetricFilter.jsx app-web/src/App.jsx
git commit -m "feat: render remaining marker layers, delta layer, and metric/pair filters"
```

---

### Task 8: Compare panel

**Files:**
- Create: `app-web/src/components/CompareTable.jsx`, `app-web/src/components/CompareTable.test.jsx`
- Modify: `app-web/src/App.jsx`

**Interfaces:**
- Consumes: `BASE_KEYS`, `COLORS`, `LABELS` (Task 6).
- Produces: `<CompareTable selection data>` — consumed by Task 10's final App wiring. `selection` shape: `{ props: object, coords: [number, number] } | null`.

- [ ] **Step 1: Write the failing test**

Create `app-web/src/components/CompareTable.test.jsx`:

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CompareTable from './CompareTable';

const data = {
  hugo_leal: { features: [
    { properties: { nr_local: '10', ano: 2018, QT_VOTOS: 40 } },
    { properties: { nr_local: '10', ano: 2022, QT_VOTOS: 60 } },
  ] },
  felipe_peixoto: { features: [
    { properties: { nr_local: '10', ano: 2022, QT_VOTOS: 200 } },
  ] },
  psd: { features: [] },
};

describe('CompareTable', () => {
  it('renders nothing when there is no selection', () => {
    const { container } = render(<CompareTable selection={null} data={data} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders a row per candidate with data at the selected local, one column per year', () => {
    render(<CompareTable selection={{ props: { nr_local: '10', nm_local: 'Escola Teste' }, coords: [1, 2] }} data={data} />);
    expect(screen.getByText('Escola Teste')).toBeInTheDocument();
    expect(screen.getByText('Hugo Leal')).toBeInTheDocument();
    expect(screen.getByText('Felipe Peixoto')).toBeInTheDocument();
    expect(screen.queryByText('PSD')).not.toBeInTheDocument();
    expect(screen.getByText('2018')).toBeInTheDocument();
    expect(screen.getByText('40')).toBeInTheDocument();
    expect(screen.getByText('200')).toBeInTheDocument();
  });

  it('renders nothing when the selected local has no data in any layer', () => {
    const { container } = render(<CompareTable selection={{ props: { nr_local: '999' }, coords: [1, 2] }} data={data} />);
    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test` — expect FAIL.

- [ ] **Step 3: Write `CompareTable`**

Create `app-web/src/components/CompareTable.jsx`:

```jsx
import { BASE_KEYS, COLORS, LABELS } from '../lib/constants';

export default function CompareTable({ selection, data }) {
  if (!selection) return null;
  const { props: clickedProps } = selection;
  const localId = clickedProps.nr_local;

  const rows = BASE_KEYS.map(key => {
    const fc = data[key];
    if (!fc) return null;
    const localFeats = fc.features.filter(f => f.properties.nr_local === localId);
    if (localFeats.length === 0) return null;
    const byYear = {};
    localFeats.forEach(f => { byYear[f.properties.ano] = f.properties.QT_VOTOS; });
    return { key, byYear };
  }).filter(Boolean);

  if (rows.length === 0) return null;

  const allYears = [...new Set(rows.flatMap(r => Object.keys(r.byYear)))].sort();

  return (
    <div id="compare-panel">
      <div style={{ fontWeight: 700, marginBottom: 8 }}>{clickedProps.nm_local || `Local ${localId}`}</div>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <tbody>
          <tr>
            <td></td>
            {allYears.map(y => (
              <td key={y} style={{ padding: '2px 8px', color: '#888', fontSize: 11, textAlign: 'right' }}>{y}</td>
            ))}
          </tr>
          {rows.map(r => (
            <tr key={r.key}>
              <td style={{ padding: '2px 8px', color: COLORS[r.key], fontWeight: 600, whiteSpace: 'nowrap' }}>{LABELS[r.key]}</td>
              {allYears.map(y => (
                <td key={y} style={{ padding: '2px 8px', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                  {r.byYear[y] ? r.byYear[y].toLocaleString('pt-BR') : '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test` — expect PASS.

- [ ] **Step 5: Wire `CompareTable` into `App.jsx`, including click-outside-to-close**

In `app-web/src/App.jsx`, add the import:

```jsx
import { useState, useMemo, useEffect } from 'react';
import CompareTable from './components/CompareTable.jsx';
```

(`useEffect` added to the existing `react` import line; `CompareTable` added as a new import line.)

Add this `useEffect` inside the `App` function, after the existing `useState` declarations:

```jsx
  useEffect(() => {
    const handler = (e) => {
      const cp = document.getElementById('compare-panel');
      if (cp && !cp.contains(e.target) && !e.target.closest('.leaflet-interactive')) {
        setCompareSelection(null);
      }
    };
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, []);
```

Add `<CompareTable selection={compareSelection} data={data} />` as the last line inside the top-level `<>...</>` fragment, after the closing `</div>` of `#panel`.

- [ ] **Step 6: Manual browser check**

Run: `npm run dev`
Expected: clicking a marker opens the compare panel at the bottom of the screen showing a per-year table for Hugo/Felipe/PSD at that local. Clicking elsewhere on the map (not on a marker) closes it. Stop the server.

- [ ] **Step 7: Commit**

```bash
git add app-web/src/components/CompareTable.jsx app-web/src/components/CompareTable.test.jsx app-web/src/App.jsx
git commit -m "feat: add compare panel with click-outside-to-close"
```

---

### Task 9: Stats panel

**Files:**
- Create: `app-web/src/components/StatsPanel.jsx`, `app-web/src/components/StatsPanel.test.jsx`
- Modify: `app-web/src/App.jsx`

**Interfaces:**
- Consumes: `passesGeoFilter` (Task 3), `electionType`/`electionPairLabel`/`formatSigned` (Task 5), `BASE_KEYS`/`COLORS`/`LABELS`/`DELTA_METRICS` (Task 6).
- Produces: `<StatsPanel data selectedYear selectedRegion selectedBairro selectedPair selectedDeltaMetric deltaEnabled>` — consumed by Task 10's final App wiring.

- [ ] **Step 1: Write the failing test**

Create `app-web/src/components/StatsPanel.test.jsx`:

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatsPanel from './StatsPanel';

const data = {
  hugo_leal: { features: [
    { properties: { ano: 2022, nr_local: '10', QT_VOTOS: 40 } },
    { properties: { ano: 2022, nr_local: '20', QT_VOTOS: 60 } },
  ] },
  felipe_peixoto: { features: [] },
  psd: { features: [] },
  vote_deltas: { features: [
    { properties: { pair: '2022-2024', ano_inicio: 2022, ano_fim: 2024, delta_hugo: -10, votos_hugo_inicio: 100, votos_hugo_fim: 90 } },
  ] },
};

describe('StatsPanel', () => {
  it('shows the selected-year total and local count for each layer with data', () => {
    render(<StatsPanel data={data} selectedYear={2022} selectedRegion="all" selectedBairro="all" selectedPair="2022-2024" selectedDeltaMetric="hugo" deltaEnabled={false} />);
    expect(screen.getByText('Resumo 2022')).toBeInTheDocument();
    expect(screen.getByText('Hugo Leal')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument(); // 40 + 60
    expect(screen.getByText('2')).toBeInTheDocument(); // 2 locais
  });

  it('shows "todos os anos" summary when no year is selected', () => {
    render(<StatsPanel data={data} selectedYear={null} selectedRegion="all" selectedBairro="all" selectedPair="2022-2024" selectedDeltaMetric="hugo" deltaEnabled={false} />);
    expect(screen.getByText('Resumo (todos os anos)')).toBeInTheDocument();
  });

  it('shows the delta summary when deltaEnabled is true', () => {
    render(<StatsPanel data={data} selectedYear={2022} selectedRegion="all" selectedBairro="all" selectedPair="2022-2024" selectedDeltaMetric="hugo" deltaEnabled />);
    expect(screen.getByText('Delta Hugo (2022-2024)')).toBeInTheDocument();
    expect(screen.getByText('-10')).toBeInTheDocument();
  });

  it('omits the delta summary when deltaEnabled is false', () => {
    render(<StatsPanel data={data} selectedYear={2022} selectedRegion="all" selectedBairro="all" selectedPair="2022-2024" selectedDeltaMetric="hugo" deltaEnabled={false} />);
    expect(screen.queryByText(/Delta Hugo/)).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test` — expect FAIL.

- [ ] **Step 3: Write `StatsPanel`**

Create `app-web/src/components/StatsPanel.jsx`:

```jsx
import { BASE_KEYS, COLORS, LABELS, DELTA_METRICS } from '../lib/constants';
import { electionType, electionPairLabel, formatSigned } from '../lib/format';
import { passesGeoFilter } from '../lib/geo';

export default function StatsPanel({ data, selectedYear, selectedRegion, selectedBairro, selectedPair, selectedDeltaMetric, deltaEnabled }) {
  const regionLabel = selectedRegion === 'all' ? 'todas as regioes' : selectedRegion;
  const bairroLabel = selectedBairro === 'all' ? 'todos os bairros' : selectedBairro;

  const baseSections = BASE_KEYS.map(key => {
    const fc = data[key];
    if (!fc) return null;
    const feats = (selectedYear ? fc.features.filter(f => f.properties.ano === selectedYear) : fc.features)
      .filter(f => passesGeoFilter(f.properties, selectedRegion, selectedBairro));
    if (feats.length === 0) return null;
    const total = feats.reduce((s, f) => s + f.properties.QT_VOTOS, 0);
    const nLocais = new Set(feats.map(f => f.properties.nr_local)).size;
    return { key, total, nLocais };
  }).filter(Boolean);

  let deltaSection = null;
  if (data.vote_deltas && selectedPair && deltaEnabled) {
    const metric = DELTA_METRICS[selectedDeltaMetric];
    const feats = data.vote_deltas.features
      .filter(f => f.properties.pair === selectedPair)
      .filter(f => passesGeoFilter(f.properties, selectedRegion, selectedBairro));
    const startTotal = feats.reduce((s, f) => s + (Number(f.properties[`votos_${selectedDeltaMetric}_inicio`]) || 0), 0);
    const endTotal = feats.reduce((s, f) => s + (Number(f.properties[`votos_${selectedDeltaMetric}_fim`]) || 0), 0);
    const total = feats.reduce((s, f) => s + (Number(f.properties[metric.field]) || 0), 0);
    const gained = feats.reduce((s, f) => s + Math.max(Number(f.properties[metric.field]) || 0, 0), 0);
    const lost = feats.reduce((s, f) => s + Math.max(-(Number(f.properties[metric.field]) || 0), 0), 0);
    deltaSection = {
      metric, startTotal, endTotal, total, gained, lost,
      anoInicio: feats[0]?.properties.ano_inicio || 0,
      anoFim: feats[0]?.properties.ano_fim || 0,
    };
  }

  return (
    <div id="stats">
      <div style={{ fontWeight: 600, marginBottom: 6 }}>
        {selectedYear ? `Resumo ${selectedYear}` : 'Resumo (todos os anos)'}
      </div>
      {selectedYear && <div style={{ color: '#888', marginBottom: 6 }}>{electionType(selectedYear)}</div>}
      {(selectedRegion !== 'all' || selectedBairro !== 'all') && (
        <div style={{ color: '#888', marginBottom: 6 }}>{regionLabel} / {bairroLabel}</div>
      )}
      {baseSections.map(({ key, total, nLocais }) => (
        <div key={key}>
          <div style={{ marginTop: 4 }}><span style={{ color: COLORS[key] }}>{LABELS[key]}</span></div>
          <div className="popup-row"><span className="popup-label">Votos</span><span className="stat-val">{total.toLocaleString('pt-BR')}</span></div>
          <div className="popup-row"><span className="popup-label">Locais</span><span className="stat-val">{nLocais}</span></div>
        </div>
      ))}
      {deltaSection && (
        <>
          <div style={{ marginTop: 8 }}><span style={{ color: COLORS.deltaGain }}>Delta {deltaSection.metric.label} ({selectedPair})</span></div>
          <div style={{ color: '#888', marginBottom: 6 }}>{electionPairLabel(deltaSection.anoInicio, deltaSection.anoFim)}</div>
          <div className="popup-row"><span className="popup-label">Inicio</span><span className="stat-val">{deltaSection.startTotal.toLocaleString('pt-BR')}</span></div>
          <div className="popup-row"><span className="popup-label">Fim</span><span className="stat-val">{deltaSection.endTotal.toLocaleString('pt-BR')}</span></div>
          <div className="popup-row"><span className="popup-label">Saldo</span><span className="stat-val">{formatSigned(deltaSection.total)}</span></div>
          <div className="popup-row"><span className="popup-label">Ganhos</span><span className="stat-val">{deltaSection.gained.toLocaleString('pt-BR')}</span></div>
          <div className="popup-row"><span className="popup-label">Perdas</span><span className="stat-val">{deltaSection.lost.toLocaleString('pt-BR')}</span></div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test` — expect PASS.

- [ ] **Step 5: Wire `StatsPanel` into `App.jsx`**

In `app-web/src/App.jsx`, add the import:

```jsx
import StatsPanel from './components/StatsPanel.jsx';
```

Add `<StatsPanel data={data} selectedYear={year} selectedRegion="all" selectedBairro="all" selectedPair={pair} selectedDeltaMetric={selectedDeltaMetric} deltaEnabled={toggles.delta} />` as the last child inside `#panel`'s `<div>`, right before its closing tag (after the delta legend). The hardcoded `"all"` region/bairro values are replaced with real state in Task 10, once `GeoFilter` exists.

- [ ] **Step 6: Manual browser check**

Run: `npm run dev`
Expected: the stats box at the bottom of the sidebar shows vote totals and local counts per candidate for the selected year, and a delta summary (Inicio/Fim/Saldo/Ganhos/Perdas) when the delta layer is on — numbers should match the vanilla `app/`'s stats box for the same filters. Stop the server.

- [ ] **Step 7: Commit**

```bash
git add app-web/src/components/StatsPanel.jsx app-web/src/components/StatsPanel.test.jsx app-web/src/App.jsx
git commit -m "feat: add stats panel"
```

---

### Task 10: Boundary layers and region/bairro filters

**Files:**
- Create: `app-web/src/lib/useBoundaries.js`, `app-web/src/lib/useBoundaries.test.js`
- Create: `app-web/src/components/BoundaryLayer.jsx`
- Create: `app-web/src/components/GeoFilter.jsx`, `app-web/src/components/GeoFilter.test.jsx`
- Modify: `app-web/src/App.jsx`

**Interfaces:**
- Consumes: `normalizeText`/`featureName`/`annotateFeatureCollection` (Task 3), `BASE_KEYS` (Task 6).
- Produces: `useBoundaries(): { regionFeatures: Feature[], bairroFeatures: Feature[], error: Error | null }`, `<BoundaryLayer features selectedName inactiveColor opacity fillOpacity>`, `<GeoFilter regions bairros selectedRegion selectedBairro onRegionChange onBairroChange showRegionBoundaries showBairroBoundaries onToggleRegionBoundaries onToggleBairroBoundaries disabled>` — this is the final task wiring `App.jsx` into its complete feature-parity form.

- [ ] **Step 1: Write the failing test for `useBoundaries`**

Create `app-web/src/lib/useBoundaries.test.js`:

```js
import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useBoundaries } from './useBoundaries';

describe('useBoundaries', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('populates regionFeatures and bairroFeatures on successful fetch', async () => {
    const regionFC = { features: [{ properties: { tx_nome: 'Regiao Oceanica' } }] };
    const bairroFC = { features: [{ properties: { tx_nome: 'Icarai' } }] };
    let call = 0;
    vi.stubGlobal('fetch', vi.fn(() => {
      call += 1;
      const body = call === 1 ? regionFC : bairroFC;
      return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
    }));

    const { result } = renderHook(() => useBoundaries());

    await waitFor(() => expect(result.current.regionFeatures).toHaveLength(1));
    expect(result.current.bairroFeatures).toHaveLength(1);
    expect(result.current.error).toBeNull();
  });

  it('sets an error and leaves features empty when the fetch fails', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: false, status: 500 })));
    vi.spyOn(console, 'warn').mockImplementation(() => {});

    const { result } = renderHook(() => useBoundaries());

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.regionFeatures).toEqual([]);
    expect(result.current.bairroFeatures).toEqual([]);
    expect(console.warn).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails, then write `useBoundaries.js`**

Run: `npm test` — expect FAIL.

Create `app-web/src/lib/useBoundaries.js`:

```js
import { useState, useEffect } from 'react';

const REGION_SERVICE = 'https://geo.niteroi.rj.gov.br/arcgis/rest/services/Aplicacoes/PD_MAPA1_mapservice/MapServer';
const REGION_URL = `${REGION_SERVICE}/10/query?where=1%3D1&outFields=tx_nome,si_nome&returnGeometry=true&f=geojson&outSR=4326`;
const BAIRRO_URL = `${REGION_SERVICE}/20/query?where=1%3D1&outFields=tx_nome&returnGeometry=true&f=geojson&outSR=4326`;

async function fetchGeoJson(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Failed to load ${url}: ${resp.status}`);
  return resp.json();
}

export function useBoundaries() {
  const [regionFeatures, setRegionFeatures] = useState([]);
  const [bairroFeatures, setBairroFeatures] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchGeoJson(REGION_URL), fetchGeoJson(BAIRRO_URL)])
      .then(([regions, bairros]) => {
        if (cancelled) return;
        setRegionFeatures(regions.features || []);
        setBairroFeatures(bairros.features || []);
      })
      .catch(err => {
        if (cancelled) return;
        console.warn('boundary load failed', err);
        setError(err);
      });
    return () => { cancelled = true; };
  }, []);

  return { regionFeatures, bairroFeatures, error };
}
```

Run: `npm test` — expect PASS.

- [ ] **Step 3: Write `BoundaryLayer` (no separate test — covered by manual browser check)**

Create `app-web/src/components/BoundaryLayer.jsx`:

```jsx
import { GeoJSON } from 'react-leaflet';
import { normalizeText, featureName } from '../lib/geo';

export default function BoundaryLayer({ features, selectedName, inactiveColor, opacity, fillOpacity }) {
  const active = normalizeText(selectedName);
  const shown = selectedName === 'all' ? features : features.filter(f => normalizeText(featureName(f)) === active);

  return (
    <GeoJSON
      key={selectedName}
      data={{ type: 'FeatureCollection', features: shown }}
      style={(feature) => ({
        color: normalizeText(featureName(feature)) === active ? '#ffffff' : inactiveColor,
        weight: normalizeText(featureName(feature)) === active ? 2 : 1,
        opacity,
        fillOpacity,
      })}
      onEachFeature={(feature, layer) => {
        layer.bindTooltip(featureName(feature), { sticky: true, direction: 'top' });
      }}
    />
  );
}
```

- [ ] **Step 4: Write the failing test for `GeoFilter`**

Create `app-web/src/components/GeoFilter.test.jsx`:

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import GeoFilter from './GeoFilter';

const baseProps = {
  regions: ['Regiao Oceanica', 'Regiao Norte'],
  bairros: ['Icarai', 'Centro'],
  selectedRegion: 'all',
  selectedBairro: 'all',
  onRegionChange: () => {},
  onBairroChange: () => {},
  showRegionBoundaries: true,
  showBairroBoundaries: false,
  onToggleRegionBoundaries: () => {},
  onToggleBairroBoundaries: () => {},
  disabled: false,
};

describe('GeoFilter', () => {
  it('lists all region and bairro options plus an "all" default', () => {
    render(<GeoFilter {...baseProps} />);
    expect(screen.getByText('Todas as regioes')).toBeInTheDocument();
    expect(screen.getByText('Regiao Oceanica')).toBeInTheDocument();
    expect(screen.getByText('Icarai')).toBeInTheDocument();
  });

  it('fires onRegionChange/onBairroChange when a select changes', () => {
    const onRegionChange = vi.fn();
    render(<GeoFilter {...baseProps} onRegionChange={onRegionChange} />);
    fireEvent.change(screen.getByDisplayValue('Todas as regioes'), { target: { value: 'Regiao Norte' } });
    expect(onRegionChange).toHaveBeenCalledWith('Regiao Norte');
  });

  it('reflects the boundary-toggle checkbox state', () => {
    render(<GeoFilter {...baseProps} />);
    expect(screen.getByText('Mostrar limites das regioes').previousSibling).toBeChecked();
    expect(screen.getByText('Mostrar limites dos bairros').previousSibling).not.toBeChecked();
  });

  it('disables both selects when disabled is true', () => {
    render(<GeoFilter {...baseProps} disabled />);
    expect(screen.getByDisplayValue('Todas as regioes')).toBeDisabled();
  });
});
```

- [ ] **Step 5: Run test to verify it fails, then write `GeoFilter`**

Run: `npm test` — expect FAIL.

Create `app-web/src/components/GeoFilter.jsx`:

```jsx
export default function GeoFilter({
  regions, bairros, selectedRegion, selectedBairro, onRegionChange, onBairroChange,
  showRegionBoundaries, showBairroBoundaries, onToggleRegionBoundaries, onToggleBairroBoundaries,
  disabled,
}) {
  return (
    <div className="control-grid">
      <div className="control-row">
        <select className="control-select" value={selectedRegion} disabled={disabled} onChange={(e) => onRegionChange(e.target.value)}>
          <option value="all">Todas as regioes</option>
          {regions.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <select className="control-select" value={selectedBairro} disabled={disabled} onChange={(e) => onBairroChange(e.target.value)}>
          <option value="all">Todos os bairros</option>
          {bairros.map(b => <option key={b} value={b}>{b}</option>)}
        </select>
      </div>
      <label className="control-toggle">
        <input type="checkbox" checked={showRegionBoundaries} onChange={onToggleRegionBoundaries} />
        <span>Mostrar limites das regioes</span>
      </label>
      <label className="control-toggle">
        <input type="checkbox" checked={showBairroBoundaries} onChange={onToggleBairroBoundaries} />
        <span>Mostrar limites dos bairros</span>
      </label>
    </div>
  );
}
```

Run: `npm test` — expect PASS.

- [ ] **Step 6: Wire everything into the final `App.jsx`**

Replace `app-web/src/App.jsx` in full — this is the complete, feature-parity version:

```jsx
import { useState, useMemo, useEffect } from 'react';
import MapView from './components/MapView.jsx';
import MarkerLayer from './components/MarkerLayer.jsx';
import DeltaLayer from './components/DeltaLayer.jsx';
import BoundaryLayer from './components/BoundaryLayer.jsx';
import CompareTable from './components/CompareTable.jsx';
import StatsPanel from './components/StatsPanel.jsx';
import LayerToggles from './components/LayerToggles.jsx';
import YearFilter from './components/YearFilter.jsx';
import DeltaPairFilter from './components/DeltaPairFilter.jsx';
import DeltaMetricFilter from './components/DeltaMetricFilter.jsx';
import GeoFilter from './components/GeoFilter.jsx';
import { useMapData } from './lib/useMapData.js';
import { useBoundaries } from './lib/useBoundaries.js';
import { aggregateByLocal } from './lib/aggregate.js';
import { annotateFeatureCollection, normalizeText, featureName, passesGeoFilter } from './lib/geo.js';
import { BASE_KEYS, DELTA_METRICS } from './lib/constants.js';

const LAYER_ORDER = ['psd', 'felipe_peixoto', 'hugo_leal'];
const TOGGLE_ID_BY_LAYER_KEY = { psd: 'psd', felipe_peixoto: 'felipe', hugo_leal: 'hugo' };

export default function App() {
  const rawData = useMapData();
  const { regionFeatures, bairroFeatures } = useBoundaries();

  const data = useMemo(() => {
    if (!rawData) return null;
    if (regionFeatures.length === 0 && bairroFeatures.length === 0) return rawData;
    const annotated = { ...rawData };
    [...BASE_KEYS, 'vote_deltas'].forEach(key => {
      if (annotated[key]) annotated[key] = annotateFeatureCollection(annotated[key], regionFeatures, bairroFeatures);
    });
    return annotated;
  }, [rawData, regionFeatures, bairroFeatures]);

  const allYears = useMemo(() => {
    if (!data) return [];
    return [...new Set(
      BASE_KEYS.flatMap(key => (data[key]?.features || []).map(f => Number(f.properties.ano)).filter(Number.isFinite))
    )].sort((a, b) => a - b);
  }, [data]);

  const deltaPairs = useMemo(() => {
    if (!data?.vote_deltas) return [];
    return [...new Set(data.vote_deltas.features.map(f => f.properties.pair))]
      .sort((a, b) => Number(a.slice(0, 4)) - Number(b.slice(0, 4)));
  }, [data]);

  const regionOptions = useMemo(() => {
    const map = new Map(regionFeatures.map(f => [normalizeText(featureName(f)), featureName(f)]));
    return [...map.values()].sort((a, b) => a.localeCompare(b, 'pt-BR'));
  }, [regionFeatures]);

  const bairroOptions = useMemo(() => {
    const map = new Map(bairroFeatures.map(f => [normalizeText(featureName(f)), featureName(f)]));
    return [...map.values()].sort((a, b) => a.localeCompare(b, 'pt-BR'));
  }, [bairroFeatures]);

  const [selectedYear, setSelectedYear] = useState(() => (allYears.includes(2022) ? 2022 : (allYears[allYears.length - 1] ?? null)));
  const [selectedPair, setSelectedPair] = useState(() => (deltaPairs.includes('2022-2024') ? '2022-2024' : (deltaPairs[deltaPairs.length - 1] ?? null)));
  const [selectedDeltaMetric, setSelectedDeltaMetric] = useState('hugo');
  const [selectedRegion, setSelectedRegion] = useState('all');
  const [selectedBairro, setSelectedBairro] = useState('all');
  const [toggles, setToggles] = useState({ hugo: true, felipe: true, psd: false, delta: true, regionBoundaries: true, bairroBoundaries: false });
  const [compareSelection, setCompareSelection] = useState(null);

  useEffect(() => {
    const handler = (e) => {
      const cp = document.getElementById('compare-panel');
      if (cp && !cp.contains(e.target) && !e.target.closest('.leaflet-interactive')) {
        setCompareSelection(null);
      }
    };
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, []);

  if (!data) {
    return <div style={{ padding: 24, color: '#e0e0e0' }}>Dados nao carregados.</div>;
  }

  const year = selectedYear;
  const pair = selectedPair;

  const counts = {};
  const markerLayers = LAYER_ORDER
    .filter(key => toggles[TOGGLE_ID_BY_LAYER_KEY[key]])
    .map(key => {
      const fc = data[key];
      if (!fc) return null;
      const filtered = (year ? fc.features.filter(f => f.properties.ano === year) : fc.features)
        .filter(f => passesGeoFilter(f.properties, selectedRegion, selectedBairro));
      const points = year ? filtered : aggregateByLocal(filtered);
      const id = TOGGLE_ID_BY_LAYER_KEY[key];
      counts[id] = points.reduce((s, f) => s + f.properties.QT_VOTOS, 0).toLocaleString('pt-BR');
      return { key, features: points };
    })
    .filter(Boolean);

  const deltaFeats = data.vote_deltas && pair
    ? data.vote_deltas.features.filter(f => f.properties.pair === pair).filter(f => passesGeoFilter(f.properties, selectedRegion, selectedBairro))
    : [];
  if (data.vote_deltas && pair && toggles.delta) {
    const metric = DELTA_METRICS[selectedDeltaMetric];
    const total = deltaFeats.reduce((s, f) => s + (Number(f.properties[metric.field]) || 0), 0);
    counts.delta = `${total > 0 ? '+' : ''}${Math.round(total).toLocaleString('pt-BR')}`;
  }

  return (
    <>
      <MapView>
        {toggles.regionBoundaries && regionFeatures.length > 0 && (
          <BoundaryLayer features={regionFeatures} selectedName={selectedRegion} inactiveColor="#7f8aa6" opacity={0.95} fillOpacity={0.02} />
        )}
        {toggles.bairroBoundaries && bairroFeatures.length > 0 && (
          <BoundaryLayer features={bairroFeatures} selectedName={selectedBairro} inactiveColor="#c7b56a" opacity={0.8} fillOpacity={0.01} />
        )}
        {markerLayers.map(({ key, features }) => (
          <MarkerLayer
            key={key}
            layerKey={key}
            features={features}
            onSelect={(p, coords) => setCompareSelection({ props: p, coords })}
          />
        ))}
        {toggles.delta && pair && (
          <DeltaLayer features={deltaFeats} metric={DELTA_METRICS[selectedDeltaMetric]} selectedDeltaMetric={selectedDeltaMetric} data={data} />
        )}
      </MapView>

      <div id="panel">
        <h1>LEAL</h1>
        <div className="subtitle">Mapa Eleitoral — Niterói</div>

        <div className="section-title">Camadas</div>
        <LayerToggles
          toggles={toggles}
          counts={counts}
          onToggle={(id) => setToggles(t => ({ ...t, [id]: !t[id] }))}
        />

        <div className="section-title">Ano</div>
        <YearFilter years={allYears} selectedYear={year} onChange={setSelectedYear} />

        <div className="section-title">Deltas</div>
        <label className="layer-row">
          <input type="checkbox" checked={toggles.delta} onChange={() => setToggles(t => ({ ...t, delta: !t.delta }))} />
          <span className="layer-dot delta-dot" />
          <span className="layer-label">Variacao por local</span>
          <span className="layer-count">{counts.delta ?? '-'}</span>
        </label>
        <DeltaPairFilter pairs={deltaPairs} selectedPair={pair} onChange={setSelectedPair} />
        <DeltaMetricFilter metrics={DELTA_METRICS} selectedMetric={selectedDeltaMetric} onChange={setSelectedDeltaMetric} />
        <div className="delta-legend"><span>perdeu</span><span className="delta-scale" /><span>ganhou</span></div>

        <div className="section-title">Regiao / Bairro</div>
        <GeoFilter
          regions={regionOptions}
          bairros={bairroOptions}
          selectedRegion={selectedRegion}
          selectedBairro={selectedBairro}
          onRegionChange={setSelectedRegion}
          onBairroChange={setSelectedBairro}
          showRegionBoundaries={toggles.regionBoundaries}
          showBairroBoundaries={toggles.bairroBoundaries}
          onToggleRegionBoundaries={() => setToggles(t => ({ ...t, regionBoundaries: !t.regionBoundaries }))}
          onToggleBairroBoundaries={() => setToggles(t => ({ ...t, bairroBoundaries: !t.bairroBoundaries }))}
          disabled={regionOptions.length === 0}
        />
        <div className="control-note">Os filtros usam os limites oficiais do Plano Diretor de Niteroi.</div>

        <StatsPanel
          data={data}
          selectedYear={year}
          selectedRegion={selectedRegion}
          selectedBairro={selectedBairro}
          selectedPair={pair}
          selectedDeltaMetric={selectedDeltaMetric}
          deltaEnabled={toggles.delta}
        />
      </div>

      <CompareTable selection={compareSelection} data={data} />
    </>
  );
}
```

- [ ] **Step 7: Manual browser check**

Run: `npm run dev`
Expected: region/bairro dropdowns populate with real Niterói boundary names once the ArcGIS fetch resolves (a beat after page load). Selecting a region highlights its boundary on the map and filters markers/stats to it. Toggling "Mostrar limites das regioes/bairros" shows/hides the boundary overlay. To check the error path: temporarily change `REGION_URL` in `useBoundaries.js` to an invalid URL, reload, confirm the app still renders (markers work, dropdowns stay empty/disabled, a warning appears in the console) rather than crashing — then revert the change.

- [ ] **Step 8: Commit**

```bash
git add app-web/src/lib/useBoundaries.js app-web/src/lib/useBoundaries.test.js app-web/src/components/BoundaryLayer.jsx app-web/src/components/GeoFilter.jsx app-web/src/components/GeoFilter.test.jsx app-web/src/App.jsx
git commit -m "feat: add boundary layers and region/bairro filters"
```

---

### Task 11: Full parity pass

**Files:** none (verification only; fix any discrepancy found using the normal file for whichever piece it belongs to, then re-run this task's checklist).

**Interfaces:** none — this is the spec's exit criterion, not new functionality.

- [ ] **Step 1: Run the full test suite**

Run: `npm test` (from `app-web/`)
Expected: all tests from Tasks 2–10 pass together.

- [ ] **Step 2: Build and serve the production bundle**

Run: `npm run build && npm run preview` (from `app-web/`), note the printed local URL.

- [ ] **Step 3: Serve the vanilla app side-by-side**

Run: `python -m http.server 8000` (from `LEAL/app/`)

- [ ] **Step 4: Walk the parity checklist, comparing the two side-by-side in two browser tabs**

For each item, same filters/inputs on both, confirm matching output:

1. Default load — same map center/zoom, same default year (2022), same default delta pair (2022-2024), same layers checked (Hugo + Felipe + Delta on, PSD off).
2. Click a Hugo Leal marker — popup fields match exactly (name, bairro, candidate, year, votes, seções). Expand "Concorrência" — same top-3 names/parties/votes.
3. Click a Felipe Peixoto marker — same check.
4. Toggle PSD on, click a PSD marker — popup shows no competitor section on both.
5. Switch to "Todos" (all years) — markers aggregate by local on both, popup shows per-year breakdown + total, no competitor section on either.
6. Click a marker to open the compare panel — same per-year table on both. Click elsewhere — closes on both.
7. Switch delta metric between Hugo/Felipe/PSD — delta marker colors and popup competitor sections (present for Hugo/Felipe, absent for PSD) match.
8. Switch delta pair — delta markers and stats update to match on both.
9. Select a region, then a bairro — boundary outline, marker filtering, and stats numbers match on both.
10. Toggle region/bairro boundary overlays on/off — visual match.
11. Year button colors (Municipal teal dot / Federal purple dot) match between the two (the vanilla app has this from earlier in this session; confirm the React port kept it).
12. Dropdown legibility — region/bairro `<option>` list is readable (dark background, light text) in the React version, matching the earlier vanilla-app contrast fix.

- [ ] **Step 5: Fix any discrepancy found**

If a mismatch turns up, fix it in the relevant component/hook file from whichever earlier task owns it, add or extend that task's test to cover the specific case that broke, re-run `npm test`, and re-check the specific parity-checklist item before continuing.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "chore: React UI migration parity pass complete"
```

Stop both local servers (`npm run preview` and `python -m http.server`).
