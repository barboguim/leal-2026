# Top Competitors per Local — Design Spec

**Date:** 2026-08-11
**Status:** Approved, not yet implemented

## Context

LEAL currently ships `scripts/06_build_vote_deltas.py`, which computes vote
deltas between consecutive election pairs per local de votação and flags a
"migration signal" guessing whether Hugo Leal's vote losses correspond to
Felipe Peixoto or PSD gains at the same local (`mig_signal`, `mig_score`,
etc.). That framing is being dropped.

The actual question is: **at a given local (and year), who besides Hugo and
Felipe got the most votes?** This reframes the analysis from "did our guy's
votes migrate to our other guy" to "who is actually winning this territory,"
which is the basis for later storytelling about who is beating them and
where.

This is the first of three planned sub-projects on LEAL:
1. **This spec** — replace the migration signal with a top-competitors
   analysis.
2. Voter-profile overlay (age/gender/schooling) as a toggleable map layer.
3. UI overhaul with a storytelling/conclusions tab.

Only (1) is designed here.

## Scope

### In scope
- New script `scripts/07_top_competitors.py` producing top-3 competitor
  data per `(year, cargo, local)`, merged onto the existing
  `hugo_leal.geojson` / `felipe_peixoto.geojson` features.
- Removal of the migration-signal fields and logic from
  `scripts/06_build_vote_deltas.py`.
- A collapsible "Concorrência" section in the map popup showing the top-3.

### Out of scope (deferred to later sub-projects or not planned)
- Seção-level competitor breakdown (local-level only, matching the existing
  popup granularity).
- Political-spectrum/ideology labeling of competitors (name + party + votes
  only — no left/right classification to build or maintain).
- The storytelling tab itself (sub-project 3). This spec produces the data
  it will eventually draw on, but does not build the tab.
- Felipe's 2024 data (not currently extracted at all — pre-existing gap,
  unrelated to this change).

## Design

### 1. Competitor ranking rules

For each `(year, cargo, local)` where Hugo or Felipe personally ran that
cargo that year (per the existing `elections` dicts in `config.py`):

- Pull all candidate-level votes for that cargo, in Niterói, at that local,
  from the raw `votacao_secao_{year}` file (not the pre-filtered
  Hugo/Felipe/PSD extracts from `02_process_votes.py`, which discard
  everyone else).
- Exclude non-candidate rows (voto branco, voto nulo, legenda-only votes).
- Exclude **both** Hugo Leal and Felipe Peixoto from the candidate pool,
  regardless of which of their features the result will be attached to.
- Rank the remainder by `QT_VOTOS` descending; keep the top 3
  (`nome`, `partido`, `votos`).

**Shared-cargo years:** when Hugo and Felipe ran the same cargo in the same
year (2022: both Deputado Federal), compute the ranking once per
`(year, cargo, local)` rather than once per person. The same top-3 list is
attached to both `hugo_leal.geojson` and `felipe_peixoto.geojson` for that
year — this avoids duplicate computation and avoids either of them
appearing as a "competitor" to the other. In years where they ran different
cargos, this rule has no effect (each gets their own single ranking as
before).

No minimum-vote threshold — always show the literal top 3, even at small
locais.

### 2. New script: `scripts/07_top_competitors.py`

Runs after `05_build_geojson.py` (needs its local-level GeoJSON as the base
to enrich) and independently of `06` (no shared state).

- Reads raw `votacao_secao_{year}` files in chunks, same encoding-fallback
  and chunked-read helpers already used in `06` (`read_tse_chunks_safe`
  pattern) — reused rather than duplicated.
- Filters to Niterói + the relevant cargo(s) per year, aggregates candidate
  votes to `nr_local` using the same `NR_LOCAL_VOTACAO` join used elsewhere
  in the pipeline.
- Applies the shared-cargo dedup rule above.
- Writes the top-3 fields as new properties directly onto the matching
  features in `hugo_leal.geojson` and `felipe_peixoto.geojson`:
  `top1_nome`, `top1_partido`, `top1_votos`, `top2_nome`, `top2_partido`,
  `top2_votos`, `top3_nome`, `top3_partido`, `top3_votos`. Missing slots
  (fewer than 3 other candidates ran) are `null`.
