# Voter Profile Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill the "Perfil do Eleitorado" CAMADAS slot with a working demographic-context overlay (`ProfileLayer`) and a popup breakdown on all three marker types, built on 11 verified, mutually-exclusive TSE fields across Gênero/Faixa etária/Escolaridade (Raça/Cor cut entirely — confirmed structurally unpopulated in TSE's Niterói data for the whole 2010-2024 span).

**Architecture:** New pipeline script `09_voter_profile_geojson.py` aggregates `04`'s seção-grain output up to local-de-votação grain and computes the 11 fields, emitting a standalone `voter_profile.geojson` (feeds `ProfileLayer`) plus merging the same fields onto `hugo_leal.geojson`/`felipe_peixoto.geojson`/`psd.geojson` (feeds the popup). A shared-code refactor moves reusable geojson/roster helpers out of `06_build_vote_deltas.py` into `_pipeline_utils.py` first, so `09` doesn't duplicate or rebuild them. Frontend mirrors the existing `DeltaLayer`/`DeltaMetricFilter` pattern but with a neutral sequential color scale (not the diverging red/green one) and framing-safe copy baked into a single shared `ProfileSection` component used everywhere the breakdown appears.

**Tech Stack:** Python 3.11+ (pandas), React + react-leaflet, Vitest + React Testing Library.

## Global Constraints

