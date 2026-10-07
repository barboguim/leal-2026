# LEAL Design Tokens Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace LEAL's hand-rolled dark-theme CSS with a light, token-driven design system (Tailwind v4 + centralized palette + IBM Plex typography), per `design_direction.md`, without changing any component's markup structure or rendered text.

**Architecture:** Install Tailwind v4 via its Vite plugin and define the neutral UI-chrome tokens (background/surface/border/text/fonts) in a single `@theme` block in `app-web/src/index.css`. Candidate/delta/sequential colors are never Tailwind classes — they're applied dynamically via inline `style` props (Leaflet markers, colored dots), so they stay centralized in `app-web/src/lib/constants.js` as the one source of truth, and every place that currently hardcodes a duplicate of those hex values gets pointed at that source instead. `index.css`'s existing selectors are kept as plain CSS (not rewritten to Tailwind utility classes) and simply swapped from hardcoded dark literals to `var(--color-*)` references — a full componentwise utility-class migration is out of scope for this plan and belongs to whichever later plan actually touches each component (the delta-control-collapse and popup-redesign plans).

**Tech Stack:** React 19, react-leaflet 5, Vite 8, Vitest 4 + React Testing Library, Tailwind CSS v4 (`@tailwindcss/vite`, CSS-native `@theme` config — no `tailwind.config.js`/`postcss.config.js` needed).

## Global Constraints

- No new frameworks beyond Tailwind (per `design_brief.md`) — no CSS-in-JS, no component library.
- Stay mobile-responsive — the existing `@media (max-width: 640px)` rule in `index.css` must keep working; don't remove it.
- Every existing test must stay green unless a task explicitly updates a test's expected values (and says why).
- Palette values are exact hex from `design_direction.md` / `colors.md` — copy them verbatim, do not eyeball-approximate:
  - Chrome: bg `#F7F8FA`, surface `#FFFFFF`, surface-muted `#EEF1F5`, border `#DDE3EA`, text `#151B26`, text-muted `#5B6472`, primary `#1E3A5F`.
  - Candidates: Hugo `#6D4AAE`, Felipe `#1B7952`, PSD primary `#0B3C5D`, PSD olive `#6E7B3D`, PSD orange `#E07A1F`.
  - Delta diverging: loss `#B91C1C`, neutral `#EDEFF2`, gain `#0F766E`.
  - Sequential (demographic concentration): low `#EEF2FF`, high `#312E81`.
  - Fonts: IBM Plex Sans (UI/labels), IBM Plex Mono (all numbers).
- This plan does not touch: the delta year-pair control surface (`DeltaPairFilter`/`DeltaMetricFilter`/`YearFilter`), popup information design, or any new chart forms. Those are separate plans.

## File Structure

- Modify `app-web/package.json` — add `tailwindcss` + `@tailwindcss/vite` devDependencies.
- Modify `app-web/vite.config.js` — register the Tailwind Vite plugin.
- Modify `app-web/index.html` — add IBM Plex Google Fonts `<link>`s.
- Modify `app-web/src/index.css` — add `@theme` token block; swap every hardcoded dark-theme color literal for a `var(--color-*)` reference; flip the two gradient legends to the new delta/sequential hex.
- Modify `app-web/src/lib/constants.js` — update `COLORS` to the redesigned palette; add `psdOlive`, `psdOrange` (reserved for a future PSD chapa-breakdown chart), `profileAccent` (sequential-scale high end, needed by the profile toggle dot).
- Create `app-web/src/lib/constants.test.js` — guards the palette values now that many modules depend on them.
- Modify `app-web/src/components/LayerToggles.jsx` — stop hardcoding a duplicate color/label array, derive from `constants.js`.
- Create `app-web/src/components/LayerToggles.test.jsx` — guards that the dots read from the shared palette.
- Modify `app-web/src/App.jsx` — replace the hardcoded `'#5a3ca0'` profile-dot color with `COLORS.profileAccent`.
- Modify `app-web/src/lib/visual.js` — update `getDivergingColor`'s and `getSequentialColor`'s RGB anchor arrays to the new palette.
- Modify `app-web/src/lib/visual.test.js` — update the exact-value assertions that hardcode the old RGB output.
- Modify `app-web/src/components/MapView.jsx` — swap the CARTO `dark_all` basemap tile for `light_all` (Positron), matching the light-theme rationale in `design_direction.md`.

---

