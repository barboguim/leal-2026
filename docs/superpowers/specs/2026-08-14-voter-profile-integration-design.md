# Voter Profile Integration — Design Spec

## Context

`scripts/04_voter_profile.py` extracts Niterói voter demographics (gender, age, education, race) from TSE's `perfil_eleitor_secao` files, at `(ano, NR_ZONA, NR_SECAO)` grain, into `data/processed/voter_profile_by_secao.csv` (10,083 rows, all 8 election years, already generated). It is fully orphaned today — confirmed via a repo-wide grep — nothing in `05`/`06`/`07`/`app-web` reads it, despite `05`'s docstring and the README both describing a merge that was never built (see `docs/voter_profile_backbone.md` for the full investigation).

This spec adds a working demographic-context layer to the React map: a **new** "Perfil do Eleitorado" toggle in the CAMADAS panel (there is no existing placeholder for it — grepped the whole `app-web/src` tree, zero hits, so this is net-new UI, not filling in dead wiring) plus a demographic breakdown inside the existing Hugo/Felipe/PSD marker popups. The analytical goal: let campaign staff read a candidate's vote share **against** the electorate composition at the same location — never as a claim about who that candidate's actual voters are.

## Scope

**In scope:**
- New pipeline script aggregating `04`'s seção-grain output up to local-de-votação grain and computing a fixed set of demographic-share fields.
- A shared-code refactor (zero behavior change) so the new script can reuse the existing seção→local crosswalk and geocoding lookup rather than rebuilding either.
- `ProfileLayer` — a new, independently-toggled map layer coloring every local by one selected demographic share at a time.
- A demographic breakdown section added to the existing popup for **all three** marker types (Hugo, Felipe, PSD).
- `ProfilePopupContent` — `ProfileLayer`'s own click popup.
- Framing-safe copy throughout (see §4 — non-negotiable).

**Out of scope (this task):**
- Seção-level map rendering — stays at local-de-votação grain, matching what the map already renders everywhere else.
- The TSE fields `04` doesn't currently extract (`DS_IDENTIDADE_GENERO`, `DS_QUILOMBOLA`, `DS_INTERPRETE_LIBRAS`, biometric/disability/social-name counts) — pulling these in means re-running the 8-file, multi-GB extraction cycle this task is explicitly avoiding. Documented as a future layer.
- Visual restyling — separate `ui-ux-pro-max` pass, comes after this.
- **"Zonas com potencial"** (lookalike-targeting/similarity-scoring future layer) — this design's output is exactly what that layer would consume, but the scoring computation itself is not built here (see §6).

## §1 Data Model

### Dimensions and fields — finalized after investigating real data quality

Three dimensions, **11 fields total**, each dimension's fields mutually exclusive and exhaustive (sum to `total_eleitores` exactly — verified against the real generated `voter_profile_by_secao.csv`):

**Gênero** (3): `pct_mulheres`, `pct_homens`, `pct_genero_nao_informado`
Source: `gen__feminino`, `gen__masculino`, `gen__nao informado`. `nao informado` is 0.02% of the electorate — trivial, included for exhaustiveness/consistency, not because it's analytically interesting on its own.

**Faixa etária** (4): `pct_jovens_16_24`, `pct_adultos_25_59`, `pct_60_mais`, `pct_idade_nao_informado`
- Jovens 16-24 = `fai__16 anos` + `fai__17 anos` + `fai__18 anos` + `fai__19 anos` + `fai__20 anos` + `fai__21 a 24 anos`
- Adultos 25-59 = `fai__25 a 29 anos` through `fai__55 a 59 anos` (7 brackets)
- 60+ = `fai__60 a 64 anos` through `fai__100 anos ou mais` (9 brackets)
- Não informado = `fai__invalido` + `fai__invalida` — **these two columns are the same category under two raw labels** (a TSE label-agreement inconsistency across years — normalizes differently depending on year). Real volume: 43 people total across all 8 years and all of Niterói — genuinely negligible, but merging costs nothing and keeps the dimension exhaustive without an unexplained gap.

**Escolaridade** (4): `pct_ate_fundamental`, `pct_ensino_medio`, `pct_ensino_superior`, `pct_escolaridade_nao_informado`
- Até Fundamental = `gra__analfabeto` + `gra__le e escreve` + `gra__ensino fundamental completo` + `gra__ensino fundamental incompleto`
- Ensino Médio = `gra__ensino medio completo` + `gra__ensino medio incompleto`
- Ensino Superior = `gra__superior completo` + `gra__superior incompleto`
- Não informado = `gra__nao informado` (0.03% of the electorate — trivial)

### Raça/Cor — cut entirely, not deferred as a cleanup item

Originally scoped as a fourth dimension (`% Pretos e Pardos` per an earlier draft of this spec). Investigation of the **real raw TSE files** (not the already-processed CSV) found:

