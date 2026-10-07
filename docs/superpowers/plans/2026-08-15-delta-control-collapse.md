# Delta Control Collapse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace LEAL's delta control surface — 6+ pre-baked year-pair buttons (`DeltaPairFilter`) stacked above a separate candidate toggle (`DeltaMetricFilter`) — with one row of three dependent dropdowns (Candidate → Ano A → Ano B), per `design_direction.md` §4.

**Architecture:** `App.jsx` currently owns a single `selectedPair` string ("YYYY-YYYY") threaded unchanged into `DeltaLayer`, `StatsPanel`, `CompareTable`, and `DeltaPopupContent`. This plan splits that one piece of state into `selectedYearA`/`selectedYearB` (matching the design doc's `{candidate, yearA, yearB}` model) and *derives* the same "YYYY-YYYY" string from them each render — so all four downstream consumers keep receiving the exact same prop shape they do today and require zero changes. The dependent-dropdown logic (which years are valid for a candidate, what happens to the selection when the candidate changes) is pure, framework-free logic in a new `lib/deltaPairs.js`, unit-tested in isolation; `DeltaControls.jsx` is a thin, fully presentational component that only renders `<select>`s and calls back up.

**Tech Stack:** React 19, Vitest + React Testing Library (existing test stack, no new dependencies).

## Global Constraints

- The four existing consumers of `selectedPair` — `DeltaLayer.jsx`, `StatsPanel.jsx`, `CompareTable.jsx`, `DeltaPopupContent.jsx` — must not be modified. They keep receiving a "YYYY-YYYY" string or `null`, exactly as today.
- `selectedDeltaMetric` (the `'hugo' | 'felipe' | 'psd'` state) keeps its existing name and shape — only how it's *set* changes (it now also triggers the year-selection transition logic below).
- Interaction rules, copied verbatim from `design_direction.md` §4:
  - Candidate select first; Ano A only offers years valid for the selected candidate; Ano B only offers years that pair with the selected Ano A for that candidate (no dead-end selections).
  - If only one valid Ano B exists for a given Ano A, auto-select it.
  - Selection is the action — no separate "apply" button; the delta layer renders as soon as both years are set (already true today via `toggles.delta && pair`).
  - On candidate change: keep Ano A if it's still valid for the new candidate; if the *same* Ano B is also still valid, keep both unchanged; otherwise auto-select Ano B if exactly one option remains, else clear Ano B (not the whole selection). If Ano A itself isn't valid for the new candidate, clear both.
- Reuse the existing `.control-select`/`.control-grid` CSS classes and visual pattern from `GeoFilter.jsx` — don't invent a new select styling.
- No new npm dependencies.

## File Structure

- Create `app-web/src/lib/deltaPairs.js` — pure functions deriving dropdown options and the candidate-change transition rule from a candidate's list of valid "YYYY-YYYY" pair strings. No React, no app state — independently unit-testable.
- Create `app-web/src/lib/deltaPairs.test.js` — unit tests for the above.
- Create `app-web/src/components/DeltaControls.jsx` — the three-dropdown row. Purely presentational: renders from props, calls the three `onXChange` callbacks it's given. Owns no state of its own.
- Create `app-web/src/components/DeltaControls.test.jsx` — RTL tests for the component.
- Modify `app-web/src/index.css` — add a `.control-row-3` rule (three-column variant of the existing `.control-row`).
- Modify `app-web/src/App.jsx` — replace `selectedPair` state + `deltaPairs` memo with `selectedYearA`/`selectedYearB` state + `pairsByMetric` memo; add two handler functions using `lib/deltaPairs.js`; replace the `DeltaPairFilter`/`DeltaMetricFilter` JSX with `DeltaControls`.
- Delete `app-web/src/components/DeltaPairFilter.jsx` and `app-web/src/components/DeltaMetricFilter.jsx` — fully superseded, no other file imports them (confirmed via repo-wide grep), and neither has an existing test file to remove.

---

### Task 1: Pure pair-selection logic (`lib/deltaPairs.js`)

**Files:**
- Create: `app-web/src/lib/deltaPairs.js`
- Test: `app-web/src/lib/deltaPairs.test.js`

**Interfaces:**
- Produces: `yearAOptions(pairs: string[]): number[]`, `yearBOptions(pairs: string[], yearA: number | null): number[]`, `nextYearSelection(pairs: string[], currentYearA: number | null, currentYearB: number | null): { yearA: number | null, yearB: number | null }` — all consumed by Task 3 (`DeltaControls.jsx`) and Task 4 (`App.jsx`). `pairs` is always a candidate-specific list of "YYYY-YYYY" strings (e.g. `['2010-2014', '2014-2018', '2018-2022']`) — the same strings already used throughout the app as `pair` (see `DeltaLayer.jsx`'s `f.properties.pair === pair` filter).

- [ ] **Step 1: Write the failing tests**

Create `app-web/src/lib/deltaPairs.test.js`:
```js
import { describe, it, expect } from 'vitest';
import { yearAOptions, yearBOptions, nextYearSelection } from './deltaPairs';

const PAIRS = ['2010-2014', '2014-2018', '2018-2022', '2010-2018'];

describe('yearAOptions', () => {
  it('returns the unique start years across all pairs, sorted ascending', () => {
    expect(yearAOptions(PAIRS)).toEqual([2010, 2014, 2018]);
  });

  it('returns an empty array for no pairs', () => {
    expect(yearAOptions([])).toEqual([]);
  });
});

describe('yearBOptions', () => {
  it('returns the end years paired with the given start year, sorted ascending', () => {
    expect(yearBOptions(PAIRS, 2010)).toEqual([2014, 2018]);
  });

  it('returns an empty array when yearA is null', () => {
    expect(yearBOptions(PAIRS, null)).toEqual([]);
  });

  it('returns an empty array when yearA has no matching pairs', () => {
    expect(yearBOptions(PAIRS, 1999)).toEqual([]);
  });
});

describe('nextYearSelection', () => {
  it('keeps both years when the exact same pair is still valid for the new candidate', () => {
    expect(nextYearSelection(PAIRS, 2010, 2014)).toEqual({ yearA: 2010, yearB: 2014 });
  });

  it('clears both years when yearA is not valid for the new candidate', () => {
    expect(nextYearSelection(PAIRS, 2016, 2020)).toEqual({ yearA: null, yearB: null });
  });

  it('clears both years when yearA is null', () => {
    expect(nextYearSelection(PAIRS, null, null)).toEqual({ yearA: null, yearB: null });
  });

  it('keeps yearA and auto-selects yearB when yearA is valid but the old yearB is not, and only one option remains', () => {
    // Only pairs starting at 2014: '2014-2018' -- exactly one yearB option.
    expect(nextYearSelection(PAIRS, 2014, 2099)).toEqual({ yearA: 2014, yearB: 2018 });
  });

  it('keeps yearA and clears yearB when yearA is valid but the old yearB is not, and more than one option remains', () => {
    // Pairs starting at 2010: '2010-2014' and '2010-2018' -- two yearB options, no old yearB match.
    expect(nextYearSelection(PAIRS, 2010, 2099)).toEqual({ yearA: 2010, yearB: null });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `app-web/`): `npx vitest run src/lib/deltaPairs.test.js`
Expected: FAIL — `Cannot find module './deltaPairs'` (the module doesn't exist yet).

- [ ] **Step 3: Implement the module**

Create `app-web/src/lib/deltaPairs.js`:
```js
export function yearAOptions(pairs) {
  return [...new Set(pairs.map(p => Number(p.split('-')[0])))].sort((a, b) => a - b);
}

export function yearBOptions(pairs, yearA) {
  if (yearA == null) return [];
  return pairs
    .filter(p => Number(p.split('-')[0]) === yearA)
    .map(p => Number(p.split('-')[1]))
    .sort((a, b) => a - b);
}

// Given the pairs valid for a newly selected candidate, and the years selected
// before that change, decide the next {yearA, yearB}. Rules (design_direction.md §4):
// keep yearA if still valid; if the exact same yearB is also still valid, keep both;
// otherwise auto-select yearB if exactly one option remains, else clear yearB only.
// If yearA itself isn't valid for the new candidate, clear both.
export function nextYearSelection(pairs, currentYearA, currentYearB) {
  if (currentYearA == null || !pairs.some(p => Number(p.split('-')[0]) === currentYearA)) {
    return { yearA: null, yearB: null };
  }
  const options = yearBOptions(pairs, currentYearA);
  if (currentYearB != null && options.includes(currentYearB)) {
    return { yearA: currentYearA, yearB: currentYearB };
  }
  return { yearA: currentYearA, yearB: options.length === 1 ? options[0] : null };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run src/lib/deltaPairs.test.js`
Expected: PASS (10/10)

- [ ] **Step 5: Commit**

```bash
git add app-web/src/lib/deltaPairs.js app-web/src/lib/deltaPairs.test.js
git commit -m "feat: add pure pair-selection logic for the delta candidate/year dropdowns"
```

---

### Task 2: `DeltaControls` component

**Files:**
- Create: `app-web/src/components/DeltaControls.jsx`
- Test: `app-web/src/components/DeltaControls.test.jsx`
- Modify: `app-web/src/index.css` (add `.control-row-3`)

**Interfaces:**
- Consumes: `yearAOptions`, `yearBOptions` from `app-web/src/lib/deltaPairs.js` (Task 1).
- Produces: `DeltaControls` component, props `{ metrics, selectedMetric, pairsByMetric, selectedYearA, selectedYearB, onCandidateChange, onYearAChange, onYearBChange }` — consumed by Task 4 (`App.jsx`). `metrics` is the existing `DELTA_METRICS` shape from `lib/constants.js` (`{ hugo: { label, field }, felipe: {...}, psd: {...} }`). `pairsByMetric` is `{ hugo: string[], felipe: string[], psd: string[] }` (candidate key → its valid "YYYY-YYYY" pairs). `onCandidateChange(key: string)`, `onYearAChange(year: number)`, `onYearBChange(year: number)`.

- [ ] **Step 1: Write the failing tests**

Create `app-web/src/components/DeltaControls.test.jsx`:
```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import DeltaControls from './DeltaControls';

const METRICS = {
  hugo: { label: 'Hugo', field: 'delta_hugo' },
  felipe: { label: 'Felipe', field: 'delta_felipe' },
  psd: { label: 'PSD', field: 'delta_psd' },
};

const PAIRS_BY_METRIC = {
  hugo: ['2010-2014', '2014-2018', '2018-2022'],
  felipe: ['2012-2016', '2016-2020'],
  psd: ['2018-2022'],
};

function renderControls(overrides = {}) {
  const props = {
    metrics: METRICS,
    selectedMetric: 'hugo',
    pairsByMetric: PAIRS_BY_METRIC,
    selectedYearA: null,
    selectedYearB: null,
    onCandidateChange: vi.fn(),
    onYearAChange: vi.fn(),
    onYearBChange: vi.fn(),
    ...overrides,
  };
  render(<DeltaControls {...props} />);
  return props;
}

describe('DeltaControls', () => {
  it('renders one option per candidate in the candidate select', () => {
    renderControls();
    expect(screen.getByRole('option', { name: 'Hugo' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Felipe' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'PSD' })).toBeInTheDocument();
  });

  it('offers only the years valid for the selected candidate in Ano A', () => {
    renderControls({ selectedMetric: 'felipe' });
    expect(screen.getByRole('option', { name: '2012' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: '2016' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: '2010' })).not.toBeInTheDocument();
  });

  it('disables Ano B until Ano A is selected', () => {
    renderControls({ selectedYearA: null });
    const selects = screen.getAllByRole('combobox');
    expect(selects[2]).toBeDisabled();
  });

  it('enables Ano B and offers only years paired with the selected Ano A', () => {
    renderControls({ selectedYearA: 2014 });
    const selects = screen.getAllByRole('combobox');
    expect(selects[2]).not.toBeDisabled();
    expect(screen.getByRole('option', { name: '2018' })).toBeInTheDocument();
  });

  it('calls onCandidateChange with the new key when the candidate select changes', () => {
    const props = renderControls();
    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[0], { target: { value: 'felipe' } });
    expect(props.onCandidateChange).toHaveBeenCalledWith('felipe');
  });

  it('calls onYearAChange with a number when Ano A changes', () => {
    const props = renderControls();
    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[1], { target: { value: '2014' } });
    expect(props.onYearAChange).toHaveBeenCalledWith(2014);
  });

  it('calls onYearBChange with a number when Ano B changes', () => {
    const props = renderControls({ selectedYearA: 2014 });
    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[2], { target: { value: '2018' } });
    expect(props.onYearBChange).toHaveBeenCalledWith(2018);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npx vitest run src/components/DeltaControls.test.jsx`
Expected: FAIL — `Cannot find module './DeltaControls'`.

- [ ] **Step 3: Add the CSS row variant**

Modify `app-web/src/index.css` — add immediately after the existing `.control-row` rule (currently `.control-row { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }`):
```css
.control-row-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; }
```

- [ ] **Step 4: Implement the component**

Create `app-web/src/components/DeltaControls.jsx`:
```jsx
import { yearAOptions, yearBOptions } from '../lib/deltaPairs';

export default function DeltaControls({
  metrics, selectedMetric, pairsByMetric, selectedYearA, selectedYearB,
  onCandidateChange, onYearAChange, onYearBChange,
}) {
  const pairs = pairsByMetric[selectedMetric] || [];
  const yearAOpts = yearAOptions(pairs);
  const yearBOpts = yearBOptions(pairs, selectedYearA);

  return (
    <div className="control-grid">
      <div className="control-row-3">
        <select
          className="control-select"
          value={selectedMetric}
          onChange={(e) => onCandidateChange(e.target.value)}
        >
          {Object.entries(metrics).map(([key, metric]) => (
            <option key={key} value={key}>{metric.label}</option>
          ))}
        </select>
        <select
          className="control-select"
          value={selectedYearA ?? ''}
          onChange={(e) => onYearAChange(Number(e.target.value))}
        >
          <option value="" disabled>Ano A</option>
          {yearAOpts.map(y => <option key={y} value={y}>{y}</option>)}
        </select>
        <select
          className="control-select"
          value={selectedYearB ?? ''}
          disabled={selectedYearA == null}
          onChange={(e) => onYearBChange(Number(e.target.value))}
        >
          <option value="" disabled>Ano B</option>
          {yearBOpts.map(y => <option key={y} value={y}>{y}</option>)}
        </select>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx vitest run src/components/DeltaControls.test.jsx`
Expected: PASS (7/7)

- [ ] **Step 6: Commit**

```bash
git add app-web/src/components/DeltaControls.jsx app-web/src/components/DeltaControls.test.jsx app-web/src/index.css
git commit -m "feat: add DeltaControls, a three-dropdown candidate/year-A/year-B row"
```

---

### Task 3: Wire `DeltaControls` into `App.jsx`, remove the old components

**Files:**
- Modify: `app-web/src/App.jsx`
- Delete: `app-web/src/components/DeltaPairFilter.jsx`
- Delete: `app-web/src/components/DeltaMetricFilter.jsx`

**Interfaces:**
- Consumes: `DeltaControls` (Task 2), `nextYearSelection`, `yearBOptions` from `lib/deltaPairs.js` (Task 1).
- Produces: nothing new for later tasks — this is the integration point.

`App.jsx` currently (relevant excerpts):
```jsx
// imports
import DeltaPairFilter from './components/DeltaPairFilter.jsx';
import DeltaMetricFilter from './components/DeltaMetricFilter.jsx';
// ...
  const deltaPairs = useMemo(() => {
    if (!data?.vote_deltas) return [];
    return [...new Set(data.vote_deltas.features.map(f => f.properties.pair))]
      .sort((a, b) => Number(a.slice(0, 4)) - Number(b.slice(0, 4)));
  }, [data]);
// ...
  const [selectedPair, setSelectedPair] = useState(() => (deltaPairs.includes('2018-2022') ? '2018-2022' : (deltaPairs[deltaPairs.length - 1] ?? null)));
  const [selectedDeltaMetric, setSelectedDeltaMetric] = useState('hugo');
// ...
  const pair = selectedPair;
// ...
        <DeltaPairFilter pairs={deltaPairs} selectedPair={pair} onChange={setSelectedPair} />
        <DeltaMetricFilter metrics={DELTA_METRICS} selectedMetric={selectedDeltaMetric} onChange={setSelectedDeltaMetric} />
```

- [ ] **Step 1: Replace the imports**

Modify `app-web/src/App.jsx` — replace:
```jsx
import DeltaPairFilter from './components/DeltaPairFilter.jsx';
import DeltaMetricFilter from './components/DeltaMetricFilter.jsx';
```
with:
```jsx
import DeltaControls from './components/DeltaControls.jsx';
```

And add the pure-logic import alongside the existing `lib` imports (near `import { COLORS, BASE_KEYS, DELTA_METRICS, PROFILE_METRICS } from './lib/constants.js';`):
```jsx
import { nextYearSelection, yearBOptions } from './lib/deltaPairs.js';
```

- [ ] **Step 2: Replace `deltaPairs` with `pairsByMetric`**

Modify `app-web/src/App.jsx` — replace the `deltaPairs` useMemo block:
```jsx
  const deltaPairs = useMemo(() => {
    if (!data?.vote_deltas) return [];
    return [...new Set(data.vote_deltas.features.map(f => f.properties.pair))]
      .sort((a, b) => Number(a.slice(0, 4)) - Number(b.slice(0, 4)));
  }, [data]);
```
with:
```jsx
  const pairsByMetric = useMemo(() => {
    if (!data?.vote_deltas) return {};
    const result = {};
    for (const [key, metric] of Object.entries(DELTA_METRICS)) {
      const valid = new Set(
        data.vote_deltas.features
          .filter(f => f.properties[metric.field] !== null && f.properties[metric.field] !== undefined)
          .map(f => f.properties.pair)
      );
      result[key] = [...valid].sort((a, b) => Number(a.slice(0, 4)) - Number(b.slice(0, 4)));
    }
    return result;
  }, [data]);
```

- [ ] **Step 3: Replace `selectedPair` state with `selectedYearA`/`selectedYearB`**

Modify `app-web/src/App.jsx` — replace:
```jsx
  // 2018-2022 is verified against real vote_deltas data to be fully gated
  // for all three metrics (unlike 2022-2024, which doesn't exist under the
  // matrix-gated pairing, and 2020-2024, whose fallback leaves Hugo — the
  // default metric — gated to null everywhere).
  const [selectedPair, setSelectedPair] = useState(() => (deltaPairs.includes('2018-2022') ? '2018-2022' : (deltaPairs[deltaPairs.length - 1] ?? null)));
  const [selectedDeltaMetric, setSelectedDeltaMetric] = useState('hugo');
```
with:
```jsx
  // 2018-2022 is verified against real vote_deltas data to be fully gated for
  // Hugo (the default candidate) -- unlike 2022-2024, which doesn't exist
  // under the matrix-gated pairing, and 2020-2024, which leaves Hugo gated to
  // null everywhere. Default candidate is 'hugo', so the fallback is scoped
  // to hugo's own valid pairs (see pairsByMetric above), not the old
  // candidate-agnostic union.
  const defaultHugoPairs = pairsByMetric.hugo || [];
  const defaultDeltaPair = defaultHugoPairs.includes('2018-2022')
    ? '2018-2022'
    : (defaultHugoPairs[defaultHugoPairs.length - 1] ?? null);
  const [selectedYearA, setSelectedYearA] = useState(() => (defaultDeltaPair ? Number(defaultDeltaPair.split('-')[0]) : null));
  const [selectedYearB, setSelectedYearB] = useState(() => (defaultDeltaPair ? Number(defaultDeltaPair.split('-')[1]) : null));
  const [selectedDeltaMetric, setSelectedDeltaMetric] = useState('hugo');
```

- [ ] **Step 4: Add the two change handlers**

Modify `app-web/src/App.jsx` — add these two functions in the component body, right after the `useEffect` for the outside-click handler (before `if (!data) { ... }`):
```jsx
  function handleDeltaCandidateChange(newKey) {
    setSelectedDeltaMetric(newKey);
    const { yearA, yearB } = nextYearSelection(pairsByMetric[newKey] || [], selectedYearA, selectedYearB);
    setSelectedYearA(yearA);
    setSelectedYearB(yearB);
  }

  function handleDeltaYearAChange(year) {
    setSelectedYearA(year);
    const options = yearBOptions(pairsByMetric[selectedDeltaMetric] || [], year);
    setSelectedYearB(options.length === 1 ? options[0] : null);
  }
```

- [ ] **Step 5: Derive `pair` from the two year states**

Modify `app-web/src/App.jsx` — replace:
```jsx
  const year = selectedYear;
  const pair = selectedPair;
```
with:
```jsx
  const year = selectedYear;
  const pair = selectedYearA != null && selectedYearB != null ? `${selectedYearA}-${selectedYearB}` : null;
```

- [ ] **Step 6: Replace the JSX**

Modify `app-web/src/App.jsx` — replace:
```jsx
        <DeltaPairFilter pairs={deltaPairs} selectedPair={pair} onChange={setSelectedPair} />
        <DeltaMetricFilter metrics={DELTA_METRICS} selectedMetric={selectedDeltaMetric} onChange={setSelectedDeltaMetric} />
```
with:
```jsx
        <DeltaControls
          metrics={DELTA_METRICS}
          selectedMetric={selectedDeltaMetric}
          pairsByMetric={pairsByMetric}
          selectedYearA={selectedYearA}
          selectedYearB={selectedYearB}
          onCandidateChange={handleDeltaCandidateChange}
          onYearAChange={handleDeltaYearAChange}
          onYearBChange={setSelectedYearB}
        />
```

- [ ] **Step 7: Delete the superseded components**

```bash
git rm app-web/src/components/DeltaPairFilter.jsx app-web/src/components/DeltaMetricFilter.jsx
```

- [ ] **Step 8: Run the full test suite**

Run (from `app-web/`): `npm test`
Expected: full suite passes, including the existing `App.test.jsx` test (it doesn't touch delta state, so it's unaffected by this change) — no test anywhere references `DeltaPairFilter`, `DeltaMetricFilter`, or `selectedPair` by name (confirmed by repo-wide grep before writing this plan).

- [ ] **Step 9: Manual dev-server check**

Run: `npm run dev`, open the app in a browser, expand the "Deltas" section.
Expected: one row with three dropdowns (candidate, Ano A, Ano B). Selecting a candidate shows only that candidate's valid years in Ano A. Picking Ano A narrows Ano B to only its valid pairings (auto-selecting if there's just one). The delta layer/markers update as soon as both years are set, with no separate apply step. Switching candidate with a full pair already selected either keeps both years (if still valid) or resets only what's no longer valid, per the Global Constraints rule above.

- [ ] **Step 10: Commit**

```bash
git add app-web/src/App.jsx
git commit -m "feat: wire DeltaControls into App, replacing the year-pair button grid"
```

---

### Task 4: Final full-suite regression pass

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite from a clean state**

Run (from `app-web/`): `npm test`
Expected: 100% pass.

- [ ] **Step 2: Run the production build**

Run: `npm run build`
Expected: succeeds with no errors.

- [ ] **Step 3: No commit needed — this task is verification-only, not a code change.**

---

## Self-Review Notes

- **Spec coverage:** design_direction.md §4's full pseudocode (candidate-first ordering, yearA-narrows-yearB, auto-select-single-option, selection-is-the-action, keep-or-reset on candidate change) is covered across Tasks 1-3. The mock's visual arrow (`→`) between Ano A and Ano B is a nice-to-have not called out as a hard requirement; skipped to keep the diff minimal — easy to add as a `<span>` between the two selects later if wanted.
- **Placeholder scan:** no TBD/TODO language; every step has literal code.
- **Type/name consistency:** `pairsByMetric`, `selectedYearA`/`selectedYearB`, `handleDeltaCandidateChange`, `handleDeltaYearAChange` are defined once (Task 3) and referenced identically wherever used. `DeltaControls`' prop names match exactly between Task 2's implementation and Task 3's usage.
