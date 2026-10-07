# Voter Profile Data Backbone — Investigation Report

Investigation only — no pipeline code was modified.

## 1. What `scripts/04_voter_profile.py` does

**Raw input:** TSE's `perfil_eleitor_secao` files — one national-scope zip per election year, pre-filtered to RJ state at download time (`perfil_eleitor_secao_{year}_RJ.csv`, per `config.py::url_perfil_eleitor_secao`). The script itself filters these RJ-wide files down to Niterói by `NM_MUNICIPIO`.

**Geographic grain:** **zona + seção**, not local de votação. `GROUP_COLS = ["NR_ZONA", "NR_SECAO"]`, combined with `ano`. Note the raw file *does* carry `NR_LOCAL_VOTACAO`/`NM_LOCAL_VOTACAO` columns (TSE ships this for every year checked, 2010 and 2022), but `04` never reads or aggregates by them — it discards that finer join path and stays at zona+seção.

**Per-year:** yes. The script loops `for year in ALL_YEARS`, processes each year's file independently (skipping years whose raw folder is absent), and concatenates all years into one combined output. Each output row is scoped to a single `ano`.

**Demographic columns extracted** (from `DEMO_COLS`), each pivoted into one-hot count columns prefixed by a 3-letter code:
- `DS_GENERO` → `gen__*` (feminino, masculino, nao informado)
- `DS_FAIXA_ETARIA` → `fai__*` (age brackets, e.g. `fai__21 a 24 anos`, plus an `invalido`/`invalida` bucket — see data-quality note below)
- `DS_GRAU_ESCOLARIDADE` → `gra__*` (education level: analfabeto, ensino fundamental/médio, superior, etc.)
- `DS_RACA_COR` → `rac__*` (race/color: branca, preta, parda, amarela, indígena, nao informado)
- `DS_ESTADO_CIVIL` → `est__*` (marital status)

**Output:** `data/processed/voter_profile_by_secao.csv` — **this file already exists on disk** (generated 2026-08-10, 10,083 data rows). Schema, confirmed from the real file header:

```
NR_ZONA, NR_SECAO, ano, total_eleitores,
gen__feminino, gen__masculino, gen__nao informado,
fai__16 anos ... fai__100 anos ou mais, fai__invalido, fai__invalida,
gra__analfabeto, gra__ensino fundamental completo, ... , gra__superior completo, gra__superior incompleto,
rac__branca, rac__preta, rac__parda, rac__amarela, rac__indigena, rac__nao informado, rac__#ne,
est__casado, est__divorciado, est__separado judicialmente, est__solteiro, est__viuvo, est__nao informado
```

**Data-quality notes spotted while reading the output** (not fixed, just flagged for planning):
- `fai__invalido` and `fai__invalida` appear as two separate near-duplicate columns — almost certainly a gender-agreement inconsistency in TSE's raw category label across different years that the script's per-value normalization doesn't merge.
- `rac__#ne` — an odd literal column name, likely from an unnormalized raw code (e.g. `#NE#` or similar) in one year's file.
- Neither breaks the pipeline; both would need cleanup if this data goes user-facing.

## 2. Downstream usage — dormant/orphaned

**Confirmed: `voter_profile_by_secao.csv` is never read anywhere else in the codebase.** Grepped `scripts/`, `app-web/src/`, and the repo root for `voter_profile`, `perfil_eleitor`, `demographic`, `DEMO_COLS`, and `total_eleitores` — the only hits are inside `04_voter_profile.py` itself and its own download step in `01_download_tse.py`/`config.py`.

Specifically:
- `scripts/05_build_geojson.py`'s **module docstring** claims: *"Merge votes + geocoded locations + voter profiles into GeoJSON for the web map."* This is aspirational/stale — the actual `main()` only loads `hugo_leal_by_secao.csv`, `felipe_peixoto_by_secao.csv`, `psd_by_secao.csv`, and `locais_votacao_niteroi.csv`. It never opens `voter_profile_by_secao.csv`. No demographic field ever reaches any `.geojson` file.
- `README.md`'s pipeline list (step 4) similarly describes `04_voter_profile.py` as feeding "demographics" into step 5's merge — same stale claim, not what the code does.
- `scripts/06_build_vote_deltas.py`, `scripts/07_top_competitors.py`, and every `app-web/src/` component: zero references.

So the demographic backbone is fully built and sitting in `data/processed/`, but nothing downstream consumes it. It's a dormant/orphaned dataset today, not a partially-wired one — there's no half-finished merge code to work around, just a clean gap.

## 3. Join key

**The real, usable join key is `(ano, NR_ZONA, NR_SECAO)`.**

Confirmed directly from both files' actual headers:
- `voter_profile_by_secao.csv`: `NR_ZONA, NR_SECAO, ano, ...`
- `hugo_leal_by_secao.csv` (and presumably `felipe_peixoto_by_secao.csv`/`psd_by_secao.csv`, same code path in `02_process_votes.py::aggregate_by_secao`): `ano, NR_ZONA, NR_SECAO, NR_TURNO, QT_VOTOS, label, NR_LOCAL_VOTACAO, ...`

