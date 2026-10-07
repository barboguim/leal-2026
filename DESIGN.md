# LEAL Design Handoff

This document is a visual handoff for the next design pass. It describes the
existing product structure and should not be used as permission to change the
data model, analytical labels, or component behavior.

## Current Product

LEAL is a map-first electoral analysis tool for Niteroi. The map is the primary
workspace. The sidebar controls visibility and comparison state; popups explain
one polling location at a time.

The active frontend is `app-web`, built with React and react-leaflet.

## Phase B Contract

The current phase includes the design-token foundation and the collapsed delta
control surface. Preserve these behaviors during visual refinement:

- Candidate layers: Hugo Leal, Felipe Peixoto, and PSD.
- Delta layer: one selected candidate/party and one valid pair of comparable
  years.
- Profile layer: a contextual view of local electorate composition.
- Region and bairro filters, with optional official boundaries.
- Existing popup components and their tests.
- Collapsible `Concorrencia` and `Perfil do eleitorado` sections.

Do not reintroduce the old six-button delta-pair grid.

## Analytical Framing

The interface must never imply that the tool traces individual voters or that
votes migrated from Hugo to Felipe. Deltas describe changes in observed votes at
the same mapped location. Section movement is a polling-section geography
diagnostic, not voter movement.

Demographic fields describe the composition of the electorate registered at the
local. They do not describe the candidate's voters. Keep the disclaimer visible
when the profile section opens:

> Composicao do eleitorado local — nao indica em quem estes eleitores votaram.

Use `Concorrencia`, not `Competidor`, in visible Portuguese labels.

## Popup Structure

### Candidate popup

The default view should show the location, bairro, candidate, party, cargo
pretendido, election type, year, votes, share, and section count. Secondary
analysis stays collapsed:

```text
Local
Bairro
Candidato
Partido
Cargo pretendido
Tipo de eleicao
Ano
Votos
Participacao
Secoes

▸ Concorrencia
▸ Perfil do eleitorado deste local
```

`Candidato` and `Partido` are separate rows, not one combined
"Candidato / Partido" line — the candidate's name never tells you their party
on its own, and party is not fixed per person: it changes across a
candidate's career (e.g. Felipe ran PDT in 2010/2012, PSB in 2016, PSD from
2018 on). `Cargo pretendido` (e.g. "DEPUTADO FEDERAL", "PREFEITO") is not
optional polish — a candidate's cargo also changes year to year (Felipe alone
has run for Deputado Estadual, Prefeito, and Deputado Federal at different
elections), and the votes/participacao numbers on this popup are only
interpretable once you know which contest they belong to. Never drop it from
the default (non-collapsed) view.

The expanded `Concorrencia` section contains the top three competing candidates
for that local, year, and cargo. It is a ranking context, not a migration path.

### Delta popup

The delta popup shows both endpoints as a comparison record:

```text
Local
Bairro
Par: 2018–2022
Tipo: Geral → Geral
Delta Hugo
Hugo: start → end (signed delta)
Felipe: start → end (signed delta)
PSD: start → end (signed delta)
Secoes: start → end
Movimento de secoes

▸ Concorrencia 2018
▸ Concorrencia 2022
```

Each competitor disclosure contains the top three candidates for its own year
and cargo. Do not collapse the two years into a single “top competitor” row.

## Visual Direction

Previous wording here said "hybrid of the references" without pinning actual
values, which is exactly why three separate visual passes each interpreted it
differently and left `index.css` with unreconciled, stacked override blocks
for the same selectors. This section replaces that with concrete numbers.
Do not substitute different values because a reference file suggests them —
the values below are the settled choice, adapted from `references.md`'s two
references to fit LEAL's own density and existing token set, not copied
wholesale from either.

**Base tokens: unchanged.** `index.css`'s existing `@theme` block
(`--color-bg`, `--color-surface`, `--color-surface-muted`, `--color-border`,
`--color-text`, `--color-text-muted`, `--color-primary`, IBM Plex Sans/Mono)
is already a light, neutral, shadcn-shaped system. Do not swap the palette.
The gap is radius/shadow/type consistency, which this section pins.

