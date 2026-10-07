# Top Competitors per Local Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Hugo→Felipe/PSD migration-signal guess in `06_build_vote_deltas.py` with a factual "who else is winning this local" competitor ranking, surfaced as a collapsible section in the map popups.

**Architecture:** A new script, `scripts/07_top_competitors.py`, re-reads the raw TSE `votacao_secao_{year}` files (they were only ever filtered down to Hugo/Felipe/PSD by `02_process_votes.py`, discarding every other candidate), ranks the top-3 non-Hugo/non-Felipe candidates per `(year, cargo, local)`, and merges those fields directly onto the existing `hugo_leal.geojson` / `felipe_peixoto.geojson` features produced by `05_build_geojson.py`. `06_build_vote_deltas.py` loses its migration-signal fields but keeps its delta/churn computation. Shared chunked-CSV-reading helpers move to a new `scripts/_pipeline_utils.py` so `06` and `07` don't duplicate ~50 lines of encoding-fallback logic. `app/index.html` gets a native `<details>` collapsible section in both popup builders.

**Tech Stack:** Python 3.11+, pandas, pytest (new dev dependency), vanilla Leaflet/JS (no frameworks — existing project constraint).

## Global Constraints

- `LEAL` is not currently a git repository. Every "Commit" step below is written as if it were — skip those steps (or run `git init` first if the user asks for one) until then.
- No frameworks in `app/` — vanilla Leaflet and vanilla JS only.
- No ideology/political-spectrum labeling of competitors — name + party + votes only.
- No minimum-vote threshold on the top-3 ranking — always show the literal top 3.
- Local-level granularity only — no seção-level competitor breakdown.
- Shared-cargo years (Hugo and Felipe running the same cargo the same year, e.g. 2022 Deputado Federal) get exactly one ranking computed and reused for both, excluding both of them from the candidate pool.

---

## File Structure