### Task 1: Install Tailwind v4 and define base tokens + fonts

**Files:**
- Modify: `app-web/package.json`
- Modify: `app-web/vite.config.js`
- Modify: `app-web/index.html`
- Modify: `app-web/src/index.css:1-2` (top of file + body rule only — the rest of `index.css` is Task 6)

**Interfaces:**
- Produces: CSS custom properties `--color-bg`, `--color-surface`, `--color-surface-muted`, `--color-border`, `--color-text`, `--color-text-muted`, `--color-primary`, `--font-sans`, `--font-mono` — every later task that touches `index.css` (Task 6) consumes these via `var(--color-*)` / `var(--font-*)`.

- [ ] **Step 1: Install Tailwind's Vite plugin**

Run inside `app-web/`:
```bash
npm install -D tailwindcss @tailwindcss/vite
```
Expected: `package.json` devDependencies gain `tailwindcss` and `@tailwindcss/vite`.

- [ ] **Step 2: Register the plugin in Vite config**

Modify `app-web/vite.config.js`:
```js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test-setup.js',
    passWithNoTests: true,
  },
});
```

- [ ] **Step 3: Add the IBM Plex Google Fonts links**

Modify `app-web/index.html` — add inside `<head>`, after the `viewport` meta tag:
```html
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap"
      rel="stylesheet"
    />
```

- [ ] **Step 4: Add the `@theme` token block and apply base body styles**