- Aggregation grain: `(ano, nr_local)` — matches everything else the map already renders. No seção-level rendering anywhere in this feature.
- 11 fields total, 3 dimensions (Gênero: 3, Faixa etária: 4, Escolaridade: 4), each dimension mutually exclusive and exhaustive (sums to `total_eleitores`). Raça/Cor is out — do not add it back.
- The exact same 11 fields feed both `ProfileLayer`'s map coloring and every popup breakdown — one data model, computed once in Python, never recomputed or re-curated differently in the frontend.
- Framing copy is non-negotiable: popup section title is always `"Perfil do eleitorado deste local"` (never anything implying a candidate's own voters), with the mandatory subtitle `"Composicao do eleitorado local — nao indica em quem estes eleitores votaram."` present every time the breakdown renders.
- `ProfileLayer`'s color scale is a neutral single-hue sequential scale — never the existing red/green diverging scale used for deltas.
- Zero behavior change to `06_build_vote_deltas.py`'s actual delta/gating computation or its real output — the refactor only relocates helper functions.
- `05_build_geojson.py` is not touched at all in this plan.

---

### Task 1: Shared plumbing — move reusable geojson/roster helpers into `_pipeline_utils.py`

**Files:**
- Modify: `scripts/_pipeline_utils.py`, `scripts/06_build_vote_deltas.py`
- Test: `tests/test_pipeline_utils.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `load_local_info(data_geo)`, `build_section_id(df)`, `load_section_roster_from_raw(year, data_raw, municipio)`, `load_section_roster_from_votes(year, votes_by_secao)`, `load_section_roster(votes_by_secao, all_years, data_raw, municipio)`, `section_local_lookup(roster, year)`, `json_value(value)`, `to_geojson(df, layer_name)` — all now live in `_pipeline_utils.py`. Consumed by `06` (re-imported, behavior unchanged) and by Task 3's new script 09.

**Grounding note (corrects an assumption in the approved spec):** the spec said to move `get_local_coords()`/`to_geojson()` out of `05_build_geojson.py`. Reading both files in full during plan-writing found that `06_build_vote_deltas.py` has its own, independently-evolved and more complete versions of the same ideas (`load_local_info()` self-loads+cleans the CSV in one call, vs. `05`'s two-step `load_csv()`+`get_local_coords()`; `06`'s `to_geojson()`/`json_value()` correctly handles NaN, bool fields, and 6-decimal float rounding, vs. `05`'s simpler 4-decimal version with no bool handling). Moving `05`'s versions would mean either leaving them duplicated (defeating the point) or switching `05` to the shared version, which is a real, if minor, behavior change to an already-shipped script. Moving `06`'s versions is strictly lower-risk: `06` re-imports the exact same implementation it already has (truly zero behavior change), and `09` gets the more robust versions. `05_build_geojson.py` is not touched at all by this plan.

`_pipeline_utils.py` currently has zero dependency on `config.py` (every existing function takes paths/values as parameters). The moved functions preserve this — they gain `data_geo`/`data_raw`/`all_years`/`municipio` parameters instead of reading `06`'s module-level config imports directly.

- [ ] **Step 1: Write the failing tests**

`tests/test_pipeline_utils.py` currently starts with `import json`, `from conftest import load_script`, and `pu = load_script("_pipeline_utils", "_pipeline_utils.py")` — no `pandas` import yet, needed for the new tests below. Add `import pandas as pd` alongside the existing `import json` line, then append:

```python
def test_load_local_info_reads_and_cleans_locais_csv(tmp_path):
    geo = tmp_path / "geo"
    geo.mkdir()
    (geo / "locais_votacao_niteroi.csv").write_text(
        "nr_local,nm_local,bairro,lat,lon\n"
        "1015.0,Escola Teste,Icarai,-22.9,-43.1\n",
        encoding="utf-8",
    )
    result = pu.load_local_info(geo)
    assert list(result["nr_local"]) == ["1015"]
    assert result.iloc[0]["lat"] == -22.9


def test_load_local_info_missing_file_returns_empty_frame(tmp_path):
    result = pu.load_local_info(tmp_path / "nope")
    assert result.empty
    assert list(result.columns) == ["nr_local", "nm_local", "bairro", "lat", "lon"]


def test_build_section_id_concatenates_zona_and_secao():
    df = pd.DataFrame({"NR_ZONA": ["113", "114"], "NR_SECAO": ["1", "22"]})
    result = pu.build_section_id(df)
    assert list(result) == ["113-1", "114-22"]


def test_section_local_lookup_dedupes_by_section_id():
    roster = pd.DataFrame({
        "ano": [2022, 2022, 2020],
        "section_id": ["113-1", "113-1", "113-1"],
        "nr_local": ["1015", "1015", "1099"],
    })
    result = pu.section_local_lookup(roster, 2022)
    assert result == {"113-1": "1015"}


def test_json_value_handles_nan_bool_float_int():
    assert pu.json_value(float("nan")) is None
    assert pu.json_value(True) is True
    assert pu.json_value(3.0) == 3
    assert pu.json_value(3.5) == 3.5
    assert pu.json_value(7) == 7


def test_to_geojson_drops_rows_missing_coordinates():
    df = pd.DataFrame([
        {"nr_local": "1", "lat": -22.9, "lon": -43.1, "total": 5},
        {"nr_local": "2", "lat": None, "lon": -43.1, "total": 9},
    ])
    result = pu.to_geojson(df, "test_layer")
    assert len(result["features"]) == 1
    assert result["features"][0]["properties"]["nr_local"] == "1"
    assert "lat" not in result["features"][0]["properties"]
```

The file's existing imports already include `import pandas as pd` and `from conftest import load_script` / `pu = load_script(...)` per its current top-of-file pattern — read the file first to confirm the exact module alias used (likely `pu`), matching the rest of this test file rather than introducing a new one.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pipeline_utils.py -v -k "load_local_info or build_section_id or section_local_lookup or json_value or to_geojson"`
Expected: FAIL — `AttributeError: module has no attribute ...` for each.

- [ ] **Step 3: Move the functions into `_pipeline_utils.py`**

Append to `scripts/_pipeline_utils.py`:

```python
def load_local_info(data_geo: Path) -> pd.DataFrame:
    path = data_geo / "locais_votacao_niteroi.csv"
    if not path.exists():
        print("  [warn] locais_votacao_niteroi.csv not found; GeoJSON will be empty")
        return pd.DataFrame(columns=["nr_local", "nm_local", "bairro", "lat", "lon"])

    locais = pd.read_csv(path, dtype=str)
    locais["nr_local"] = clean_id_series(locais["nr_local"])
    for col in ("lat", "lon"):
        locais[col] = pd.to_numeric(locais[col], errors="coerce")

    keep = [c for c in ("nr_local", "nm_local", "bairro", "lat", "lon") if c in locais.columns]
    locais = locais[keep].drop_duplicates(subset=["nr_local"]).reset_index(drop=True)
    print(f"  Loaded locais_votacao_niteroi.csv: {len(locais):,} locais")
    return locais


def build_section_id(df: pd.DataFrame) -> pd.Series:
    return clean_id_series(df["NR_ZONA"]) + "-" + clean_id_series(df["NR_SECAO"])


def load_section_roster_from_raw(year: int, data_raw: Path, municipio: str) -> pd.DataFrame:
    folder = data_raw / f"votacao_secao_{year}"
    csv_file = find_csv(folder)
    if csv_file is None:
        return pd.DataFrame()

    header = read_tse_csv_safe(csv_file, nrows=0)
    required = ["NM_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO"]
    if any(col not in header.columns for col in required):
        return pd.DataFrame()

    pieces = []
    for chunk in read_tse_chunks_safe(csv_file, usecols=required):
        mask = chunk["NM_MUNICIPIO"].apply(lambda x: normalize(x) == normalize(municipio))
        nit = chunk.loc[mask, ["NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO"]].copy()
        if nit.empty:
            continue
        nit["ano"] = year
        nit["NR_ZONA"] = clean_id_series(nit["NR_ZONA"])
        nit["NR_SECAO"] = clean_id_series(nit["NR_SECAO"])
        nit["nr_local"] = clean_id_series(nit["NR_LOCAL_VOTACAO"])
        nit["section_id"] = build_section_id(nit)
        pieces.append(nit[["ano", "NR_ZONA", "NR_SECAO", "section_id", "nr_local"]].drop_duplicates())

    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, ignore_index=True).drop_duplicates()


def load_section_roster_from_votes(year: int, votes_by_secao: dict[str, pd.DataFrame]) -> pd.DataFrame:
    pieces = []
    for df in votes_by_secao.values():
        if df.empty:
            continue
        sub = df[df["ano"] == year]
        if sub.empty:
            continue
        pieces.append(sub[["ano", "NR_ZONA", "NR_SECAO", "section_id", "nr_local"]].drop_duplicates())
    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, ignore_index=True).drop_duplicates()


def load_section_roster(
    votes_by_secao: dict[str, pd.DataFrame], all_years, data_raw: Path, municipio: str
) -> pd.DataFrame:
    all_rows = []
    for year in sorted(all_years):
        print(f"  Reading section roster {year} ...")
        roster = load_section_roster_from_raw(year, data_raw, municipio)
        if roster.empty:
            print(f"    [fallback] using processed vote rows for {year}")
            roster = load_section_roster_from_votes(year, votes_by_secao)
        print(f"    {len(roster):,} section/local rows")
        if not roster.empty:
            all_rows.append(roster)
    if not all_rows:
        return pd.DataFrame(columns=["ano", "NR_ZONA", "NR_SECAO", "section_id", "nr_local"])
    return pd.concat(all_rows, ignore_index=True).drop_duplicates()


def section_local_lookup(roster: pd.DataFrame, year: int) -> dict[str, str]:
    sub = roster[roster["ano"] == year]
    deduped = sub.drop_duplicates(subset=["section_id"])
    return dict(zip(deduped["section_id"], deduped["nr_local"]))


def json_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return round(value, 6)
    if isinstance(value, int):
        return value
    return value


def to_geojson(df: pd.DataFrame, layer_name: str) -> dict:
    features = []
    if df.empty:
        return {"type": "FeatureCollection", "name": layer_name, "features": features}

    for _, row in df.dropna(subset=["lat", "lon"]).iterrows():
        props = {
            key: json_value(value)
            for key, value in row.items()
            if key not in ("lat", "lon")
        }
        features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row["lon"]), float(row["lat"])],
                },
            }
        )
    return {"type": "FeatureCollection", "name": layer_name, "features": features}
```

- [ ] **Step 4: Update `06_build_vote_deltas.py` to import the moved functions and delete its local copies**

In `scripts/06_build_vote_deltas.py`, replace the import block:

```python
from _pipeline_utils import (
    clean_id_series,
    election_type,
    find_csv,
    normalize,
    read_tse_csv_safe,
    read_tse_chunks_safe,
    rebuild_data_js as _rebuild_data_js,
)
```

with:

```python
from _pipeline_utils import (
    build_section_id,
    clean_id_series,
    election_type,
    find_csv,
    json_value,
    load_local_info,
    load_section_roster,
    normalize,
    read_tse_csv_safe,
    read_tse_chunks_safe,
    rebuild_data_js as _rebuild_data_js,
    section_local_lookup,
    to_geojson,
)
```

Delete these function definitions from the file entirely (they now live in `_pipeline_utils.py`): `build_section_id`, `load_local_info`, `load_section_roster_from_raw`, `load_section_roster_from_votes`, `load_section_roster`, `section_local_lookup`, `json_value`, `to_geojson`.

Update the two call sites that now need extra arguments. Replace:

```python
    print("\nLoading polling-place coordinates ...")
    locais = load_local_info()
```

with:

```python
    print("\nLoading polling-place coordinates ...")
    locais = load_local_info(DATA_GEO)
```

Replace:

```python
    print("\nBuilding section/local roster from raw vote files ...")
    roster = load_section_roster(votes_by_secao)
```

with:

```python
    print("\nBuilding section/local roster from raw vote files ...")
    roster = load_section_roster(votes_by_secao, ALL_YEARS, DATA_RAW, MUNICIPIO)
```

(`ALL_YEARS`, `DATA_RAW`, `MUNICIPIO`, `DATA_GEO` are already imported into this file from `config` — no import changes needed for these.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_pipeline_utils.py -v`
Expected: PASS, including all 6 new tests.

- [ ] **Step 6: Run the full existing test suite**

Run: `python -m pytest tests/ -v`
Expected: all 48 tests pass, including `tests/test_vote_deltas.py`'s existing suite (which exercises `06`'s functions indirectly through `build_local_delta_frame`/`build_section_delta_frame` — this is the real regression check that the refactor changed nothing observable).

- [ ] **Step 7: Run `06` against real data and spot-check zero behavior change**

Run: `python scripts/06_build_vote_deltas.py`
Expected: completes with `Done.`, same row counts as before this task (`vote_deltas_by_local.csv`: 501 rows, `vote_deltas.geojson`: 501 features — confirm against the file's current state before running, since this task's refactor must not change these numbers).

- [ ] **Step 8: Commit**

```bash
git add scripts/_pipeline_utils.py scripts/06_build_vote_deltas.py tests/test_pipeline_utils.py
git commit -m "refactor: move reusable geojson/roster helpers from 06 into _pipeline_utils"
```

---

### Task 2: Script 09 — demographic aggregation and share computation

**Files:**
- Create: `scripts/09_voter_profile_geojson.py`
- Test: `tests/test_voter_profile_geojson.py`

**Interfaces:**
- Consumes: `load_local_info`, `load_section_roster`, `to_geojson` (`_pipeline_utils.py`, Task 1).
- Produces: `ALL_METRIC_COLS: dict[str, list[str]]`, `aggregate_profile_to_local(profile, roster) -> pd.DataFrame`, `compute_shares(grouped) -> pd.DataFrame`, `profile_lookup(shares) -> dict[tuple[int, str], dict]`, `merge_profile_onto_layer(geojson, lookup) -> dict` — all consumed by Task 3's `main()` in this same file, and the field names produced (`pct_mulheres`, `pct_homens`, etc.) are consumed by the frontend (Task 5-7).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_voter_profile_geojson.py`:

```python
import pandas as pd

from conftest import load_script

vp = load_script("_voter_profile_geojson", "09_voter_profile_geojson.py")


def make_profile_row(ano, zona, secao, **overrides):
    row = {
        "ano": ano, "NR_ZONA": zona, "NR_SECAO": secao, "total_eleitores": 100,
        "gen__feminino": 55, "gen__masculino": 44, "gen__nao informado": 1,
        "fai__16 anos": 2, "fai__17 anos": 2, "fai__18 anos": 2, "fai__19 anos": 2,
        "fai__20 anos": 2, "fai__21 a 24 anos": 5,
        "fai__25 a 29 anos": 5, "fai__30 a 34 anos": 5, "fai__35 a 39 anos": 5,
        "fai__40 a 44 anos": 5, "fai__45 a 49 anos": 5, "fai__50 a 54 anos": 5, "fai__55 a 59 anos": 5,
        "fai__60 a 64 anos": 5, "fai__65 a 69 anos": 5, "fai__70 a 74 anos": 5,
        "fai__75 a 79 anos": 5, "fai__80 a 84 anos": 5, "fai__85 a 89 anos": 5,
        "fai__90 a 94 anos": 5, "fai__95 a 99 anos": 5, "fai__100 anos ou mais": 4,
        "fai__invalido": 0, "fai__invalida": 0,
        "gra__analfabeto": 5, "gra__le e escreve": 5,
        "gra__ensino fundamental completo": 10, "gra__ensino fundamental incompleto": 10,
        "gra__ensino medio completo": 30, "gra__ensino medio incompleto": 10,
        "gra__superior completo": 20, "gra__superior incompleto": 9,
        "gra__nao informado": 1,
    }
    row.update(overrides)
    return row


def make_roster_row(ano, zona, secao, nr_local):
    return {"ano": ano, "NR_ZONA": zona, "NR_SECAO": secao, "section_id": f"{zona}-{secao}", "nr_local": nr_local}


def test_aggregate_profile_to_local_sums_raw_counts_across_secoes():
    profile = pd.DataFrame([
        make_profile_row(2022, "113", "1"),
        make_profile_row(2022, "113", "2"),
    ])
    roster = pd.DataFrame([
        make_roster_row(2022, "113", "1", "1015"),
        make_roster_row(2022, "113", "2", "1015"),
    ])
    result = vp.aggregate_profile_to_local(profile, roster)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["ano"] == 2022
    assert row["nr_local"] == "1015"
    assert row["total_eleitores"] == 200
    assert row["gen__feminino"] == 110


def test_aggregate_profile_to_local_keeps_different_locais_separate():
    profile = pd.DataFrame([
        make_profile_row(2022, "113", "1"),
        make_profile_row(2022, "114", "5"),
    ])
    roster = pd.DataFrame([
        make_roster_row(2022, "113", "1", "1015"),
        make_roster_row(2022, "114", "5", "1099"),
    ])
    result = vp.aggregate_profile_to_local(profile, roster)
    assert sorted(result["nr_local"]) == ["1015", "1099"]


def test_aggregate_profile_to_local_empty_inputs_return_empty_frame():
    result = vp.aggregate_profile_to_local(pd.DataFrame(), pd.DataFrame())
    assert result.empty
    assert "total_eleitores" in result.columns


def test_compute_shares_gender_sums_to_100():
    grouped = pd.DataFrame([{
        "ano": 2022, "nr_local": "1015", "total_eleitores": 100,
        "gen__feminino": 55, "gen__masculino": 44, "gen__nao informado": 1,
        "fai__16 anos": 0, "fai__17 anos": 0, "fai__18 anos": 0, "fai__19 anos": 0,
        "fai__20 anos": 0, "fai__21 a 24 anos": 0, "fai__25 a 29 anos": 0, "fai__30 a 34 anos": 0,
        "fai__35 a 39 anos": 0, "fai__40 a 44 anos": 0, "fai__45 a 49 anos": 0, "fai__50 a 54 anos": 0,
        "fai__55 a 59 anos": 0, "fai__60 a 64 anos": 0, "fai__65 a 69 anos": 0, "fai__70 a 74 anos": 0,
        "fai__75 a 79 anos": 0, "fai__80 a 84 anos": 0, "fai__85 a 89 anos": 0, "fai__90 a 94 anos": 0,
        "fai__95 a 99 anos": 0, "fai__100 anos ou mais": 0, "fai__invalido": 0, "fai__invalida": 0,
        "gra__analfabeto": 0, "gra__le e escreve": 0, "gra__ensino fundamental completo": 0,
        "gra__ensino fundamental incompleto": 0, "gra__ensino medio completo": 0,
        "gra__ensino medio incompleto": 0, "gra__superior completo": 0, "gra__superior incompleto": 0,
        "gra__nao informado": 0,
    }])
    result = vp.compute_shares(grouped)
    assert result.iloc[0]["pct_mulheres"] == 55.0
    assert result.iloc[0]["pct_homens"] == 44.0
    assert result.iloc[0]["pct_genero_nao_informado"] == 1.0


def test_compute_shares_age_bands_collapse_correctly():
    profile = pd.DataFrame([make_profile_row(2022, "113", "1")])
    roster = pd.DataFrame([make_roster_row(2022, "113", "1", "1015")])
    grouped = vp.aggregate_profile_to_local(profile, roster)
    result = vp.compute_shares(grouped)
    row = result.iloc[0]
    # jovens: 2+2+2+2+2+5 = 15; adultos: 5*7 = 35; 60+: 5*8+4 = 44; total 100 -> 15%, 35%, 44%
    assert row["pct_jovens_16_24"] == 15.0
    assert row["pct_adultos_25_59"] == 35.0
    assert row["pct_60_mais"] == 44.0
    assert row["pct_idade_nao_informado"] == 0.0


def test_compute_shares_education_bands_include_le_e_escreve_in_ate_fundamental():
    profile = pd.DataFrame([make_profile_row(2022, "113", "1")])
    roster = pd.DataFrame([make_roster_row(2022, "113", "1", "1015")])
    grouped = vp.aggregate_profile_to_local(profile, roster)
    result = vp.compute_shares(grouped)
    row = result.iloc[0]
    # ate_fundamental: 5(analfabeto)+5(le_e_escreve)+10+10 = 30
    assert row["pct_ate_fundamental"] == 30.0
    assert row["pct_ensino_medio"] == 40.0
    assert row["pct_ensino_superior"] == 29.0
    assert row["pct_escolaridade_nao_informado"] == 1.0


def test_compute_shares_zero_total_eleitores_does_not_divide_by_zero():
    grouped = pd.DataFrame([{
        "ano": 2022, "nr_local": "1015", "total_eleitores": 0,
        "gen__feminino": 0, "gen__masculino": 0, "gen__nao informado": 0,
    }])
    result = vp.compute_shares(grouped)
    assert pd.isna(result.iloc[0]["pct_mulheres"])


def test_no_race_fields_anywhere_in_metric_columns():
    all_cols = [c for cols in vp.ALL_METRIC_COLS.values() for c in cols]
    assert not any(c.startswith("rac__") for c in all_cols)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_voter_profile_geojson.py -v`
Expected: FAIL — `09_voter_profile_geojson.py` doesn't exist yet.

- [ ] **Step 3: Create the script with the data-model and aggregation logic**

Create `scripts/09_voter_profile_geojson.py`:

```python
"""Aggregate seção-level voter demographics (04's output) up to local de
votação grain, collapsing TSE's raw category columns into a fixed set of
11 mutually-exclusive shares across three dimensions (gender, age,
education). Race/cor is deliberately not included — confirmed against the
real raw TSE files that it is structurally unpopulated for Niterói across
the whole 2010-2024 span (100% "#NE"/not-informed in 2010-2022, 93%+
not-informed even in 2024) — see docs/voter_profile_backbone.md.

The same 11 fields feed both this script's standalone voter_profile.geojson
(for the map's ProfileLayer) and the fields merged onto the three candidate
geojson files (for the popup breakdown) — one data model, computed once.
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import ALL_YEARS, DATA_GEO, DATA_PROCESSED, DATA_RAW, MUNICIPIO
from _pipeline_utils import load_local_info, load_section_roster, to_geojson

GENDER_COLS = {
    "pct_mulheres": ["gen__feminino"],
    "pct_homens": ["gen__masculino"],
    "pct_genero_nao_informado": ["gen__nao informado"],
}

AGE_COLS = {
    "pct_jovens_16_24": [
        "fai__16 anos", "fai__17 anos", "fai__18 anos",
        "fai__19 anos", "fai__20 anos", "fai__21 a 24 anos",
    ],
    "pct_adultos_25_59": [
        "fai__25 a 29 anos", "fai__30 a 34 anos", "fai__35 a 39 anos",
        "fai__40 a 44 anos", "fai__45 a 49 anos", "fai__50 a 54 anos", "fai__55 a 59 anos",
    ],
    "pct_60_mais": [
        "fai__60 a 64 anos", "fai__65 a 69 anos", "fai__70 a 74 anos",
        "fai__75 a 79 anos", "fai__80 a 84 anos", "fai__85 a 89 anos",
        "fai__90 a 94 anos", "fai__95 a 99 anos", "fai__100 anos ou mais",
    ],
    # fai__invalido / fai__invalida are the same category under two raw
    # labels — a TSE label-agreement inconsistency across years. Real
    # volume is 43 people across all 8 years of Niterói data; merging
    # costs nothing and keeps the dimension exhaustive.
    "pct_idade_nao_informado": ["fai__invalido", "fai__invalida"],
}

EDUCATION_COLS = {
    "pct_ate_fundamental": [
        "gra__analfabeto", "gra__le e escreve",
        "gra__ensino fundamental completo", "gra__ensino fundamental incompleto",
    ],
    "pct_ensino_medio": ["gra__ensino medio completo", "gra__ensino medio incompleto"],
    "pct_ensino_superior": ["gra__superior completo", "gra__superior incompleto"],
    "pct_escolaridade_nao_informado": ["gra__nao informado"],
}

ALL_METRIC_COLS = {**GENDER_COLS, **AGE_COLS, **EDUCATION_COLS}


def aggregate_profile_to_local(profile: pd.DataFrame, roster: pd.DataFrame) -> pd.DataFrame:
    """Join seção-grain profile counts to nr_local via the roster, then sum
    raw counts (not pre-computed percentages) up to (ano, nr_local) — summing
    raw counts first avoids compounding rounding error from averaging
    already-rounded percentages."""
    empty_cols = ["ano", "nr_local", "total_eleitores"] + [c for cols in ALL_METRIC_COLS.values() for c in cols]
    if profile.empty or roster.empty:
        return pd.DataFrame(columns=empty_cols)

    crosswalk = roster[["ano", "NR_ZONA", "NR_SECAO", "nr_local"]].drop_duplicates()
    joined = profile.merge(crosswalk, on=["ano", "NR_ZONA", "NR_SECAO"], how="inner")
    joined = joined[joined["nr_local"] != ""]
    if joined.empty:
        return pd.DataFrame(columns=empty_cols)

    raw_cols = [c for cols in ALL_METRIC_COLS.values() for c in cols if c in joined.columns]
    sum_cols = ["total_eleitores"] + raw_cols
    grouped = joined.groupby(["ano", "nr_local"], as_index=False)[sum_cols].sum()
    return grouped


def compute_shares(grouped: pd.DataFrame) -> pd.DataFrame:
    """Turn summed raw counts into the 11 published percentage fields."""
    grouped = grouped.copy()
    safe_total = grouped["total_eleitores"].astype(float).replace(0, pd.NA)
    for field, cols in ALL_METRIC_COLS.items():
        present = [c for c in cols if c in grouped.columns]
        numerator = grouped[present].sum(axis=1) if present else pd.Series(0, index=grouped.index)
        grouped[field] = (numerator / safe_total * 100).round(1)
    return grouped


def profile_lookup(shares: pd.DataFrame) -> dict[tuple[int, str], dict]:
    fields = ["total_eleitores"] + list(ALL_METRIC_COLS)
    lookup = {}
    for _, row in shares.iterrows():
        lookup[(int(row["ano"]), row["nr_local"])] = {
            f: (None if pd.isna(row[f]) else row[f]) for f in fields
        }
    return lookup


def merge_profile_onto_layer(geojson: dict, lookup: dict[tuple[int, str], dict]) -> dict:
    for feature in geojson.get("features", []):
        props = feature["properties"]
        year = props.get("ano")
        nr_local = str(props.get("nr_local", "")).strip()
        fields = lookup.get((year, nr_local))
        if fields:
            props.update(fields)
    return geojson
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_voter_profile_geojson.py -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/09_voter_profile_geojson.py tests/test_voter_profile_geojson.py
git commit -m "feat: add voter-profile aggregation and 11-field share computation"
```

---

### Task 3: Script 09 — `main()`, geojson emission, real pipeline run

**Files:**
- Modify: `scripts/09_voter_profile_geojson.py`, `scripts/_pipeline_utils.py`

**Interfaces:**
- Consumes: `aggregate_profile_to_local`, `compute_shares`, `profile_lookup`, `merge_profile_onto_layer` (Task 2, this same file).
- Produces: `data/geo/voter_profile.geojson` (consumed by Task 5's `ProfileLayer`) and the 11 fields merged onto `hugo_leal.geojson`/`felipe_peixoto.geojson`/`psd.geojson` (consumed by Task 6's popup section). `APP_GEOJSON_LAYERS` in `_pipeline_utils.py` gains `"voter_profile"` so it flows into `app/data.js` automatically the next time `06` or `07` runs (both already call `rebuild_data_js` at the end of their own `main()` — no new call site needed here).

- [ ] **Step 1: Add `"voter_profile"` to the shared app-bundle layer list**

In `scripts/_pipeline_utils.py`, replace:

```python
APP_GEOJSON_LAYERS = ["hugo_leal", "felipe_peixoto", "psd", "vote_deltas"]
```

with:

```python
APP_GEOJSON_LAYERS = ["hugo_leal", "felipe_peixoto", "psd", "vote_deltas", "voter_profile"]
```

This is the only change needed for `voter_profile.geojson` to reach `app/data.js` — `06` and `07` both already call `rebuild_data_js(DATA_GEO, ...)` with this list as the default at the end of their `main()`, and the real documented execution order (`...→09→06→07`) means `07`'s call, running last, picks up whatever `09` wrote.

- [ ] **Step 2: Append `main()` to `scripts/09_voter_profile_geojson.py`**

```python
def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    DATA_GEO.mkdir(parents=True, exist_ok=True)

    print("Loading voter_profile_by_secao.csv ...")
    profile_path = DATA_PROCESSED / "voter_profile_by_secao.csv"
    if not profile_path.exists():
        print("  [skip] voter_profile_by_secao.csv not found; run 04_voter_profile.py first")
        return
    profile = pd.read_csv(profile_path)
    print(f"  {len(profile):,} seção-grain rows")

    print("\nLoading polling-place coordinates ...")
    locais = load_local_info(DATA_GEO)

    print("\nBuilding section/local roster ...")
    # 09 has no votes_by_secao of its own to offer the roster's raw-file-read
    # fallback path — passing {} is correct, not a placeholder: the real raw
    # votacao_secao files are already present for every year in this
    # project, so load_section_roster_from_raw() succeeds directly and the
    # fallback is never exercised.
    roster = load_section_roster({}, ALL_YEARS, DATA_RAW, MUNICIPIO)

    print("\nAggregating profile to local grain ...")
    grouped = aggregate_profile_to_local(profile, roster)
    shares = compute_shares(grouped)
    print(f"  {len(shares):,} (ano, nr_local) rows with demographic shares")
    lookup = profile_lookup(shares)

    print("\nBuilding standalone voter_profile.geojson ...")
    merged = shares.merge(locais, on="nr_local", how="left")
    geojson = to_geojson(merged, "voter_profile")
    out = DATA_GEO / "voter_profile.geojson"
    out.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Saved {out.name}: {len(geojson['features']):,} features")

    print("\nMerging profile fields onto candidate layers ...")
    for name in ("hugo_leal", "felipe_peixoto", "psd"):
        path = DATA_GEO / f"{name}.geojson"
        if not path.exists():
            print(f"  [skip] {path.name} not found; run 05_build_geojson.py first")
            continue
        cand_geojson = json.loads(path.read_text(encoding="utf-8"))
        merge_profile_onto_layer(cand_geojson, lookup)
        path.write_text(json.dumps(cand_geojson, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Updated {path.name}")

    print("Done.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the full test suite to verify nothing broke**

Run: `python -m pytest tests/ -v`
Expected: all tests pass (same count as Task 2's end, `main()` itself has no direct unit test — matches this codebase's existing pattern of not unit-testing `main()` orchestration functions).

- [ ] **Step 4: Run against real data**

Run: `python scripts/09_voter_profile_geojson.py`

If this takes more than a couple of minutes, background it with an explicit generous timeout (300000-600000ms) rather than the default — do NOT wrap it in a Monitor/watcher you might later stop, since a `TaskStop` call on a Monitor-wrapped pipe kills the whole pipe, not just the watcher (a real incident from an earlier plan in this project). This run should be fast, though — `voter_profile_by_secao.csv` is small (10,083 rows) and already on disk; no raw-file re-reading happens unless the roster's raw-file path is exercised, and per Step 2's roster call, `votacao_secao` raw files are already present for every year.

Expected: completes with `Done.`, `data/geo/voter_profile.geojson` created, all three candidate geojson files updated in place.

- [ ] **Step 5: Spot-check the real output**

```bash
python -c "
import json
vp = json.load(open('data/geo/voter_profile.geojson', encoding='utf-8'))
print('voter_profile.geojson features:', len(vp['features']))
sample = vp['features'][0]['properties']
print('sample keys:', sorted(k for k in sample if k.startswith('pct_') or k == 'total_eleitores'))
assert not any(k.startswith('rac__') or 'raca' in k.lower() for k in sample), 'race field leaked into output'
pct_sum = sum(v for k, v in sample.items() if k in ('pct_mulheres','pct_homens','pct_genero_nao_informado'))
print('gender pct sum (should be ~100):', pct_sum)

hugo = json.load(open('data/geo/hugo_leal.geojson', encoding='utf-8'))
sample_hugo = next((f['properties'] for f in hugo['features'] if 'pct_mulheres' in f['properties']), None)
assert sample_hugo is not None, 'profile fields never merged onto hugo_leal.geojson'
print('Hugo feature has pct_mulheres:', sample_hugo['pct_mulheres'])
print('OK')
"
```

Expected: `OK` printed, gender percentages summing close to 100 (allowing for rounding), no `rac__`/race key anywhere, and confirmation that at least one `hugo_leal.geojson` feature now carries `pct_mulheres`.

- [ ] **Step 6: Commit**

```bash
git add scripts/09_voter_profile_geojson.py scripts/_pipeline_utils.py
git commit -m "feat: emit voter_profile.geojson and merge demographic fields onto candidate layers"
```

(Generated data files — `data/geo/voter_profile.geojson`, the three updated candidate geojsons, `app/data.js` — are left uncommitted per this project's convention; they get committed together in the final task's pipeline-refresh step.)

---

### Task 4: README — document script 09 and the real execution order

**Files:**
- Modify: `README.md`

**Interfaces:** None — documentation only.

- [ ] **Step 1: Read the current README's Pipeline section in full before editing**

The real execution order is currently documented as `01 → 02 → 03 → 04 → 05 → 08 → 06 → 07`. This task inserts `09` between `05` (which it depends on for the candidate geojson merge target) and `08`/`06`/`07` (which it doesn't depend on and don't depend on it) — giving `01 → 02 → 03 → 04 → 05 → 08 → 09 → 06 → 07`. `09` needs to run after `08`? No — re-check: `09` only depends on `02` (roster fallback, unused in practice), `04` (`voter_profile_by_secao.csv`), and `05` (candidate geojson merge targets). It does not depend on `08`, and nothing downstream of `09` (`06`/`07`) depends on `09`'s output either. Its position relative to `08` is arbitrary; placing it immediately after `08` keeps the two "runs after 05, merges additional fields onto already-built geojson" scripts grouped together in the documented order, matching the existing narrative structure.

- [ ] **Step 2: Add script 09 to the pipeline list**

Add an entry matching the existing numbered-list style and the existing execution-order-note pattern already present for script `08`:

```markdown
9. `scripts/09_voter_profile_geojson.py` — aggregate voter demographics
   (from `04`'s seção-grain output) up to local de votação grain, compute
   11 demographic share fields across gender/age/education, and write
   `voter_profile.geojson` plus merge the same fields onto
   `hugo_leal.geojson`/`felipe_peixoto.geojson`/`psd.geojson`
```

Update the execution-order note to:

```
01 → 02 → 03 → 04 → 05 → 08 → 09 → 06 → 07
```

- [ ] **Step 3: Document the new fields**

Add a short new section (matching the style of the existing "Candidacy Matrix" section) covering:
- The 11 fields and their three dimensions, with the exact collapsing formulas from `scripts/09_voter_profile_geojson.py`'s `GENDER_COLS`/`AGE_COLS`/`EDUCATION_COLS`.
- One line noting Raça/Cor was investigated and deliberately excluded — structurally unpopulated in TSE's Niterói data across the whole dataset (100% "#NE" 2010-2022, 93%+ not-informed even in 2024) — with a pointer to `docs/voter_profile_backbone.md` for the full investigation.
- One line noting `data/geo/voter_profile.geojson` is the standalone layer (used by the map's "Perfil do Eleitorado" toggle) while the same 11 fields are also merged directly onto the three candidate geojson files (used by the popup breakdown).

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document scripts/09_voter_profile_geojson.py and the updated pipeline order"
```

---

### Task 5: Frontend — `ProfileLayer`, `ProfileMetricFilter`, constants, sequential color scale

**Files:**
- Create: `app-web/src/components/ProfileLayer.jsx`, `app-web/src/components/ProfileLayer.test.jsx`, `app-web/src/components/ProfileMetricFilter.jsx`
- Modify: `app-web/src/lib/constants.js`, `app-web/src/lib/visual.js`, `app-web/src/lib/visual.test.js`

**Interfaces:**
- Consumes: nothing new from earlier tasks (reads `voter_profile.geojson`'s fields by name, matching Task 2/3's output).
- Produces: `PROFILE_DIMENSIONS`, `PROFILE_METRICS` (`lib/constants.js`), `getSequentialColor(pct)` (`lib/visual.js`), `<ProfileLayer>`, `<ProfileMetricFilter>` — `PROFILE_DIMENSIONS` is also consumed directly by Task 6's `ProfileSection`; `<ProfileLayer>`/`<ProfileMetricFilter>`/`PROFILE_METRICS` are consumed by Task 7's `App.jsx` wiring.

- [ ] **Step 1: Write the failing tests**

The file already exists (`app-web/src/lib/visual.test.js`) with a single `import { interpolateChannel, interpolateColor, getDivergingColor, getRadius, getDeltaRadius } from './visual';` line feeding several `describe` blocks. Add `getSequentialColor` to that existing import line (do not add a second import statement), then append:

```js
describe('getSequentialColor', () => {
  it('returns a distinct color at 0% vs 100%', () => {
    const low = getSequentialColor(0);
    const high = getSequentialColor(100);
    expect(low).not.toBe(high);
  });

  it('treats null/undefined as 0%', () => {
    expect(getSequentialColor(null)).toBe(getSequentialColor(0));
    expect(getSequentialColor(undefined)).toBe(getSequentialColor(0));
  });

  it('clamps values outside 0-100', () => {
    expect(getSequentialColor(150)).toBe(getSequentialColor(100));
    expect(getSequentialColor(-10)).toBe(getSequentialColor(0));
  });
});
```

Create `app-web/src/components/ProfileLayer.test.jsx`:

```jsx
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { MapContainer } from 'react-leaflet';
import ProfileLayer from './ProfileLayer';
import { PROFILE_METRICS } from '../lib/constants';

const feature = (nrLocal, pct) => ({
  type: 'Feature',
  geometry: { type: 'Point', coordinates: [-43.0783, -22.9017] },
  properties: { nr_local: nrLocal, ano: 2022, pct_mulheres: pct, nm_local: 'Escola Teste', bairro: 'Icarai', total_eleitores: 100 },
});

describe('ProfileLayer', () => {
  it('renders one marker per feature for the selected metric', () => {
    const features = [feature('1', 55), feature('2', 40)];
    const { container } = render(
      <MapContainer center={[-22.9017, -43.0783]} zoom={13}>
        <ProfileLayer features={features} metric={PROFILE_METRICS.mulheres} />
      </MapContainer>
    );
    const paths = container.querySelectorAll('.leaflet-marker-pane path');
    expect(paths.length).toBe(2);
  });

  it('skips a feature whose selected metric is null', () => {
    const features = [feature('1', null), feature('2', 40)];
    const { container } = render(
      <MapContainer center={[-22.9017, -43.0783]} zoom={13}>
        <ProfileLayer features={features} metric={PROFILE_METRICS.mulheres} />
      </MapContainer>
    );
    const paths = container.querySelectorAll('.leaflet-marker-pane path');
    expect(paths.length).toBe(1);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- --run` (from `app-web/`)
Expected: FAIL — `getSequentialColor`/`PROFILE_METRICS`/`ProfileLayer` don't exist yet.

- [ ] **Step 3: Add the sequential color scale**

In `app-web/src/lib/visual.js`, append:

```js
export function getSequentialColor(pct) {
  const light = [216, 216, 222];
  const dark = [90, 60, 160];
  const value = Number(pct);
  const clamped = Number.isFinite(value) ? Math.min(100, Math.max(0, value)) : 0;
  return interpolateColor(light, dark, clamped / 100);
}
```

(Light gray → purple. Deliberately not red/green — that pair already means "lost/gained votes" in `DeltaLayer`; reusing it here would visually imply a performance judgment on a neutral demographic fact. Also distinct from the existing candidate colors: Hugo blue `#4a90d9`, Felipe green `#50c878`, PSD orange `#e8a838`.)

- [ ] **Step 4: Add the constants**

In `app-web/src/lib/constants.js`, append:

```js
export const PROFILE_DIMENSIONS = [
  {
    id: 'genero',
    label: 'Genero',
    metrics: [
      { id: 'mulheres', label: '% Mulheres', field: 'pct_mulheres' },
      { id: 'homens', label: '% Homens', field: 'pct_homens' },
      { id: 'genero_nao_informado', label: '% Nao informado', field: 'pct_genero_nao_informado' },
    ],
  },
  {
    id: 'idade',
    label: 'Faixa etaria',
    metrics: [
      { id: 'jovens_16_24', label: '% Jovens 16-24', field: 'pct_jovens_16_24' },
      { id: 'adultos_25_59', label: '% Adultos 25-59', field: 'pct_adultos_25_59' },
      { id: '60_mais', label: '% 60+', field: 'pct_60_mais' },
      { id: 'idade_nao_informado', label: '% Nao informado', field: 'pct_idade_nao_informado' },
    ],
  },
  {
    id: 'escolaridade',
    label: 'Escolaridade',
    metrics: [
      { id: 'ate_fundamental', label: '% Ate Fundamental', field: 'pct_ate_fundamental' },
      { id: 'ensino_medio', label: '% Ensino Medio', field: 'pct_ensino_medio' },
      { id: 'ensino_superior', label: '% Ensino Superior', field: 'pct_ensino_superior' },
      { id: 'escolaridade_nao_informado', label: '% Nao informado', field: 'pct_escolaridade_nao_informado' },
    ],
  },
];

export const PROFILE_METRICS = Object.fromEntries(
  PROFILE_DIMENSIONS.flatMap(d => d.metrics).map(m => [m.id, m])
);
```

- [ ] **Step 5: Create `ProfileMetricFilter.jsx`**

```jsx
import { useState } from 'react';
import { PROFILE_DIMENSIONS } from '../lib/constants';

export default function ProfileMetricFilter({ selectedMetricId, onChange }) {
  const activeDimension = PROFILE_DIMENSIONS.find(d =>
    d.metrics.some(m => m.id === selectedMetricId)
  ) || PROFILE_DIMENSIONS[0];
  const [openDimensionId, setOpenDimensionId] = useState(activeDimension.id);
  const openDimension = PROFILE_DIMENSIONS.find(d => d.id === openDimensionId) || PROFILE_DIMENSIONS[0];

  return (
    <div>
      <div className="year-bar">
        {PROFILE_DIMENSIONS.map(d => (
          <button
            key={d.id}
            className={'year-btn' + (d.id === openDimensionId ? ' active' : '')}
            onClick={() => setOpenDimensionId(d.id)}
          >
            {d.label}
          </button>
        ))}
      </div>
      <div className="year-bar">
        {openDimension.metrics.map(m => (
          <button
            key={m.id}
            className={'year-btn' + (m.id === selectedMetricId ? ' active' : '')}
            onClick={() => onChange(m.id)}
          >
            {m.label}
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Create `ProfileLayer.jsx`**

```jsx
import { CircleMarker, Popup } from 'react-leaflet';
import ProfilePopupContent from './ProfilePopupContent';
import { getSequentialColor } from '../lib/visual';

export default function ProfileLayer({ features, metric }) {
  return (
    <>
      {features.map(f => {
        const p = f.properties;
        const [lng, lat] = f.geometry.coordinates;
        const pct = p[metric.field];
        if (pct === null || pct === undefined) return null;
        const color = getSequentialColor(pct);

        return (
          <CircleMarker
            key={`profile-${p.nr_local}-${p.ano}`}
            center={[lat, lng]}
            radius={6}
            pane="markerPane"
            pathOptions={{ fillColor: color, fillOpacity: 0.78, color, weight: 1, opacity: 0.95 }}
            eventHandlers={{
              mouseover: (e) => e.target.setStyle({ fillOpacity: 0.95, weight: 2 }),
              mouseout: (e) => e.target.setStyle({ fillOpacity: 0.78, weight: 1 }),
            }}
          >
            <Popup>
              <ProfilePopupContent p={p} />
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}
```

Note: this references `./ProfilePopupContent`, created in Task 6 — Task 5's own tests (Step 1) don't click markers or open popups, so this forward reference doesn't break Task 5's own test run, but `npm test` as a whole won't fully pass until Task 6 adds the file. Run Task 5's tests scoped (`npm test -- --run ProfileLayer visual`) rather than the full suite at the end of this task, and note the forward dependency in the task's completion report.

- [ ] **Step 7: Run the scoped tests to verify they pass**

Run: `npm test -- --run -t "ProfileLayer|getSequentialColor"` (from `app-web/`) — or run the two test files directly: `npx vitest run src/components/ProfileLayer.test.jsx src/lib/visual.test.js`
Expected: FAIL on `ProfileLayer`'s import of `./ProfilePopupContent` (doesn't exist until Task 6) — this is expected and documented above, not a real failure to fix in this task. Confirm `visual.test.js`'s 3 new tests pass; confirm `ProfileLayer.test.jsx`'s import error is exactly a missing-module error for `ProfilePopupContent`, nothing else.

- [ ] **Step 8: Commit**

```bash
git add app-web/src/components/ProfileLayer.jsx app-web/src/components/ProfileLayer.test.jsx app-web/src/components/ProfileMetricFilter.jsx app-web/src/lib/constants.js app-web/src/lib/visual.js app-web/src/lib/visual.test.js
git commit -m "feat: add ProfileLayer, ProfileMetricFilter, and sequential color scale"
```

---

### Task 6: Frontend — `ProfileSection`, `ProfilePopupContent`, and popup integration on all three marker types

**Files:**
- Create: `app-web/src/components/ProfileSection.jsx`, `app-web/src/components/ProfileSection.test.jsx`, `app-web/src/components/ProfilePopupContent.jsx`, `app-web/src/components/ProfilePopupContent.test.jsx`
- Modify: `app-web/src/components/PopupContent.jsx`, `app-web/src/components/PopupContent.test.jsx`

**Interfaces:**
- Consumes: `PROFILE_DIMENSIONS` (`lib/constants.js`, Task 5).
- Produces: `<ProfileSection>` (the framing-safe shared breakdown, reused by both `PopupContent` and `ProfilePopupContent` — mirrors how `CompetitorSection` is already reused by both `PopupContent` and `DeltaPopupContent`), `<ProfilePopupContent>` (consumed by Task 5's `ProfileLayer`, completing the forward reference from Task 5 Step 6).

- [ ] **Step 1: Write the failing tests**

Create `app-web/src/components/ProfileSection.test.jsx`:

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ProfileSection from './ProfileSection';

const props = {
  total_eleitores: 500,
  pct_mulheres: 55.2, pct_homens: 44.1, pct_genero_nao_informado: 0.7,
  pct_jovens_16_24: 15.0, pct_adultos_25_59: 60.0, pct_60_mais: 24.0, pct_idade_nao_informado: 1.0,
  pct_ate_fundamental: 20.0, pct_ensino_medio: 45.0, pct_ensino_superior: 34.0, pct_escolaridade_nao_informado: 1.0,
};

describe('ProfileSection', () => {
  it('renders the framing-safe title and mandatory subtitle', () => {
    render(<ProfileSection props={props} defaultOpen />);
    expect(screen.getByText('Perfil do eleitorado deste local')).toBeInTheDocument();
    expect(screen.getByText(/Composicao do eleitorado local/)).toBeInTheDocument();
    expect(screen.getByText(/nao indica em quem estes eleitores votaram/)).toBeInTheDocument();
  });

  it('never renders forbidden candidate-attribution phrasing', () => {
    render(<ProfileSection props={props} defaultOpen />);
    const text = document.body.textContent;
    expect(text).not.toMatch(/eleitores d[eo] (Hugo|Felipe|candidato)/i);
    expect(text).not.toMatch(/quem votou/i);
  });

  it('renders all 11 fields grouped under 3 dimension headers, plus total', () => {
    render(<ProfileSection props={props} defaultOpen />);
    expect(screen.getByText('500')).toBeInTheDocument();
    expect(screen.getByText('Genero')).toBeInTheDocument();
    expect(screen.getByText('Faixa etaria')).toBeInTheDocument();
    expect(screen.getByText('Escolaridade')).toBeInTheDocument();
    expect(screen.getByText('55,2%')).toBeInTheDocument();
    expect(screen.getByText('% 60+')).toBeInTheDocument();
    expect(screen.getByText('34%')).toBeInTheDocument();
  });

  it('is collapsed by default unless defaultOpen is set', () => {
    render(<ProfileSection props={props} />);
    const details = screen.getByText('Perfil do eleitorado deste local').closest('details');
    expect(details).not.toHaveAttribute('open');
  });

  it('shows a dash for missing fields instead of crashing', () => {
    render(<ProfileSection props={{}} defaultOpen />);
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThan(0);
  });
});
```

Create `app-web/src/components/ProfilePopupContent.test.jsx`:

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ProfilePopupContent from './ProfilePopupContent';

const p = {
  nm_local: 'Escola Teste', bairro: 'Icarai', ano: 2022, nr_local: '1015',
  total_eleitores: 500, pct_mulheres: 55.2,
};

describe('ProfilePopupContent', () => {
  it('renders the local header and the profile breakdown expanded by default', () => {
    render(<ProfilePopupContent p={p} />);
    expect(screen.getByText('Escola Teste')).toBeInTheDocument();
    expect(screen.getByText('Icarai')).toBeInTheDocument();
    expect(screen.getByText('2022')).toBeInTheDocument();
    const details = screen.getByText('Perfil do eleitorado deste local').closest('details');
    expect(details).toHaveAttribute('open');
  });
});
```

Append to `app-web/src/components/PopupContent.test.jsx` (read the file first to match its existing fixture shape and imports):

```jsx
it('renders the demographic profile section on hugo_leal, felipe_peixoto, and psd popups alike', () => {
  const withProfile = { ...hugoProps, total_eleitores: 500, pct_mulheres: 55.2 };
  const { rerender } = render(<PopupContent p={withProfile} layerKey="hugo_leal" />);
  expect(screen.getByText('Perfil do eleitorado deste local')).toBeInTheDocument();

  rerender(<PopupContent p={withProfile} layerKey="felipe_peixoto" />);
  expect(screen.getByText('Perfil do eleitorado deste local')).toBeInTheDocument();

  const psdProps = { nm_local: 'Escola Teste', bairro: 'Icarai', ano: 2022, QT_VOTOS: 500, n_secoes: 3, total_eleitores: 500, pct_mulheres: 55.2 };
  rerender(<PopupContent p={psdProps} layerKey="psd" />);
  expect(screen.getByText('Perfil do eleitorado deste local')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- --run` (from `app-web/`)
Expected: FAIL on the new `ProfileSection`/`ProfilePopupContent` tests (modules don't exist), and on `PopupContent`'s new test (section not yet rendered). `ProfileLayer.test.jsx`'s Task 5 failure now also resolves once `ProfilePopupContent` exists — confirm it does after this task's Step 5.

- [ ] **Step 3: Create `ProfileSection.jsx`**

```jsx
import { PROFILE_DIMENSIONS } from '../lib/constants';

function formatPct(v) {
  if (v === null || v === undefined) return '—';
  return `${Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
}

export default function ProfileSection({ props, defaultOpen = false }) {
  const total = props.total_eleitores;

  return (
    <details className="popup-competitors" open={defaultOpen || undefined}>
      <summary>Perfil do eleitorado deste local</summary>
      <div className="control-note">Composicao do eleitorado local — nao indica em quem estes eleitores votaram.</div>
      <div className="popup-row">
        <span className="popup-label">Total eleitores</span>
        <span className="popup-val">{total != null ? Number(total).toLocaleString('pt-BR') : '—'}</span>
      </div>
      {PROFILE_DIMENSIONS.map(dim => (
        <div key={dim.id}>
          <div className="popup-row" style={{ borderTop: '1px solid rgba(255,255,255,0.1)', marginTop: 4, paddingTop: 4 }}>
            <span className="popup-label">{dim.label}</span>
          </div>
          {dim.metrics.map(m => (
            <div className="popup-row" key={m.id}>
              <span className="popup-label">{m.label}</span>
              <span className="popup-val">{formatPct(props[m.field])}</span>
            </div>
          ))}
        </div>
      ))}
    </details>
  );
}
```

- [ ] **Step 4: Create `ProfilePopupContent.jsx`**

```jsx
import ProfileSection from './ProfileSection';

export default function ProfilePopupContent({ p }) {
  return (
    <div>
      <div className="popup-title">{p.nm_local || `Local ${p.nr_local}`}</div>
      <div className="popup-bairro">{p.bairro || ''}</div>
      <div className="popup-row"><span className="popup-label">Ano</span><span className="popup-val">{p.ano}</span></div>
      <ProfileSection props={p} defaultOpen />
    </div>
  );
}
```

- [ ] **Step 5: Wire `ProfileSection` into `PopupContent.jsx`**

In `app-web/src/components/PopupContent.jsx`, add the import:

```jsx
import ProfileSection from './ProfileSection';
```

Replace the line `{layerKey === 'psd' && <PsdBreakdownSection props={p} />}` with:

```jsx
          {layerKey === 'psd' && <PsdBreakdownSection props={p} />}
          <ProfileSection props={p} />
```

(Unconditional — renders on all three layer keys, per the explicit design decision that the demographic breakdown is a property of the location, not the candidate.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `npm test -- --run` (from `app-web/`)
Expected: full suite passes, including `ProfileLayer.test.jsx`'s two tests from Task 5 (now resolved) and all new tests from this task.

- [ ] **Step 7: Commit**

```bash
git add app-web/src/components/ProfileSection.jsx app-web/src/components/ProfileSection.test.jsx app-web/src/components/ProfilePopupContent.jsx app-web/src/components/ProfilePopupContent.test.jsx app-web/src/components/PopupContent.jsx app-web/src/components/PopupContent.test.jsx
git commit -m "feat: add framing-safe demographic breakdown to all three marker popups"
```

---

### Task 7: Frontend — wire `ProfileLayer` into the CAMADAS panel

**Files:**
- Modify: `app-web/src/App.jsx`, `app-web/src/index.css`

**Interfaces:**
- Consumes: `ProfileLayer`, `ProfileMetricFilter`, `PROFILE_METRICS` (Task 5).
- Produces: the "Perfil do Eleitorado" CAMADAS section — this is a leaf integration task, nothing downstream depends on it within this plan.

- [ ] **Step 1: Add the sequential legend CSS**

In `app-web/src/index.css`, near the existing `.delta-scale` rule, add:

```css
.profile-scale { height: 6px; flex: 1; border-radius: 999px; background: linear-gradient(90deg, #d8d8de, #5a3ca0); }
```

- [ ] **Step 2: Add state and data annotation in `App.jsx`**

Replace:

```jsx
  const [toggles, setToggles] = useState({ hugo: true, felipe: true, psd: false, delta: true, regionBoundaries: true, bairroBoundaries: false });
```

with:

```jsx
  const [toggles, setToggles] = useState({ hugo: true, felipe: true, psd: false, delta: true, profile: false, regionBoundaries: true, bairroBoundaries: false });
  const [selectedProfileMetricId, setSelectedProfileMetricId] = useState('mulheres');
```

Replace:

```jsx
    [...BASE_KEYS, 'vote_deltas'].forEach(key => {
```

with:

```jsx
    [...BASE_KEYS, 'vote_deltas', 'voter_profile'].forEach(key => {
```

(So region/bairro filtering also applies to `ProfileLayer` markers, consistent with every other layer on the map.)

Add the import:

```jsx
import ProfileLayer from './components/ProfileLayer.jsx';
import ProfileMetricFilter from './components/ProfileMetricFilter.jsx';
```

and:

```jsx
import { BASE_KEYS, DELTA_METRICS, PROFILE_METRICS } from './lib/constants.js';
```

(extending the existing `constants.js` import line, not adding a second one).

- [ ] **Step 3: Compute the filtered profile features**

After the existing `deltaFeats` computation block (the `const deltaFeats = ...` / `if (data.vote_deltas && pair && toggles.delta) { ... }` block), add:

```jsx
  const profileFeats = data.voter_profile && year
    ? data.voter_profile.features.filter(f => f.properties.ano === year).filter(f => passesGeoFilter(f.properties, selectedRegion, selectedBairro))
    : [];
```

- [ ] **Step 4: Render `ProfileLayer` inside `MapView`**

Replace:

```jsx
        {toggles.delta && pair && (
          <DeltaLayer features={deltaFeats} metric={DELTA_METRICS[selectedDeltaMetric]} selectedDeltaMetric={selectedDeltaMetric} data={data} />
        )}
      </MapView>
```

with:

```jsx
        {toggles.delta && pair && (
          <DeltaLayer features={deltaFeats} metric={DELTA_METRICS[selectedDeltaMetric]} selectedDeltaMetric={selectedDeltaMetric} data={data} />
        )}
        {toggles.profile && (
          <ProfileLayer features={profileFeats} metric={PROFILE_METRICS[selectedProfileMetricId]} />
        )}
      </MapView>
```

- [ ] **Step 5: Add the CAMADAS panel section**

Replace:

```jsx
        <div className="delta-legend"><span>perdeu</span><span className="delta-scale" /><span>ganhou</span></div>

        <div className="section-title">Regiao / Bairro</div>
```

with:

```jsx
        <div className="delta-legend"><span>perdeu</span><span className="delta-scale" /><span>ganhou</span></div>

        <div className="section-title">Perfil do Eleitorado</div>
        <label className="layer-row">
          <input type="checkbox" checked={toggles.profile} onChange={() => setToggles(t => ({ ...t, profile: !t.profile }))} />
          <span className="layer-dot" style={{ background: '#5a3ca0' }} />
          <span className="layer-label">Perfil do eleitorado</span>
          <span className="layer-count">{profileFeats.length || '-'}</span>
        </label>
        <ProfileMetricFilter selectedMetricId={selectedProfileMetricId} onChange={setSelectedProfileMetricId} />
        <div className="delta-legend"><span>menor concentracao</span><span className="profile-scale" /><span>maior concentracao</span></div>

        <div className="section-title">Regiao / Bairro</div>
```

- [ ] **Step 6: Run the full test suite**

Run: `npm test -- --run` (from `app-web/`)
Expected: all tests pass — this task adds no new test file (it's integration wiring in an already-covered component), but must not break any existing `App.jsx`-adjacent test.

- [ ] **Step 7: Manual browser check**

Run `npm run dev` from `app-web/` (real data from Task 3's pipeline run should already be present in `app/data.js`). Verify:
1. "Perfil do Eleitorado" section appears in CAMADAS, toggle off by default, map unchanged until toggled on.
2. Toggling it on shows colored markers (light-to-purple, not red/green) once a metric is selected.
3. `ProfileMetricFilter`'s two-row selector correctly switches dimension groups and, within a group, switches which metric colors the map.
4. Clicking a profile marker opens `ProfilePopupContent`, expanded by default, showing the framing-safe title/subtitle and all 11 fields.
5. Clicking a Hugo/Felipe/PSD marker's popup, expanding "Perfil do eleitorado deste local", shows the same data, collapsed by default.
6. Region/bairro filtering also restricts which profile markers appear.

Record concrete values observed (real local names, real percentages), not vague confirmation — a reviewer will cross-check against real data, matching this project's established verification standard.

- [ ] **Step 8: Commit**

```bash
git add app-web/src/App.jsx app-web/src/index.css
git commit -m "feat: wire ProfileLayer into the CAMADAS panel"
```

---

### Task 8: Full pipeline run and regression verification

**Files:** none (verification only; fix any discrepancy found in whichever task's file owns it, then re-run this task's checklist).

**Interfaces:** none — this is the plan's exit criterion.

- [ ] **Step 1: Run the full pipeline in the correct documented order**

```bash
python scripts/05_build_geojson.py
python scripts/08_candidacy_matrix.py
python scripts/09_voter_profile_geojson.py
python scripts/06_build_vote_deltas.py
python scripts/07_top_competitors.py
```

Expected: all five complete with `Done.`, no unhandled exceptions. (`01`-`04` are assumed already run — raw/processed data already exists in this project.)

- [ ] **Step 2: Run both full test suites**

Run: `python -m pytest tests/ -v` (from repo root) — expect all tests pass, including every test added across Tasks 1-3.
Run: `npm test -- --run` (from `app-web/`) — expect all tests pass, including every test added across Tasks 5-7.

- [ ] **Step 3: Verify the 11 fields are correct end to end on real, freshly-regenerated data**

```bash
python -c "
import json
vp = json.load(open('data/geo/voter_profile.geojson', encoding='utf-8'))
assert len(vp['features']) > 0, 'voter_profile.geojson is empty'
bad = [f for f in vp['features'] if any(k.startswith('rac__') for k in f['properties'])]
assert not bad, f'race field leaked into {len(bad)} features'

sample = vp['features'][0]['properties']
dim_totals = {
    'genero': sum(sample.get(k, 0) or 0 for k in ('pct_mulheres','pct_homens','pct_genero_nao_informado')),
    'idade': sum(sample.get(k, 0) or 0 for k in ('pct_jovens_16_24','pct_adultos_25_59','pct_60_mais','pct_idade_nao_informado')),
    'escolaridade': sum(sample.get(k, 0) or 0 for k in ('pct_ate_fundamental','pct_ensino_medio','pct_ensino_superior','pct_escolaridade_nao_informado')),
}
for dim, total in dim_totals.items():
    assert 95 <= total <= 105, f'{dim} shares sum to {total}, expected ~100'

hugo = json.load(open('data/geo/hugo_leal.geojson', encoding='utf-8'))
merged = [f for f in hugo['features'] if 'pct_mulheres' in f['properties']]
assert len(merged) > 0, 'profile fields never reached hugo_leal.geojson'
felipe = json.load(open('data/geo/felipe_peixoto.geojson', encoding='utf-8'))
assert any('pct_mulheres' in f['properties'] for f in felipe['features'])
psd = json.load(open('data/geo/psd.geojson', encoding='utf-8'))
assert any('pct_mulheres' in f['properties'] for f in psd['features'])

data_js = open('app/data.js', encoding='utf-8').read()
assert '\"voter_profile\"' in data_js, 'voter_profile missing from app/data.js'
print('OK — 11 fields present, exhaustive, race-free, and merged onto all three candidate layers plus the app bundle')
"
```

Expected: `OK` printed, no assertion error.

- [ ] **Step 4: Manual browser walkthrough**

Run `npm run dev` from `app-web/`. Repeat Task 7 Step 7's checklist against the freshly-regenerated data (not the data from Task 7, which predates this task's full pipeline re-run), plus:
1. Confirm the framing-safe subtitle text renders correctly with real accented characters (`Composição`/`não`) — verify no mojibake from the pipeline's encoding handling.
2. Confirm switching between all three dimensions and multiple metrics within each produces visibly different marker colorings.
3. Confirm the existing candidate/delta layers and Região/Bairro filtering still work unchanged — this task's changes shouldn't have touched that code path.

Stop the dev server (specific PID only — never a blanket process-kill command).

- [ ] **Step 5: Fix any discrepancy found**

If a mismatch turns up, fix it in the file from whichever earlier task owns it, extend that task's existing test file to cover the specific case, re-run the relevant test suite, and re-check the specific checklist item before continuing.

- [ ] **Step 6: Final commit**

Review `git status` in full before staging — this stages every regenerated data file (the one commit in this whole plan that does), so scan for anything unexpected first.

```bash
git add -A
git commit -m "chore: voter profile integration pipeline run and regression verification complete"
```
