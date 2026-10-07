# Candidacy Matrix & Delta Gating — Design Spec

**Date:** 2026-08-12
**Status:** Approved, not yet implemented

## Context

`scripts/06_build_vote_deltas.py` currently computes a delta between every
consecutive TSE election year for Hugo Leal, Felipe Peixoto, and PSD,
treating "no votes extracted" identically to "zero votes received." Three
genuinely different situations collapse into that one number:

1. The candidate didn't run that year.
2. The party didn't exist yet (PSD was founded in 2011 — 2010 predates it).
3. The candidate ran and genuinely received few votes.

This produces fake losses: Felipe shows `-6.919` for 2024 because he
**didn't run** in 2024, not because he lost votes. PSD shows `0` in 2010
because the **party didn't exist**, not because it received no votes.

Comparisons also currently cross incomparable races. Felipe ran Deputado
Estadual in 2010, Prefeito in 2012/2016/2020, Deputado Estadual in 2018,
Deputado Federal in 2022 — a majoritarian citywide race (Prefeito) and
proportional statewide races (Estadual/Federal) have structurally different
vote ceilings and dynamics, and none of that distinction exists in the
current delta computation.

PSD compounds this: it's a party fielding multiple candidates across
multiple cargos per election, currently flattened into one number per
seção per year by `scripts/02_process_votes.py`. A drop like 2012→2016
(34.597→2.653) is uninterpretable without knowing *which* candidates made
up each year's total.

This is the second of three planned sub-projects on LEAL's UI/analysis
layer (see [2026-08-11-vote-competitors-design.md](2026-08-11-vote-competitors-design.md)'s
sub-project list — this spec supersedes that doc's placeholder for
sub-project 2). The third, a storytelling/conclusions tab, still isn't
designed here.

## Scope

### In scope
- A candidacy matrix (`data/processed/candidacy_matrix.csv`), sourced from
  TSE's `consulta_cand` registration files (downloaded fresh — not
  currently present in `data/raw/`), confirming for each candidate × year:
  did they run, for which cargo, in which election type.
- Gating all deltas off that matrix: N/A (not 0) when a candidate didn't
  run or a party didn't exist; deltas only computed between years with the
  same election type (Geral vs Municipal); pairs found by nearest matching
  cycle rather than assumed-consecutive TSE years.
- A PSD slate breakdown: candidate count, top-3 by votes (across cargos),
  and per-cargo volume, per `(year, local)`.
- A vote-share denominator (total valid votes per race) extending the
  existing competitor-ranking mechanism in `scripts/07_top_competitors.py`.
- Popup redesign: `Nome · Partido · Cargo pretendido · Votos · % share`.
- Legend fix: "Geral" instead of "Federal" (general elections bundle
  federal + estadual races).

### Out of scope (deferred to future specs)
- Timeline slider UI.
- Campaign finance data.
- Cross-type comparison as an explicit opt-in view (the request names this
  as a future addition; this spec only removes cross-type comparison from
  the *default* view — it does not build the opt-in view itself).

## Design

### 1. Data Model

**New file:** `data/processed/candidacy_matrix.csv` — one row per
`(candidate_key, ano)`, built from `consulta_cand`:

| Field | Meaning |
|---|---|
| `candidate_key` | `hugo_leal` \| `felipe_peixoto` \| `psd_<nr_candidato>` (one row per PSD candidate, not just the party) |
| `ano` | election year |
| `cargo` | registered cargo, e.g. `DEPUTADO FEDERAL` |
| `tipo_eleicao` | `Geral` or `Municipal` — derived the same way `electionType()` already does (`ano % 4 == 0` → Municipal), reused from the existing Python and JS implementations, not reimplemented |
| `partido` | party at time of registration |
| `situacao_candidatura` | raw TSE status string, kept for audit, not used in gating logic |

**Gating rule:** two years are comparable for a given candidate only if
both have a matrix row **and** both rows share the same `tipo_eleicao`.
Cargo does not need to match — Deputado Estadual and Deputado Federal are
both `Geral` and are comparable; Prefeito (`Municipal`) is never comparable
to either.

**PSD gating:** PSD as an aggregate is gated on party existence (founded
2011 — 2010 is always N/A) plus the same `tipo_eleicao` bucketing (a
Municipal-year PSD total sums Vereador/Prefeito candidates; a Geral-year
PSD total sums Deputado Federal/Estadual candidates — different pools,
never compared cross-type).

