# LEAL — Electoral Mapping Project

Mapping votes for **Hugo Leal** (dep. federal, PSD-RJ) and **Felipe Peixoto** (PSD, Niterói)
by seção eleitoral in Niterói across multiple election cycles.

## Candidates

### Hugo Leal (main)
| Year | Office          | Party | Votes   |
|------|-----------------|-------|---------|
| 2022 | Dep. Federal    | PSD   | 50,067  |
| 2018 | Dep. Federal    | PSD   | 63,561  |
| 2014 | Dep. Federal    | PROS  | 85,449  |
| 2010 | Dep. Federal    | PSC   | 98,164  |

### Felipe Peixoto (partner)
| Year | Office          | Party | Votes   |
|------|-----------------|-------|---------|
| 2024 | TBD             | PSD   | TBD     |
| 2022 | Dep. Estadual?  | PSD   | TBD     |
| 2020 | Prefeito?       | PSD   | TBD     |
| 2018 | TBD             | PSD   | TBD     |

### PSD party-wide (Niterói)
Track all PSD candidates across elections to see the party's territorial footprint.

## Data Sources

- **TSE Portal de Dados Abertos**: dadosabertos.tse.jus.br
  - Votação por seção eleitoral (votes by polling section)
  - Perfil do eleitorado (voter demographics by section)
  - Candidatos (candidate metadata)
- **Locais de votação**: TSE or TRE-RJ (polling place addresses for geocoding)

## Elections Covered

| Year | Type      | Relevance                                    |
|------|-----------|----------------------------------------------|
| 2024 | Municipal | Felipe Peixoto, PSD vereadores               |
| 2022 | Geral     | Hugo Leal (dep. fed.), Felipe (dep. est.?)    |
| 2020 | Municipal | Felipe Peixoto (prefeito?), PSD vereadores    |
| 2018 | Geral     | Hugo Leal (dep. fed.), PSD                    |
| 2016 | Municipal | Felipe Peixoto, PSD vereadores               |
| 2014 | Geral     | Hugo Leal (PROS), PSD                         |
| 2012 | Municipal | Felipe Peixoto, PSD vereadores               |

## Pipeline