Modify `app-web/src/index.css` — replace lines 1-2 with:
```css
@import "tailwindcss";

@theme {
  --color-bg: #F7F8FA;
  --color-surface: #FFFFFF;
  --color-surface-muted: #EEF1F5;
  --color-border: #DDE3EA;
  --color-text: #151B26;
  --color-text-muted: #5B6472;
  --color-primary: #1E3A5F;

  --font-sans: 'IBM Plex Sans', ui-sans-serif, system-ui, sans-serif;
  --font-mono: 'IBM Plex Mono', ui-monospace, monospace;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: var(--font-sans); background: var(--color-bg); color: var(--color-text); }
```
(Leave the rest of the file — `#map` onward — untouched for now; that's Task 6.)

- [ ] **Step 5: Verify the build and existing test suite still pass**

Run: `npm run build` (inside `app-web/`)
Expected: build succeeds with no Tailwind/PostCSS errors.

Run: `npm test`
Expected: full existing suite still passes (this task changed no component logic, only added tooling + two CSS rules that no test asserts against).

- [ ] **Step 6: Commit**

```bash
git add app-web/package.json app-web/package-lock.json app-web/vite.config.js app-web/index.html app-web/src/index.css
git commit -m "feat: install Tailwind v4 and define base design tokens"
```

---

### Task 2: Centralize the redesigned palette in constants.js

**Files:**
- Modify: `app-web/src/lib/constants.js:1-8`
- Create: `app-web/src/lib/constants.test.js`

**Interfaces:**
- Produces: `COLORS.hugo_leal`, `COLORS.felipe_peixoto`, `COLORS.psd`, `COLORS.psdOlive`, `COLORS.psdOrange`, `COLORS.deltaLoss`, `COLORS.deltaNeutral`, `COLORS.deltaGain`, `COLORS.profileAccent` — consumed by Tasks 3, 4, 5, 6.

- [ ] **Step 1: Write the failing test**

Create `app-web/src/lib/constants.test.js`:
```js
import { describe, it, expect } from 'vitest';
import { COLORS, LABELS, BASE_KEYS } from './constants';

describe('COLORS', () => {
  it('assigns the redesigned candidate identity colors', () => {
    expect(COLORS.hugo_leal).toBe('#6D4AAE');
    expect(COLORS.felipe_peixoto).toBe('#1B7952');
    expect(COLORS.psd).toBe('#0B3C5D');
  });

  it('exposes the PSD secondary brand colors for a future chapa breakdown chart', () => {
    expect(COLORS.psdOlive).toBe('#6E7B3D');
    expect(COLORS.psdOrange).toBe('#E07A1F');
  });

  it('uses a colorblind-safe red-teal diverging scale, not red-green', () => {
    expect(COLORS.deltaLoss).toBe('#B91C1C');
    expect(COLORS.deltaNeutral).toBe('#EDEFF2');
    expect(COLORS.deltaGain).toBe('#0F766E');
  });

  it('exposes the profile/demographic sequential-scale accent', () => {
    expect(COLORS.profileAccent).toBe('#312E81');
  });

  it('keeps every BASE_KEYS entry covered by both COLORS and LABELS', () => {
    BASE_KEYS.forEach(key => {
      expect(COLORS[key]).toBeDefined();
      expect(LABELS[key]).toBeDefined();
    });
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npx vitest run src/lib/constants.test.js`
Expected: FAIL — `COLORS.hugo_leal` is still `'#4a90d9'`, `COLORS.psdOlive`/`psdOrange`/`profileAccent` are `undefined`.

- [ ] **Step 3: Update the palette**

Modify `app-web/src/lib/constants.js:1-8`:
```js
export const COLORS = {
  hugo_leal: '#6D4AAE',
  felipe_peixoto: '#1B7952',
  psd: '#0B3C5D',
  psdOlive: '#6E7B3D',
  psdOrange: '#E07A1F',
  deltaLoss: '#B91C1C',
  deltaNeutral: '#EDEFF2',
  deltaGain: '#0F766E',
  profileAccent: '#312E81',
};
```

- [ ] **Step 4: Run it to verify it passes**

Run: `npx vitest run src/lib/constants.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app-web/src/lib/constants.js app-web/src/lib/constants.test.js
git commit -m "feat: update candidate/delta/sequential palette to the redesign"
```

---

### Task 3: Fix LayerToggles' duplicated color array

**Files:**
- Modify: `app-web/src/components/LayerToggles.jsx` (whole file, 20 lines)
- Create: `app-web/src/components/LayerToggles.test.jsx`

**Interfaces:**
- Consumes: `COLORS`, `LABELS` from `app-web/src/lib/constants.js` (Task 2).

`LayerToggles.jsx` currently hardcodes its own `ROWS` array with the *old* candidate hex values, completely independent of `constants.js` — so Task 2's palette update alone would silently leave this component still showing the old colors. Fix the duplication instead of adding a third place to update next time.

- [ ] **Step 1: Write the failing test**

Create `app-web/src/components/LayerToggles.test.jsx`:
```jsx
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import LayerToggles from './LayerToggles';
import { COLORS } from '../lib/constants';

describe('LayerToggles', () => {
  it('colors each dot from the shared COLORS palette, not a local duplicate', () => {
    const { container } = render(
      <LayerToggles
        toggles={{ hugo: true, felipe: true, psd: true }}
        counts={{ hugo: 10, felipe: 20, psd: 30 }}
        onToggle={() => {}}
      />
    );
    const dots = container.querySelectorAll('.layer-dot');
    expect(dots[0].style.background).toBe(COLORS.hugo_leal);
    expect(dots[1].style.background).toBe(COLORS.felipe_peixoto);
    expect(dots[2].style.background).toBe(COLORS.psd);
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `npx vitest run src/components/LayerToggles.test.jsx`
Expected: FAIL — dots still read the old hardcoded hex (`#4a90d9` etc.), not `COLORS.hugo_leal` (`#6D4AAE`).

- [ ] **Step 3: Derive ROWS from constants.js**

Replace `app-web/src/components/LayerToggles.jsx` entirely:
```jsx
import { COLORS, LABELS } from '../lib/constants';

const ROWS = [
  { id: 'hugo', label: LABELS.hugo_leal, color: COLORS.hugo_leal },
  { id: 'felipe', label: LABELS.felipe_peixoto, color: COLORS.felipe_peixoto },
  { id: 'psd', label: 'PSD (total)', color: COLORS.psd },
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

- [ ] **Step 4: Run it to verify it passes**

Run: `npx vitest run src/components/LayerToggles.test.jsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app-web/src/components/LayerToggles.jsx app-web/src/components/LayerToggles.test.jsx
git commit -m "fix: derive LayerToggles colors from constants.js instead of a local duplicate"
```

---

### Task 4: Fix App.jsx's hardcoded profile-dot color

**Files:**
- Modify: `app-web/src/App.jsx:19,178`

**Interfaces:**
- Consumes: `COLORS.profileAccent` from `app-web/src/lib/constants.js` (Task 2).

- [ ] **Step 1: Add COLORS to the existing constants import**

Modify `app-web/src/App.jsx:19`:
```js
import { COLORS, BASE_KEYS, DELTA_METRICS, PROFILE_METRICS } from './lib/constants.js';
```

- [ ] **Step 2: Replace the hardcoded hex**

Modify `app-web/src/App.jsx:178` — change:
```jsx
          <span className="layer-dot" style={{ background: '#5a3ca0' }} />
```
to:
```jsx
          <span className="layer-dot" style={{ background: COLORS.profileAccent }} />
```

- [ ] **Step 3: Run the full suite to confirm no regression**

Run: `npm test`
Expected: PASS (no existing test asserts this inline style's value — `App.test.jsx` doesn't reference `5a3ca0` or `layer-dot`, confirmed by grep before writing this task).

- [ ] **Step 4: Commit**

```bash
git add app-web/src/App.jsx
git commit -m "fix: derive profile-dot color from constants.js instead of a hardcoded hex"
```

---

### Task 5: Update visual.js's color-scale anchors to the new palette

**Files:**
- Modify: `app-web/src/lib/visual.js:9-15,28-34`
- Modify: `app-web/src/lib/visual.test.js:18-32,61-103`

**Interfaces:**
- Consumes: nothing new (this task's RGB literals are the canonical source for the delta/sequential gradients — Task 6's CSS gradients must match these exactly, called out there).
- Produces: `getDivergingColor(value, maxAbs)` and `getSequentialColor(pct, min, max)` unchanged in signature, changed in output color.

`getDivergingColor`'s three anchor colors and `getSequentialColor`'s two anchor colors are RGB arrays, not hex — hand-convert the new hex tokens: loss `#B91C1C` → `[185, 28, 28]`, neutral `#EDEFF2` → `[237, 239, 242]`, gain `#0F766E` → `[15, 118, 110]`; sequential low `#EEF2FF` → `[238, 242, 255]`, high `#312E81` → `[49, 46, 129]`.

- [ ] **Step 1: Update the exact-value test assertions first**

Modify `app-web/src/lib/visual.test.js` — replace the `getDivergingColor` describe block (lines 18-32):
```js
describe('getDivergingColor', () => {
  it('trends toward the gain color for positive values', () => {
    const color = getDivergingColor(100, 100);
    expect(color).toBe('rgb(15, 118, 110)');
  });

  it('trends toward the loss color for negative values', () => {
    const color = getDivergingColor(-100, 100);
    expect(color).toBe('rgb(185, 28, 28)');
  });

  it('returns the neutral color at zero', () => {
    expect(getDivergingColor(0, 100)).toBe('rgb(237, 239, 242)');
  });
});
```
The rest of `visual.test.js` (`getSequentialColor` describe block, lines 61-103) asserts relative behavior (distinctness, clamping, null-handling, domain normalization) rather than exact RGB strings — it needs no changes and should keep passing unmodified once Step 3 lands.

- [ ] **Step 2: Run it to verify the diverging-color tests fail**

Run: `npx vitest run src/lib/visual.test.js`
Expected: FAIL on the 3 `getDivergingColor` tests (still returns the old `rgb(85, 185, 106)` / `rgb(217, 74, 74)` / `rgb(216, 216, 206)`).

- [ ] **Step 3: Update the anchor colors**

Modify `app-web/src/lib/visual.js:9-15`:
```js
export function getDivergingColor(value, maxAbs) {
  const neutral = [237, 239, 242];
  const gain = [15, 118, 110];
  const loss = [185, 28, 28];
  const t = Math.min(1, Math.sqrt(Math.abs(value) / Math.max(maxAbs, 1)));
  return value >= 0 ? interpolateColor(neutral, gain, t) : interpolateColor(neutral, loss, t);
}
```

Modify `app-web/src/lib/visual.js:28-34`:
```js
export function getSequentialColor(pct, min = 0, max = 100) {
  const light = [238, 242, 255];
  const dark = [49, 46, 129];
  const value = Number.isFinite(Number(pct)) ? Number(pct) : min;
  const t = max === min ? 0.5 : Math.min(1, Math.max(0, (value - min) / (max - min)));
  return interpolateColor(light, dark, t);
}
```

- [ ] **Step 4: Run the full test file to verify it passes**

Run: `npx vitest run src/lib/visual.test.js`
Expected: PASS (all `getDivergingColor` tests pass on the new values; all `getSequentialColor` tests pass unmodified since they test relative, not absolute, color behavior).

- [ ] **Step 5: Commit**

```bash
git add app-web/src/lib/visual.js app-web/src/lib/visual.test.js
git commit -m "feat: update delta/sequential color scales to the redesigned palette"
```

---

### Task 6: Light-theme pass — basemap + index.css

**Files:**
- Modify: `app-web/src/components/MapView.jsx:13`
- Modify: `app-web/src/index.css:4-106` (everything from `#map` onward — lines 1-2 were already handled in Task 1)

**Interfaces:**
- Consumes: `--color-*`/`--font-*` custom properties from Task 1's `@theme` block; the exact delta/sequential hex from Task 5 (must match, so the CSS gradient legends agree visually with the Leaflet marker colors computed by `visual.js`).

- [ ] **Step 1: Switch the basemap tile from dark to light**

Modify `app-web/src/components/MapView.jsx:13` — change:
```jsx
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
```
to:
```jsx
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
```

- [ ] **Step 2: Replace the rest of index.css's dark-theme literals with token references**

Modify `app-web/src/index.css` — replace everything from `#panel {` (previously line 6) through the end of the file with:
```css
#map { position: absolute; top: 0; left: 0; right: 0; bottom: 0; z-index: 1; }

#panel {
  position: absolute; top: 12px; left: 12px; z-index: 1000;
  background: var(--color-surface);
  border-radius: 10px; padding: 16px; width: 320px;
  border: 1px solid var(--color-border);
  max-height: calc(100vh - 24px); overflow-y: auto;
  box-shadow: 0 1px 3px rgba(21, 27, 38, 0.08);
}

#panel h1 { font-size: 18px; font-weight: 700; margin-bottom: 2px; color: var(--color-text); }
#panel .subtitle { font-size: 11px; color: var(--color-text-muted); margin-bottom: 14px; }

.section-title { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--color-text-muted); margin: 14px 0 6px; font-weight: 600; }

.layer-row {
  display: flex; align-items: center; gap: 8px; padding: 6px 8px;
  border-radius: 6px; cursor: pointer; transition: background 0.15s;
  margin-bottom: 2px;
}
.layer-row:hover { background: var(--color-surface-muted); }
.layer-row input { cursor: pointer; }
.layer-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
/* keep in sync with COLORS.deltaLoss/deltaNeutral/deltaGain in lib/constants.js */
.delta-dot { background: linear-gradient(90deg, #B91C1C, #EDEFF2, #0F766E); }
.layer-label { font-size: 13px; flex: 1; color: var(--color-text); }
.layer-count { font-size: 12px; color: var(--color-text-muted); font-variant-numeric: tabular-nums; font-family: var(--font-mono); }

.control-grid { display: grid; gap: 6px; }
.control-row { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.control-select {
  width: 100%;
  padding: 6px 8px;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text);
  font-size: 12px;
}
.control-select:focus { outline: none; border-color: var(--color-primary); }
.control-select option { background: var(--color-surface); color: var(--color-text); }
.control-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 2px 0;
  font-size: 12px;
  color: var(--color-text-muted);
}
.control-note { font-size: 11px; color: var(--color-text-muted); line-height: 1.45; margin-top: 4px; }

.year-bar { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 4px; }
.year-btn {
  padding: 4px 10px; border-radius: 4px; border: 1px solid var(--color-border);
  background: var(--color-surface); color: var(--color-text-muted); font-size: 12px; cursor: pointer;
  transition: all 0.15s;
}
.year-btn:hover { border-color: var(--color-primary); color: var(--color-text); }
.year-btn.active { background: var(--color-primary); color: #fff; border-color: var(--color-primary); font-weight: 600; }
.year-btn.municipal::before, .year-btn.geral::before {
  content: ''; display: inline-block; width: 6px; height: 6px; border-radius: 50%;
  margin-right: 5px; vertical-align: middle;
}
.year-btn.municipal::before { background: #2dd4bf; }
.year-btn.geral::before { background: #a78bfa; }
.year-type-legend { display: flex; align-items: center; gap: 12px; margin-top: 4px; font-size: 10px; color: var(--color-text-muted); }
.year-type-legend .dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }

#stats {
  margin-top: 14px; padding: 10px; background: var(--color-surface-muted);
  border-radius: 6px; font-size: 12px; line-height: 1.6; color: var(--color-text);
}
#stats .stat-val { font-weight: 600; color: var(--color-text); font-variant-numeric: tabular-nums; font-family: var(--font-mono); }
.delta-legend { display: flex; align-items: center; gap: 8px; margin-top: 8px; color: var(--color-text-muted); font-size: 11px; }
/* keep in sync with getDivergingColor's anchor colors in lib/visual.js */
.delta-scale { height: 6px; flex: 1; border-radius: 999px; background: linear-gradient(90deg, #B91C1C, #EDEFF2, #0F766E); }
/* keep in sync with getSequentialColor's anchor colors in lib/visual.js */
.profile-scale { height: 6px; flex: 1; border-radius: 999px; background: linear-gradient(90deg, #EEF2FF, #312E81); }

.leaflet-popup-content-wrapper {
  background: var(--color-surface) !important;
  color: var(--color-text) !important; border-radius: 8px !important;
  border: 1px solid var(--color-border) !important;
  box-shadow: 0 2px 8px rgba(21, 27, 38, 0.12) !important;
}
.leaflet-popup-tip { background: var(--color-surface) !important; }
.leaflet-popup-content { font-size: 13px !important; line-height: 1.5 !important; }
.popup-title { font-weight: 700; font-size: 14px; margin-bottom: 4px; color: var(--color-text); }
.popup-bairro { font-size: 11px; color: var(--color-text-muted); margin-bottom: 8px; }
.popup-row { display: flex; justify-content: space-between; padding: 2px 0; }
.popup-label { color: var(--color-text-muted); }
.popup-val { font-weight: 600; font-variant-numeric: tabular-nums; font-family: var(--font-mono); }
.popup-competitors { margin-top: 6px; padding-top: 4px; border-top: 1px solid var(--color-border); }
.popup-competitors summary { cursor: pointer; color: var(--color-text-muted); font-size: 12px; outline: none; }
.popup-competitors[open] summary { margin-bottom: 4px; }

#compare-panel {
  position: absolute; bottom: 24px; left: 50%; transform: translateX(-50%);
  z-index: 1000; background: var(--color-surface);
  border-radius: 10px; padding: 12px 20px; border: 1px solid var(--color-border);
  font-size: 13px; text-align: center; color: var(--color-text);
  box-shadow: 0 1px 3px rgba(21, 27, 38, 0.08);
}

@media (max-width: 640px) {
  #panel { width: calc(100vw - 24px); max-height: 52vh; }
  #compare-panel { left: 12px; right: 12px; bottom: 12px; transform: none; overflow-x: auto; }
}
```
(`backdrop-filter: blur(8px)` was dropped from `#panel` and `#compare-panel` — it was compensating for the old semi-transparent `rgba(20, 20, 40, 0.92)` background; both are opaque now, so the blur had nothing left to do.)

- [ ] **Step 3: Run the full test suite**

Run: `npm test`
Expected: full suite passes — no test in this repo asserts CSS values or the tile URL (confirmed by grep before writing this task), so this is a pure visual change from the test suite's perspective.

- [ ] **Step 4: Manual visual check**

Run: `npm run dev`, open the app in a browser.
Expected: light basemap, white floating panel, IBM Plex fonts, candidate dots in violet/teal-green/navy, no leftover dark-theme (`#1a1a2e`-style) chrome anywhere.

- [ ] **Step 5: Commit**

```bash
git add app-web/src/components/MapView.jsx app-web/src/index.css
git commit -m "feat: flip LEAL to the light, token-driven theme"
```

---

### Task 7: Final full-suite regression pass

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite one more time from a clean state**

Run: `npm test` (inside `app-web/`)
Expected: 100% pass — this is the same suite Tasks 1-6 kept green incrementally; this step is the final gate before calling the foundation done.

- [ ] **Step 2: Run the production build**

Run: `npm run build`
Expected: succeeds with no errors/warnings about missing Tailwind classes or unresolved `var(...)` tokens.

- [ ] **Step 3: No commit needed — this task is verification-only, not a code change**

---

## Self-Review Notes

- **Spec coverage:** `design_direction.md` §2 (palette) and §3 (typography) are fully covered by this plan. §1 (chart forms), §4 (delta control collapse), §5 (popup info design), §6 (framing — already satisfied, no code change needed) are explicitly out of scope, deferred to later plans per the phased-plan decision.
- **Placeholder scan:** no TBD/TODO/"add appropriate" language; every step has literal code.
- **Type/name consistency:** `COLORS.profileAccent`, `COLORS.psdOlive`, `COLORS.psdOrange` are defined in Task 2 and referenced by their exact names in Tasks 4 and 6 (comment only, not consumed in code, for `psdOlive`/`psdOrange` — flagged as reserved for a future chart, not a dangling reference).