**Radius scale** (compact — LEAL's panel is a ~350px dense sidebar, not a
marketing card grid, so shadcn's 18/24px scale is too loose):
- Panel / card container: `10px`
- Inputs, selects, buttons: `8px`
- Chips, badges, pills: `999px` (full pill — already right on `.delta-pair-chip`)

**Shadow** (one quiet elevation, not the `0 14px 32px` / `0 18px 46px` stacks
introduced across the three passes — those read as a floating card, not a
calm field instrument):
```css
--shadow-panel: 0 1px 2px rgba(21, 27, 38, 0.06), 0 1px 3px rgba(21, 27, 38, 0.08);
```
Use this single value everywhere something currently has a heavier shadow
(`#panel`, `#compare-panel`, popups).

**Type scale** (all IBM Plex, sizes pinned — stop reintroducing ad hoc px
values per pass):
| Role | Font | Size | Weight |
|---|---|---|---|
| Panel title (`h1`) | Plex Sans | 16px | 600 |
| Section-title (uppercase group label) | Plex Sans | 10px, 0.06em tracking | 600 |
| Body / control text | Plex Sans | 12px | 400–500 |
| Popup title | Plex Sans | 13px | 600 |
| Popup label | Plex Sans | 11px | 400 |
| Numeric values (votes, %, years) | Plex Mono | 12px, tabular | 500 |

**Borders:** only ever `var(--color-border)`. No ad hoc `rgba(119,132,150,...)`
one-offs like the ones visual-pass-2 introduced for `--panel-line`.

**Two specific fixes to the current CSS, decided, not open questions:**
- `.delta-pair-context`'s `border-left: 3px solid var(--color-primary)` (a
  colored side-tab accent — flagged by design review as a common AI-generated-UI
  tell) is removed. Replace with a plain `background: var(--color-surface-muted)`
  tint and no border — the label text already carries the meaning.
- `#panel::before`'s 4-color gradient stripe (candidate colors as page
  decoration) is removed. It's decorative, not informational — a panel-level
  color accent implies "this whole panel is about these 4 things," which isn't
  true. If a top accent is wanted at all, it's a plain 1px `var(--color-border)`
  rule, not a gradient.

The result should feel like a credible field-analysis instrument: calm,
information-dense, and geographic. It should not become a generic SaaS admin
dashboard, a marketing landing page, or a glowing war-room HUD.

## Visual Rules

- Keep the map visually dominant; panels should frame it, not cover it.
- Use IBM Plex Sans for interface text and IBM Plex Mono for numeric values.
- Use direct signs (`+`, `-`) and labels alongside delta colors.
- Keep red/teal reserved for the loss/gain meaning of the delta scale.
- Keep demographic concentration on the separate indigo sequential scale.
- Use color, typography, and spacing together; never make color the only cue.
- Keep secondary rows visible when transparency requires them, but de-emphasize
  near-zero demographic values instead of hiding them.
- Maintain the existing mobile behavior: the sidebar becomes a constrained
  upper panel and the comparison panel remains usable horizontally.
- Use modest radii and restrained shadows. Avoid nested cards and decorative
  blobs.

## Sidebar Information Architecture — settled, superseding earlier drafts

This section went through several rounds against `design-mockups.html` before
landing; the structure below is the approved one. **No dropdowns anywhere in
the sidebar** — year selection, delta-pair selection, and profile-dimension
selection are all chips/buttons, consistently, everywhere.