- **2010–2022** (7 of 8 election years): 100% of every single Niterói record has `DS_RACA_COR = "#NE"` (`CD_RACA_COR = -3`). Zero real categories present — confirmed directly against the raw 2022 file, not inferred.
- **2024**: real categories exist (Branca/Preta/Parda/Amarela/Indígena, 26,899 people) but are only **6.6%** of that year's electorate; the other 93.4% is `CD_RACA_COR = -1, "NÃO INFORMADO"`.

This is not a data-quality nit to clean up (unlike the age/education label-splits above, which are genuine same-category duplicates with negligible volume) — TSE structurally did not collect this field for Niterói's registered electorate across the entire dataset. A "% Pretos e Pardos" map layer built on this would read as "almost no Black or Brown voters here," which is false — it would actually mean "this field is unanswered for 99%+ of records." Given the framing-discipline requirement (§4) to never mislead, this dimension is dropped entirely rather than shipped with a giant caveat. Documented here as a real finding for whoever revisits this later, not silently dropped.

### Aggregation

- **Input:** `data/processed/voter_profile_by_secao.csv` (04's output, seção grain) + the seção→local crosswalk (§2).
- **Grain:** `(ano, nr_local)` — matches what `05_build_geojson.py` already renders everywhere else on the map. No seção-level rendering anywhere in this feature.
- **Method:** sum raw counts (not pre-computed percentages) across all seções mapping to the same local, then divide once at the local grain. Avoids compounding rounding error from summing already-rounded percentages.
- **Every field's collapsing formula lives in the pipeline, not the frontend** — testable in Python, and guarantees the popup and the map layer read from identical numbers (no risk of the two surfaces drifting apart).

## §2 Pipeline Architecture

### Shared-code refactor (prerequisite, zero behavior change)

Two groups of functions currently live inside single numbered scripts with no shared-module presence, even though a second script now needs them:

1. `get_local_coords()` and `to_geojson()` — currently only in `scripts/05_build_geojson.py`. Move to `scripts/_pipeline_utils.py`. `05` re-imports the identical functions; its own behavior is unchanged.
2. `build_section_id()`, `load_section_roster_from_raw()`, `load_section_roster_from_votes()`, `load_section_roster()`, `section_local_lookup()` — currently only in `scripts/06_build_vote_deltas.py`. Move to `scripts/_pipeline_utils.py`. `06` re-imports the identical functions; its delta/gating computation itself is untouched — only where the roster-building code physically lives changes. `06`'s existing tests continue to assert the same behavior, updated only to import from the new location.

This follows the project's established convention (no script currently imports from another numbered script — shared logic always lives in `_pipeline_utils.py`) and directly satisfies "reuse the existing lookup, do not rebuild geocoding" without introducing script-to-script coupling.

### New script: `scripts/09_voter_profile_geojson.py`

Numbered by introduction order per the project's convention (scripts are numbered by when they were added, not by execution order — see `08`, which runs after `05` despite its number). Real execution position: after `02` (needs processed vote data for the roster fallback), `04` (needs `voter_profile_by_secao.csv`), and `05` (merges onto the geojson files `05` produces). Independent of `06`/`07`/`08`. **Documented execution order becomes `01→02→03→04→05→08→09→06→07`.**

**What it does:**
1. Load `voter_profile_by_secao.csv`.
2. Build/reuse the shared section→local roster to aggregate seção-level raw counts up to `(ano, nr_local)`.
3. Compute the 11 fields from §1's formulas, plus keep `total_eleitores`.
4. Emit two outputs:
   - **`data/geo/voter_profile.geojson`** — standalone, one feature per `(ano, nr_local)`, real point geometry via the shared `get_local_coords()`. Source for `ProfileLayer` — needs every local with profile data, independent of which candidates ran there, so it can't live merged inside a candidate-specific file.
   - **Merge the same fields onto `hugo_leal.geojson` / `felipe_peixoto.geojson` / `psd.geojson`**, matched on `(ano, nr_local)` — same `props.update(...)` pattern `08` already uses for the PSD breakdown merge. Source for the popup section.

## §3 Frontend Architecture

### `ProfileLayer` (new component, mirrors `DeltaLayer`'s structure, not its color scheme)

- New `PROFILE_METRICS` constant in `lib/constants.js` — 11 entries, grouped by dimension (`{ dimension: 'Gênero', id: 'mulheres', label: '% Mulheres', field: 'pct_mulheres' }`, etc.).
- New `ProfileMetricFilter.jsx` — a two-level selector (dimension, then category within it). This reverses an earlier flat-list proposal from this same brainstorm — the flat shape only made sense for a 6-entry curated list; with 11 real TSE categories across 3 dimensions, grouping by dimension is how a user would actually browse them.
- New `ProfileLayer.jsx` — one `CircleMarker` per `voter_profile.geojson` feature for the selected year, colored by the selected metric.
- **Color scale: a neutral single-hue sequential scale (light → dark), not `DeltaLayer`'s red/green diverging scale.** Red/green in this app already means "lost/gained votes." Reusing that language for a demographic share (e.g. "% 60+") would visually imply a performance judgment on a neutral fact — exactly what the framing discipline (§4) forbids.
- New "Perfil do Eleitorado" section in the CAMADAS panel, parallel to "Deltas": own toggle (default **off** — new advanced layer, shouldn't clutter first paint), own two-level metric selector, own legend.

### Popup integration

- A new collapsible section in `PopupContent.jsx` (same `<details>` pattern as `CompetitorSection`/`PsdBreakdownSection`), rendered on **all three** marker types (Hugo, Felipe, PSD) — confirmed explicitly: even though PSD's popup has no vote-share number to compare against (deliberate, per the existing candidacy-matrix design — PSD is a multi-candidate aggregate with no single denominator), the demographic section is a property of the *location*, not the candidate, so it's still informative there.
- Shows all 11 fields, grouped under 3 dimension headers, plus `total_eleitores` — the same data `ProfileLayer` reads, no separate curated subset. (An earlier draft of this brainstorm proposed a different, smaller "curated" set for the popup than the map layer — rejected: it produced a confusing redundant view, e.g. showing individual race categories alongside a separately-computed aggregate of the same categories. One field list, used identically in both places, is simpler and cannot drift.)
- `ProfilePopupContent.jsx` — `ProfileLayer`'s own click popup, reusing the same 11-field data and row labels as the merged popup section, for when a user clicks a profile marker directly.

## §4 Framing & Copy (non-negotiable)

The Brazilian vote is secret; TSE never links a voter's demographics to their ballot choice. Every label in this feature must read as **"vote share vs. electorate composition at this location,"** never as a claim about who a candidate's actual voters are.

- **Popup section title:** `"Perfil do eleitorado deste local"` — not just "Perfil do eleitorado." This section renders physically nested inside e.g. Hugo Leal's popup; making the location-scope explicit in the title itself (not just implied) closes the risk that visual proximity alone reads as "Hugo's voters."
- **Mandatory subtitle line**, same visual weight as the existing `.popup-bairro` text: `"Composição do eleitorado local — não indica em quem estes eleitores votaram."`
- **`ProfileLayer` legend:** `"menor concentração ↔ maior concentração"` — no "perdeu/ganhou" language anywhere near this layer (see the color-scale reasoning in §3).
- **Row labels:** `% Mulheres`, `% Homens`, `% Jovens 16-24`, `% Adultos 25-59`, `% 60+`, `% Até Fundamental`, `% Ensino Médio`, `% Ensino Superior`, plus each dimension's `Não informado` row, plus `Total eleitores`.

**Explicitly not included:** a disclaimer paragraph on every popup, or correlation/causation essay text. The forbidden-framing list is about labels lying; a location-scoped title plus one subtitle line closes that without cluttering a popup that already has several other sections. The heavier ecological-inference framing belongs to the future "Zonas com potencial" layer (§6), which will make an actual ranked claim — this task only ever displays two separate facts side by side.

## §5 Testing Strategy

**Python (`tests/test_voter_profile_geojson.py`, new):**
- Each of the 11 collapsing formulas, on a small synthetic seção-grain fixture, asserting the computed field matches a hand-calculated expected value.
- Fields sum to `total_eleitores` (exhaustiveness check) on the fixture.
- Aggregation correctly sums raw counts across multiple seções mapping to the same `nr_local` before computing percentages (not averaging pre-computed percentages).
- Zero-`total_eleitores` edge case (a local with no profile data) doesn't divide by zero.
- Real-data spot check: run against the real regenerated `voter_profile.geojson`, confirm no `rac__*`/race field exists anywhere in the output, confirm at least one real local's 11 fields sum to ~100% (allowing for floating-point rounding).

**Python (refactor verification):**
- `06_build_vote_deltas.py`'s existing test suite (already covering `load_section_roster`/`section_local_lookup` indirectly) continues to pass unchanged after the functions move to `_pipeline_utils.py`, aside from import-path updates.

**Frontend (`app-web/src/components/*.test.jsx`, new/extended):**
- `ProfileLayer` renders one marker per feature for the selected year, correctly excludes features for other years.
- `ProfileMetricFilter` correctly switches which field colors the map.
- `PopupContent` renders the demographic section on all three layer keys (hugo_leal, felipe_peixoto, psd) — a regression test here directly guards the "all three, not just Hugo/Felipe" decision.
- `ProfilePopupContent` renders the same 11 fields + total.
- **Framing-copy test:** assert the mandatory section title and subtitle text are present verbatim, and assert none of the forbidden phrasing patterns (e.g. "eleitores de Hugo", "eleitores do candidato") appear anywhere in the rendered popup output.

## §6 Future compatibility (not built now)

**"Zonas com potencial"** (lookalike-targeting): once a candidate's per-local vote share and per-local demographic composition are both available at the same `(ano, nr_local)` grain — which this design produces — a later task can profile the demographic fingerprint of a candidate's strongholds, find similarly-shaped locais where they underperform, and surface those as ranked leads. This design doesn't compute or reserve UI for a similarity score; it just ensures both inputs that computation would need already exist in a consistent, tested shape. Framing discipline applies there even more strongly (ranked leads to investigate, never statistical certainty) — a concern for that task's own spec, not this one's.