**Pair selection:** nearest matching cycle within each candidate's
`tipo_eleicao` bucket, not strictly-consecutive TSE years. Example (Felipe):

```
Geral bucket:     2010 -> 2018,  2018 -> 2022
Municipal bucket: 2012 -> 2016,  2016 -> 2020
```

Hugo is unaffected — he ran Deputado Federal (Geral) every cycle he
competed, so his pairs stay consecutive: `2010 -> 2014 -> 2018 -> 2022`.

**N/A representation:** every per-year vote/delta field becomes `null`
(never `0`) when the matrix has no comparable row, paired with a
`candidacy_status` field (`concorreu` | `nao_concorreu` |
`partido_inexistente`) that the frontend reads to decide what to render.
Numeric fields stay real-number-or-null; no sentinel strings.

**Vote share denominator:** valid votes only (excludes voto branco `95` /
voto nulo `96`) — matches TSE's own convention for candidate vote-share
reporting, and matches how `is_real_candidate()` in
`scripts/07_top_competitors.py` already filters.

### 2. Pipeline Architecture

**New script:** `scripts/08_candidacy_matrix.py`, doing three things:

1. **Download-if-missing `consulta_cand`.** `data/raw/` currently has no
   `consulta_cand` files — confirmed absent this session. `01_download_tse.py`
   also defines but never calls a `url_candidato_munzona` helper; that's a
   *different* TSE dataset (vote results by candidate) and stays unused —
   `consulta_cand` (registration) is the correct, authoritative source
   named in the request. Add `url_consulta_cand(year)` to `config.py`.
   Move `download_and_extract()` from `01_download_tse.py` into
   `_pipeline_utils.py` so both scripts share it instead of duplicating
   (matches this project's existing precedent for shared pipeline code).
2. **Build `candidacy_matrix.csv`** from the downloaded registration files
   — rows for Hugo, Felipe, and every PSD candidate.
3. **Build the PSD slate breakdown** — re-reads raw `votacao_secao` (same
   mechanism `07_top_competitors.py` already uses to rank competitors),
   filters to PSD candidates, and per `(year, local)` ranks the top-3 PSD
   candidates by votes **across all their cargos** (not per-cargo — a
   single local's PSD total mixes a Vereador slate and a Prefeito
   candidate in the same year, and ranking across cargos is what actually
   explains a swing like the 2012→2016 example). Also computes
   `psd_candidate_count` and a per-cargo volume split. Merges these fields
   onto the existing `psd.geojson` (same merge-onto-existing-features
   pattern `07` already uses for `hugo_leal.geojson`/`felipe_peixoto.geojson`).

**Scripts 02, 03, 04 — untouched.** `02`'s flat PSD aggregate stays
exactly as-is; it's still correct as "the party's total that year," just
incomplete without `08`'s breakdown, which is purely additive.

**Script 05 — one field added, otherwise untouched.** The new popup's
"Cargo pretendido" field needs a `cargo` property on each
`hugo_leal.geojson`/`felipe_peixoto.geojson` feature. `05_build_geojson.py`
already builds these features per person per year and already has access
to `config.py`'s `HUGO_LEAL`/`FELIPE_PEIXOTO` `elections` dicts elsewhere
in the pipeline — it looks up `cargo` from there directly, no new
dependency on the candidacy matrix for this single field. PSD doesn't get
a single `cargo` property on its base feature (it fields multiple cargos
at once); its per-candidate cargo lives entirely in the `08`-built
breakdown fields already specified above.

**Script 06 — the only existing script modified.** Rewritten to:
- Consume `candidacy_matrix.csv` for gating instead of assuming every
  consecutive TSE year pair is comparable.
- Enumerate pairs via nearest-matching-cycle within each `tipo_eleicao`
  bucket, per candidate (see Data Model above), replacing the current
  hardcoded consecutive-year pairing.
- Stamp `candidacy_status` and null out vote/delta fields on ungated pairs
  instead of computing a numeric delta against an absent candidacy.

**Script 07 — extended, not replaced.** Add `total_votos_validos` (sum of
all real-candidate votes, reusing the existing `is_real_candidate` filter,
*not* excluding Hugo/Felipe themselves since vote share naturally includes
the candidate's own votes in its denominator) to the per-local grouping
already computed for `rank_top3_by_local()`'s raw data, merged onto
`hugo_leal.geojson`/`felipe_peixoto.geojson` only (already merges there).
One new field, no new raw-file read — reuses the same per-(year, cargo,
local) grouping `07` already computes for the top-3 ranking.

`psd.geojson` does **not** get this field. PSD's base feature aggregates
votes across multiple cargos per year (a Vereador slate and a Prefeito
candidate summed together) — there's no single well-defined "total valid
votes for this race" for a multi-cargo aggregate. Vote share is scoped to
individual candidates with one specific cargo, so it applies inside the
PSD breakdown (each entry has its own cargo, computed by `08` alongside
the per-cargo total it already needs for ranking), not on PSD's base
popup.

**⚠️ Execution order ≠ script number.** `08` must run after `05` (it
merges PSD breakdown onto `psd.geojson`, which `05` produces) but before
`06` (which consumes the matrix `08` builds). Actual pipeline order:

```
01 → 02 → 03 → 04 → 05 → 08 → 06 → 07
```

Confirmed with the user: document this explicitly in the README's
pipeline list rather than renumber any script.

### 3. Frontend Changes (`app-web/`)

- **`PopupContent.jsx`** — replace the single "Candidato/Partido" row with
  `Nome · Partido · Cargo pretendido · Votos · % share`. Vote share is
  computed client-side (`QT_VOTOS / total_votos_validos * 100`), not
  precomputed server-side — a one-line division, no reason to duplicate it
  in the pipeline.
- **`candidacy_status` handling** — both `PopupContent` and
  `DeltaPopupContent` check `candidacy_status`/null delta fields first and
  render "N/A (não concorreu)" or "N/A (partido inexistente)" instead of
  passing a null through `formatSigned`.
- **PSD's base popup is otherwise unchanged** — still party name, year,
  aggregate votes, seções. "Cargo pretendido" and "% share" don't apply to
  a multi-cargo aggregate feature, so the `Nome · Partido · Cargo
  pretendido · Votos · % share` redesign above applies to Hugo/Felipe only.
- **New `PsdBreakdownSection` component** — PSD popups currently show
  almost nothing beyond that (PSD isn't in `COMPETITOR_LAYER_BY_METRIC`,
  so no competitor section renders either). New component, same
  collapsible `<details>` pattern as the existing `CompetitorSection`,
  showing candidate count, top-3 by votes with their cargo, each entry's
  own vote share against its cargo's valid-vote total (computed by `08`
  alongside the per-cargo total it already needs for ranking), and the
  per-cargo volume split.
- **Legend fix** — `electionType()` in `lib/format.js` returns `'Geral'`
  instead of `'Federal'` at the source. This cascades through the CSS
  class (`.year-btn.federal` → `.year-btn.geral`) and the delta popup's
  "Tipo de eleição" line for free, since both already just consume this
  function's return value — a mechanical rename, not a new decision point.
- **`StatsPanel.jsx` correctness fix** — the Ganhos/Perdas/Saldo
  aggregation currently does `Number(f.properties[metric.field]) || 0`,
  which would silently coerce a new `null` delta to `0` — exactly the bug
  class this spec exists to eliminate. Must filter N/A rows out of the sum
  entirely, not coerce them.

### 4. Testing Strategy

Same split established in this project: pytest for the pipeline,
Vitest/RTL for the frontend.

**Pipeline — two areas need real rigor, not just transcription:**
- **Pair enumeration (nearest-matching-cycle)** is genuinely new logic.
  Tests needed: multiple gaps, a candidate with only one candidacy ever
  (zero pairs), `tipo_eleicao` buckets never crossing, and the two
  concrete regressions named in the original request as explicit test
  cases — Felipe's 2024 delta must be `null`/`nao_concorreu` (not
  `-6919`), PSD's 2010 delta must be `null`/`partido_inexistente` (not `0`).
- **PSD breakdown ranking** — a direct test recreating the 2012→2016
  example: a Prefeito candidate present with volume in 2012, absent in
  2016, confirming the breakdown surfaces that candidate by name and cargo
  rather than just the unexplained aggregate drop.

**Frontend:** N/A rendering in `PopupContent`/`DeltaPopupContent`, the new
`PsdBreakdownSection`, and a regression test for `StatsPanel`'s
null-filtering fix — written the same way as the pipeline test: assert a
null delta is excluded from Ganhos/Perdas, not coerced to 0.