1. **Candidatos** — three self-contained rows, one per candidate (Hugo Leal,
   Felipe Peixoto, PSD), each a native `<details>`. Two independent
   affordances per row, not one repurposed:
   - The **checkbox** means exactly what it means today: show/hide that
     candidate's single-year dots on the map. Unchanged, multi-select (any
     combination of the three can be visible at once).
   - **Clicking the name/summary** expands that candidate's own panel. Each
     expanded panel is fully self-contained:
     - Their own year-chip row (button per year, **only years that candidate
       actually has data for** — not the full 2010-2024 range; e.g. Hugo only
       ever ran in Geral years, so his row has 4 chips, not 8) plus a
       Municipal/Geral dot legend directly beneath that candidate's own year
       row (repeated per candidate, not shared once at the group level —
       tried shared-once, it read as disconnected from the three separate
       chip rows below it).
     - A **"Comparar dois anos"** checkbox — an independent sub-layer toggle,
       off by default. When on, reveals that candidate's valid year-pair
       chips (from `pairsByMetric[candidate]`, i.e. exactly what
       `lib/deltaPairs.js` already computes) plus the perdeu/ganhou legend.
   - All three candidates' expanded/comparing states are independent — any
     combination can be open or comparing at once. Not an accordion, not
     mutually exclusive (an earlier draft made them mutually exclusive; that
     turned out wrong once each candidate carries its own year state instead
     of sharing one global "Ano" control).
   - This also retires two pieces of state the old design needed:
     the standalone "Candidato" selector (Camadas already lists them) and the
     "Variacao por local" enable checkbox (selecting a pair via chip inside an
     expanded candidate *is* the enable action — no separate step).
2. **Perfil do Eleitorado** — own section, own visibility checkbox + count,
   Dimensao as chips (Genero / Faixa etaria / Escolaridade), not a select.
3. **Zonas com Potencial** — own compact single row (one checkbox + one note
   line), doesn't need a group of its own.
4. **Filtros** (Regiao/Bairro) — collapsed by default. Native
   `<details>`/`<summary>`, not custom JS toggle state.
5. **Stats** — pinned at the bottom, always visible, outside any collapsible
   group.

Popup content fixes carried by this same pass (see § Popup Structure above):
`Candidato`/`Partido` split into separate rows, `Cargo pretendido` restored
as its own row.

## Interaction & Spacing

**Spacing scale** (4px base unit, compact density — matches what the mockup
already uses, formalized here so it doesn't drift): `4, 6, 8, 10, 12, 16, 20,
24`px. Panel padding `16px`; gap between groups `12px`; gap between a
group's internal rows `6-8px`; tight gaps (chip-to-chip, dot-to-label) `4-5px`.

**Interactive states — required, not optional polish** (accessibility
priority, not decoration):
- Every clickable element (chip, candidate summary, details summary, button,
  checkbox) needs a visible `:hover` state — a subtle background/border shift
  toward `var(--color-surface-muted)` / `var(--color-primary)`, `150-200ms`
  transition. The current mockup has none; that's a gap this pass closes.
- Every focusable element needs a visible `:focus-visible` outline (keyboard
  navigation — this is a priority-1 accessibility requirement, not
  priority-10 polish). Use `outline: 2px solid var(--color-primary); outline-offset: 1px`,
  not the browser default and not `outline: none`.
- Chip/button touch targets: keep a minimum ~28-30px height even though this
  is primarily a desktop tool — LEAL's own constraint is "maintain mobile
  behavior," so tap targets can't regress on the constrained mobile panel.

## Design-Pass Scope

**Structure is approved.** This next pass applies the actual reference-derived
visual treatment (tokens above, `references.md`) to `design-mockups.html` in
place — still a static mockup, still not touching `app-web/` (no React, no
`index.css`) until this polished version is reviewed and approved. Once
approved, a separate pass wires it into the real components.

What "applying the references" means concretely, since vague language here is
exactly what produced three divergent, unreconciled CSS passes earlier:
- Base palette stays LEAL's own (already shadcn-shaped, confirmed above) —
  don't reach for new hex values from `references.md`.
- Felt's actual dark moss-green palette and GT Alpina serif are explicitly
  **not** adopted — they'd contradict the light-theme decision and the IBM
  Plex typography decision, both already settled. What transfers from Felt is
  compositional only: map-first framing, cartographic overlay discipline —
  which LEAL's floating-panel-over-map structure already has.
- What this pass actually adds: real Google Fonts loading (the mockup must
  render in the real IBM Plex, not a system-font fallback), the hover/focus
  states from § Interaction & Spacing, and a basemap placeholder that reads
  as a credible light map (subtle, muted) rather than the current gray/teal
  gradient block, which doesn't resemble the real CartoDB Positron tiles the
  production map actually uses.

The next visual pass may refine CSS, layout, type scale, panel density, popup
hierarchy, disclosure affordances, and map-overlay contrast. It should not
change the pipeline, candidate gating, election-pair validity, profile framing,
or competitor ranking logic.