- **Create** `scripts/_pipeline_utils.py` — shared TSE CSV reading helpers (`normalize`, `clean_id`/`clean_id_series`, `find_csv`, `read_csv_safe`, `read_tse_csv_safe`, `read_tse_chunks_safe`) and `rebuild_data_js`/`APP_GEOJSON_LAYERS`, extracted out of `06_build_vote_deltas.py` so `07` can reuse them without duplication.
- **Create** `scripts/07_top_competitors.py` — the new competitor-ranking script.
- **Create** `tests/conftest.py` — `load_script()` helper for importing the numeric-prefixed script files (`06_build_vote_deltas.py`, `07_top_competitors.py` aren't valid Python module names, so tests load them by file path).
- **Create** `tests/test_pipeline_utils.py`, `tests/test_top_competitors.py`, `tests/test_vote_deltas.py` — unit tests.
- **Modify** `scripts/06_build_vote_deltas.py` — use `_pipeline_utils` instead of local copies; remove migration-signal fields/logic.
- **Modify** `app/index.html` — remove `Leitura`/`Força da leitura` popup rows and `humanSignal()`; add a collapsible `Concorrência` section to both popup builders.
- **Modify** `README.md` — document the new script and drop the migration-signal description.
- **Modify** `requirements.txt` — add `pytest`.

---

### Task 1: Extract shared pipeline utilities

**Files:**
- Create: `scripts/_pipeline_utils.py`
- Modify: `scripts/06_build_vote_deltas.py:1-101` (imports and helper functions), `:37-42` (`APP_GEOJSON_LAYERS`), `:545-559` (`rebuild_data_js`), `:590` (call site)
- Modify: `requirements.txt`
- Test: `tests/conftest.py`, `tests/test_pipeline_utils.py`

**Interfaces:**
- Produces: `normalize(value: str) -> str`, `clean_id(value) -> str`, `clean_id_series(series: pd.Series) -> pd.Series`, `find_csv(folder: Path) -> Path | None`, `read_csv_safe(path: Path, **kwargs) -> pd.DataFrame`, `read_tse_csv_safe(path: Path, **kwargs) -> pd.DataFrame`, `read_tse_chunks_safe(path: Path, **kwargs) -> Iterator[pd.DataFrame]`, `rebuild_data_js(data_geo: Path, app_dir: Path, layers: list[str] = APP_GEOJSON_LAYERS) -> None`, `APP_GEOJSON_LAYERS: list[str]`, `ENCODINGS: list[str]`, `CHUNKSIZE: int` — all consumed by Task 4 (`07_top_competitors.py`) and by the Task 1 edit to `06_build_vote_deltas.py`.
- `tests/conftest.py` produces: `load_script(module_name: str, filename: str) -> ModuleType` — consumed by every later test file.

- [ ] **Step 1: Add pytest to requirements**

Edit `requirements.txt`, append:

```
pytest>=7.4
```

- [ ] **Step 2: Install pytest**

Run: `pip install -r requirements.txt`

- [ ] **Step 3: Write the test-loading helper**

Create `tests/conftest.py`:

```python
"""Shared pytest helpers. Scripts in scripts/ start with digits (e.g.
06_build_vote_deltas.py), so they can't be imported as normal Python
modules — this loads them directly from their file path instead."""

import importlib.util
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def load_script(module_name: str, filename: str):
    path = SCRIPTS_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
```

- [ ] **Step 4: Write the failing test for `_pipeline_utils`**

Create `tests/test_pipeline_utils.py`:

```python
import json

from conftest import load_script

pu = load_script("_pipeline_utils", "_pipeline_utils.py")


def test_normalize_strips_accents_and_uppercases():
    assert pu.normalize("hugo leal") == "HUGO LEAL"
    assert pu.normalize("Niterói") == "NITEROI"


def test_clean_id_strips_trailing_float_suffix():
    assert pu.clean_id("1058.0") == "1058"
    assert pu.clean_id("1058") == "1058"
    assert pu.clean_id(None) == ""


def test_rebuild_data_js_writes_only_existing_layers(tmp_path):
    data_geo = tmp_path / "geo"
    data_geo.mkdir()
    app_dir = tmp_path / "app"
    (data_geo / "hugo_leal.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8"
    )

    pu.rebuild_data_js(data_geo, app_dir, layers=["hugo_leal", "felipe_peixoto"])

    data_js = (app_dir / "data.js").read_text(encoding="utf-8")
    assert data_js.startswith("const DATA = ")
    assert '"hugo_leal"' in data_js
    assert "felipe_peixoto" not in data_js
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `python -m pytest tests/test_pipeline_utils.py -v` (from the `LEAL` directory)
Expected: FAIL — `scripts/_pipeline_utils.py` doesn't exist yet (`FileNotFoundError` or `ModuleNotFoundError` from `load_script`).

- [ ] **Step 6: Create `scripts/_pipeline_utils.py`**

```python
"""Shared TSE CSV reading helpers used by the LEAL data pipeline scripts."""

import json
from pathlib import Path

import pandas as pd
from unidecode import unidecode

ENCODINGS = ["latin-1", "utf-8", "cp1252"]
CHUNKSIZE = 200_000


def normalize(value: str) -> str:
    return unidecode(str(value)).upper().strip()


def clean_id(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().strip('"')
    if text.endswith(".0"):
        text = text[:-2]
    return text


def clean_id_series(series: pd.Series) -> pd.Series:
    return series.map(clean_id)


def find_csv(folder: Path) -> Path | None:
    for pattern in ("*.csv", "*.txt"):
        files = sorted(folder.glob(pattern))
        if files:
            return files[0]
    return None


def read_csv_safe(path: Path, **kwargs) -> pd.DataFrame:
    for enc in ENCODINGS:
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    raise ValueError(f"Cannot read {path} with any configured encoding")


def read_tse_csv_safe(path: Path, **kwargs) -> pd.DataFrame:
    return read_csv_safe(path, sep=";", dtype=str, **kwargs)


def read_tse_chunks_safe(path: Path, **kwargs):
    last_error = None
    for enc in ENCODINGS:
        try:
            reader = pd.read_csv(
                path,
                sep=";",
                encoding=enc,
                dtype=str,
                chunksize=CHUNKSIZE,
                **kwargs,
            )
            for chunk in reader:
                yield chunk
            return
        except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as exc:
            last_error = exc
            continue
    raise ValueError(f"Cannot read {path} in chunks") from last_error


APP_GEOJSON_LAYERS = ["hugo_leal", "felipe_peixoto", "psd", "vote_deltas"]


def rebuild_data_js(data_geo: Path, app_dir: Path, layers: list[str] = APP_GEOJSON_LAYERS) -> None:
    all_data = {}
    for name in layers:
        path = data_geo / f"{name}.geojson"
        if path.exists():
            all_data[name] = json.loads(path.read_text(encoding="utf-8"))

    app_dir.mkdir(exist_ok=True)
    data_js = app_dir / "data.js"
    data_js.write_text(
        "const DATA = " + json.dumps(all_data, ensure_ascii=False, separators=(",", ":")) + ";",
        encoding="utf-8",
    )
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest tests/test_pipeline_utils.py -v`
Expected: PASS (3 tests)

- [ ] **Step 8: Point `06_build_vote_deltas.py` at the shared helpers**

In `scripts/06_build_vote_deltas.py`, replace the import block:

```python
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
from unidecode import unidecode

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import ALL_YEARS, DATA_GEO, DATA_PROCESSED, DATA_RAW, MUNICIPIO

ENCODINGS = ["latin-1", "utf-8", "cp1252"]
CHUNKSIZE = 200_000
MIN_SIGNAL_VOTES = 10
```

with:

```python
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import ALL_YEARS, DATA_GEO, DATA_PROCESSED, DATA_RAW, MUNICIPIO
from _pipeline_utils import (
    APP_GEOJSON_LAYERS,
    clean_id_series,
    find_csv,
    normalize,
    read_tse_csv_safe,
    read_tse_chunks_safe,
    rebuild_data_js as _rebuild_data_js,
)
```

Then delete these now-duplicated function definitions from the file (they live in `_pipeline_utils.py` now): `normalize`, `clean_id`, `clean_id_series`, `find_csv`, `read_csv_safe`, `read_tse_csv_safe`, `read_tse_chunks_safe`, and the `APP_GEOJSON_LAYERS = [...]` list.

Delete the local `rebuild_data_js()` function (the one that builds `app_dir` and writes `data.js`) and update its call site in `main()`:

```python
    print("\nUpdating app bundle ...")
    rebuild_data_js()
```

becomes:

```python
    print("\nUpdating app bundle ...")
    _rebuild_data_js(DATA_GEO, DATA_GEO.parent.parent / "app")
```

- [ ] **Step 9: Verify `06` still imports and runs**

Run: `python -c "import sys; sys.path.insert(0, 'scripts'); import importlib.util; spec = importlib.util.spec_from_file_location('m', 'scripts/06_build_vote_deltas.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print('ok')"` (from the `LEAL` directory)
Expected: `ok` printed, no `ImportError`/`NameError`.

If you have the raw TSE data available locally, also run the real script end to end and confirm it completes without error and `data/geo/vote_deltas.geojson` / `app/data.js` are rewritten:

Run: `python scripts/06_build_vote_deltas.py`
Expected: Completes with `Done.`, same file outputs as before this refactor (field names unchanged at this point — only the *location* of the helper functions changed).

- [ ] **Step 10: Commit**

```bash
git add requirements.txt tests/conftest.py tests/test_pipeline_utils.py scripts/_pipeline_utils.py scripts/06_build_vote_deltas.py
git commit -m "refactor: extract shared TSE CSV helpers into _pipeline_utils"
```

(If this project isn't a git repo yet, skip this step — `git init` first only if the user asks for it.)

---

### Task 2: Ranking core — candidate filtering and top-3 selection

**Files:**
- Create: `scripts/07_top_competitors.py` (started here, extended in Tasks 3 and 4)
- Test: `tests/test_top_competitors.py`

**Interfaces:**
- Consumes: nothing from other tasks yet (pure logic, no I/O).
- Produces: `TOP_N = 3`, `BLANK_NULL_CODES: set[str]`, `PROPORTIONAL_CARGOS: set[str]`, `is_real_candidate(nr_votavel: str, cargo_norm: str) -> bool`, `build_party_lookup(df_year: pd.DataFrame) -> dict[str, str]`, `party_for(nr_votavel: str, party_lookup: dict[str, str]) -> str`, `rank_top3_by_local(df_cargo: pd.DataFrame, exclude: set[str], party_lookup: dict[str, str]) -> dict[str, list[dict]]`, `top3_fields(entries: list[dict]) -> dict` — all consumed by Task 3 and Task 4 of this same file, and by `tests/test_top_competitors.py`.

**Background on `is_real_candidate`:** verified against real 2022 Niterói data — Deputado Federal candidate numbers are always 4 digits, Deputado Estadual always 5; legenda (party-list) votes and voto branco (95) / voto nulo (96) are always ≤2 digits in proportional races. Prefeito is majoritarian: legitimate candidate numbers there ARE 2 digits (equal to the party number), so the length rule only applies to proportional cargos (`DEPUTADO FEDERAL`, `DEPUTADO ESTADUAL`) — for `PREFEITO` only the explicit 95/96 codes are excluded.

**Background on `build_party_lookup`:** the raw `votacao_secao` files have no party-name column. Legenda rows in proportional races repeat the full party name as `NM_VOTAVEL` (e.g. `NR_VOTAVEL="55"`, `NM_VOTAVEL="Partido Social Democrático"`) — this builds a `party number -> party name` map from those rows within the same year's data, rather than hardcoding a party-number table that would need to stay in sync with TSE registrations across 2010–2024.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_top_competitors.py`:

```python
import pandas as pd

from conftest import load_script

tc = load_script("_top_competitors", "07_top_competitors.py")


def make_df(rows):
    return pd.DataFrame(rows)


def test_is_real_candidate_excludes_blank_and_null():
    assert tc.is_real_candidate("95", "DEPUTADO FEDERAL") is False
    assert tc.is_real_candidate("96", "PREFEITO") is False


def test_is_real_candidate_excludes_legenda_for_proportional_cargo():
    assert tc.is_real_candidate("55", "DEPUTADO FEDERAL") is False


def test_is_real_candidate_keeps_two_digit_number_for_majoritarian_cargo():
    assert tc.is_real_candidate("55", "PREFEITO") is True


def test_is_real_candidate_keeps_full_candidate_number():
    assert tc.is_real_candidate("5512", "DEPUTADO FEDERAL") is True
    assert tc.is_real_candidate("10008", "DEPUTADO ESTADUAL") is True


def test_build_party_lookup_reads_legenda_rows_only():
    df = make_df([
        {"NR_VOTAVEL": "55", "NM_VOTAVEL": "Partido Social Democratico", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "5512", "NM_VOTAVEL": "FELIPE DOS SANTOS PEIXOTO", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "96", "NM_VOTAVEL": "VOTO NULO", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "12", "NM_VOTAVEL": "AXEL GRAEL", "cargo_norm": "PREFEITO"},
    ])
    lookup = tc.build_party_lookup(df)
    assert lookup == {"55": "Partido Social Democratico"}


def test_party_for_falls_back_to_number_when_unknown():
    assert tc.party_for("9012", {}) == "90"
    assert tc.party_for("5512", {"55": "PSD"}) == "PSD"


def test_rank_top3_by_local_excludes_named_people_and_sorts_by_votes():
    df = make_df([
        {"NR_VOTAVEL": "7733", "NM_VOTAVEL": "AUREO RIBEIRO", "QT_VOTOS": 30, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "5555", "NM_VOTAVEL": "HUGO LEAL", "QT_VOTOS": 100, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "1000", "NM_VOTAVEL": "MARCELO CRIVELLA", "QT_VOTOS": 20, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "1006", "NM_VOTAVEL": "ANTONIO RIBEIRO", "QT_VOTOS": 10, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "95", "NM_VOTAVEL": "VOTO BRANCO", "QT_VOTOS": 5, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
    ])
    result = tc.rank_top3_by_local(df, {"HUGO LEAL"}, {})
    assert list(result.keys()) == ["1015"]
    names = [c["nome"] for c in result["1015"]]
    assert names == ["AUREO RIBEIRO", "MARCELO CRIVELLA", "ANTONIO RIBEIRO"]
    assert "HUGO LEAL" not in names
    assert "VOTO BRANCO" not in names


def test_rank_top3_by_local_caps_at_three():
    rows = [
        {"NR_VOTAVEL": str(1000 + i), "NM_VOTAVEL": f"CAND {i}", "QT_VOTOS": 10 - i, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"}
        for i in range(5)
    ]
    result = tc.rank_top3_by_local(make_df(rows), set(), {})
    assert len(result["1015"]) == 3


def test_rank_top3_by_local_returns_empty_dict_when_no_candidates_survive():
    df = make_df([
        {"NR_VOTAVEL": "5555", "NM_VOTAVEL": "HUGO LEAL", "QT_VOTOS": 100, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
    ])
    assert tc.rank_top3_by_local(df, {"HUGO LEAL"}, {}) == {}


def test_top3_fields_pads_missing_slots_with_none():
    fields = tc.top3_fields([{"nome": "A", "partido": "PSD", "votos": 10}])
    assert fields["top1_nome"] == "A"
    assert fields["top1_partido"] == "PSD"
    assert fields["top1_votos"] == 10
    assert fields["top2_nome"] is None
    assert fields["top2_partido"] is None
    assert fields["top2_votos"] is None
    assert fields["top3_nome"] is None


def test_top3_fields_empty_list_is_all_none():
    fields = tc.top3_fields([])
    assert all(v is None for v in fields.values())
    assert set(fields.keys()) == {
        "top1_nome", "top1_partido", "top1_votos",
        "top2_nome", "top2_partido", "top2_votos",
        "top3_nome", "top3_partido", "top3_votos",
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_top_competitors.py -v`
Expected: FAIL — `scripts/07_top_competitors.py` doesn't exist.

- [ ] **Step 3: Create `scripts/07_top_competitors.py` with the ranking core**

```python
"""Rank the top-3 competing candidates per (year, cargo, local), excluding
Hugo Leal and Felipe Peixoto, and merge them onto hugo_leal.geojson /
felipe_peixoto.geojson."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import FELIPE_PEIXOTO, HUGO_LEAL
from _pipeline_utils import normalize

TOP_N = 3
BLANK_NULL_CODES = {"95", "96"}
PROPORTIONAL_CARGOS = {"DEPUTADO FEDERAL", "DEPUTADO ESTADUAL"}
PEOPLE = {"hugo_leal": HUGO_LEAL, "felipe_peixoto": FELIPE_PEIXOTO}
EXCLUDED_NAMES = {normalize(p["name"]) for p in PEOPLE.values()}


def is_real_candidate(nr_votavel: str, cargo_norm: str) -> bool:
    code = str(nr_votavel).strip()
    if code in BLANK_NULL_CODES:
        return False
    if cargo_norm in PROPORTIONAL_CARGOS and len(code) <= 2:
        return False
    return True


def build_party_lookup(df_year: pd.DataFrame) -> dict[str, str]:
    prop = df_year[df_year["cargo_norm"].isin(PROPORTIONAL_CARGOS)]
    legenda = prop[prop["NR_VOTAVEL"].str.len() <= 2]
    legenda = legenda[~legenda["NR_VOTAVEL"].isin(BLANK_NULL_CODES)]
    pairs = legenda[["NR_VOTAVEL", "NM_VOTAVEL"]].drop_duplicates()
    return dict(zip(pairs["NR_VOTAVEL"], pairs["NM_VOTAVEL"]))


def party_for(nr_votavel: str, party_lookup: dict[str, str]) -> str:
    prefix = str(nr_votavel).strip()[:2]
    return party_lookup.get(prefix, prefix)


def rank_top3_by_local(
    df_cargo: pd.DataFrame, exclude: set[str], party_lookup: dict[str, str]
) -> dict[str, list[dict]]:
    if df_cargo.empty:
        return {}

    keep_mask = df_cargo.apply(
        lambda r: is_real_candidate(r["NR_VOTAVEL"], r["cargo_norm"]), axis=1
    )
    candidates = df_cargo[keep_mask]
    candidates = candidates[~candidates["NM_VOTAVEL"].apply(normalize).isin(exclude)]
    candidates = candidates[candidates["nr_local"] != ""]
    if candidates.empty:
        return {}

    grouped = candidates.groupby(
        ["nr_local", "NR_VOTAVEL", "NM_VOTAVEL"], as_index=False
    )["QT_VOTOS"].sum()

    result: dict[str, list[dict]] = {}
    for nr_local, group in grouped.groupby("nr_local"):
        top = group.sort_values("QT_VOTOS", ascending=False).head(TOP_N)
        result[nr_local] = [
            {
                "nome": row["NM_VOTAVEL"],
                "partido": party_for(row["NR_VOTAVEL"], party_lookup),
                "votos": int(row["QT_VOTOS"]),
            }
            for _, row in top.iterrows()
        ]
    return result


def top3_fields(entries: list[dict]) -> dict:
    fields = {}
    for i in range(TOP_N):
        n = i + 1
        entry = entries[i] if i < len(entries) else None
        fields[f"top{n}_nome"] = entry["nome"] if entry else None
        fields[f"top{n}_partido"] = entry["partido"] if entry else None
        fields[f"top{n}_votos"] = entry["votos"] if entry else None
    return fields
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_top_competitors.py -v`
Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/07_top_competitors.py tests/test_top_competitors.py
git commit -m "feat: add top-competitor ranking core"
```

---

### Task 3: Raw-file loading and shared-cargo-year dedup

**Files:**
- Modify: `scripts/07_top_competitors.py` (append to the file from Task 2)
- Test: `tests/test_top_competitors.py` (append)

**Interfaces:**
- Consumes: `is_real_candidate`, `build_party_lookup`, `rank_top3_by_local`, `EXCLUDED_NAMES`, `PEOPLE` from Task 2.
- Produces: `RAW_COLUMNS: list[str]`, `load_niteroi_year(year: int) -> pd.DataFrame`, `year_cargo_pairs() -> set[tuple[int, str]]`, `build_all_rankings() -> dict[tuple[int, str], dict[str, list[dict]]]`, `rankings_for_person(person_key: str, all_rankings: dict) -> dict[int, dict[str, list[dict]]]`, plus module-level `DATA_RAW`, `MUNICIPIO` — consumed by Task 4 (`main()`) and by `tests/test_top_competitors.py`.

- [ ] **Step 1: Write the failing test for the shared-cargo-year dedup rule**

Append to `tests/test_top_competitors.py`:

```python
def write_fixture_year(raw_dir, year, rows):
    header = "NM_MUNICIPIO;DS_CARGO;NR_VOTAVEL;NM_VOTAVEL;QT_VOTOS;NR_LOCAL_VOTACAO\n"
    folder = raw_dir / f"votacao_secao_{year}"
    folder.mkdir(parents=True)
    lines = [header] + [";".join(row) + "\n" for row in rows]
    (folder / f"votacao_secao_{year}_RJ.csv").write_text("".join(lines), encoding="utf-8")


def test_shared_cargo_year_produces_one_ranking_reused_by_both(tmp_path, monkeypatch):
    write_fixture_year(tmp_path, 2022, [
        ['"NITEROI"', '"Deputado Federal"', '"5555"', '"HUGO LEAL"', '"100"', '"1015"'],
        ['"NITEROI"', '"Deputado Federal"', '"5512"', '"FELIPE DOS SANTOS PEIXOTO"', '"80"', '"1015"'],
        ['"NITEROI"', '"Deputado Federal"', '"1000"', '"MARCELO CRIVELLA"', '"50"', '"1015"'],
        ['"NITEROI"', '"Deputado Federal"', '"95"', '"VOTO BRANCO"', '"5"', '"1015"'],
        ['"OUTRA CIDADE"', '"Deputado Federal"', '"1000"', '"MARCELO CRIVELLA"', '"999"', '"1015"'],
    ])
    monkeypatch.setattr(tc, "DATA_RAW", tmp_path)

    all_rankings = tc.build_all_rankings()
    hugo_rankings = tc.rankings_for_person("hugo_leal", all_rankings)
    felipe_rankings = tc.rankings_for_person("felipe_peixoto", all_rankings)

    assert hugo_rankings[2022] == felipe_rankings[2022]
    assert hugo_rankings[2022]["1015"][0]["nome"] == "MARCELO CRIVELLA"
    assert hugo_rankings[2022]["1015"][0]["votos"] == 50


def test_load_niteroi_year_returns_empty_frame_when_folder_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(tc, "DATA_RAW", tmp_path)
    assert tc.load_niteroi_year(1999).empty
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_top_competitors.py -v -k shared_cargo or missing`
Expected: FAIL — `AttributeError: module has no attribute 'DATA_RAW'` / `build_all_rankings`.

- [ ] **Step 3: Append the raw-loading functions to `scripts/07_top_competitors.py`**

Update the imports at the top of the file:

```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_RAW, FELIPE_PEIXOTO, HUGO_LEAL, MUNICIPIO
from _pipeline_utils import clean_id_series, find_csv, normalize, read_tse_chunks_safe
```

Append:

```python
RAW_COLUMNS = ["NM_MUNICIPIO", "DS_CARGO", "NR_VOTAVEL", "NM_VOTAVEL", "QT_VOTOS", "NR_LOCAL_VOTACAO"]


def load_niteroi_year(year: int) -> pd.DataFrame:
    folder = DATA_RAW / f"votacao_secao_{year}"
    csv_file = find_csv(folder)
    if csv_file is None:
        return pd.DataFrame()

    pieces = []
    for chunk in read_tse_chunks_safe(csv_file, usecols=RAW_COLUMNS):
        mask = chunk["NM_MUNICIPIO"].apply(lambda x: normalize(x) == normalize(MUNICIPIO))
        nit = chunk.loc[mask].copy()
        if not nit.empty:
            pieces.append(nit)
    if not pieces:
        return pd.DataFrame()

    df = pd.concat(pieces, ignore_index=True)
    df["QT_VOTOS"] = pd.to_numeric(df["QT_VOTOS"], errors="coerce").fillna(0).astype(int)
    df["nr_local"] = clean_id_series(df["NR_LOCAL_VOTACAO"])
    df["cargo_norm"] = df["DS_CARGO"].apply(normalize)
    return df


def year_cargo_pairs() -> set[tuple[int, str]]:
    pairs = set()
    for person in PEOPLE.values():
        for year, info in person["elections"].items():
            pairs.add((year, normalize(info["cargo"])))
    return pairs


def build_all_rankings() -> dict[tuple[int, str], dict[str, list[dict]]]:
    pairs = year_cargo_pairs()
    years = sorted({year for year, _ in pairs})
    rankings = {}
    for year in years:
        print(f"  Reading {year} ...")
        df_year = load_niteroi_year(year)
        if df_year.empty:
            print(f"    [skip] no Niteroi rows for {year}")
            continue
        party_lookup = build_party_lookup(df_year)
        cargos = {cargo for y, cargo in pairs if y == year}
        for cargo in cargos:
            df_cargo = df_year[df_year["cargo_norm"] == cargo]
            rankings[(year, cargo)] = rank_top3_by_local(df_cargo, EXCLUDED_NAMES, party_lookup)
            print(f"    {cargo}: {len(rankings[(year, cargo)])} locais ranked")
    return rankings


def rankings_for_person(person_key: str, all_rankings: dict) -> dict[int, dict[str, list[dict]]]:
    person = PEOPLE[person_key]
    result = {}
    for year, info in person["elections"].items():
        cargo = normalize(info["cargo"])
        result[year] = all_rankings.get((year, cargo), {})
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_top_competitors.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/07_top_competitors.py tests/test_top_competitors.py
git commit -m "feat: load raw TSE files and dedup shared-cargo election years"
```

---

### Task 4: Merge into GeoJSON and wire up `main()`

**Files:**
- Modify: `scripts/07_top_competitors.py` (append)
- Test: `tests/test_top_competitors.py` (append)

**Interfaces:**
- Consumes: `rankings_for_person`, `top3_fields`, `PEOPLE`, `_pipeline_utils.rebuild_data_js` from earlier tasks.
- Produces: `merge_top_competitors(geojson: dict, rankings_by_year: dict[int, dict[str, list[dict]]]) -> dict`, `main() -> None`.

- [ ] **Step 1: Write the failing test for `merge_top_competitors`**

Append to `tests/test_top_competitors.py`:

```python
def test_merge_top_competitors_matches_on_year_and_local():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"ano": 2022, "nr_local": "1015"}, "geometry": None},
            {"type": "Feature", "properties": {"ano": 2018, "nr_local": "1015"}, "geometry": None},
        ],
    }
    rankings_by_year = {
        2022: {"1015": [{"nome": "MARCELO CRIVELLA", "partido": "PRTB", "votos": 50}]},
    }

    tc.merge_top_competitors(geojson, rankings_by_year)

    assert geojson["features"][0]["properties"]["top1_nome"] == "MARCELO CRIVELLA"
    assert geojson["features"][0]["properties"]["top1_votos"] == 50
    assert geojson["features"][1]["properties"]["top1_nome"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_top_competitors.py -v -k merge`
Expected: FAIL — `AttributeError: module 'tc' has no attribute 'merge_top_competitors'`.

- [ ] **Step 3: Append `merge_top_competitors` and `main()` to `scripts/07_top_competitors.py`**

Update imports one more time (add `json`, `DATA_GEO`, and `rebuild_data_js`):

```python
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_GEO, DATA_RAW, FELIPE_PEIXOTO, HUGO_LEAL, MUNICIPIO
from _pipeline_utils import clean_id_series, find_csv, normalize, read_tse_chunks_safe, rebuild_data_js
```

Append:

```python
def merge_top_competitors(geojson: dict, rankings_by_year: dict[int, dict[str, list[dict]]]) -> dict:
    for feature in geojson.get("features", []):
        props = feature["properties"]
        year = props.get("ano")
        nr_local = str(props.get("nr_local", "")).strip()
        entries = rankings_by_year.get(year, {}).get(nr_local, [])
        props.update(top3_fields(entries))
    return geojson


def main() -> None:
    DATA_GEO.mkdir(parents=True, exist_ok=True)

    print("Building competitor rankings from raw TSE files ...")
    all_rankings = build_all_rankings()

    for person_key in PEOPLE:
        path = DATA_GEO / f"{person_key}.geojson"
        if not path.exists():
            print(f"  [skip] {path.name} not found; run 05_build_geojson.py first")
            continue
        geojson = json.loads(path.read_text(encoding="utf-8"))
        rankings = rankings_for_person(person_key, all_rankings)
        merge_top_competitors(geojson, rankings)
        path.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Updated {path.name}")

    print("\nUpdating app bundle ...")
    rebuild_data_js(DATA_GEO, DATA_GEO.parent.parent / "app")
    print("Done.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_top_competitors.py -v`
Expected: PASS (13 tests)

- [ ] **Step 5: Run the full script against real data**

Run: `python scripts/07_top_competitors.py` (from the `LEAL` directory — requires `05_build_geojson.py` to have already been run so `hugo_leal.geojson`/`felipe_peixoto.geojson` exist)
Expected: Prints progress per year, `Updated hugo_leal.geojson`, `Updated felipe_peixoto.geojson`, `Done.`

- [ ] **Step 6: Spot-check the merged output**

Run:

```bash
python -c "
import json
hugo = json.load(open('data/geo/hugo_leal.geojson', encoding='utf-8'))
felipe = json.load(open('data/geo/felipe_peixoto.geojson', encoding='utf-8'))

hugo_2022 = {f['properties']['nr_local']: f['properties'] for f in hugo['features'] if f['properties']['ano'] == 2022}
felipe_2022 = {f['properties']['nr_local']: f['properties'] for f in felipe['features'] if f['properties']['ano'] == 2022}

sample = next(iter(hugo_2022))
h, f = hugo_2022[sample], felipe_2022.get(sample, {})
print('2022 shared-cargo check, local', sample)
print('hugo top1:', h.get('top1_nome'), '| felipe top1:', f.get('top1_nome'))
assert h.get('top1_nome') == f.get('top1_nome'), 'shared-cargo ranking mismatch'
assert h.get('top1_nome') not in ('HUGO LEAL', 'FELIPE DOS SANTOS PEIXOTO', 'VOTO BRANCO', 'VOTO NULO')
print('OK')
"
```

Expected: `OK` printed, no assertion error.

- [ ] **Step 7: Commit**

```bash
git add scripts/07_top_competitors.py tests/test_top_competitors.py
git commit -m "feat: merge top-competitor rankings into hugo_leal/felipe_peixoto geojson"
```

---

### Task 5: Remove the migration signal from `06_build_vote_deltas.py`

**Files:**
- Modify: `scripts/06_build_vote_deltas.py`
- Test: `tests/test_vote_deltas.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: trimmed `add_delta_fields(row: dict, get_votes) -> None` (same signature, fewer fields written) — consumed by `tests/test_vote_deltas.py` and by the app popup work in Task 6 (which stops expecting `mig_signal`/`mig_score`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_vote_deltas.py`:

```python
from conftest import load_script

vd = load_script("_vote_deltas", "06_build_vote_deltas.py")

MIGRATION_FIELDS = {
    "hugo_perda", "felipe_ganho", "psd_ganho",
    "mig_hugo_felipe_votos", "mig_hugo_psd_votos",
    "mig_hugo_felipe_score", "mig_hugo_psd_score",
    "mig_alvo", "mig_score", "mig_votos_correspondentes", "mig_signal",
}


def test_add_delta_fields_no_longer_writes_migration_fields():
    row = {"ano_inicio": 2010, "ano_fim": 2014}
    votes = {
        ("hugo", 2010): 100, ("hugo", 2014): 60,
        ("felipe", 2010): 20, ("felipe", 2014): 55,
        ("psd", 2010): 30, ("psd", 2014): 30,
    }

    def get_votes(key, year):
        return votes.get((key, year), 0)

    vd.add_delta_fields(row, get_votes)

    assert MIGRATION_FIELDS.isdisjoint(row.keys())
    assert not hasattr(vd, "migration_score")
    assert not hasattr(vd, "MIN_SIGNAL_VOTES")


def test_add_delta_fields_keeps_deltas_and_map_fields():
    row = {"ano_inicio": 2010, "ano_fim": 2014}
    votes = {("hugo", 2010): 100, ("hugo", 2014): 60}

    def get_votes(key, year):
        return votes.get((key, year), 0)

    vd.add_delta_fields(row, get_votes)

    assert row["votos_hugo_inicio"] == 100
    assert row["votos_hugo_fim"] == 60
    assert row["delta_hugo"] == -40
    assert row["pct_delta_hugo"] == -40.0
    assert row["map_delta"] == -40
    assert row["map_abs_delta"] == 40
    assert row["tipo_par"] == "Municipal -> Federal"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_vote_deltas.py -v`
Expected: FAIL on `test_add_delta_fields_no_longer_writes_migration_fields` — `mig_signal` etc. are present; `hasattr(vd, "migration_score")` is `True`.

- [ ] **Step 3: Remove the migration-signal constant, function, and fields**

In `scripts/06_build_vote_deltas.py`, delete the `MIN_SIGNAL_VOTES = 10` line (already removed as part of Task 1's import-block edit if done in order — if not, remove it now).

Delete the `migration_score` function:

```python
def migration_score(loss: int, gain: int) -> float:
    if loss <= 0 or gain <= 0:
        return 0.0
    return round(min(loss, gain) / max(loss, gain), 4)
```

Replace the body of `add_delta_fields` — everything from the `hugo_loss = max(...)` line through the end of the function — with just the `map_delta`/`map_abs_delta` lines. Before:

```python
    hugo_loss = max(-row["delta_hugo"], 0)
    felipe_gain = max(row["delta_felipe"], 0)
    psd_gain = max(row["delta_psd"], 0)
    felipe_score = migration_score(hugo_loss, felipe_gain)
    psd_score = migration_score(hugo_loss, psd_gain)

    row["hugo_perda"] = hugo_loss
    row["felipe_ganho"] = felipe_gain
    row["psd_ganho"] = psd_gain
    row["mig_hugo_felipe_votos"] = min(hugo_loss, felipe_gain)
    row["mig_hugo_psd_votos"] = min(hugo_loss, psd_gain)
    row["mig_hugo_felipe_score"] = felipe_score
    row["mig_hugo_psd_score"] = psd_score

    target = ""
    score = 0.0
    matched_votes = 0
    if hugo_loss >= MIN_SIGNAL_VOTES:
        candidates = [
            ("felipe", felipe_score, row["mig_hugo_felipe_votos"]),
            ("psd", psd_score, row["mig_hugo_psd_votos"]),
        ]
        target, score, matched_votes = max(candidates, key=lambda item: (item[1], item[2]))

    if hugo_loss < MIN_SIGNAL_VOTES:
        signal = "sem_perda_hugo_relevante"
    elif matched_votes < MIN_SIGNAL_VOTES:
        signal = "perda_hugo_sem_ganho_correspondente"
    elif score >= 0.75:
        signal = f"forte_hugo_para_{target}"
    elif score >= 0.45:
        signal = f"possivel_hugo_para_{target}"
    else:
        signal = f"fraco_hugo_para_{target}"

    row["mig_alvo"] = target
    row["mig_score"] = score
    row["mig_votos_correspondentes"] = matched_votes
    row["mig_signal"] = signal
    row["map_delta"] = row["delta_hugo"]
    row["map_abs_delta"] = abs(row["delta_hugo"])
```

After:

```python
    row["map_delta"] = row["delta_hugo"]
    row["map_abs_delta"] = abs(row["delta_hugo"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_vote_deltas.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run the full script against real data**

Run: `python scripts/06_build_vote_deltas.py`
Expected: Completes with `Done.`

Then verify the removed columns are actually gone from the CSV:

```bash
python -c "
import pandas as pd
df = pd.read_csv('data/processed/vote_deltas_by_local.csv', nrows=1)
removed = {'hugo_perda','felipe_ganho','psd_ganho','mig_hugo_felipe_votos','mig_hugo_psd_votos','mig_hugo_felipe_score','mig_hugo_psd_score','mig_alvo','mig_score','mig_votos_correspondentes','mig_signal'}
assert removed.isdisjoint(df.columns), df.columns.tolist()
assert 'map_delta' in df.columns and 'delta_hugo' in df.columns
print('OK')
"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add scripts/06_build_vote_deltas.py tests/test_vote_deltas.py
git commit -m "refactor: remove migration-signal guess from vote deltas"
```

---

### Task 6: README updates

**Files:**
- Modify: `README.md`

**Interfaces:** None — documentation only.

- [ ] **Step 1: Update the Pipeline section**

In `README.md`, replace:

```markdown
6. `scripts/06_build_vote_deltas.py` — compute consecutive-election vote deltas and probable Hugo-to-Felipe/PSD migration signals
7. `app/` — web map (Leaflet) for visualization
```

with:

```markdown
6. `scripts/06_build_vote_deltas.py` — compute consecutive-election vote deltas per local de votação (and seção-level churn diagnostics)
7. `scripts/07_top_competitors.py` — rank the top-3 competing candidates (excluding Hugo/Felipe) per local, year, and cargo
8. `app/` — web map (Leaflet) for visualization
```

- [ ] **Step 2: Update the Delta Outputs section**

Replace:

```markdown
## Delta Outputs

`scripts/06_build_vote_deltas.py` writes:

- `data/processed/vote_deltas_by_local.csv`
- `data/processed/vote_deltas_by_secao.csv`
- `data/geo/vote_deltas.geojson`
- `data/geo/vote_deltas_secao.geojson`
- `app/data.js`

The local layer is intended for the Leaflet map. The section layer is a diagnostic output for checking section moves between polling places.
```

with:

```markdown
## Delta Outputs

`scripts/06_build_vote_deltas.py` writes:

- `data/processed/vote_deltas_by_local.csv`
- `data/processed/vote_deltas_by_secao.csv`
- `data/geo/vote_deltas.geojson`
- `data/geo/vote_deltas_secao.geojson`

The local layer is intended for the Leaflet map. The section layer is a diagnostic output for checking section moves between polling places.

## Competitor Outputs

`scripts/07_top_competitors.py` re-reads the raw TSE files (which `02_process_votes.py` filters down to only Hugo/Felipe/PSD, discarding everyone else) and writes `top1_nome`/`top1_partido`/`top1_votos` through `top3_*` properties directly onto the existing `data/geo/hugo_leal.geojson` and `data/geo/felipe_peixoto.geojson` features — the top-3 candidates for that cargo at that local and year, excluding Hugo and Felipe themselves. Also rebuilds `app/data.js`.
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document scripts/07_top_competitors.py"
```

---

### Task 7: Collapsible "Concorrência" section in the map popups

**Files:**
- Modify: `app/index.html`

**Interfaces:**
- Consumes: `top1_nome`/`top1_partido`/`top1_votos` through `top3_*` properties on `DATA.hugo_leal`/`DATA.felipe_peixoto` features (produced by Task 4), and the existing `DELTA_METRICS`, `buildPopup`, `buildDeltaPopup` in `app/index.html`.
- Produces: `COMPETITOR_LAYER_BY_METRIC`, `competitorRows(props)`, `buildCompetitorSection(title, props)`, `findYearLocalFeature(layerKey, ano, nrLocal)` — used only within `app/index.html`, nothing downstream depends on them.

- [ ] **Step 1: Remove the migration-signal popup rows and `humanSignal()`**

In `app/index.html`, find `buildDeltaPopup` and remove these two lines:

```javascript
  html += popupRow('Leitura', humanSignal(p.mig_signal));
  html += popupRow('Forca da leitura', Number(p.mig_score || 0).toLocaleString('pt-BR', { maximumFractionDigits: 2 }));
```

Delete the now-unused `humanSignal` function entirely:

```javascript
function humanSignal(signal) {
  const labels = {
    ...
  };
  return labels[signal] || String(signal || '-').replaceAll('_', ' ');
}
```

- [ ] **Step 2: Add CSS for the collapsible section**

Near the existing `.popup-row`/`.popup-label`/`.popup-val` rules, add:

```css
.popup-competitors { margin-top: 6px; padding-top: 4px; border-top: 1px solid rgba(255,255,255,0.1); }
.popup-competitors summary { cursor: pointer; color: #aaa; font-size: 12px; outline: none; }
.popup-competitors[open] summary { margin-bottom: 4px; }
```

- [ ] **Step 3: Add the competitor lookup and rendering helpers**

Near `DELTA_METRICS` (after its closing `};`), add:

```javascript
const COMPETITOR_LAYER_BY_METRIC = { hugo: 'hugo_leal', felipe: 'felipe_peixoto' };

function findYearLocalFeature(layerKey, ano, nrLocal) {
  const fc = DATA[layerKey];
  if (!fc) return null;
  return fc.features.find(
    f => f.properties.ano === ano && String(f.properties.nr_local) === String(nrLocal)
  ) || null;
}

function competitorRows(props) {
  let rows = '';
  for (let i = 1; i <= 3; i++) {
    const nome = props[`top${i}_nome`];
    if (!nome) continue;
    const partido = props[`top${i}_partido`] || '-';
    const votos = Number(props[`top${i}_votos`] || 0).toLocaleString('pt-BR');
    rows += `<div class="popup-row"><span class="popup-label">${i}º</span><span class="popup-val">${nome} (${partido}) — ${votos}</span></div>`;
  }
  return rows || '<div class="popup-row"><span class="popup-label">Sem dados</span></div>';
}

function buildCompetitorSection(title, props) {
  return `<details class="popup-competitors"><summary>${title}</summary>${competitorRows(props)}</details>`;
}
```

- [ ] **Step 4: Wire the section into `buildPopup`**

In `buildPopup`, the `else` branch (single-year mode) currently ends with:

```javascript
  } else {
    html += `<div class="popup-row"><span class="popup-label">Ano</span><span class="popup-val">${p.ano}</span></div>`;
    html += `<div class="popup-row"><span class="popup-label">Votos</span><span class="popup-val">${p.QT_VOTOS.toLocaleString('pt-BR')}</span></div>`;
    html += `<div class="popup-row"><span class="popup-label">Secoes</span><span class="popup-val">${p.n_secoes}</span></div>`;
  }
```

Add the competitor section only in that branch (the aggregated multi-year `if (p._years)` branch has no single coherent top-3 to show, since `top1_nome` etc. only reflect whichever year's feature was aggregated first — so it's intentionally skipped there):

```javascript
  } else {
    html += `<div class="popup-row"><span class="popup-label">Ano</span><span class="popup-val">${p.ano}</span></div>`;
    html += `<div class="popup-row"><span class="popup-label">Votos</span><span class="popup-val">${p.QT_VOTOS.toLocaleString('pt-BR')}</span></div>`;
    html += `<div class="popup-row"><span class="popup-label">Secoes</span><span class="popup-val">${p.n_secoes}</span></div>`;
    html += buildCompetitorSection('Concorrencia', p);
  }
```

- [ ] **Step 5: Wire the section into `buildDeltaPopup`**

At the end of `buildDeltaPopup`, right before `return html;`, add:

```javascript
  const competitorLayer = COMPETITOR_LAYER_BY_METRIC[selectedDeltaMetric];
  if (competitorLayer) {
    const startFeat = findYearLocalFeature(competitorLayer, p.ano_inicio, p.nr_local);
    const endFeat = findYearLocalFeature(competitorLayer, p.ano_fim, p.nr_local);
    html += buildCompetitorSection(`Concorrencia ${p.ano_inicio}`, startFeat ? startFeat.properties : {});
    html += buildCompetitorSection(`Concorrencia ${p.ano_fim}`, endFeat ? endFeat.properties : {});
  }
```

(When `selectedDeltaMetric` is `psd`, `competitorLayer` is `undefined` and the section is skipped — `07_top_competitors.py` never writes `top*` fields onto a PSD layer, so there's nothing to show there.)

- [ ] **Step 6: Manual browser verification**

Serve the app (any static file server works, e.g. `python -m http.server 8000` from the `LEAL/app` directory) and open it in a browser.

Check:
1. Click a Hugo Leal or Felipe Peixoto marker with a specific year selected. The popup should look exactly as before, plus a collapsed `▸ Concorrencia` line at the bottom. Confirm the popup's default (collapsed) height is unchanged from before this task.
2. Click the `Concorrencia` line — it expands to show up to 3 rows of `Nome (Partido) — votos`.
3. Switch to "all years" (no year filter) and click the same marker — confirm the `Concorrencia` section does NOT appear (aggregated mode).
4. Enable the delta layer, pick a pair, click a marker with the Hugo or Felipe metric selected — confirm two collapsible sections appear (`Concorrencia <ano_inicio>` and `Concorrencia <ano_fim>`), both collapsed by default, both expandable.
5. Switch the delta metric to PSD — confirm no `Concorrencia` section appears on that popup.

- [ ] **Step 7: Commit**

```bash
git add app/index.html
git commit -m "feat: add collapsible competitor section to map popups"
```

---

## Self-Review Notes

- **Spec coverage:** ranking rule + shared-cargo dedup (Tasks 2–4), local-only granularity (no seção code path added anywhere), name+party+votes only (no ideology field anywhere in `top3_fields`), replace-not-add (Task 5 deletes `mig_*` outright), collapsible popup section (Task 7), README documentation (Task 6). All spec sections have a task.
- **Placeholder scan:** no TBD/TODO; every step has literal code, not a description of code.
- **Type consistency:** `rank_top3_by_local` returns `dict[str, list[dict]]` in Task 2 and is consumed with that exact shape in `build_all_rankings` (Task 3) and `merge_top_competitors` (Task 4). `top3_fields` keys (`top1_nome`/`top1_partido`/`top1_votos` … `top3_*`) match exactly what `app/index.html`'s `competitorRows` reads in Task 7. `rankings_for_person` returns `dict[int, dict[str, list[dict]]]`, matching `merge_top_competitors`'s `rankings_by_year` parameter.
- Note: Tasks 2–4 all modify the same file (`scripts/07_top_competitors.py`) incrementally — each task's code block is additive (new imports superseding the previous task's import line, new functions appended below). Follow the tasks in order.
