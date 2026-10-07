# Zonas com Potencial — Implementation Brief

Handoff spec for a new feature, not a visual pass. Read fully before touching code —
the methodology decisions below are settled (confirmed with the project owner); do
not re-derive or substitute a different approach.

## What this is

A ranked list of locais de votação where Hugo currently underperforms but whose
electorate composition resembles the locais where he's strongest — demographic
lookalike targeting. It answers "where does Hugo's existing base profile also
exist, but he hasn't captured it yet," not "who will vote for Hugo."

This was deliberately out of scope for the earlier redesign work
(`design_direction.md` §7 calls it a "reserved future feature") and is now being
built for real.

## Framing discipline — non-negotiable, carried from the rest of the project

This ranks **locais by how similar their registered electorate's composition is**
to Hugo's stronghold locais. It does **not** identify individual voters, predict
votes, or claim causation. Every label, popup, and legend for this layer must
read as composition-similarity, never as "provável eleitor de Hugo" or
"eleitores potenciais." Reuse the exact disclaimer pattern already used for the
Perfil layer (`app-web/src/components/ProfileSection.jsx`): state it prominently,
not buried behind a disclosure toggle.

Suggested label for the layer/legend: **"Similaridade de composição com as
bases de Hugo"** — composition similarity, not a prediction.

## Data sources (all already exist — no new raw TSE processing)

- `data/geo/hugo_leal.geojson` — per (nr_local, ano): `QT_VOTOS`, `total_votos_validos`
  (→ `pct_share = QT_VOTOS / total_votos_validos * 100`), and the demographic fields
  below, already merged onto this file by `scripts/09_voter_profile_geojson.py`.
- Demographic vector fields (already present on every local, every year):
  `pct_mulheres`, `pct_jovens_16_24`, `pct_adultos_25_59`, `pct_60_mais`,
  `pct_ate_fundamental`, `pct_ensino_medio`, `pct_ensino_superior`.
  (Skip `pct_homens`, `pct_genero_nao_informado`, `pct_idade_nao_informado`,
  `pct_escolaridade_nao_informado` — redundant with the above or near-zero noise,
  same reasoning as the earlier `answer.md` metric-curation pass.)

## Methodology (confirmed, implement exactly this)

1. **Year:** use Hugo's most recent election year present in the data (2022,
   `DEPUTADO FEDERAL`) — "potential" should reflect current targeting opportunity,
   not a historical snapshot. Pull this from `config.HUGO_LEAL["elections"]`
   (already sorted; take the max year) rather than hardcoding `2022`.
2. **Strongholds:** locais in the top quartile by `pct_share` that year (i.e.
   `pct_share >= locais["pct_share"].quantile(0.75)`).
3. **Stronghold profile:** the mean of the 7-field demographic vector across the
   stronghold locais — one centroid vector.
4. **Candidate pool:** locais **below the median** `pct_share` that year (excludes
   the strongholds themselves and the solid-but-not-top middle tier — this is
   about surfacing genuinely underexploited locais, not re-ranking the whole city).
5. **Similarity score:** for each candidate-pool local, plain Euclidean distance
   between its 7-field vector and the stronghold centroid (all 7 fields are
   already 0–100 percentages, so no additional normalization/z-scoring is needed
   — don't add it, it's unjustified complexity for same-scale features).
   Convert distance to a similarity score for display: `similarity = 100 - distance`
   is fine as a relative ranking aid; do not present it as a percentage probability
   of anything.
6. **Output:** rank ascending by distance (most similar first), keep the top 20.
   Ties broken by lower `pct_share` first (bigger untapped gap ranks higher).

## Pipeline script

Create `scripts/10_potential_locations.py`, following the existing conventions
(see `scripts/09_voter_profile_geojson.py` for the shape to match: module
docstring explaining intent, `sys.path.insert` + `from config import ...` +
`from _pipeline_utils import ...` at the top, small pure helper functions, a
`main()` guarded by `if __name__ == "__main__":`, prints progress with row
counts, writes with `encoding="utf-8"`).

- Read `data/geo/hugo_leal.geojson` for Hugo's target year (per Methodology
  step 1).
- Output `data/geo/potential_hugo.geojson` — Point features (reuse `lat`/`lon`
  already on each local via `_pipeline_utils.load_local_info`), properties:
  `nr_local, nm_local, bairro, ano, pct_share, similarity_score, rank`
  (1-indexed, 1 = most similar).
- Also rebuild `app/data.js` via `_pipeline_utils.rebuild_data_js`, adding
  `"potential_hugo"` to the `layers` list passed in (mirrors how every other
  layer gets published).
- Add a focused test `tests/test_potential_locations.py` (pytest, matching the
  existing test files' style) covering: centroid computed only from top-quartile
  locais, candidate pool excludes locais at/above median, output ranked
  ascending by distance, top-20 cap enforced.

## Frontend

- New `app-web/src/components/PotentialLayer.jsx`, modeled directly on
  `ProfileLayer.jsx` (same `CircleMarker` + `Popup` shape) — radius can be fixed
  (this isn't a magnitude encoding, it's a ranked list) or scaled inversely by
  `rank` (top-ranked locais slightly larger); color from a **new, distinct**
  sequential scale — do not reuse the existing indigo profile-concentration
  scale or any candidate/delta color, this is a fourth, independent signal.
  Add `potentialAccent` (single accent color, not a full ramp — a plain
  "highlighted marker" treatment is enough for a ranked list, no need for a
  5-stop gradient) to `COLORS` in `lib/constants.js`, picked from an unused hue
  family (everything already used: Hugo violet ~262°, Felipe teal-green ~155°,
  PSD navy ~204°/olive ~73°/orange ~25°, delta red~0°/teal~175°, profile
  indigo~243°. A muted rose/magenta ~330-340° is the largest remaining open gap
  — e.g. `#A6396B` was already vetted as safe in an earlier palette pass and
  never assigned; reuse that exact hex rather than picking a new one.)
- New `PotentialPopupContent.jsx` (or extend `PopupContent.jsx` if the shape
  ends up trivial) showing: local name/bairro, rank, `pct_share` (Hugo's actual
  current share there — the "underexploited" evidence), and the composition-
  similarity disclaimer from the Framing section above. Do **not** show a raw
  "similarity_score" number as the headline — rank is more legible than a
  distance-derived score with no natural units; keep the score available but
  secondary.
- Wire into `App.jsx`'s Camadas toggle group as a fourth layer (`toggles.potential`),
  same pattern as `toggles.profile` — a checkbox row with dot + count, not a new
  top-level nav item. This was the explicit placement call already made in
  `design_direction.md` §7.
- List view: reuse the grouped-horizontal-bar pattern from `design_direction.md`
  §1 (rank order, single comparable metric per row — `pct_share` as the bar
  length) rather than inventing a new chart form. This can be a simple ranked
  list inside the panel section, doesn't need to be a separate route/view.

## Explicitly out of scope for this pass

- Felipe/PSD potential-locations equivalents — Hugo only, for now.
- Any visual styling beyond making the layer functionally distinguishable
  (the CSS consolidation pass covers real polish separately — see the note in
  commit `f348046`).
- Changing the methodology based on results that "look wrong" — if the ranked
  list looks surprising, that's a finding to report back, not a reason to
  silently swap in a different similarity metric or year.