1. `scripts/01_download_tse.py` — download raw CSVs from TSE
2. `scripts/02_process_votes.py` — filter to Niterói, extract candidate/party votes by seção
3. `scripts/03_geocode_locais.py` — geocode polling places (locais de votação)
4. `scripts/04_voter_profile.py` — voter demographics by seção
5. `scripts/05_build_geojson.py` — merge votes + coordinates + demographics → GeoJSON
6. `scripts/06_build_vote_deltas.py` — compute vote deltas per local de votação between each candidate's nearest-matching election cycle of the same type (not necessarily consecutive calendar years) (and seção-level churn diagnostics)
7. `scripts/07_top_competitors.py` — rank the top-3 competing candidates (excluding Hugo/Felipe) per local, year, and cargo
8. `scripts/08_candidacy_matrix.py` — download TSE candidate-registration files (`consulta_cand`), build a candidacy matrix confirming which years Hugo Leal, Felipe Peixoto, and PSD actually ran (and for which cargo/election type), and build the PSD slate breakdown
9. `scripts/09_voter_profile_geojson.py` — aggregate voter demographics
   (from `04`'s seção-grain output) up to local de votação grain, compute
   11 demographic share fields across gender/age/education, and write
   `voter_profile.geojson` plus merge the same fields onto
   `hugo_leal.geojson`/`felipe_peixoto.geojson`/`psd.geojson`
10. `app/` — web map (Leaflet) for visualization

**Execution order note:** despite the filename numbering, `08` must run *after* `05` (it merges the PSD slate breakdown onto `psd.geojson`, which `05` produces) and *before* `06` (which reads the candidacy matrix `08` builds, to gate vote deltas to years with confirmed candidacies). `09` also runs after `05` (it merges demographic fields onto the same candidate geojson files) but has no dependency relationship with `08` or `06`/`07` in either direction — it's placed after `08` here simply to keep the two "runs after 05, merges additional fields onto already-built geojson" scripts grouped together. The real run order is:

```
01 → 02 → 03 → 04 → 05 → 08 → 09 → 06 → 07
```

## Delta Outputs

`scripts/06_build_vote_deltas.py` writes:

- `data/processed/vote_deltas_by_local.csv`
- `data/processed/vote_deltas_by_secao.csv`
- `data/geo/vote_deltas.geojson`
- `data/geo/vote_deltas_secao.geojson`
- `app/data.js`

The local layer is intended for the Leaflet map. The section layer is a diagnostic output for checking section moves between polling places.

A vote/delta pair between two years is only computed when the candidate (Hugo, Felipe, or PSD) has a confirmed candidacy — per the candidacy matrix built by `08_candidacy_matrix.py` — in *both* years, and those years are the same election type (`Geral` or `Municipal` — `Geral` is the code/data value; it's colloquially what people call a "Federal" election). Otherwise the vote/delta fields are `null` (not `0`), and a `candidacy_status_hugo`/`candidacy_status_felipe`/`candidacy_status_psd` field explains why:

- `concorreu` — ran in both years; delta computed
- `nao_concorreu` — did not run in either compared year
- `nao_concorreu_inicio` / `nao_concorreu_fim` — did not run in the earlier / later year of the pair
- `tipo_incompativel` — the two years are different election types (e.g. comparing a Geral year to a Municipal year), so a delta isn't meaningful
- `partido_inexistente` — the party (PSD) didn't exist yet in the compared year (PSD was founded in 2011) — distinct from `nao_concorreu`, which means the party/candidate existed but chose not to run that cycle

## Competitor Outputs

`scripts/07_top_competitors.py` re-reads the raw TSE files (which `02_process_votes.py` filters down to only Hugo/Felipe/PSD, discarding everyone else) and writes `top1_nome`/`top1_partido`/`top1_votos` through `top3_*` properties directly onto the existing `data/geo/hugo_leal.geojson` and `data/geo/felipe_peixoto.geojson` features — the top-3 candidates for that cargo at that local and year, excluding Hugo and Felipe themselves. It also writes a `total_votos_validos` field — the total valid votes cast at that local for that cargo, including Hugo's/Felipe's own votes and voto de legenda (party-list votes on proportional cargos), and excluding only voto branco/nulo — so callers can compute vote shares consistent with TSE's own denominator. Also rebuilds `app/data.js`.

## Candidacy Matrix

`scripts/08_candidacy_matrix.py` downloads TSE candidate-registration files (`consulta_cand`) and writes `data/processed/candidacy_matrix.csv`, one row per candidate per year: `candidate_key`, `ano`, `cargo`, `tipo_eleicao`, `partido`, `situacao_candidatura`. It cross-references this against the `HUGO_LEAL`/`FELIPE_PEIXOTO` election dicts in `config.py` and prints a `[WARN]` when they disagree — the matrix, built from TSE's own candidate registry, is authoritative over the hardcoded config.

It also builds the PSD slate breakdown (which PSD candidates ran, and the top-3 by votes, per polling location and year) and merges these fields onto `data/geo/psd.geojson`:

- `psd_candidate_count` — number of PSD candidates who ran at that local/year, across all cargos (Prefeito, Vereador, etc. combined) — the same value is stamped on every feature at that local regardless of its own cargo
- `psd_top1_nome` / `psd_top1_cargo` / `psd_top1_votos` / `psd_top1_share` (and `top2`/`top3`) — the top-3 PSD candidates by votes
- `psd_total_por_cargo` — total PSD votes at that local/year, broken down by cargo

Separately, `scripts/05_build_geojson.py` adds a `cargo` field (sourced from `config.py`) to every `hugo_leal.geojson`/`felipe_peixoto.geojson` feature. This field is not present on `psd.geojson`.

## Voter Profile

`scripts/09_voter_profile_geojson.py` aggregates `scripts/04_voter_profile.py`'s seção-grain demographics up to local de votação grain and collapses TSE's raw category columns into 11 mutually-exclusive share fields (percent of that local's electorate) across three dimensions:

- **Gender** — `pct_mulheres` (`gen__feminino`), `pct_homens` (`gen__masculino`), `pct_genero_nao_informado` (`gen__nao informado`)
- **Age** — `pct_jovens_16_24` (16-24), `pct_adultos_25_59` (25-59), `pct_60_mais` (60+), `pct_idade_nao_informado` (`fai__invalido`/`fai__invalida`, the same category under two raw TSE labels)
- **Education** — `pct_ate_fundamental` (illiterate through ensino fundamental, complete or not), `pct_ensino_medio` (ensino médio, complete or not), `pct_ensino_superior` (superior, complete or not), `pct_escolaridade_nao_informado` (`gra__nao informado`)

Shares are computed from summed raw counts (not averaged pre-rounded percentages) to avoid compounding rounding error. Raça/Cor was investigated and deliberately excluded — structurally unpopulated in TSE's Niterói data across the whole dataset (100% "#NE"/not-informed 2010-2022, 93%+ not-informed even in 2024) — see `docs/voter_profile_backbone.md` for the full investigation.

`data/geo/voter_profile.geojson` is the standalone layer (used by the map's "Perfil do Eleitorado" toggle); the same 11 fields are also merged directly onto `hugo_leal.geojson`/`felipe_peixoto.geojson`/`psd.geojson` (used by the popup breakdown).

## Tech Stack

- Python 3.11+ (pandas, geopandas, requests)
- Leaflet.js for web maps
- GeoJSON as interchange format
