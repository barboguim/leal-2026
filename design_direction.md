# LEAL — Design Direction (ui-ux-pro-max output)

Direction only, per `design_brief.md`. No code. Feeds the later build spec.

---

## 1. Charts

Database matches for "diverging/delta" and "demographic breakdown" kept steering toward waterfall/treemap/pie — wrong shape for this data (single time-series deltas per local, not cumulative or hierarchical). Overriding the raw matches with the shapes actually correct for electoral analysis, using the DB's accessibility rules (no color-alone encoding, mandatory table fallback) as the constraint:

| Data | Chart | Why | Reject |
|---|---|---|---|
| Vote delta (2 years, 1 candidate, 1 local) | **Diverging horizontal bar**, zero-baseline, one bar | Single signed number — a bar reads instantly, direction is unambiguous even before color registers | Waterfall (implies additive multi-step change, this is one delta); gauge (hides sign) |
| Vote-share comparison across years (same candidate, 3+ years) | **Small-multiple sparkline or slope chart** (year on x, % on y) | Campaign staff scan many locais fast — sparkline is glanceable at list-row size; slope chart if only 2 points need emphasis | Line chart with full axis chrome (too heavy per-row); pie per year (can't compare across years) |
| Candidate head-to-head (same local, same year) | **Grouped horizontal bar**, candidates as rows, shared 0–100% axis | Direct rank + magnitude comparison, sorts naturally by vote share | Radar (fails on 2–3 candidates, DB flags it needs 5–8 axes); pie (slice differences under 5% go unreadable, common in tight races) |
| Demographic profile (gender/age/education, one dimension at a time) | **100%-stacked horizontal bar**, one bar per dimension, segments = brackets | Shares always sum to 100 — stacked bar states that visually; matches the existing "collapse to 2–3 curated cuts" logic from prior work (see `answer.md`) | Donut/pie per dimension (three donuts side by side is harder to compare than one stacked bar); treemap (wrong: this isn't hierarchical) |
| Demographic-vs-vote-share (correlation read) | **Dot/strip plot**: x = demographic %, y = candidate vote share %, one dot per local, current local highlighted | This is the ecological-inference view — a scatter is the honest form for "these two numbers co-occur here," and doesn't imply causation the way a combined bar would | Dual-axis combo bar+line (visually implies the two series are causally linked — exactly the framing this project must avoid) |

Glance vs. drill-down split: map markers and list rows show the single-number diverging bar or sparkline only. The full grouped bar / stacked bar / scatter forms live inside the popup's expandable sections, per §5.

All charts: label values directly on the mark (bar end, dot), never rely on a legend alone to convey gained/lost — matches the DB's "don't convey information by color alone" rule (ux-guidelines.csv, Accessibility/Color Only, severity High).

---

## 2. Color

### Base theme: light, neutral — not dark

Justification (the brief leaves this open, so reasoning it through):

- **Map integration.** react-leaflet basemaps (CartoDB Positron-class light tiles, which is what reads as "credible/neutral" rather than "gamer HUD") sit inside a light chrome without a seam. A dark UI shell around a light map creates a jarring bright rectangle — the map becomes the loudest thing on screen for the wrong reason.
- **Genre match.** Real electoral-results tooling (TSE Resultados, election-night broadcast graphics, official apuração dashboards) is light-background with saturated party/candidate color doing the signaling. Dark, glowing dashboards read as "monitoring/security tool" genre, not "electoral analysis" — wrong trust signal for an audience of campaign operatives, some of whom are older and non-technical.
- **Long sessions ≠ automatic dark-mode win.** Long-session eye strain is a font-size/contrast/whitespace problem more than a light/dark problem; a light UI with restrained contrast (not pure #FFFFFF/#000000) avoids both glare and the "screen glow in a war room" issue.
- Net: light base now; if night-session war-room use turns out to be real, add a dark variant later as a toggle, not the default.

### Tokens (light, neutral base — adapted from the DB's Government/Civic-Portal and Data-Dense-Dashboard matches, deduped for WCAG AA)

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#F7F8FA` | App background (off-white, not stark white — cuts glare) |
| `--surface` | `#FFFFFF` | Cards, popups, panels |
| `--surface-muted` | `#EEF1F5` | Nested panels, disabled rows |
| `--border` | `#DDE3EA` | Dividers, card borders |
| `--text` | `#151B26` | Primary text (near-black slate, not pure black) |
| `--text-muted` | `#5B6472` | Labels, secondary metadata (meets 4.5:1 on `--surface`) |
| `--ring` / `--primary` | `#1E3A5F` | Institutional navy — nav, primary buttons, focus ring |

### Candidate / party identity colors

**Update:** PSD's official colors are confirmed (azul escuro, verde oliva, laranja) — using the real brand palette instead of the earlier placeholder gray. `constants.js` treats `hugo`, `felipe`, and `psd` as three parallel sibling series (`delta_hugo`, `delta_felipe`, `delta_psd`, all independently toggleable and shown together), so the design constraint is: PSD's three brand hues, Hugo, Felipe, and the delta scale all have to stay mutually distinguishable when stacked in the same legend.

| Entity | Hex | Note |
|---|---|---|
| **PSD — primary** | `#0B3C5D` (azul escuro) | Party identity anchor — chapa/slate header, primary marker color when PSD is shown as a whole |
| PSD — secondary | `#6E7B3D` (verde oliva) | Slate/chapa breakdown chart, second series |
| PSD — tertiary | `#E07A1F` (laranja) | Slate/chapa breakdown chart, third series |
| Hugo | `#6D4AAE` (violet) | Moved off blue — PSD's navy now owns that hue, and the two appear as sibling toggles on the same map, so they can't share a color family even though Hugo is a PSD figure in reality |
| Felipe | `#1B7952` (deep teal-green, adjusted) | Requested as `#1B7A6B`; nudged — see collision check below |

Three collision checks run against this set:

- **Verde oliva vs. the delta "gained" teal** (`#0F766E`, §below): different enough in hue (olive ~73°, teal ~175° — ~100° apart) and in warmth (olive reads warm/yellow-green, teal reads cool/blue-green) to stay distinguishable side by side. Still, treat verde oliva as **PSD-context-only** — never repurpose it as a generic "positive" indicator elsewhere, or the two meanings will bleed into each other.
- **Felipe (`#1B7952`) vs. verde oliva** (`#6E7B3D`): ~82° apart in hue (155° vs. 73°) — clears the same margin as the olive/gained-teal pair above. Fine as-is.
- **Felipe vs. the delta "gained" teal** (`#0F766E`) — this one failed at the requested hex and needed the adjustment: `#1B7A6B` sits at hue ~171°, only 4° from gained-teal's 175°, with near-identical lightness (0.29 vs 0.26) and near-identical blue channel (107 vs 110) — a candidate marker that color-matches the "vote gained" indicator is a real read-it-wrong risk on this map. Nudged Felipe to `#1B7952`: blue channel dropped 107→82 (the main fix — CVD simulation relies on the blue channel staying distinct since red/green cones are the ones affected), hue shifted 171°→155° (now 20° from gained-teal instead of 4°). R and G channels barely moved, so it reads as the same "deep teal-green" family requested, just less blue-leaning.
- **PSD's azul escuro vs. `--ring`/`--primary`** (`#1E3A5F`, the app's own UI-chrome navy, above): kept them visually apart on purpose — PSD's navy is deeper/more saturated so a PSD data series never gets mistaken for app chrome (nav bars, focus rings, buttons).

These hexes approximate "dark blue / olive green / orange" from description — **confirm against PSD's actual style guide or campaign-material swatches if one exists**, and swap in the exact hex before this becomes a build spec. Same caveat applies to Hugo/Felipe if either already has an established color on printed materials.

### Diverging scale — vote delta (lost ↔ gained)

Explicitly **not** red-green. Red-green diverging is the single most common colorblind failure in dashboards (fails ~8% of men). Using a red-teal axis instead — keeps the intuitive "red = lost" read (matches every election broadcast convention) while staying safe for deuteranopia/protanopia:

| Delta | Hex |
|---|---|
| Strong loss | `#B91C1C` |
| Mild loss | `#F0A99A` |
| ~0 / no change | `#EDEFF2` |
| Mild gain | `#7FD4C4` |
| Strong gain | `#0F766E` |

Always pair with a `+`/`−` sign and an arrow glyph on the value label — never color alone (DB accessibility rule, severity High).

### Sequential scale — demographic concentration

Single hue, distinct from both the above so a reader never confuses "this local has a lot of X demographic" with "this candidate gained here":

`#EEF2FF → #C7D2FE → #818CF8 → #4338CA → #312E81` (indigo ramp, low→high concentration)

---

## 3. Typography

**IBM Plex Sans** (UI labels, candidate names, cargo titles, section headers) + **IBM Plex Mono** (every number: vote counts, %, seções, years).

Why this pairing over the DB's top dashboard match (Fira Code/Fira Sans): Fira Code reads as developer-tool/sci-fi HUD, which undercuts the "credible institutional analysis" trust signal this audience needs. IBM Plex was the DB's own "Financial Trust" match (banking/insurance/serious data) — same family design goal as this tool, and IBM Plex Mono has genuine monospaced tabular figures (every digit is fixed-width by construction), so columns of vote counts/percentages align without needing `font-variant-numeric: tabular-nums` fallbacks.

Hierarchy:

| Element | Font | Weight | Size (rem) | Notes |
|---|---|---|---|---|
| Candidate name | Plex Sans | 600 | 1.05 | |
| Cargo pretendido ("DEPUTADO FEDERAL") | Plex Sans | 500, uppercase, +0.04em tracking | 0.7 | Small-caps-style label, not competing with the name |
| Vote count / % share (headline numbers) | Plex Mono | 600 | 1.5 | The number a scanning eye should land on first |
| Vote count / % (secondary, in tables/rows) | Plex Mono | 400–500 | 0.875 | tabular by default |
| Year | Plex Mono | 500 | 0.875 | Always mono, even inline in sentences — years are data, not prose |
| Section labels (Concorrência, Perfil do eleitorado) | Plex Sans | 600, uppercase | 0.75 | |
| Body/disclaimer text | Plex Sans | 400 | 0.8125 | e.g. the ecological-inference disclaimer — legible but clearly secondary to the numbers |

Base UI text stays ≥ 13px equivalent even in dense table rows — the DB's "no body text under 12px" floor, and this audience reads it for long sessions.

---

## 4. Interaction: collapsing the delta control surface

Current surface: 6 hardcoded year-pair buttons + candidate toggle + year-filter row stacked simultaneously. Problem is redundancy, not information — the 6 buttons *are* just "pick two years" with the invalid combinations pre-filtered out.

Recommended replacement — one row, three controls, in a fixed left-to-right dependency order that matches how a staffer actually thinks ("who, then when, then when-else"):

```
[ Candidate ▾ ]   [ Ano A ▾ ]   →   [ Ano B ▾ ]        (Δ renders automatically once both years are set)
```

Pseudocode:

```
state = { candidate: null, yearA: null, yearB: null }

validYearPairs(candidate) = precomputed set of (yearA, yearB) that exist for that candidate
  // this is exactly the 6 pairs today — same data, just not rendered as 6 separate buttons

on candidate select:
  state.candidate = chosen
  state.yearA = state.yearB = null   // reset downstream, avoid stale invalid pair
  yearA_options = unique years in validYearPairs(candidate)
  disable yearB control until yearA is set

on yearA select:
  state.yearA = chosen
  yearB_options = years paired with yearA in validYearPairs(candidate)
    // only ever shows years that produce a real delta — no dead-end selections possible
  if only one valid yearB exists: auto-select it (one less click for the common case)

on yearB select:
  state.yearB = chosen
  render delta layer for (candidate, yearA, yearB)
  // no separate "apply" button — selection IS the action, consistent with how the
  // existing layer toggles already behave

on candidate change while a full pair is active:
  keep yearA if it's valid for the new candidate, else reset (don't silently show
  a delta computed against the wrong candidate's year set)
```

This removes the year-filter row entirely as a separate control — year filtering *is* the yearA/yearB selection now, one mechanism instead of two. Layer toggles (candidates / delta / demographic profile) stay a separate, persistent control group above this row since they're orthogonal (what's visible) rather than sequential (what's compared).

Mobile: same three controls stack full-width vertically in the same top-to-bottom dependency order; no redesign needed since the dependency chain already reads naturally top-to-bottom.

---

## 5. Popup information design

**Recommendation: keep every row, including 0%/near-zero, but de-emphasize rather than collapse.**

Reasoning: the brief already made the honesty call deliberately (rows sum to ~100% including "Não informado"). The design problem isn't whether to show the row, it's that all rows currently compete at equal visual weight. Fix the weight, not the list:

- Rows above a threshold (e.g. ≥ 3%) render at full weight: Plex Mono number, full-opacity sequential-scale bar.
- Rows below threshold render at reduced weight: `--text-muted` color, thinner bar, same Plex Mono figure — present, scannable on purpose, but clearly not where the eye should stop first.
- Never hide behind an extra click (no "show more" for this list) — the brief's transparency goal fails if a reader has to opt in to see the full accounting. De-emphasis via weight preserves both exhaustiveness and glanceability.
- Sort order stays value-descending regardless of weight class, so the near-zero rows naturally fall to the bottom without needing a separate visual "cutoff line."

This is the same "state it in place, don't gate it behind disclosure" logic that should apply to the ecological-inference disclaimer (§6) — the two are the same design principle applied twice: honesty is a weighting problem, not a visibility toggle.

Concorrência and Perfil sections: keep as expandable (they're genuinely secondary — a staffer often just wants the headline number and doesn't always need competitor detail), collapsed by default, but the *disclaimer inside Perfil* is never itself collapsed — it renders above the fold of that section the instant it opens, not nested inside a further disclosure.

---

## 6. Framing discipline (carried through, not just noted)

Every demographic label pattern: **"[X]% da composição do eleitorado local"**, never "[X]% dos eleitores de [candidate]." The disclaimer ("Composição do eleitorado local — não indica em quem estes eleitores votaram") gets a fixed position at the top of the Perfil section, styled as `--text-muted` Plex Sans italic — present but not screaming, exactly like a footnote whose absence would be the actual problem. It is not inside the expand/collapse — expanding Perfil reveals the disclaimer *first*, data second.

Same rule applies to the demographic-vs-vote-share scatter in §1: axis labels read "Vote share (%)" and "Local demographic composition (%)," never "voters who are [X]."

---

## 7. Future: Zonas com potencial (out of scope, noted for continuity)

If/when the ranked-target-locations panel ships, it belongs as a fourth item in the same layer-toggle group from §4 (candidates / delta / demographic profile / **potencial**), not a new top-level nav — it's another lens on the same map, same interaction grammar. Its ranked list would reuse the grouped-horizontal-bar pattern from §1 (rank order, single comparable metric per row) rather than introducing a new chart form.

---

## Sources

- ui-ux-pro-max DB: `--design-system` (electoral/dashboard/dense query), `--domain chart`, `--domain color` (diverging, sequential — 0 results, fell back to standard colorblind-safe diverging/sequential construction, noted inline), `--domain typography`, `--domain google-fonts`, `--domain ux`.
- `--domain ux` returned 0 results for "progressive disclosure" / popup-disclosure specific queries — §5 and §4 interaction logic beyond the DB's literal matches is direct design reasoning, not a DB citation.
