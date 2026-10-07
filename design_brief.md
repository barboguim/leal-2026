# LEAL — Design Direction Brief (ui-ux-pro-max)

Use the **ui-ux-pro-max** skill. Return a **design direction brief (not code)**: chart recommendations, palette + hex values, font pairing + hierarchy, and interaction-pattern pseudocode. This feeds a later build spec — do not implement yet.

## Product

LEAL is a **tactical electoral decision-support tool** for campaign staff and volunteers in Niterói (RJ), Brazil. Not a marketing site, not a public-facing dashboard. The audience is political operatives who need credible, data-driven analysis fast. They compare the same polling location across election years, drill into candidate matchups, read a candidate's vote share against the local electorate profile, and (later) get ranked "potential" target locations.

Current state: React + react-leaflet map, sidebar with layer toggles, year filters, a vote-delta comparison layer, candidate popups, a demographic profile overlay, and data sections for competitor rankings and PSD slate breakdown. It is currently styled with placeholder/functional-only CSS carried over from a pre-migration vanilla version — **the current look is not a design decision, it's a stand-in.** This pass sets the real visual language.

## What to recommend

1. **Chart types for electoral data.** Vote deltas (diverging, gained/lost), vote-share comparisons, candidate head-to-head, demographic profile breakdowns (gender/age/education as share bars), and demographic-vs-vote-share reads. What chart forms best serve political analysis at a glance vs. on drill-down?

2. **Color palette.** What do credible real-world political/electoral dashboards use vs. generic AI-dashboard defaults? Consider: candidate/party identity colors (Hugo, Felipe, PSD each need a stable identity color that stays legible), a diverging scale for deltas (lost↔gained), and a sequential scale for demographic concentration. **No theme constraint — recommend light, dark, or neutral based on what best serves a data-dense analytical tool that people read for long sessions.** Justify the choice.

3. **Typography for data-dense interfaces.** The UI carries vote counts, percentages, candidate names, cargo titles (e.g. "DEPUTADO FEDERAL"), years, and demographic breakdowns. Recommend a font pairing and a clear numeric/label hierarchy. Tabular figures for the number columns matter.

4. **Interaction patterns.** Toggling layers (candidates / delta / demographic profile), switching demographic dimensions, and drilling into a local via popup. **Specific problem to solve:** the delta comparison currently exposes SIX pre-baked year-pair buttons (2010-2014, 2010-2018, 2012-2016, 2014-2018, 2016-2020, 2018-2022, 2020-2024) plus a candidate toggle plus a year-filter row — too many stacked controls. Recommend a cleaner interaction for "pick a candidate, pick two comparable years, see the delta" that collapses this control surface.

5. **Popup information design.** The candidate popup shows: name, cargo pretendido, year, votes, % share, seções count, an expandable competitor ("Concorrência") section, and an expandable "Perfil do eleitorado deste local" section with gender/age/education shares. It currently renders every sub-row including "% Não informado" even at 0% (a deliberate transparency choice so shares sum to ~100%). **Design decision to make:** how to present this honestly and legibly — keep zero/near-zero rows for exhaustiveness, or collapse/de-emphasize them? Recommend the pattern.

## Constraints (architectural — keep; these protect prior work)

- Stay in **React + react-leaflet + Tailwind**. No new frameworks, no map-engine swap.
- Must remain **mobile-responsive**.

## Constraints (aesthetic)

- **None.** No dark-theme requirement, no imposed style. Recommend the visual direction that best fits a credible, data-dense electoral-intelligence tool. Justify it.

## Framing discipline (must survive the redesign)

Labels must always frame demographics as **electorate composition vs. vote share** — never as "the candidate's voters." The vote is secret; the tool correlates outcome with local composition (ecological inference), it never traces who voted for whom. The popup already carries the disclaimer "Composição do eleitorado local — não indica em quem estes eleitores votaram." The redesign must preserve this framing prominently, not bury or drop it.

## Out of scope

- Implementation/code (this is direction only).
- The "Zonas com potencial" lookalike-targeting layer (reserved future feature — but if the design system anticipates a ranked-results panel, note where it would live).