Both are plain integer-valued columns with matching names — **no grain mismatch, no transformation needed to join them.** A direct `merge(on=["ano", "NR_ZONA", "NR_SECAO"])` works today.

One wrinkle to plan around: the vote data can carry a `NR_TURNO` column (present when a race went to a runoff — second-round Prefeito elections in municipal years) with one row per turno, while the profile data has a single row per `(ano, NR_ZONA, NR_SECAO)` regardless of turno. A join would need to either drop/ignore `NR_TURNO` on the vote side first, or treat the profile row as turno-invariant (which is factually correct — the electorate's demographic composition doesn't change between rounds).

**A finer join is also possible but not what `04` currently produces.** Both the raw perfil files and the raw vote files carry `NR_LOCAL_VOTACAO` for every year checked (2010 and 2022 both have it) — so a local-de-votação-level profile (matching the grain `05_build_geojson.py` actually maps to points) is achievable from the same raw data, but would require re-aggregating `04`'s logic by `NR_LOCAL_VOTACAO` instead of `NR_ZONA`+`NR_SECAO`, or aggregating the current seção-level output up to local afterward (using the same `nr_local` lookup `05` builds from `locais_votacao_niteroi.csv`).

## 4. Raw `perfil_eleitor_secao` files on disk

All 8 election years are present under `data/raw/`, matching the same even-year cadence as `votacao_secao`:

| Year | Folder | File | Size |
|---|---|---|---|
| 2010 | `perfil_eleitor_secao_2010/` | `perfil_eleitor_secao_2010_RJ.csv` | ~1.1 GB |
| 2012 | `perfil_eleitor_secao_2012/` | `perfil_eleitor_secao_2012_RJ.csv` | present |
| 2014 | `perfil_eleitor_secao_2014/` | `perfil_eleitor_secao_2014_RJ.csv` | present |
| 2016 | `perfil_eleitor_secao_2016/` | `perfil_eleitor_secao_2016_RJ.csv` | present |
| 2018 | `perfil_eleitor_secao_2018/` | `perfil_eleitor_secao_2018_RJ.csv` | present |
| 2020 | `perfil_eleitor_secao_2020/` | `perfil_eleitor_secao_2020_RJ.csv` | present |
| 2022 | `perfil_eleitor_secao_2022/` | `perfil_eleitor_secao_2022_RJ.csv` | ~1.5 GB |
| 2024 | `perfil_eleitor_secao_2024/` | `perfil_eleitor_secao_2024_RJ.csv` | present |

Format: semicolon-delimited CSV (`;`), one `leiame.pdf` (TSE's readme) alongside each. Each is RJ-state-wide, not pre-filtered to Niterói — `04_voter_profile.py` does that filtering itself, same pattern as `02_process_votes.py` does for `votacao_secao`. Real header (identical across 2010 and 2022, the two years checked directly):

```
DT_GERACAO, HH_GERACAO, ANO_ELEICAO, SG_UF, CD_MUNICIPIO, NM_MUNICIPIO,
NR_ZONA, NR_SECAO, NR_LOCAL_VOTACAO, NM_LOCAL_VOTACAO,
CD_GENERO, DS_GENERO, CD_ESTADO_CIVIL, DS_ESTADO_CIVIL,
CD_FAIXA_ETARIA, DS_FAIXA_ETARIA, CD_GRAU_ESCOLARIDADE, DS_GRAU_ESCOLARIDADE,
CD_RACA_COR, DS_RACA_COR, CD_IDENTIDADE_GENERO, DS_IDENTIDADE_GENERO,
CD_QUILOMBOLA, DS_QUILOMBOLA, CD_INTERPRETE_LIBRAS, DS_INTERPRETE_LIBRAS,
TP_OBRIGATORIEDADE_VOTO, QT_ELEITORES_PERFIL, QT_ELEITORES_BIOMETRIA,
QT_ELEITORES_DEFICIENCIA, QT_ELEITORES_INC_NM_SOCIAL
```

Three columns TSE ships that `04_voter_profile.py` doesn't currently extract, worth knowing about for future planning: `DS_IDENTIDADE_GENERO`, `DS_QUILOMBOLA`, `DS_INTERPRETE_LIBRAS` (gender identity, quilombola self-identification, Libras interpreter need) — plus `QT_ELEITORES_BIOMETRIA`/`QT_ELEITORES_DEFICIENCIA`/`QT_ELEITORES_INC_NM_SOCIAL` (biometric registration, disability, social-name inclusion counts).

## Summary

- `04_voter_profile.py` is a complete, working, per-year extraction of Niterói voter demographics at **zona+seção** grain, already run and sitting at `data/processed/voter_profile_by_secao.csv` (10,083 rows).
- It is **fully orphaned** — no downstream script or frontend component reads it, despite `05`'s docstring and the README both claiming otherwise.
- The join to vote data is **clean and direct**: `(ano, NR_ZONA, NR_SECAO)`, same column names, same types, on both sides — no grain mismatch. `NR_TURNO` on the vote side is the only wrinkle (profile data is turno-invariant).
- All 8 raw `perfil_eleitor_secao` years (2010–2024) are present and correctly formatted; the real header includes several demographic fields not yet extracted.