- No new GeoJSON file, no new layer to wire into the map.
- Rebuilds `app/data.js` at the end (reuses the same rebuild logic as `06`)
  so the app reflects the enriched features.

### 3. Script 06 cleanup

Remove entirely, since the migration-signal framing is replaced:
- `migration_score()` function
- `MIN_SIGNAL_VOTES` constant
- Fields: `hugo_perda`, `felipe_ganho`, `psd_ganho`,
  `mig_hugo_felipe_votos`, `mig_hugo_psd_votos`, `mig_hugo_felipe_score`,
  `mig_hugo_psd_score`, `mig_alvo`, `mig_score`,
  `mig_votos_correspondentes`, `mig_signal`

Keep everything else unchanged:
- `votos_{hugo,felipe,psd}_{inicio,fim}`, `delta_{hugo,felipe,psd}`,
  `pct_delta_{hugo,felipe,psd}` — still shown in the popup as
  before/after/delta rows.
- `map_delta` / `map_abs_delta` — these are just `delta_hugo` restated for
  the diverging color scale (green=gained/red=lost); unrelated to the
  migration guess and still needed.
- Seção-churn fields (`secao_status`, `secoes_comuns`, `secao_churn`,
  `secoes_movidas_in/out`, `secao_moved`) — this is a real structural
  signal (seções moving between locais between elections), not a guess,
  and stays as-is.

### 4. UI changes (`app/index.html`)

- In `buildDeltaPopup`: remove the `Leitura` and `Força da leitura` rows
  and the now-unused `humanSignal()` function.
- Add a collapsible `▸ Concorrência` section (collapsed by default, click
  to expand) to both `buildPopup` (plain vote layer) and `buildDeltaPopup`
  (delta layer), showing the top-3 for that local/year, pulled from the
  `topN_nome/partido/votos` properties on the matching
  `hugo_leal.geojson`/`felipe_peixoto.geojson` feature. Collapsed by
  default keeps the popup's default height unchanged — this was a direct
  response to the popup already being dense (10 rows in the delta view)
  before adding anything.
- Vanilla Leaflet/vanilla JS only — no frameworks, per existing project
  constraint.

## Data flow summary

```
raw votacao_secao_{year}.csv
        |
        +--> 02_process_votes.py --> hugo/felipe/psd_by_secao.csv --> 05 --> hugo_leal.geojson / felipe_peixoto.geojson
        |                                                                          ^
        +--> 07_top_competitors.py (reads raw again, ranks by cargo) -------------+
                                                                                   |
                                                                                   v
                                                                          app/data.js (rebuilt)
```

`06_build_vote_deltas.py` continues to run independently, producing
`vote_deltas_by_local.csv` / `vote_deltas_secao.geojson` with the
migration-signal fields removed.

## Testing / verification

- Spot-check 2022 (shared Hugo/Felipe cargo) at a handful of locais: confirm
  `hugo_leal.geojson` and `felipe_peixoto.geojson` carry identical top-3 for
  that year, and neither Hugo nor Felipe appear in their own top-3.
- Spot-check a year where they ran different cargos (e.g. 2018: Hugo Dep.
  Federal, Felipe Dep. Estadual): confirm the two rankings differ and each
  excludes only the relevant person's own cargo pool (not cross-cargo
  exclusion of the other).
- Confirm voto branco/nulo/legenda rows never appear in `topN_nome`.
- Visual check in the map: popup opens with the same height as before this
  change (Concorrência collapsed), and expands correctly on click.

## Open items for later sub-projects (not blocking this spec)

- Sub-project 2 (voter-profile overlay) and sub-project 3 (storytelling
  tab) are separate specs, not covered here.
- README.md's `TBD` placeholders in the Felipe Peixoto candidate table
  should get cleaned up at some point, but that's a docs fix, not part of
  this design.
