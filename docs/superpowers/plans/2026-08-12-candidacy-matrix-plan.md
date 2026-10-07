# Candidacy Matrix & Delta Gating Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop treating "didn't run," "party didn't exist yet," and "genuinely got few votes" identically as 0 votes in the vote-delta computation, by gating all deltas off a TSE-registration-backed candidacy matrix.

**Architecture:** A new `scripts/08_candidacy_matrix.py` downloads TSE's `consulta_cand` registration files (currently absent from `data/raw/`), builds `data/processed/candidacy_matrix.csv` (Hugo/Felipe from `consulta_cand`, PSD from party-existence + `psd_by_secao.csv`), and separately builds a PSD slate breakdown by re-reading raw vote files (same mechanism `07_top_competitors.py` already uses). `scripts/06_build_vote_deltas.py` is rewritten to consume the matrix: pairs are found per-candidate by nearest matching cycle within the same election type (Geral vs Municipal), not assumed-consecutive TSE years, and gated-out pairs get `null` + a `candidacy_status` field instead of a fake numeric delta. `scripts/07_top_competitors.py` gains one new field (`total_votos_validos`) for vote-share. The React app (`app-web/`) gets a popup redesign, N/A rendering, a new PSD breakdown section, and two null-coercion bugs fixed (`StatsPanel`, `DeltaLayer`) that would otherwise silently undo the whole point of this work at the aggregate/marker level.

**Tech Stack:** Python 3.11+ (pandas, unchanged pipeline stack), pytest, React 19 + Vite (unchanged frontend stack), Vitest + React Testing Library.

## Global Constraints

- Real TSE URL verified this session: `https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_{year}.zip` — confirmed 200 OK for 2010 and 2022. This is a **national** zip (~30 files: all 27 states + national aggregates), unlike `votacao_secao`'s already-per-UF zips. The Rio de Janeiro file inside is named exactly `consulta_cand_{year}_RJ.csv` — do not reuse `find_csv()` (grabs the first alphabetical `*.csv`, which would be wrong here) to select it.
- Real column names confirmed from the actual 2022 RJ file (50 columns): the ones this plan uses are `NM_CANDIDATO`, `NM_URNA_CANDIDATO`, `DS_CARGO`, `SG_PARTIDO`, `NR_PARTIDO`, `DS_SITUACAO_CANDIDATURA`, `ANO_ELEICAO`.
- Brazilian Municipal and Geral elections never share a calendar year — `election_type(year)` (already implemented identically in both `scripts/06_build_vote_deltas.py:190-191` and `app-web/src/lib/format.js:1-3`) fully determines `tipo_eleicao` from year alone. PSD's own gating therefore does NOT need `consulta_cand` data — party existence (founded 2011, so 2010 is always N/A) plus presence in the already-existing `psd_by_secao.csv` is sufficient.
- PSD's per-candidate breakdown cargo comes directly from the raw `votacao_secao` file's `DS_CARGO` column (same file `07_top_competitors.py` already re-reads) — not from `consulta_cand` either.
- Matrix is authoritative for gating; `config.py`'s `HUGO_LEAL`/`FELIPE_PEIXOTO` `elections` dicts are NOT modified and NOT read by the new gating logic in `06`. If `consulta_cand` disagrees with `config.py`, script 08 prints a loud warning naming the exact discrepancy and proceeds using the matrix; it does not edit `config.py`.
- Vote share denominator: valid votes only (excludes voto branco `95` / voto nulo `96`), matching the existing `is_real_candidate()` filter in `scripts/07_top_competitors.py`.
- Vote share (and the `Cargo pretendido` popup field) applies to Hugo/Felipe and to individual PSD breakdown entries — never to PSD's base aggregate feature, which spans multiple cargos per year and has no single well-defined race total.
- N/A representation: numeric vote/delta fields become `null` (never `0` or a sentinel string) when ungated; a separate `candidacy_status` field carries the reason.
- Pipeline execution order is `01 → 02 → 03 → 04 → 05 → 08 → 06 → 07` — script number is introduction order, not run order. `08` needs `05`'s `psd.geojson` to merge onto, and `06` needs `08`'s matrix. Document this explicitly in the README; do not renumber any script.
- No new frontend dependencies, no TypeScript, no CSS framework (unchanged constraints from the prior migration).

Full design: [`docs/superpowers/specs/2026-08-12-candidacy-matrix-design.md`](../specs/2026-08-12-candidacy-matrix-design.md)

---

### Task 1: Shared plumbing — `_pipeline_utils.py`, `config.py`, `01`'s imports

**Files:**
- Modify: `scripts/_pipeline_utils.py`, `scripts/01_download_tse.py`, `scripts/06_build_vote_deltas.py`, `config.py`
- Test: `tests/test_pipeline_utils.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `download_and_extract(url: str, dest: Path, label: str) -> bool`, `election_type(year: int) -> str` (both now in `_pipeline_utils.py`) — consumed by Task 2's script 08 and by the existing `06_build_vote_deltas.py`. `url_consulta_cand(year: int) -> str` (in `config.py`) — consumed by Task 2.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pipeline_utils.py`:

```python
def test_election_type_classifies_municipal_and_federal_years():
    assert pu.election_type(2012) == "Municipal"
    assert pu.election_type(2022) == "Federal"


def test_download_and_extract_skips_when_already_extracted(tmp_path):
    dest = tmp_path / "already_here"
    dest.mkdir()
    (dest / "existing.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    # No network call should happen — if it tried, this would fail on the
    # fake URL. skip path returns True without touching the network.
    assert pu.download_and_extract("http://example.invalid/x.zip", dest, "test") is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pipeline_utils.py -v` (from the `LEAL` directory)
Expected: FAIL — `_pipeline_utils` has no attribute `election_type` or `download_and_extract`.

- [ ] **Step 3: Move `election_type` into `_pipeline_utils.py`**

In `scripts/_pipeline_utils.py`, add after the existing `normalize` function:

```python
def election_type(year: int) -> str:
    return "Municipal" if year % 4 == 0 else "Federal"
```

- [ ] **Step 4: Move `download_and_extract` into `_pipeline_utils.py`**

Add to `scripts/_pipeline_utils.py` (needs new imports at the top of the file — add `zipfile`, `io`, `requests`, and `tqdm` to the existing import block):

```python
import zipfile
import io

import requests
from tqdm import tqdm
```

Append the function itself:

```python
DOWNLOAD_TIMEOUT = 120
DOWNLOAD_CHUNK = 8192


def download_and_extract(url: str, dest: Path, label: str) -> bool:
    if any(dest.glob("*.csv")) or any(dest.glob("*.txt")):
        print(f"  [skip] {label} — already extracted")
        return True

    dest.mkdir(parents=True, exist_ok=True)
    print(f"  [GET]  {label}")
    print(f"         {url}")

    try:
        resp = requests.get(url, timeout=DOWNLOAD_TIMEOUT, stream=True)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [FAIL] {e}")
        return False

    total = int(resp.headers.get("content-length", 0))
    buf = io.BytesIO()
    with tqdm(total=total, unit="B", unit_scale=True, desc=label, leave=False) as bar:
        for chunk in resp.iter_content(DOWNLOAD_CHUNK):
            buf.write(chunk)
            bar.update(len(chunk))

    buf.seek(0)
    try:
        with zipfile.ZipFile(buf) as zf:
            zf.extractall(dest)
        print(f"  [OK]   {len(list(dest.iterdir()))} files")
    except zipfile.BadZipFile:
        print(f"  [FAIL] bad zip")
        return False
    return True
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_pipeline_utils.py -v`
Expected: PASS (2 new tests plus all pre-existing ones)

- [ ] **Step 6: Point `01_download_tse.py` at the shared helper**

In `scripts/01_download_tse.py`, replace the import block:

```python
import sys, zipfile, io
from pathlib import Path

import requests
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (
    DATA_RAW, ALL_YEARS, FEDERAL_YEARS, MUNICIPAL_YEARS, UF,
    url_votacao_secao, url_perfil_eleitor_secao, url_locais_votacao,
)

TIMEOUT = 120
CHUNK = 8192


def download_and_extract(url: str, dest: Path, label: str) -> bool:
    if any(dest.glob("*.csv")) or any(dest.glob("*.txt")):
        print(f"  [skip] {label} — already extracted")
        return True

    dest.mkdir(parents=True, exist_ok=True)
    print(f"  [GET]  {label}")
    print(f"         {url}")

    try:
        resp = requests.get(url, timeout=TIMEOUT, stream=True)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [FAIL] {e}")
        return False

    total = int(resp.headers.get("content-length", 0))
    buf = io.BytesIO()
    with tqdm(total=total, unit="B", unit_scale=True, desc=label, leave=False) as bar:
        for chunk in resp.iter_content(CHUNK):
            buf.write(chunk)
            bar.update(len(chunk))

    buf.seek(0)
    try:
        with zipfile.ZipFile(buf) as zf:
            zf.extractall(dest)
        print(f"  [OK]   {len(list(dest.iterdir()))} files")
    except zipfile.BadZipFile:
        print(f"  [FAIL] bad zip")
        return False
    return True
```

with:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import (
    DATA_RAW, ALL_YEARS, FEDERAL_YEARS, MUNICIPAL_YEARS, UF,
    url_votacao_secao, url_perfil_eleitor_secao, url_locais_votacao,
)
from _pipeline_utils import download_and_extract
```

(The rest of `01_download_tse.py` — the `main()` function and its `download_and_extract(...)` calls — is unchanged; it's calling the same function, now imported instead of defined locally.)

- [ ] **Step 7: Point `06_build_vote_deltas.py` at the shared `election_type`**

In `scripts/06_build_vote_deltas.py`, update the `_pipeline_utils` import (currently lines 18-25) to add `election_type`:

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

Delete the now-duplicated local function (currently at lines 190-191):

```python
def election_type(year: int) -> str:
    return "Municipal" if year % 4 == 0 else "Federal"
```

- [ ] **Step 8: Add the `consulta_cand` URL helper to `config.py`**

In `config.py`, add after the existing `url_candidato_munzona` function:

```python
def url_consulta_cand(year: int) -> str:
    return f"{TSE_CDN}/consulta_cand/consulta_cand_{year}.zip"
```

- [ ] **Step 9: Verify `01` and `06` still import and run**

Run: `python -m pytest tests/ -v` (from the `LEAL` directory)
Expected: all existing tests still PASS — this task changed only where code lives, not what it does.

If you have the raw TSE data available locally (you do — confirmed present this session), also run `python scripts/06_build_vote_deltas.py` end to end and confirm it completes with `Done.`, identical output to before this refactor.

- [ ] **Step 10: Commit**

```bash
git add scripts/_pipeline_utils.py scripts/01_download_tse.py scripts/06_build_vote_deltas.py config.py tests/test_pipeline_utils.py
git commit -m "refactor: move download_and_extract and election_type into _pipeline_utils"
```

---

### Task 2: Script 08 — candidacy matrix (Hugo/Felipe from consulta_cand, PSD from existence)

**Files:**
- Create: `scripts/08_candidacy_matrix.py`
- Test: `tests/test_candidacy_matrix.py`

**Interfaces:**
- Consumes: `download_and_extract`, `election_type`, `normalize`, `find_csv` (Task 1 / pre-existing `_pipeline_utils.py`), `url_consulta_cand` (Task 1), `HUGO_LEAL`, `FELIPE_PEIXOTO`, `DATA_RAW`, `DATA_PROCESSED` (`config.py`).
- Produces: `RJ_CONSULTA_CAND_COLUMNS: list[str]`, `download_consulta_cand(year: int) -> bool`, `load_consulta_cand_rj(year: int) -> pd.DataFrame`, `match_candidate(df_year: pd.DataFrame, name: str) -> pd.DataFrame`, `build_person_matrix_rows(candidate_key: str, person: dict) -> list[dict]`, `build_psd_matrix_rows() -> list[dict]`, `build_candidacy_matrix() -> pd.DataFrame` — `build_candidacy_matrix`'s output (written to `data/processed/candidacy_matrix.csv`) is consumed by Task 4 (`06_build_vote_deltas.py`'s gating).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_candidacy_matrix.py`:

```python
import pandas as pd

from conftest import load_script

cm = load_script("_candidacy_matrix", "08_candidacy_matrix.py")


def make_consulta_df(rows):
    return pd.DataFrame(rows)


def test_match_candidate_finds_exact_name_match():
    df = make_consulta_df([
        {"NM_CANDIDATO": "HUGO LEAL DA SILVA", "NM_URNA_CANDIDATO": "HUGO LEAL", "DS_CARGO": "DEPUTADO FEDERAL", "SG_PARTIDO": "PSD", "DS_SITUACAO_CANDIDATURA": "DEFERIDO"},
        {"NM_CANDIDATO": "OUTRO CANDIDATO", "NM_URNA_CANDIDATO": "OUTRO", "DS_CARGO": "PREFEITO", "SG_PARTIDO": "PSD", "DS_SITUACAO_CANDIDATURA": "DEFERIDO"},
    ])
    result = cm.match_candidate(df, "HUGO LEAL")
    assert len(result) == 1
    assert result.iloc[0]["DS_CARGO"] == "DEPUTADO FEDERAL"


def test_match_candidate_returns_empty_when_no_match():
    df = make_consulta_df([
        {"NM_CANDIDATO": "OUTRO CANDIDATO", "NM_URNA_CANDIDATO": "OUTRO", "DS_CARGO": "PREFEITO", "SG_PARTIDO": "PSD", "DS_SITUACAO_CANDIDATURA": "DEFERIDO"},
    ])
    result = cm.match_candidate(df, "HUGO LEAL")
    assert result.empty


def test_build_psd_matrix_rows_derives_existence_from_psd_by_secao(tmp_path, monkeypatch):
    psd_csv = tmp_path / "psd_by_secao.csv"
    psd_csv.write_text(
        "ano,NR_ZONA,NR_SECAO,QT_VOTOS\n"
        "2012,1,1,100\n"
        "2016,1,1,50\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cm, "DATA_PROCESSED", tmp_path)

    rows = cm.build_psd_matrix_rows()
    years = {r["ano"] for r in rows}
    assert years == {2012, 2016}
    assert all(r["candidate_key"] == "psd" for r in rows)
    row_2012 = next(r for r in rows if r["ano"] == 2012)
    assert row_2012["tipo_eleicao"] == "Municipal"


def test_build_psd_matrix_rows_returns_empty_when_no_data(tmp_path, monkeypatch):
    monkeypatch.setattr(cm, "DATA_PROCESSED", tmp_path)
    assert cm.build_psd_matrix_rows() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_candidacy_matrix.py -v`
Expected: FAIL — `scripts/08_candidacy_matrix.py` doesn't exist.

- [ ] **Step 3: Create `scripts/08_candidacy_matrix.py` with the matching and PSD-existence logic**

```python
"""Build the candidacy matrix: for Hugo Leal, Felipe Peixoto, and PSD, which
years did they actually run, for which cargo, in which election type —
confirmed from TSE's consulta_cand registration files (Hugo/Felipe) or
derived from party existence + processed vote presence (PSD)."""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_PROCESSED, DATA_RAW, FELIPE_PEIXOTO, HUGO_LEAL, url_consulta_cand
from _pipeline_utils import download_and_extract, election_type, normalize, read_csv_safe

PSD_FOUNDING_YEAR = 2011

RJ_CONSULTA_CAND_COLUMNS = [
    "ANO_ELEICAO", "DS_CARGO", "NM_CANDIDATO", "NM_URNA_CANDIDATO",
    "SG_PARTIDO", "NR_PARTIDO", "DS_SITUACAO_CANDIDATURA",
]

PEOPLE = {"hugo": HUGO_LEAL, "felipe": FELIPE_PEIXOTO}


def download_consulta_cand(year: int) -> bool:
    dest = DATA_RAW / f"consulta_cand_{year}"
    return download_and_extract(url_consulta_cand(year), dest, f"consulta_cand {year}")


def load_consulta_cand_rj(year: int) -> pd.DataFrame:
    folder = DATA_RAW / f"consulta_cand_{year}"
    rj_file = folder / f"consulta_cand_{year}_RJ.csv"
    if not rj_file.exists():
        return pd.DataFrame()
    df = read_csv_safe(rj_file, sep=";", dtype=str, usecols=RJ_CONSULTA_CAND_COLUMNS)
    return df


def match_candidate(df_year: pd.DataFrame, name: str) -> pd.DataFrame:
    if df_year.empty:
        return df_year
    target = normalize(name)
    mask = (
        df_year["NM_CANDIDATO"].apply(normalize).str.contains(target, regex=False)
        | df_year["NM_URNA_CANDIDATO"].apply(normalize).str.contains(target, regex=False)
    )
    return df_year[mask]


def build_person_matrix_rows(candidate_key: str, person: dict) -> list[dict]:
    rows = []
    known_years = sorted(person["elections"].keys())
    all_registration_years = sorted(set(known_years) | {y for y in range(2010, 2025) if y % 2 == 0})

    for year in all_registration_years:
        df_year = load_consulta_cand_rj(year)
        matched = match_candidate(df_year, person["name"])
        config_entry = person["elections"].get(year)

        if matched.empty:
            if config_entry is not None:
                print(
                    f"  [WARN] {person['name']}: config.py has a {year} entry "
                    f"({config_entry['cargo']}), but consulta_cand_{year}_RJ.csv "
                    f"shows no matching registration. Matrix will treat {year} "
                    f"as not confirmed running. Review config.py or the raw file."
                )
            continue

        candidacy_row = matched.iloc[0]
        cargo = candidacy_row["DS_CARGO"].strip().upper()
        if config_entry is not None and normalize(config_entry["cargo"]) != normalize(cargo):
            print(
                f"  [WARN] {person['name']} {year}: config.py says cargo "
                f"'{config_entry['cargo']}', consulta_cand says '{cargo}'. "
                f"Matrix uses consulta_cand's value."
            )
        if config_entry is None:
            print(
                f"  [WARN] {person['name']}: config.py has no {year} entry, "
                f"but consulta_cand_{year}_RJ.csv shows a registered candidacy "
                f"(cargo: {cargo}, situacao: {candidacy_row['DS_SITUACAO_CANDIDATURA']}). "
                f"Matrix will treat {year} as 'concorreu' for gating. "
                f"Review and update config.py if this is confirmed real."
            )

        rows.append({
            "candidate_key": candidate_key,
            "ano": year,
            "cargo": cargo,
            "tipo_eleicao": election_type(year),
            "partido": candidacy_row["SG_PARTIDO"],
            "situacao_candidatura": candidacy_row["DS_SITUACAO_CANDIDATURA"],
        })
    return rows


def build_psd_matrix_rows() -> list[dict]:
    path = DATA_PROCESSED / "psd_by_secao.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path, dtype=str)
    if df.empty or "ano" not in df.columns:
        return []
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
    years = sorted(int(y) for y in df["ano"].dropna().unique() if int(y) >= PSD_FOUNDING_YEAR)
    return [
        {
            "candidate_key": "psd",
            "ano": year,
            "cargo": "AGREGADO",
            "tipo_eleicao": election_type(year),
            "partido": "PSD",
            "situacao_candidatura": "PARTIDO_ATIVO",
        }
        for year in years
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_candidacy_matrix.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/08_candidacy_matrix.py tests/test_candidacy_matrix.py
git commit -m "feat: add candidacy matrix matching for Hugo/Felipe and PSD existence"
```

---

### Task 3: Script 08 — download step, matrix assembly, and `main()`

**Files:**
- Modify: `scripts/08_candidacy_matrix.py` (append)
- Test: `tests/test_candidacy_matrix.py` (append)

**Interfaces:**
- Consumes: `download_consulta_cand`, `build_person_matrix_rows`, `build_psd_matrix_rows`, `PEOPLE` (Task 2).
- Produces: `build_candidacy_matrix() -> pd.DataFrame`, `main() -> None` (writes `data/processed/candidacy_matrix.csv`) — consumed by Task 4.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_candidacy_matrix.py`:

```python
def test_build_candidacy_matrix_combines_people_and_psd(monkeypatch):
    monkeypatch.setattr(cm, "build_person_matrix_rows", lambda key, person: [
        {"candidate_key": key, "ano": 2022, "cargo": "DEPUTADO FEDERAL", "tipo_eleicao": "Federal", "partido": "PSD", "situacao_candidatura": "DEFERIDO"},
    ])
    monkeypatch.setattr(cm, "build_psd_matrix_rows", lambda: [
        {"candidate_key": "psd", "ano": 2012, "cargo": "AGREGADO", "tipo_eleicao": "Municipal", "partido": "PSD", "situacao_candidatura": "PARTIDO_ATIVO"},
    ])

    matrix = cm.build_candidacy_matrix()

    assert set(matrix["candidate_key"]) == {"hugo", "felipe", "psd"}
    assert len(matrix[matrix["candidate_key"] == "hugo"]) == 1
    assert len(matrix[matrix["candidate_key"] == "felipe"]) == 1
    assert len(matrix[matrix["candidate_key"] == "psd"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_candidacy_matrix.py -v -k combines`
Expected: FAIL — `AttributeError: module has no attribute 'build_candidacy_matrix'`.

- [ ] **Step 3: Append the assembly and `main()` to `scripts/08_candidacy_matrix.py`**

Update the imports at the top of the file (add `json` for the PSD-breakdown merge this task's `main()` needs, and `DATA_GEO`):

```python
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_GEO, DATA_PROCESSED, DATA_RAW, FELIPE_PEIXOTO, HUGO_LEAL, url_consulta_cand
from _pipeline_utils import download_and_extract, election_type, normalize, read_csv_safe
```

Append:

```python
def build_candidacy_matrix() -> pd.DataFrame:
    rows = []
    for candidate_key, person in PEOPLE.items():
        rows.extend(build_person_matrix_rows(candidate_key, person))
    rows.extend(build_psd_matrix_rows())
    return pd.DataFrame(rows, columns=[
        "candidate_key", "ano", "cargo", "tipo_eleicao", "partido", "situacao_candidatura",
    ])


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    print("Downloading consulta_cand (candidate registration) files ...")
    all_years = sorted({y for y in range(2010, 2025) if y % 2 == 0})
    for year in all_years:
        download_consulta_cand(year)

    print("\nBuilding candidacy matrix ...")
    matrix = build_candidacy_matrix()
    out_path = DATA_PROCESSED / "candidacy_matrix.csv"
    matrix.to_csv(out_path, index=False)
    print(f"  Saved {out_path.name}: {len(matrix):,} rows")

    print("Done.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_candidacy_matrix.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Run the download + matrix build against real data**

Run: `python scripts/08_candidacy_matrix.py` (from the `LEAL` directory)
Expected: downloads `consulta_cand_{year}.zip` for each even year 2010-2024 into `data/raw/consulta_cand_{year}/` (this will take a few minutes — each file is several MB), prints any `[WARN]` discrepancies between `config.py` and the real registration data, and writes `data/processed/candidacy_matrix.csv`. Read the printed warnings carefully — they're informational for this task (nothing to fix yet), but note anything genuinely surprising for later human review.

- [ ] **Step 6: Spot-check the real output**

Run:

```bash
python -c "
import pandas as pd
m = pd.read_csv('data/processed/candidacy_matrix.csv')
print(m[m['candidate_key'] == 'felipe'][['ano', 'cargo', 'tipo_eleicao']].sort_values('ano'))
print()
print('2024 felipe rows:', len(m[(m['candidate_key']=='felipe') & (m['ano']==2024)]))
print('2010 psd rows:', len(m[(m['candidate_key']=='psd') & (m['ano']==2010)]))
"
```

Expected: Felipe's rows show his known cargo history (Deputado Estadual 2010/2018, Prefeito 2012/2016/2020, Deputado Federal 2022) unless a `[WARN]` in Step 5 revealed something different — in which case trust the matrix output, not this expectation. `2024 felipe rows` and `2010 psd rows` should both print `0` (no 2024 candidacy confirmed for Felipe in this data; PSD didn't exist in 2010).

- [ ] **Step 7: Commit**

```bash
git add scripts/08_candidacy_matrix.py tests/test_candidacy_matrix.py
git commit -m "feat: assemble and write the candidacy matrix"
```

(Do not commit `data/raw/consulta_cand_*/` or `data/processed/candidacy_matrix.csv` — these are pipeline-generated data, same treatment as every other `data/` output in this repo. Check `.gitignore` already covers `data/` broadly; if it doesn't, that's pre-existing and out of scope for this plan.)

---

### Task 4: Script 08 — PSD slate breakdown

**Files:**
- Modify: `scripts/08_candidacy_matrix.py` (append)
- Test: `tests/test_candidacy_matrix.py` (append)

**Interfaces:**
- Consumes: `read_tse_chunks_safe`, `find_csv`, `normalize`, `clean_id_series` (pre-existing `_pipeline_utils.py`), `MUNICIPIO` (`config.py`).
- Produces: `PSD_RAW_COLUMNS: list[str]`, `load_niteroi_psd_year(year: int) -> pd.DataFrame`, `rank_psd_breakdown_by_local(df_year: pd.DataFrame) -> dict[str, dict]`, `psd_breakdown_fields(breakdown: dict) -> dict`, `merge_psd_breakdown(geojson: dict, breakdown_by_year: dict) -> dict` — `merge_psd_breakdown`'s output (written back into `data/geo/psd.geojson`) is consumed by Task 12 (frontend `PsdBreakdownSection`).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_candidacy_matrix.py`:

```python
def write_psd_fixture_year(raw_dir, year, rows):
    header = "NM_MUNICIPIO;DS_CARGO;NR_VOTAVEL;NM_VOTAVEL;SG_PARTIDO;QT_VOTOS;NR_LOCAL_VOTACAO\n"
    folder = raw_dir / f"votacao_secao_{year}"
    folder.mkdir(parents=True)
    lines = [header] + [";".join(row) + "\n" for row in rows]
    (folder / f"votacao_secao_{year}_RJ.csv").write_text("".join(lines), encoding="utf-8")


def test_rank_psd_breakdown_ranks_across_cargos_by_votes():
    df = pd.DataFrame([
        {"NR_VOTAVEL": "5501", "NM_VOTAVEL": "CANDIDATO VEREADOR", "SG_PARTIDO": "PSD", "QT_VOTOS": 200, "nr_local": "1015", "cargo_norm": "VEREADOR"},
        {"NR_VOTAVEL": "55", "NM_VOTAVEL": "CANDIDATO PREFEITO", "SG_PARTIDO": "PSD", "QT_VOTOS": 900, "nr_local": "1015", "cargo_norm": "PREFEITO"},
        {"NR_VOTAVEL": "5502", "NM_VOTAVEL": "OUTRO VEREADOR", "SG_PARTIDO": "PSD", "QT_VOTOS": 50, "nr_local": "1015", "cargo_norm": "VEREADOR"},
    ])
    result = cm.rank_psd_breakdown_by_local(df)
    assert "1015" in result
    top = result["1015"]["top3"]
    assert top[0]["nome"] == "CANDIDATO PREFEITO"
    assert top[0]["cargo"] == "PREFEITO"
    assert result["1015"]["candidate_count"] == 3
    assert result["1015"]["total_por_cargo"] == {"PREFEITO": 900, "VEREADOR": 250}


def test_rank_psd_breakdown_returns_empty_dict_for_empty_input():
    assert cm.rank_psd_breakdown_by_local(pd.DataFrame()) == {}


def test_psd_breakdown_fields_shapes_output_for_merge():
    breakdown = {
        "top3": [
            {"nome": "CANDIDATO PREFEITO", "cargo": "PREFEITO", "votos": 900, "share": 45.0},
        ],
        "candidate_count": 3,
        "total_por_cargo": {"PREFEITO": 900, "VEREADOR": 250},
    }
    fields = cm.psd_breakdown_fields(breakdown)
    assert fields["psd_candidate_count"] == 3
    assert fields["psd_top1_nome"] == "CANDIDATO PREFEITO"
    assert fields["psd_top1_cargo"] == "PREFEITO"
    assert fields["psd_top1_votos"] == 900
    assert fields["psd_top1_share"] == 45.0
    assert fields["psd_top2_nome"] is None
    assert fields["psd_total_por_cargo"] == '{"PREFEITO": 900, "VEREADOR": 250}'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_candidacy_matrix.py -v -k "psd_breakdown or rank_psd"`
Expected: FAIL — the three new functions don't exist yet.

- [ ] **Step 3: Append the PSD breakdown logic**

Update the imports one more time (add `json`, `clean_id_series`, `find_csv`, `read_tse_chunks_safe`, `MUNICIPIO`, `DATA_GEO`):

```python
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_GEO, DATA_PROCESSED, DATA_RAW, FELIPE_PEIXOTO, HUGO_LEAL, MUNICIPIO, url_consulta_cand
from _pipeline_utils import (
    clean_id_series, download_and_extract, election_type, find_csv,
    normalize, read_csv_safe, read_tse_chunks_safe,
)
```

Append:

```python
PSD_RAW_COLUMNS = ["NM_MUNICIPIO", "DS_CARGO", "NR_VOTAVEL", "NM_VOTAVEL", "SG_PARTIDO", "QT_VOTOS", "NR_LOCAL_VOTACAO"]
PSD_TOP_N = 3


def load_niteroi_psd_year(year: int) -> pd.DataFrame:
    folder = DATA_RAW / f"votacao_secao_{year}"
    csv_file = find_csv(folder)
    if csv_file is None:
        return pd.DataFrame()

    pieces = []
    for chunk in read_tse_chunks_safe(csv_file, usecols=PSD_RAW_COLUMNS):
        mask = (
            chunk["NM_MUNICIPIO"].apply(lambda x: normalize(x) == normalize(MUNICIPIO))
            & (chunk["SG_PARTIDO"].apply(normalize) == "PSD")
        )
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


def rank_psd_breakdown_by_local(df_year: pd.DataFrame) -> dict[str, dict]:
    if df_year.empty:
        return {}
    df_year = df_year[df_year["nr_local"] != ""]
    if df_year.empty:
        return {}

    grouped = df_year.groupby(
        ["nr_local", "NR_VOTAVEL", "NM_VOTAVEL", "cargo_norm"], as_index=False
    )["QT_VOTOS"].sum()

    result: dict[str, dict] = {}
    for nr_local, group in grouped.groupby("nr_local"):
        top = group.sort_values("QT_VOTOS", ascending=False).head(PSD_TOP_N)
        total_por_cargo = group.groupby("cargo_norm")["QT_VOTOS"].sum().to_dict()
        result[nr_local] = {
            "top3": [
                {
                    "nome": row["NM_VOTAVEL"],
                    "cargo": row["cargo_norm"],
                    "votos": int(row["QT_VOTOS"]),
                    "share": round(row["QT_VOTOS"] / total_por_cargo[row["cargo_norm"]] * 100, 1),
                }
                for _, row in top.iterrows()
            ],
            "candidate_count": len(group),
            "total_por_cargo": {k: int(v) for k, v in total_por_cargo.items()},
        }
    return result


def psd_breakdown_fields(breakdown: dict) -> dict:
    fields = {
        "psd_candidate_count": breakdown["candidate_count"],
        "psd_total_por_cargo": json.dumps(breakdown["total_por_cargo"]),
    }
    top3 = breakdown["top3"]
    for i in range(PSD_TOP_N):
        n = i + 1
        entry = top3[i] if i < len(top3) else None
        fields[f"psd_top{n}_nome"] = entry["nome"] if entry else None
        fields[f"psd_top{n}_cargo"] = entry["cargo"] if entry else None
        fields[f"psd_top{n}_votos"] = entry["votos"] if entry else None
        fields[f"psd_top{n}_share"] = entry["share"] if entry else None
    return fields


def build_psd_breakdown_by_year() -> dict[int, dict[str, dict]]:
    path = DATA_PROCESSED / "psd_by_secao.csv"
    if not path.exists():
        return {}
    existing = pd.read_csv(path, dtype=str)
    if existing.empty or "ano" not in existing.columns:
        return {}
    years = sorted(int(y) for y in pd.to_numeric(existing["ano"], errors="coerce").dropna().unique())

    breakdown_by_year = {}
    for year in years:
        print(f"  Reading {year} for PSD breakdown ...")
        df_year = load_niteroi_psd_year(year)
        breakdown_by_year[year] = rank_psd_breakdown_by_local(df_year)
        print(f"    {len(breakdown_by_year[year])} locais with PSD breakdown data")
    return breakdown_by_year


def merge_psd_breakdown(geojson: dict, breakdown_by_year: dict[int, dict[str, dict]]) -> dict:
    for feature in geojson.get("features", []):
        props = feature["properties"]
        year = props.get("ano")
        nr_local = str(props.get("nr_local", "")).strip()
        breakdown = breakdown_by_year.get(year, {}).get(nr_local)
        if breakdown:
            props.update(psd_breakdown_fields(breakdown))
    return geojson
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_candidacy_matrix.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Wire the merge into `main()`**

Replace `main()`'s body (from Task 3) with:

```python
def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    print("Downloading consulta_cand (candidate registration) files ...")
    all_years = sorted({y for y in range(2010, 2025) if y % 2 == 0})
    for year in all_years:
        download_consulta_cand(year)

    print("\nBuilding candidacy matrix ...")
    matrix = build_candidacy_matrix()
    out_path = DATA_PROCESSED / "candidacy_matrix.csv"
    matrix.to_csv(out_path, index=False)
    print(f"  Saved {out_path.name}: {len(matrix):,} rows")

    print("\nBuilding PSD slate breakdown ...")
    breakdown_by_year = build_psd_breakdown_by_year()
    psd_path = DATA_GEO / "psd.geojson"
    if psd_path.exists():
        geojson = json.loads(psd_path.read_text(encoding="utf-8"))
        merge_psd_breakdown(geojson, breakdown_by_year)
        psd_path.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Updated {psd_path.name}")
    else:
        print(f"  [skip] {psd_path.name} not found; run 05_build_geojson.py first")

    print("Done.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run against real data and spot-check**

Run: `python scripts/08_candidacy_matrix.py` (this now re-downloads nothing new — `consulta_cand` was already fetched in Task 3 — but re-reads raw `votacao_secao` files for the PSD breakdown, which takes a few minutes)

Then:

```bash
python -c "
import json
psd = json.load(open('data/geo/psd.geojson', encoding='utf-8'))
sample = next(f for f in psd['features'] if f['properties']['ano'] == 2012 and f['properties'].get('psd_top1_nome'))
print('2012 PSD top1:', sample['properties']['psd_top1_nome'], sample['properties']['psd_top1_cargo'], sample['properties']['psd_top1_votos'])
print('candidate_count:', sample['properties']['psd_candidate_count'])
"
```

Expected: prints a real PSD candidate name, cargo, and vote count for a 2012 local — this is the data that should explain the 2012→2016 PSD swing mentioned in the original request. No assertion here (real data varies), just confirm it's populated and plausible, not empty/null.

- [ ] **Step 7: Commit**

```bash
git add scripts/08_candidacy_matrix.py tests/test_candidacy_matrix.py
git commit -m "feat: add PSD slate breakdown, merge onto psd.geojson"
```

---

### Task 5: Script 06 — candidacy-gated pair enumeration and delta computation

**Files:**
- Modify: `scripts/06_build_vote_deltas.py`
- Test: `tests/test_vote_deltas.py`

**Interfaces:**
- Consumes: `data/processed/candidacy_matrix.csv` (Task 3's output).
- Produces: `load_candidacy_matrix() -> pd.DataFrame`, `candidacy_lookup(matrix: pd.DataFrame) -> dict[tuple[str, int], dict]`, `candidate_pairs_from_matrix(lookup: dict, candidate_key: str) -> list[tuple[int, int]]`, `all_candidate_pairs(lookup: dict) -> list[tuple[int, int]]` (replaces `consecutive_pairs`), rewritten `add_delta_fields(row: dict, get_votes, lookup: dict) -> None` (new `lookup` parameter; same-named fields plus new `candidacy_status_{key}` fields) — consumed by `build_local_delta_frame`/`build_section_delta_frame` in this same file, and by the frontend tasks (11, 12) which read the `candidacy_status_*`/null fields this produces.

This is the task with the most design judgment in the whole plan — read it fully before starting, and ask if the pairing mechanism (nearest matching cycle per candidate, unioned across candidates into shared pair-rows) doesn't make sense from the code below.

- [ ] **Step 1: Write the failing tests**

The two pre-existing tests in `tests/test_vote_deltas.py` both call `vd.add_delta_fields(row, get_votes)` with the current 2-argument signature — this task changes `add_delta_fields` to require a third `lookup` argument, so both break unless updated. Worse, the second existing test's fixture pair is `2012 → 2014`, which `election_type()` classifies as `Municipal -> Federal` — under the new gating rule that pair can never produce a real (non-null) delta regardless of what the lookup says, since it requires matching types on both ends. That test's whole premise (asserting a real numeric `delta_hugo`) only makes sense for a same-type pair, so its years need to change too, not just its `add_delta_fields` call.

Replace `tests/test_vote_deltas.py` in full:

```python
from conftest import load_script

vd = load_script("_vote_deltas", "06_build_vote_deltas.py")

MIGRATION_FIELDS = {
    "hugo_perda", "felipe_ganho", "psd_ganho",
    "mig_hugo_felipe_votos", "mig_hugo_psd_votos",
    "mig_hugo_felipe_score", "mig_hugo_psd_score",
    "mig_alvo", "mig_score", "mig_votos_correspondentes", "mig_signal",
}


def make_matrix_lookup(rows):
    # rows: list of (candidate_key, ano, tipo_eleicao)
    return {(key, ano): {"tipo_eleicao": tipo} for key, ano, tipo in rows}


def test_add_delta_fields_no_longer_writes_migration_fields():
    lookup = make_matrix_lookup([
        ("hugo", 2010, "Federal"), ("hugo", 2014, "Federal"),
        ("felipe", 2010, "Federal"), ("felipe", 2014, "Federal"),
        ("psd", 2010, "Federal"), ("psd", 2014, "Federal"),
    ])
    row = {"ano_inicio": 2010, "ano_fim": 2014}
    votes = {
        ("hugo", 2010): 100, ("hugo", 2014): 60,
        ("felipe", 2010): 20, ("felipe", 2014): 55,
        ("psd", 2010): 30, ("psd", 2014): 30,
    }

    def get_votes(key, year):
        return votes.get((key, year), 0)

    vd.add_delta_fields(row, get_votes, lookup)

    assert MIGRATION_FIELDS.isdisjoint(row.keys())
    assert not hasattr(vd, "migration_score")
    assert not hasattr(vd, "MIN_SIGNAL_VOTES")


def test_add_delta_fields_keeps_deltas_and_map_fields_when_gated():
    # 2010 and 2014 are both Federal-type years (unlike the original
    # fixture's 2012/2014, which is Municipal->Federal and can never be
    # gated under the new same-type rule) — this test now specifically
    # exercises the "both sides present, same type" path.
    lookup = make_matrix_lookup([("hugo", 2010, "Federal"), ("hugo", 2014, "Federal")])
    row = {"ano_inicio": 2010, "ano_fim": 2014}
    votes = {("hugo", 2010): 100, ("hugo", 2014): 60}

    def get_votes(key, year):
        return votes.get((key, year), 0)

    vd.add_delta_fields(row, get_votes, lookup)

    assert row["votos_hugo_inicio"] == 100
    assert row["votos_hugo_fim"] == 60
    assert row["delta_hugo"] == -40
    assert row["pct_delta_hugo"] == -40.0
    assert row["candidacy_status_hugo"] == "concorreu"
    assert row["map_delta"] == -40
    assert row["map_abs_delta"] == 40
    assert row["tipo_par"] == "Federal -> Federal"
```

Append these new tests to the same file (`make_matrix_lookup` is already defined above from the full-file replacement — don't redefine it):

```python
def test_candidate_pairs_from_matrix_finds_nearest_matching_cycle_within_type():
    lookup = make_matrix_lookup([
        ("felipe", 2010, "Federal"),
        ("felipe", 2012, "Municipal"),
        ("felipe", 2016, "Municipal"),
        ("felipe", 2018, "Federal"),
        ("felipe", 2020, "Municipal"),
        ("felipe", 2022, "Federal"),
    ])
    pairs = vd.candidate_pairs_from_matrix(lookup, "felipe")
    assert (2010, 2018) in pairs
    assert (2018, 2022) in pairs
    assert (2012, 2016) in pairs
    assert (2016, 2020) in pairs
    # never crosses type buckets
    assert (2010, 2012) not in pairs
    assert (2016, 2018) not in pairs


def test_candidate_pairs_from_matrix_empty_for_unknown_candidate():
    lookup = make_matrix_lookup([("felipe", 2010, "Federal")])
    assert vd.candidate_pairs_from_matrix(lookup, "hugo") == []


def test_candidate_pairs_from_matrix_single_candidacy_produces_no_pairs():
    lookup = make_matrix_lookup([("psd", 2012, "Municipal")])
    assert vd.candidate_pairs_from_matrix(lookup, "psd") == []


def test_all_candidate_pairs_unions_across_candidates():
    lookup = make_matrix_lookup([
        ("hugo", 2010, "Federal"), ("hugo", 2014, "Federal"),
        ("felipe", 2012, "Municipal"), ("felipe", 2016, "Municipal"),
    ])
    pairs = vd.all_candidate_pairs(lookup)
    assert (2010, 2014) in pairs
    assert (2012, 2016) in pairs
    assert len(pairs) == 2


def test_add_delta_fields_gates_ungated_pair_to_null_with_status():
    lookup = make_matrix_lookup([("hugo", 2010, "Federal"), ("hugo", 2014, "Federal")])
    row = {"ano_inicio": 2010, "ano_fim": 2014}
    votes = {("hugo", 2010): 100, ("hugo", 2014): 60, ("felipe", 2010): 20, ("felipe", 2014): 55, ("psd", 2010): 0, ("psd", 2014): 30}

    def get_votes(key, year):
        return votes.get((key, year), 0)

    vd.add_delta_fields(row, get_votes, lookup)

    # hugo is gated (both years present, same type) -> real numbers
    assert row["votos_hugo_inicio"] == 100
    assert row["delta_hugo"] == -40
    assert row["candidacy_status_hugo"] == "concorreu"

    # felipe has no matrix rows at all for either year -> null, not a fake delta
    assert row["votos_felipe_inicio"] is None
    assert row["votos_felipe_fim"] is None
    assert row["delta_felipe"] is None
    assert row["pct_delta_felipe"] is None
    assert row["candidacy_status_felipe"] == "nao_concorreu"

    # psd has no matrix rows either (2010 predates PSD's founding) -> null
    assert row["delta_psd"] is None
    assert row["candidacy_status_psd"] == "nao_concorreu"


def test_add_delta_fields_null_when_only_one_side_gated():
    lookup = make_matrix_lookup([("felipe", 2018, "Federal")])
    row = {"ano_inicio": 2018, "ano_fim": 2022}
    votes = {("felipe", 2018): 40}

    def get_votes(key, year):
        return votes.get((key, year), 0)

    vd.add_delta_fields(row, get_votes, lookup)
    assert row["delta_felipe"] is None
    assert row["candidacy_status_felipe"] == "nao_concorreu_fim"


def test_add_delta_fields_null_when_types_mismatch_despite_both_present():
    lookup = make_matrix_lookup([("felipe", 2018, "Federal"), ("felipe", 2020, "Municipal")])
    row = {"ano_inicio": 2018, "ano_fim": 2020}
    votes = {("felipe", 2018): 40, ("felipe", 2020): 300}

    def get_votes(key, year):
        return votes.get((key, year), 0)

    vd.add_delta_fields(row, get_votes, lookup)
    assert row["delta_felipe"] is None
    assert row["candidacy_status_felipe"] == "tipo_incompativel"


def test_add_delta_fields_map_fields_are_null_when_hugo_ungated():
    lookup = make_matrix_lookup([("hugo", 2012, "Municipal"), ("hugo", 2014, "Federal")])
    # deliberately NOT gated for hugo (types differ) to prove map_delta handles null
    row = {"ano_inicio": 2012, "ano_fim": 2014}

    def get_votes(key, year):
        return 0

    vd.add_delta_fields(row, get_votes, lookup)
    assert row["map_delta"] is None
    assert row["map_abs_delta"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_vote_deltas.py -v`
Expected: FAIL — none of the new functions exist yet, `add_delta_fields` doesn't accept a `lookup` argument.

- [ ] **Step 3: Add matrix loading and pair enumeration**

In `scripts/06_build_vote_deltas.py`, add to the imports (`DATA_PROCESSED` is already imported):

```python
from config import ALL_YEARS, DATA_GEO, DATA_PROCESSED, DATA_RAW, MUNICIPIO
```

(unchanged — already imports `DATA_PROCESSED`)

Append these new functions, placed after `election_type` was removed (i.e., roughly where `pct_delta`/`election_type` used to sit):

```python
CANDIDATE_KEY_TO_MATRIX_KEY = {"hugo": "hugo", "felipe": "felipe", "psd": "psd"}


def load_candidacy_matrix() -> pd.DataFrame:
    path = DATA_PROCESSED / "candidacy_matrix.csv"
    if not path.exists():
        return pd.DataFrame(columns=["candidate_key", "ano", "cargo", "tipo_eleicao", "partido", "situacao_candidatura"])
    df = pd.read_csv(path, dtype=str)
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    return df


def candidacy_lookup(matrix: pd.DataFrame) -> dict[tuple[str, int], dict]:
    lookup = {}
    for _, row in matrix.iterrows():
        if pd.isna(row["ano"]):
            continue
        lookup[(row["candidate_key"], int(row["ano"]))] = {"tipo_eleicao": row["tipo_eleicao"]}
    return lookup


def candidate_pairs_from_matrix(lookup: dict, candidate_key: str) -> list[tuple[int, int]]:
    matrix_key = CANDIDATE_KEY_TO_MATRIX_KEY[candidate_key]
    years_by_type: dict[str, list[int]] = {}
    for (key, year), info in lookup.items():
        if key != matrix_key:
            continue
        years_by_type.setdefault(info["tipo_eleicao"], []).append(year)

    pairs = []
    for years in years_by_type.values():
        years = sorted(set(years))
        pairs.extend(zip(years[:-1], years[1:]))
    return sorted(set(pairs))


def all_candidate_pairs(lookup: dict) -> list[tuple[int, int]]:
    all_pairs: set[tuple[int, int]] = set()
    for candidate_key in DATASETS:
        all_pairs.update(candidate_pairs_from_matrix(lookup, candidate_key))
    return sorted(all_pairs)
```

- [ ] **Step 4: Rewrite `add_delta_fields` to consume the matrix**

Replace the existing `add_delta_fields` function:

```python
def add_delta_fields(row: dict, get_votes) -> None:
    start_year = row["ano_inicio"]
    end_year = row["ano_fim"]
    row["tipo_inicio"] = election_type(start_year)
    row["tipo_fim"] = election_type(end_year)
    row["tipo_par"] = f"{row['tipo_inicio']} -> {row['tipo_fim']}"
    for key in DATASETS:
        start_votes = int(get_votes(key, start_year) or 0)
        end_votes = int(get_votes(key, end_year) or 0)
        delta = end_votes - start_votes
        row[f"votos_{key}_inicio"] = start_votes
        row[f"votos_{key}_fim"] = end_votes
        row[f"delta_{key}"] = delta
        row[f"pct_delta_{key}"] = pct_delta(start_votes, delta)

    row["map_delta"] = row["delta_hugo"]
    row["map_abs_delta"] = abs(row["delta_hugo"])
```

with:

```python
def add_delta_fields(row: dict, get_votes, lookup: dict) -> None:
    start_year = row["ano_inicio"]
    end_year = row["ano_fim"]
    row["tipo_inicio"] = election_type(start_year)
    row["tipo_fim"] = election_type(end_year)
    row["tipo_par"] = f"{row['tipo_inicio']} -> {row['tipo_fim']}"

    for key in DATASETS:
        matrix_key = CANDIDATE_KEY_TO_MATRIX_KEY[key]
        start_info = lookup.get((matrix_key, start_year))
        end_info = lookup.get((matrix_key, end_year))
        gated = (
            start_info is not None
            and end_info is not None
            and start_info["tipo_eleicao"] == end_info["tipo_eleicao"]
        )

        if not gated:
            row[f"votos_{key}_inicio"] = None
            row[f"votos_{key}_fim"] = None
            row[f"delta_{key}"] = None
            row[f"pct_delta_{key}"] = None
            if start_info is None and end_info is None:
                row[f"candidacy_status_{key}"] = "nao_concorreu"
            elif start_info is None:
                row[f"candidacy_status_{key}"] = "nao_concorreu_inicio"
            elif end_info is None:
                row[f"candidacy_status_{key}"] = "nao_concorreu_fim"
            else:
                row[f"candidacy_status_{key}"] = "tipo_incompativel"
            continue

        start_votes = int(get_votes(key, start_year) or 0)
        end_votes = int(get_votes(key, end_year) or 0)
        delta = end_votes - start_votes
        row[f"votos_{key}_inicio"] = start_votes
        row[f"votos_{key}_fim"] = end_votes
        row[f"delta_{key}"] = delta
        row[f"pct_delta_{key}"] = pct_delta(start_votes, delta)
        row[f"candidacy_status_{key}"] = "concorreu"

    row["map_delta"] = row["delta_hugo"]
    row["map_abs_delta"] = abs(row["delta_hugo"]) if row["delta_hugo"] is not None else None
```

- [ ] **Step 5: Update the two call sites to pass the matrix lookup and use `all_candidate_pairs`**

Replace `consecutive_pairs()`'s definition:

```python
def consecutive_pairs() -> list[tuple[int, int]]:
    years = sorted(int(y) for y in ALL_YEARS)
    return list(zip(years[:-1], years[1:]))
```

Delete it entirely — `all_candidate_pairs(lookup)` (Step 3) replaces it. It has a different signature (takes `lookup`, not no-args), so every call site needs updating, not just the definition.

In `build_local_delta_frame`, replace:

```python
def build_local_delta_frame(
    votes_by_secao: dict[str, pd.DataFrame],
    roster: pd.DataFrame,
    locais: pd.DataFrame,
) -> pd.DataFrame:
    vote_lookup = aggregate_local_votes(votes_by_secao)
    info_lookup = locais.set_index("nr_local").to_dict("index") if not locais.empty else {}
    rows = []

    for start_year, end_year in consecutive_pairs():
```

with:

```python
def build_local_delta_frame(
    votes_by_secao: dict[str, pd.DataFrame],
    roster: pd.DataFrame,
    locais: pd.DataFrame,
    candidacy: dict,
) -> pd.DataFrame:
    vote_lookup = aggregate_local_votes(votes_by_secao)
    info_lookup = locais.set_index("nr_local").to_dict("index") if not locais.empty else {}
    rows = []

    for start_year, end_year in all_candidate_pairs(candidacy):
```

Further down in the same function, replace the `add_delta_fields(row, get_votes)` call with `add_delta_fields(row, get_votes, candidacy)`.

Apply the identical pattern to `build_section_delta_frame` — add a `candidacy: dict` parameter, replace `for start_year, end_year in consecutive_pairs():` with `for start_year, end_year in all_candidate_pairs(candidacy):`, and update its `add_delta_fields(row, get_votes)` call to `add_delta_fields(row, get_votes, candidacy)`.

- [ ] **Step 6: Update `main()` to load and pass the matrix**

In `main()`, after the existing `roster = load_section_roster(votes_by_secao)` line, add:

```python
    print("\nLoading candidacy matrix ...")
    matrix = load_candidacy_matrix()
    candidacy = candidacy_lookup(matrix)
    if not candidacy:
        print("  [warn] candidacy_matrix.csv missing or empty — run scripts/08_candidacy_matrix.py first. All deltas will be gated to null.")
```

Update the two call sites further down:

```python
    local_deltas = build_local_delta_frame(votes_by_secao, roster, locais)
```
becomes
```python
    local_deltas = build_local_delta_frame(votes_by_secao, roster, locais, candidacy)
```

```python
    section_deltas = build_section_delta_frame(votes_by_secao, roster, locais)
```
becomes
```python
    section_deltas = build_section_delta_frame(votes_by_secao, roster, locais, candidacy)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m pytest tests/test_vote_deltas.py -v`
Expected: PASS (10 tests total — the 2 pre-existing tests, updated in Step 1 for the new 3-argument signature and a same-type fixture pair, plus 8 new ones covering pair enumeration and gating)

- [ ] **Step 8: Run against real data and verify the two named regressions are fixed**

Run: `python scripts/06_build_vote_deltas.py` (requires Task 3's `candidacy_matrix.csv` to already exist — it does, from this session's real run)

Then:

```bash
python -c "
import pandas as pd
df = pd.read_csv('data/processed/vote_deltas_by_local.csv')
felipe_2024_pairs = df[df['ano_fim'] == 2024]
print('Felipe delta rows ending in 2024:', len(felipe_2024_pairs))
if len(felipe_2024_pairs) > 0:
    print(felipe_2024_pairs[['pair', 'delta_felipe', 'candidacy_status_felipe']].drop_duplicates().to_string())
    assert felipe_2024_pairs['delta_felipe'].isna().all(), 'Felipe 2024 delta should be null, not a fake number'
psd_2010 = df[(df['ano_inicio'] == 2010) | (df['ano_fim'] == 2010)]
if len(psd_2010) > 0:
    assert psd_2010['delta_psd'].isna().all(), 'PSD 2010 delta should be null, party did not exist'
print('OK — no fake deltas for ungated candidacies')
"
```

Expected: `OK` printed, no assertion error. If Felipe genuinely has no delta rows ending in 2024 at all (possible, depending on what `all_candidate_pairs` produces from the real matrix), that's also correct — the point is there's no row claiming a numeric `delta_felipe` for a year he didn't run.

- [ ] **Step 9: Commit**

```bash
git add scripts/06_build_vote_deltas.py tests/test_vote_deltas.py
git commit -m "feat: gate vote deltas by candidacy matrix, nearest-matching-cycle pairing"
```

---

### Task 6: Script 07 — vote-share total

**Files:**
- Modify: `scripts/07_top_competitors.py`
- Test: `tests/test_top_competitors.py`

**Interfaces:**
- Consumes: nothing new — extends existing `rank_top3_by_local`'s data.
- Produces: `total_valid_votes_by_local(df_cargo: pd.DataFrame) -> dict[str, int]` — consumed by Task 9 (frontend `PopupContent`'s vote-share display) via the merged `total_votos_validos` field on `hugo_leal.geojson`/`felipe_peixoto.geojson`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_top_competitors.py`:

```python
def test_total_valid_votes_by_local_includes_all_real_candidates():
    df = make_df([
        {"NR_VOTAVEL": "5555", "NM_VOTAVEL": "HUGO LEAL", "QT_VOTOS": 100, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "7733", "NM_VOTAVEL": "AUREO RIBEIRO", "QT_VOTOS": 30, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "95", "NM_VOTAVEL": "VOTO BRANCO", "QT_VOTOS": 5, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
    ])
    result = tc.total_valid_votes_by_local(df)
    # Hugo's own votes count toward the total (unlike rank_top3_by_local, which excludes him)
    assert result["1015"] == 130
    # voto branco is excluded (not a real candidate)


def test_total_valid_votes_by_local_empty_for_empty_input():
    assert tc.total_valid_votes_by_local(make_df([])) == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_top_competitors.py -v -k total_valid`
Expected: FAIL — `AttributeError: module has no attribute 'total_valid_votes_by_local'`.

- [ ] **Step 3: Add the function and wire it into the merge**

Append to `scripts/07_top_competitors.py` (after `rank_top3_by_local`):

```python
def total_valid_votes_by_local(df_cargo: pd.DataFrame) -> dict[str, int]:
    if df_cargo.empty:
        return {}
    keep_mask = df_cargo.apply(
        lambda r: is_real_candidate(r["NR_VOTAVEL"], r["cargo_norm"]), axis=1
    )
    candidates = df_cargo[keep_mask]
    candidates = candidates[candidates["nr_local"] != ""]
    if candidates.empty:
        return {}
    totals = candidates.groupby("nr_local")["QT_VOTOS"].sum()
    return {nr_local: int(total) for nr_local, total in totals.items()}
```

In `build_all_rankings()`, change the return type to also carry totals. Replace:

```python
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
```

with:

```python
def build_all_rankings() -> tuple[dict[tuple[int, str], dict[str, list[dict]]], dict[tuple[int, str], dict[str, int]]]:
    pairs = year_cargo_pairs()
    years = sorted({year for year, _ in pairs})
    rankings = {}
    totals = {}
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
            totals[(year, cargo)] = total_valid_votes_by_local(df_cargo)
            print(f"    {cargo}: {len(rankings[(year, cargo)])} locais ranked")
    return rankings, totals
```

Update `rankings_for_person` to accept and thread through the totals — replace:

```python
def rankings_for_person(person_key: str, all_rankings: dict) -> dict[int, dict[str, list[dict]]]:
    person = PEOPLE[person_key]
    result = {}
    for year, info in person["elections"].items():
        cargo = normalize(info["cargo"])
        result[year] = all_rankings.get((year, cargo), {})
    return result
```

with:

```python
def rankings_for_person(person_key: str, all_rankings: dict) -> dict[int, dict[str, list[dict]]]:
    person = PEOPLE[person_key]
    result = {}
    for year, info in person["elections"].items():
        cargo = normalize(info["cargo"])
        result[year] = all_rankings.get((year, cargo), {})
    return result


def totals_for_person(person_key: str, all_totals: dict) -> dict[int, dict[str, int]]:
    person = PEOPLE[person_key]
    result = {}
    for year, info in person["elections"].items():
        cargo = normalize(info["cargo"])
        result[year] = all_totals.get((year, cargo), {})
    return result
```

Update `merge_top_competitors` to also merge the total. Replace:

```python
def merge_top_competitors(geojson: dict, rankings_by_year: dict[int, dict[str, list[dict]]]) -> dict:
    for feature in geojson.get("features", []):
        props = feature["properties"]
        year = props.get("ano")
        nr_local = str(props.get("nr_local", "")).strip()
        entries = rankings_by_year.get(year, {}).get(nr_local, [])
        props.update(top3_fields(entries))
    return geojson
```

with:

```python
def merge_top_competitors(
    geojson: dict,
    rankings_by_year: dict[int, dict[str, list[dict]]],
    totals_by_year: dict[int, dict[str, int]],
) -> dict:
    for feature in geojson.get("features", []):
        props = feature["properties"]
        year = props.get("ano")
        nr_local = str(props.get("nr_local", "")).strip()
        entries = rankings_by_year.get(year, {}).get(nr_local, [])
        props.update(top3_fields(entries))
        props["total_votos_validos"] = totals_by_year.get(year, {}).get(nr_local)
    return geojson
```

Update `main()` to match the new signatures. Replace:

```python
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
```

with:

```python
def main() -> None:
    DATA_GEO.mkdir(parents=True, exist_ok=True)

    print("Building competitor rankings from raw TSE files ...")
    all_rankings, all_totals = build_all_rankings()

    for person_key in PEOPLE:
        path = DATA_GEO / f"{person_key}.geojson"
        if not path.exists():
            print(f"  [skip] {path.name} not found; run 05_build_geojson.py first")
            continue
        geojson = json.loads(path.read_text(encoding="utf-8"))
        rankings = rankings_for_person(person_key, all_rankings)
        totals = totals_for_person(person_key, all_totals)
        merge_top_competitors(geojson, rankings, totals)
        path.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Updated {path.name}")

    print("\nUpdating app bundle ...")
    rebuild_data_js(DATA_GEO, DATA_GEO.parent.parent / "app")
    print("Done.")
```

- [ ] **Step 3.5: Fix the pre-existing test broken by the new signature**

`tests/test_top_competitors.py`'s existing `test_merge_top_competitors_matches_on_year_and_local` calls `tc.merge_top_competitors(geojson, rankings_by_year)` with the old 2-argument signature — Step 3 above just made `totals_by_year` a required third argument. Replace:

```python
    tc.merge_top_competitors(geojson, rankings_by_year)
```

with:

```python
    tc.merge_top_competitors(geojson, rankings_by_year, {})
```

(An empty `{}` is correct here — the test never asserts `total_votos_validos`, so an always-empty totals lookup, which makes every feature's `total_votos_validos` come out `None` via `.get(year, {}).get(nr_local)`, doesn't change what this test already checks.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_top_competitors.py -v`
Expected: PASS (all pre-existing tests, including the one just fixed in Step 3.5, plus the 2 new ones from Step 1)

- [ ] **Step 5: Run against real data**

Run: `python scripts/07_top_competitors.py`
Expected: completes with `Done.`. Then:

```bash
python -c "
import json
hugo = json.load(open('data/geo/hugo_leal.geojson', encoding='utf-8'))
sample = next(f for f in hugo['features'] if f['properties']['ano'] == 2022)
p = sample['properties']
share = p['QT_VOTOS'] / p['total_votos_validos'] * 100
print(f'Hugo 2022 sample: {p[\"QT_VOTOS\"]} / {p[\"total_votos_validos\"]} = {share:.1f}%')
assert p['total_votos_validos'] >= p['QT_VOTOS'], 'total must be at least the candidate own votes'
print('OK')
"
```

Expected: `OK` printed, a plausible single-digit-to-low-double-digit percentage (Hugo/Felipe are two of many candidates in a proportional race).

- [ ] **Step 6: Commit**

```bash
git add scripts/07_top_competitors.py tests/test_top_competitors.py
git commit -m "feat: add vote-share total to competitor rankings"
```

---

### Task 7: Script 05 — `cargo` field on Hugo/Felipe features

**Files:**
- Modify: `scripts/05_build_geojson.py`
- Test: `tests/test_build_geojson.py` (new file — `05` has no test coverage today)

**Interfaces:**
- Consumes: `HUGO_LEAL`, `FELIPE_PEIXOTO` (`config.py`) — **not currently imported by `05_build_geojson.py`**, contrary to an earlier assumption in the design spec; `05` is fully generic today and has zero per-person knowledge. This task adds the import fresh.
- Produces: a `cargo` property on every `hugo_leal.geojson`/`felipe_peixoto.geojson` feature (absent on `psd.geojson`, which has no single per-feature cargo) — consumed by Task 10's frontend `PopupContent` redesign.

Confirmed from reading the real file this session: `main()` loops over a `datasets = {"hugo_leal": ..., "felipe_peixoto": ..., "psd": ...}` dict identically for all three, calling `aggregate_to_local(merged)` (which groups by `["ano", "nr_local", "label"]`, so the resulting dataframe has an `ano` column) and then `to_geojson(by_local, name)`. `to_geojson` turns every column present in the dataframe into a feature property automatically — so adding a `cargo` column to the dataframe before calling `to_geojson` is sufficient, no changes to `to_geojson` itself needed.

- [ ] **Step 1: Write the failing test**

Create `tests/test_pipeline_utils.py`... no — create `tests/test_build_geojson.py`:

```python
import pandas as pd

from conftest import load_script

bg = load_script("_build_geojson", "05_build_geojson.py")


def test_add_cargo_column_maps_from_config_by_year():
    by_local = pd.DataFrame([
        {"ano": 2022, "nr_local": "1", "QT_VOTOS": 50},
        {"ano": 2014, "nr_local": "1", "QT_VOTOS": 30},
    ])
    result = bg.add_cargo_column(by_local, "hugo_leal")
    assert list(result["cargo"]) == ["DEPUTADO FEDERAL", "DEPUTADO FEDERAL"]


def test_add_cargo_column_handles_felipes_varying_cargo():
    by_local = pd.DataFrame([
        {"ano": 2012, "nr_local": "1", "QT_VOTOS": 50},
        {"ano": 2022, "nr_local": "1", "QT_VOTOS": 30},
    ])
    result = bg.add_cargo_column(by_local, "felipe_peixoto")
    assert list(result["cargo"]) == ["PREFEITO", "DEPUTADO FEDERAL"]


def test_add_cargo_column_is_noop_for_psd():
    by_local = pd.DataFrame([{"ano": 2022, "nr_local": "1", "QT_VOTOS": 500}])
    result = bg.add_cargo_column(by_local, "psd")
    assert "cargo" not in result.columns
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_build_geojson.py -v`
Expected: FAIL — `AttributeError: module has no attribute 'add_cargo_column'`.

- [ ] **Step 3: Add the import and the `add_cargo_column` function**

In `scripts/05_build_geojson.py`, replace the import line:

```python
from config import DATA_PROCESSED, DATA_GEO
```

with:

```python
from config import DATA_PROCESSED, DATA_GEO, FELIPE_PEIXOTO, HUGO_LEAL
```

Append this function after `aggregate_to_local`:

```python
PEOPLE_CONFIG = {"hugo_leal": HUGO_LEAL, "felipe_peixoto": FELIPE_PEIXOTO}


def add_cargo_column(by_local: pd.DataFrame, name: str) -> pd.DataFrame:
    person = PEOPLE_CONFIG.get(name)
    if person is None or by_local.empty:
        return by_local
    by_local = by_local.copy()
    by_local["cargo"] = by_local["ano"].map(
        lambda ano: person["elections"].get(int(ano), {}).get("cargo")
    )
    return by_local
```

- [ ] **Step 4: Wire it into `main()`**

In `main()`, replace:

```python
        by_local = aggregate_to_local(merged)

        geojson = to_geojson(by_local, name)
```

with:

```python
        by_local = aggregate_to_local(merged)
        by_local = add_cargo_column(by_local, name)

        geojson = to_geojson(by_local, name)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `python -m pytest tests/test_build_geojson.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Run against real data and spot-check**

Run: `python scripts/05_build_geojson.py`, then:

```bash
python -c "
import json
hugo = json.load(open('data/geo/hugo_leal.geojson', encoding='utf-8'))
sample = next(f for f in hugo['features'] if f['properties']['ano'] == 2014)
print('Hugo 2014 cargo:', sample['properties'].get('cargo'))
assert sample['properties'].get('cargo') == 'DEPUTADO FEDERAL'
print('OK')
"
```

Expected: `OK` printed. Note: re-running `05_build_geojson.py` regenerates `hugo_leal.geojson`/`felipe_peixoto.geojson` from scratch — re-run `07_top_competitors.py` afterward too, since `07` merges competitor/vote-share data onto these same files and Step 6 here just overwrote them back to their pre-Task-6 state.

Run: `python scripts/07_top_competitors.py` again after this step, to restore the vote-share merge on top of the freshly-regenerated files.

- [ ] **Step 7: Commit**

```bash
git add scripts/05_build_geojson.py tests/test_build_geojson.py
git commit -m "feat: add cargo field to Hugo/Felipe geojson features"
```

---

### Task 8: README — document script 08 and the real execution order

**Files:**
- Modify: `README.md`

**Interfaces:** None — documentation only.

- [ ] **Step 1: Read the current README's Pipeline section**

Read `README.md` in full before editing — this plan was not written against its exact current line numbers (it was last touched by a prior spec's Task 6, so its current numbered list should already run through step 7 or 8).

- [ ] **Step 2: Add script 08 to the pipeline list, with an explicit run-order callout**

Add a new entry for `scripts/08_candidacy_matrix.py` to the numbered pipeline list (matching whatever numbering convention the current list uses), with wording along these lines:

```markdown
8. `scripts/08_candidacy_matrix.py` — download TSE candidate-registration
   files (`consulta_cand`), build a candidacy matrix confirming which
   years Hugo Leal, Felipe Peixoto, and PSD actually ran (and for which
   cargo/election type), and build the PSD slate breakdown

**Execution order note:** despite the number, `08` must run *after* `05`
(it merges the PSD breakdown onto `psd.geojson`, which `05` produces) and
*before* `06` (which reads the candidacy matrix `08` builds for delta
gating). The real run order is:

```
01 → 02 → 03 → 04 → 05 → 08 → 06 → 07
```
```

Adjust the exact placement/heading level to match the surrounding document's existing style rather than the above verbatim if the current README's structure differs.

- [ ] **Step 3: Update the Delta Outputs / Competitor Outputs sections for the new fields**

Add a short note to whichever existing section documents `vote_deltas.geojson`'s fields, mentioning the new `candidacy_status_hugo`/`candidacy_status_felipe`/`candidacy_status_psd` fields and that vote/delta fields are now `null` (not `0`) for ungated pairs. Add a new short section documenting `psd.geojson`'s new `psd_candidate_count`/`psd_top{1,2,3}_*`/`psd_total_por_cargo` fields, and `hugo_leal.geojson`/`felipe_peixoto.geojson`'s new `cargo`/`total_votos_validos` fields.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document scripts/08_candidacy_matrix.py and the real pipeline run order"
```

---

### Task 9: Frontend — "Geral" legend rename, `StatsPanel` and `DeltaLayer` null-coercion fixes

**Files:**
- Modify: `app-web/src/lib/format.js`, `app-web/src/lib/format.test.js`, `app-web/src/index.css`, `app-web/src/components/YearFilter.jsx`, `app-web/src/components/StatsPanel.jsx`, `app-web/src/components/StatsPanel.test.jsx`, `app-web/src/components/DeltaLayer.jsx`, `app-web/src/components/DeltaLayer.test.jsx`

**Interfaces:**
- Consumes: nothing new.
- Produces: `electionType()` now returns `'Geral'` instead of `'Federal'` — consumed by every existing caller (`YearFilter`, `DeltaPopupContent`, `StatsPanel`) automatically, no call-site changes needed since they all just render the return value. Hardened `StatsPanel`/`DeltaLayer` that skip `null` metric values instead of coercing to `0` — this task's actual behavior fix, consumed by nothing further (leaf-level correctness).

- [ ] **Step 1: Write the failing tests**

In `app-web/src/lib/format.test.js`, update the existing `electionType` tests (find the `describe('electionType', ...)` block) — replace `'Federal'` with `'Geral'` in every assertion, and replace `'Municipal -> Federal'`/`'Federal -> Federal'` in the `electionPairLabel` tests with `'Municipal -> Geral'`/`'Geral -> Geral'`. Also update the two test *description* strings that say "as Federal" and "municipal-to-federal" to say "as Geral"/"municipal-to-geral" — cosmetic, but the file already exists with these exact strings, and a description that no longer matches its assertion is confusing for the next person reading it.

In `app-web/src/components/StatsPanel.test.jsx`, append:

```jsx
it('excludes null (N/A) deltas from Ganhos/Perdas instead of coercing to 0', () => {
  const dataWithNull = {
    ...data,
    vote_deltas: { features: [
      { properties: { pair: '2022-2024', ano_inicio: 2022, ano_fim: 2024, delta_hugo: null, votos_hugo_inicio: 100, votos_hugo_fim: null } },
      { properties: { pair: '2022-2024', ano_inicio: 2022, ano_fim: 2024, delta_hugo: -30, votos_hugo_inicio: 200, votos_hugo_fim: 170 } },
    ] },
  };
  render(<StatsPanel data={dataWithNull} selectedYear={2022} selectedRegion="all" selectedBairro="all" selectedPair="2022-2024" selectedDeltaMetric="hugo" deltaEnabled />);
  // Only the second row (-30) should count toward Perdas; the null row must not become a phantom -0 or be coerced to 0-and-counted.
  expect(screen.getByText('30')).toBeInTheDocument();
  expect(screen.queryByText('0')).not.toBeInTheDocument();
});
```

`app-web/src/components/DeltaLayer.test.jsx` **already exists** — it was created during the prior React migration plan's final-review fix wave, covering the `markerPane` z-order regression (a `CircleMarker` must render in `.leaflet-marker-pane`, not `.leaflet-overlay-pane`). Read it first; append a new test inside the existing `describe('DeltaLayer', ...)` block, don't replace the file:

```jsx
  it('skips rendering a marker for a feature whose selected metric is null (N/A)', () => {
    const features = [
      { type: 'Feature', geometry: { type: 'Point', coordinates: [-43.08, -22.90] }, properties: { nr_local: '1', pair: '2022-2024', delta_hugo: null } },
      { type: 'Feature', geometry: { type: 'Point', coordinates: [-43.07, -22.91] }, properties: { nr_local: '2', pair: '2022-2024', delta_hugo: -10 } },
    ];
    const { container } = render(
      <MapContainer center={[-22.9017, -43.0783]} zoom={13}>
        <DeltaLayer features={features} metric={DELTA_METRICS.hugo} selectedDeltaMetric="hugo" data={{}} />
      </MapContainer>
    );
    const paths = container.querySelectorAll('.leaflet-marker-pane path');
    expect(paths.length).toBe(1);
  });
```

(Uses the same `MapContainer`/`DELTA_METRICS` imports the existing test in this file already has — no new imports needed. Note the existing test's marker now lands in `.leaflet-marker-pane`, not `.leaflet-overlay-pane` — this new test's selector matches that, not the pre-fix pane.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test` (from `app-web/`)
Expected: FAIL on the `electionType`/`electionPairLabel` assertions (still return `'Federal'`), the `StatsPanel` null-filtering test (currently coerces null to 0 via `Number(x) || 0`), and the new `DeltaLayer` test (currently renders a marker for every feature regardless of null).

- [ ] **Step 3: Rename `electionType`'s return value**

In `app-web/src/lib/format.js`, replace:

```js
export function electionType(year) {
  return Number(year) % 4 === 0 ? 'Municipal' : 'Federal';
}
```

with:

```js
export function electionType(year) {
  return Number(year) % 4 === 0 ? 'Municipal' : 'Geral';
}
```

- [ ] **Step 4: Rename the CSS class**

In `app-web/src/index.css`, replace:

```css
.year-btn.municipal::before, .year-btn.federal::before {
  content: ''; display: inline-block; width: 6px; height: 6px; border-radius: 50%;
  margin-right: 5px; vertical-align: middle;
}
.year-btn.municipal::before { background: #2dd4bf; }
.year-btn.federal::before { background: #a78bfa; }
```

with:

```css
.year-btn.municipal::before, .year-btn.geral::before {
  content: ''; display: inline-block; width: 6px; height: 6px; border-radius: 50%;
  margin-right: 5px; vertical-align: middle;
}
.year-btn.municipal::before { background: #2dd4bf; }
.year-btn.geral::before { background: #a78bfa; }
```

`YearFilter.jsx`'s year-button class name is already derived from `electionType(y).toLowerCase()`, so it needs no edit — it'll automatically become `'geral'` once Step 3 lands. Its legend row's second `<span>` is hardcoded text, not derived from `electionType()`, though. In `app-web/src/components/YearFilter.jsx`, replace:

```jsx
        <span><span className="dot" style={{ background: '#a78bfa' }} /> Federal</span>
```

with:

```jsx
        <span><span className="dot" style={{ background: '#a78bfa' }} /> Geral</span>
```

- [ ] **Step 5: Fix `StatsPanel`'s null-coercion**

In `app-web/src/components/StatsPanel.jsx`, replace the delta aggregation block:

```jsx
    const startTotal = feats.reduce((s, f) => s + (Number(f.properties[`votos_${selectedDeltaMetric}_inicio`]) || 0), 0);
    const endTotal = feats.reduce((s, f) => s + (Number(f.properties[`votos_${selectedDeltaMetric}_fim`]) || 0), 0);
    const total = feats.reduce((s, f) => s + (Number(f.properties[metric.field]) || 0), 0);
    const gained = feats.reduce((s, f) => s + Math.max(Number(f.properties[metric.field]) || 0, 0), 0);
    const lost = feats.reduce((s, f) => s + Math.max(-(Number(f.properties[metric.field]) || 0), 0), 0);
```

with:

```jsx
    const gated = feats.filter(f => f.properties[metric.field] !== null && f.properties[metric.field] !== undefined);
    const startTotal = gated.reduce((s, f) => s + (Number(f.properties[`votos_${selectedDeltaMetric}_inicio`]) || 0), 0);
    const endTotal = gated.reduce((s, f) => s + (Number(f.properties[`votos_${selectedDeltaMetric}_fim`]) || 0), 0);
    const total = gated.reduce((s, f) => s + Number(f.properties[metric.field]), 0);
    const gained = gated.reduce((s, f) => s + Math.max(Number(f.properties[metric.field]), 0), 0);
    const lost = gated.reduce((s, f) => s + Math.max(-Number(f.properties[metric.field]), 0), 0);
```

- [ ] **Step 6: Fix `DeltaLayer`'s null-coercion**

In `app-web/src/components/DeltaLayer.jsx`, find the line computing `maxAbs` and the `.map()` that renders one `CircleMarker` per feature. Add a filter before both: replace

```jsx
export default function DeltaLayer({ features, metric, selectedDeltaMetric, data }) {
  const maxAbs = Math.max(1, ...features.map(f => Math.abs(Number(f.properties[metric.field]) || 0)));

  return (
    <>
      {features.map(f => {
```

with

```jsx
export default function DeltaLayer({ features, metric, selectedDeltaMetric, data }) {
  const gatedFeatures = features.filter(f => f.properties[metric.field] !== null && f.properties[metric.field] !== undefined);
  const maxAbs = Math.max(1, ...gatedFeatures.map(f => Math.abs(Number(f.properties[metric.field]))));

  return (
    <>
      {gatedFeatures.map(f => {
```

(The rest of the function body — the per-feature `delta`/`color`/`CircleMarker` construction — is unchanged; it now only ever receives gated features, so `Number(f.properties[metric.field])` inside it never needs a `|| 0` fallback for this reason. Leave any existing `|| 0` inside the per-feature body as-is if present — it may guard a genuinely different edge case; don't remove code this step didn't ask you to touch.)

- [ ] **Step 7: Run tests to verify they pass**

Run: `npm test` (from `app-web/`)
Expected: PASS, full suite (79 — 77 pre-existing + 1 new `StatsPanel` test + 1 test appended to the existing `DeltaLayer.test.jsx`).

- [ ] **Step 8: Commit**

```bash
git add app-web/src/lib/format.js app-web/src/lib/format.test.js app-web/src/index.css app-web/src/components/YearFilter.jsx app-web/src/components/StatsPanel.jsx app-web/src/components/StatsPanel.test.jsx app-web/src/components/DeltaLayer.jsx app-web/src/components/DeltaLayer.test.jsx
git commit -m "fix: rename Federal to Geral in legend, stop coercing N/A deltas to 0"
```

---

### Task 10: Frontend — `PopupContent` redesign and N/A handling

**Files:**
- Modify: `app-web/src/components/PopupContent.jsx`, `app-web/src/components/PopupContent.test.jsx`

**Interfaces:**
- Consumes: `formatSigned` (`lib/format.js`).
- Produces: redesigned `<PopupContent>` rendering `Nome · Partido · Cargo pretendido · Votos · % share` for Hugo/Felipe, unchanged shape for PSD — consumed by nothing further within this plan (leaf component), but this is the primary user-visible deliverable of the whole spec.

- [ ] **Step 1: Write the failing tests**

Replace `app-web/src/components/PopupContent.test.jsx` in full:

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PopupContent from './PopupContent';

const hugoProps = {
  nm_local: 'Escola Teste', bairro: 'Icarai', ano: 2022, QT_VOTOS: 50, n_secoes: 3,
  cargo: 'DEPUTADO FEDERAL', total_votos_validos: 1000,
};

describe('PopupContent', () => {
  it('renders Nome, Partido, Cargo pretendido, Votos, and % share for hugo_leal', () => {
    render(<PopupContent p={hugoProps} layerKey="hugo_leal" />);
    expect(screen.getByText('Escola Teste')).toBeInTheDocument();
    expect(screen.getByText('Icarai')).toBeInTheDocument();
    expect(screen.getByText('Hugo Leal')).toBeInTheDocument();
    expect(screen.getByText('DEPUTADO FEDERAL')).toBeInTheDocument();
    expect(screen.getByText('50')).toBeInTheDocument();
    expect(screen.getByText('5,0%')).toBeInTheDocument(); // 50/1000
  });

  it('shows the competitor section for hugo_leal and felipe_peixoto', () => {
    render(<PopupContent p={hugoProps} layerKey="hugo_leal" />);
    expect(screen.getByText('Concorrencia')).toBeInTheDocument();
  });

  it('hides the competitor section for psd and keeps the original field shape (no Cargo pretendido, no % share)', () => {
    const psdProps = { nm_local: 'Escola Teste', bairro: 'Icarai', ano: 2022, QT_VOTOS: 500, n_secoes: 3 };
    render(<PopupContent p={psdProps} layerKey="psd" />);
    expect(screen.queryByText('Concorrencia')).not.toBeInTheDocument();
    expect(screen.queryByText('Cargo pretendido')).not.toBeInTheDocument();
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });

  it('shows N/A instead of a vote share when total_votos_validos is missing', () => {
    const propsNoTotal = { ...hugoProps, total_votos_validos: null };
    render(<PopupContent p={propsNoTotal} layerKey="hugo_leal" />);
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  it('hides the competitor section in aggregated ("Todos" years) mode, showing a yearly breakdown instead', () => {
    const aggregated = { ...hugoProps, _years: { 2018: 20, 2022: 30 }, QT_VOTOS: 50 };
    render(<PopupContent p={aggregated} layerKey="hugo_leal" />);
    expect(screen.queryByText('Concorrencia')).not.toBeInTheDocument();
    expect(screen.getByText('2018')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
    expect(screen.getByText('Total')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test` (from `app-web/`)
Expected: FAIL — current `PopupContent` still renders the single "Candidato/Partido" row and has no `Cargo pretendido`/`% share`/N/A handling.

- [ ] **Step 3: Rewrite `PopupContent`**

Replace `app-web/src/components/PopupContent.jsx` in full:

```jsx
import CompetitorSection from './CompetitorSection';
import { COLORS, LABELS, COMPETITOR_LAYER_BY_METRIC } from '../lib/constants';

function voteShareText(votos, totalValidos) {
  if (votos == null || totalValidos == null || totalValidos === 0) return 'N/A';
  return `${(votos / totalValidos * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
}

export default function PopupContent({ p, layerKey }) {
  const hasCompetitorData = Object.values(COMPETITOR_LAYER_BY_METRIC).includes(layerKey);
  const isIndividualCandidate = hasCompetitorData; // hugo_leal / felipe_peixoto only, not psd

  return (
    <div>
      <div className="popup-title">{p.nm_local || `Local ${p.nr_local}`}</div>
      <div className="popup-bairro">{p.bairro || ''}</div>
      <div className="popup-row">
        <span className="popup-label">Nome</span>
        <span className="popup-val" style={{ color: COLORS[layerKey] }}>{LABELS[layerKey]}</span>
      </div>
      {p._years ? (
        <>
          {Object.entries(p._years).sort((a, b) => a[0] - b[0]).map(([y, v]) => (
            <div className="popup-row" key={y}>
              <span className="popup-label">{y}</span>
              <span className="popup-val">{v.toLocaleString('pt-BR')}</span>
            </div>
          ))}
          <div className="popup-row" style={{ borderTop: '1px solid rgba(255,255,255,0.1)', marginTop: 4, paddingTop: 4 }}>
            <span className="popup-label">Total</span>
            <span className="popup-val">{p.QT_VOTOS.toLocaleString('pt-BR')}</span>
          </div>
        </>
      ) : (
        <>
          {isIndividualCandidate && (
            <div className="popup-row"><span className="popup-label">Cargo pretendido</span><span className="popup-val">{p.cargo}</span></div>
          )}
          <div className="popup-row"><span className="popup-label">Ano</span><span className="popup-val">{p.ano}</span></div>
          <div className="popup-row"><span className="popup-label">Votos</span><span className="popup-val">{p.QT_VOTOS.toLocaleString('pt-BR')}</span></div>
          {isIndividualCandidate && (
            <div className="popup-row"><span className="popup-label">% share</span><span className="popup-val">{voteShareText(p.QT_VOTOS, p.total_votos_validos)}</span></div>
          )}
          <div className="popup-row"><span className="popup-label">Secoes</span><span className="popup-val">{p.n_secoes}</span></div>
          {hasCompetitorData && <CompetitorSection title="Concorrencia" props={p} />}
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test`
Expected: PASS.

- [ ] **Step 5: Manual browser check**

Run `npm run dev` from `app-web/` (after the pipeline tasks have regenerated real data — Task 7's spot-check already re-ran `07`, so `total_votos_validos`/`cargo` should be present in the served `data.js`). Click a Hugo Leal marker — popup should show `Nome`, `Cargo pretendido`, `Ano`, `Votos`, `% share`, `Secoes`, and the collapsible competitor section, in that order. Click a PSD marker — popup should look like today's (no `Cargo pretendido`, no `% share`), unchanged. Stop the server.

- [ ] **Step 6: Commit**

```bash
git add app-web/src/components/PopupContent.jsx app-web/src/components/PopupContent.test.jsx
git commit -m "feat: redesign popup with cargo and vote-share fields"
```

---

### Task 11: Frontend — `DeltaPopupContent` N/A handling

**Files:**
- Modify: `app-web/src/components/DeltaPopupContent.jsx`, `app-web/src/components/DeltaPopupContent.test.jsx`

**Interfaces:**
- Consumes: `formatSigned` (`lib/format.js`, unchanged signature).
- Produces: updated `<DeltaPopupContent>` rendering "N/A (não concorreu)" etc. for gated-out candidates instead of `formatSigned(null)`.

- [ ] **Step 1: Write the failing tests**

Append to `app-web/src/components/DeltaPopupContent.test.jsx`:

```jsx
it('renders N/A with the candidacy_status reason when a candidate delta is null', () => {
  const pWithNull = { ...p, delta_felipe: null, candidacy_status_felipe: 'nao_concorreu', votos_felipe_inicio: null, votos_felipe_fim: null };
  render(<DeltaPopupContent p={pWithNull} metric={metric} color="#fff" selectedDeltaMetric="hugo" findYearLocalFeature={noopFind} />);
  expect(screen.getByText(/N\/A/)).toBeInTheDocument();
  expect(screen.queryByText(/undefined -> undefined/)).not.toBeInTheDocument();
});

it('renders N/A for the primary metric row when the selected metric itself is gated out', () => {
  const pWithNull = { ...p, delta_hugo: null, candidacy_status_hugo: 'tipo_incompativel' };
  render(<DeltaPopupContent p={pWithNull} metric={metric} color="#fff" selectedDeltaMetric="hugo" findYearLocalFeature={noopFind} />);
  expect(screen.getByText(/N\/A/)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test -- DeltaPopupContent` (from `app-web/`)
Expected: FAIL — current component calls `formatSigned(null)` which renders `'0'`, and interpolates `undefined -> undefined` into the Hugo/Felipe/PSD summary rows.

- [ ] **Step 3: Add N/A handling**

Replace `app-web/src/components/DeltaPopupContent.jsx` in full:

```jsx
import CompetitorSection from './CompetitorSection';
import { formatSigned, formatPct, electionPairLabel } from '../lib/format';
import { COMPETITOR_LAYER_BY_METRIC } from '../lib/constants';

function PopupRow({ label, value, color }) {
  return (
    <div className="popup-row">
      <span className="popup-label">{label}</span>
      <span className="popup-val" style={color ? { color } : undefined}>{value}</span>
    </div>
  );
}

const STATUS_LABELS = {
  nao_concorreu: 'nao concorreu',
  nao_concorreu_inicio: 'nao concorreu no ano inicial',
  nao_concorreu_fim: 'nao concorreu no ano final',
  tipo_incompativel: 'tipos de eleicao incompativeis',
};

function candidateSummary(inicio, fim, delta, status) {
  if (delta == null) {
    const reason = STATUS_LABELS[status] || 'sem dados';
    return `N/A (${reason})`;
  }
  return `${inicio} -> ${fim} (${formatSigned(delta)})`;
}

export default function DeltaPopupContent({ p, metric, color, selectedDeltaMetric, findYearLocalFeature }) {
  const moved = (Number(p.secoes_movidas_in) || 0) + (Number(p.secoes_movidas_out) || 0);
  const competitorLayer = COMPETITOR_LAYER_BY_METRIC[selectedDeltaMetric];
  const startFeat = competitorLayer ? findYearLocalFeature(competitorLayer, p.ano_inicio, p.nr_local) : null;
  const endFeat = competitorLayer ? findYearLocalFeature(competitorLayer, p.ano_fim, p.nr_local) : null;
  const primaryValue = p[metric.field] == null
    ? `N/A (${STATUS_LABELS[p[`candidacy_status_${selectedDeltaMetric}`]] || 'sem dados'})`
    : formatSigned(p[metric.field]);

  return (
    <div>
      <div className="popup-title">{p.nm_local || `Local ${p.nr_local}`}</div>
      <div className="popup-bairro">{p.bairro || ''}</div>
      <PopupRow label="Par" value={p.pair} />
      <PopupRow label="Tipo de eleicao" value={p.tipo_par || electionPairLabel(p.ano_inicio, p.ano_fim)} />
      <PopupRow label={`Delta ${metric.label}`} value={primaryValue} color={p[metric.field] == null ? undefined : color} />
      <PopupRow label="Hugo" value={candidateSummary(p.votos_hugo_inicio, p.votos_hugo_fim, p.delta_hugo, p.candidacy_status_hugo)} />
      <PopupRow label="Felipe" value={candidateSummary(p.votos_felipe_inicio, p.votos_felipe_fim, p.delta_felipe, p.candidacy_status_felipe)} />
      <PopupRow label="PSD" value={candidateSummary(p.votos_psd_inicio, p.votos_psd_fim, p.delta_psd, p.candidacy_status_psd)} />
      <PopupRow label="Secoes" value={`${p.secoes_inicio || 0} -> ${p.secoes_fim || 0}`} />
      <PopupRow label="Troca de secoes" value={formatPct((Number(p.secao_churn) || 0) * 100)} />
      {moved > 0 && <PopupRow label="Secoes com troca" value={`+${p.secoes_movidas_in || 0} / -${p.secoes_movidas_out || 0}`} />}
      {competitorLayer && (
        <>
          <CompetitorSection title={`Concorrencia ${p.ano_inicio}`} props={startFeat ? startFeat.properties : {}} />
          <CompetitorSection title={`Concorrencia ${p.ano_fim}`} props={endFeat ? endFeat.properties : {}} />
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test`
Expected: PASS, including the pre-existing `DeltaPopupContent` tests (the fixture `p` in the existing test file has real numeric `delta_hugo`/`delta_felipe`/`delta_psd` values and no `candidacy_status_*` fields — `candidateSummary`'s `delta == null` check is `false` for those, so the pre-existing "renders the local name and delta fields" / "shows two competitor sections" / "shows no competitor sections for psd" tests keep passing unmodified).

- [ ] **Step 5: Commit**

```bash
git add app-web/src/components/DeltaPopupContent.jsx app-web/src/components/DeltaPopupContent.test.jsx
git commit -m "feat: render N/A with reason for gated-out candidacies in delta popup"
```

---

### Task 12: Frontend — `PsdBreakdownSection`

**Files:**
- Create: `app-web/src/components/PsdBreakdownSection.jsx`, `app-web/src/components/PsdBreakdownSection.test.jsx`
- Modify: `app-web/src/components/PopupContent.jsx`

**Interfaces:**
- Consumes: nothing new.
- Produces: `<PsdBreakdownSection props>` — wired into `PopupContent` for `layerKey === 'psd'`.

- [ ] **Step 1: Write the failing tests**

Create `app-web/src/components/PsdBreakdownSection.test.jsx`:

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PsdBreakdownSection from './PsdBreakdownSection';

describe('PsdBreakdownSection', () => {
  it('renders candidate count and up to 3 ranked entries with cargo and share', () => {
    render(<PsdBreakdownSection props={{
      psd_candidate_count: 3,
      psd_top1_nome: 'FULANO', psd_top1_cargo: 'PREFEITO', psd_top1_votos: 900, psd_top1_share: 45.0,
      psd_top2_nome: 'BELTRANO', psd_top2_cargo: 'VEREADOR', psd_top2_votos: 200, psd_top2_share: 12.5,
    }} />);
    expect(screen.getByText('Composicao PSD')).toBeInTheDocument();
    expect(screen.getByText(/3 candidatos/)).toBeInTheDocument();
    expect(screen.getByText(/FULANO \(PREFEITO\) — 900 — 45%/)).toBeInTheDocument();
    expect(screen.getByText(/BELTRANO \(VEREADOR\) — 200 — 12,5%/)).toBeInTheDocument();
  });

  it('shows "Sem dados" when no breakdown fields are present', () => {
    render(<PsdBreakdownSection props={{}} />);
    expect(screen.getByText('Sem dados')).toBeInTheDocument();
  });

  it('is collapsed by default (a native <details> element)', () => {
    render(<PsdBreakdownSection props={{ psd_candidate_count: 1, psd_top1_nome: 'X', psd_top1_cargo: 'VEREADOR', psd_top1_votos: 10, psd_top1_share: 1 }} />);
    const details = screen.getByText('Composicao PSD').closest('details');
    expect(details).not.toHaveAttribute('open');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm test` (from `app-web/`)
Expected: FAIL — `PsdBreakdownSection.jsx` doesn't exist.

- [ ] **Step 3: Write `PsdBreakdownSection`**

Create `app-web/src/components/PsdBreakdownSection.jsx`:

```jsx
function breakdownRows(props) {
  const rows = [];
  for (let i = 1; i <= 3; i++) {
    const nome = props[`psd_top${i}_nome`];
    if (!nome) continue;
    const cargo = props[`psd_top${i}_cargo`] || '-';
    const votos = Number(props[`psd_top${i}_votos`] || 0).toLocaleString('pt-BR');
    const share = Number(props[`psd_top${i}_share`] || 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 });
    rows.push(
      <div className="popup-row" key={i}>
        <span className="popup-label">{i}º</span>
        <span className="popup-val">{nome} ({cargo}) — {votos} — {share}%</span>
      </div>
    );
  }
  return rows;
}

export default function PsdBreakdownSection({ props }) {
  const rows = breakdownRows(props);
  const count = props.psd_candidate_count;

  return (
    <details className="popup-competitors">
      <summary>Composicao PSD</summary>
      {count != null && (
        <div className="popup-row"><span className="popup-label">{count} candidatos</span></div>
      )}
      {rows.length ? rows : <div className="popup-row"><span className="popup-label">Sem dados</span></div>}
    </details>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `npm test`
Expected: PASS.

- [ ] **Step 5: Wire it into `PopupContent`**

In `app-web/src/components/PopupContent.jsx`, add the import:

```jsx
import PsdBreakdownSection from './PsdBreakdownSection';
```

Replace the line `{hasCompetitorData && <CompetitorSection title="Concorrencia" props={p} />}` with:

```jsx
          {hasCompetitorData && <CompetitorSection title="Concorrencia" props={p} />}
          {layerKey === 'psd' && <PsdBreakdownSection props={p} />}
```

- [ ] **Step 6: Manual browser check**

Run `npm run dev` from `app-web/`. Click a PSD marker for a year/local with real breakdown data (Task 4's real-data run merged this onto `psd.geojson`). Popup should show the unchanged base fields (Nome, Ano, Votos, Secoes) plus a new collapsed "▸ Composicao PSD" line; expanding it shows candidate count and up to 3 ranked entries with cargo, votes, and share. Stop the server.

- [ ] **Step 7: Commit**

```bash
git add app-web/src/components/PsdBreakdownSection.jsx app-web/src/components/PsdBreakdownSection.test.jsx app-web/src/components/PopupContent.jsx
git commit -m "feat: add PSD slate breakdown popup section"
```

---

### Task 13: Full pipeline run and regression verification

**Files:** none (verification only; fix any discrepancy found in whichever task's file owns it, then re-run this task's checklist).

**Interfaces:** none — this is the spec's exit criterion.

- [ ] **Step 1: Run the full pipeline in the correct order**

From the `LEAL` directory:

```bash
python scripts/05_build_geojson.py
python scripts/08_candidacy_matrix.py
python scripts/06_build_vote_deltas.py
python scripts/07_top_competitors.py
```

Expected: all four complete with `Done.`, no unhandled exceptions. (`01`-`04` are assumed already run from prior sessions — raw/processed data already exists. If any of `01`-`04`'s outputs are missing, run them first in order.)

- [ ] **Step 2: Run the full test suite**

Run: `python -m pytest tests/ -v` (from `LEAL/`)
Expected: all tests pass, including every test added across Tasks 1-7.

Run: `npm test` (from `app-web/`)
Expected: all tests pass, including every test added across Tasks 9-12.

- [ ] **Step 3: Verify the two named regressions from the original request are fixed, end to end**

```bash
python -c "
import json
felipe = json.load(open('data/geo/vote_deltas.geojson', encoding='utf-8'))
felipe_2024 = [f for f in felipe['features'] if f['properties']['ano_fim'] == 2024]
bad = [f for f in felipe_2024 if f['properties']['delta_felipe'] is not None]
assert not bad, f'Found {len(bad)} rows with a non-null Felipe delta ending in 2024 (he did not run)'

psd_2010 = [f for f in felipe['features'] if f['properties']['ano_inicio'] == 2010 or f['properties']['ano_fim'] == 2010]
bad_psd = [f for f in psd_2010 if f['properties']['delta_psd'] is not None]
assert not bad_psd, f'Found {len(bad_psd)} rows with a non-null PSD delta touching 2010 (party did not exist)'
print('OK — both named regressions confirmed fixed')
"
```

Expected: `OK` printed.

- [ ] **Step 4: Manual browser walkthrough**

Run `npm run dev` from `app-web/`, `python -m http.server 8000` from `app/` (the vanilla site, for a quick visual sanity comparison on the parts that didn't change — layers, filters, compare panel).

Check, in the React app specifically:
1. Hugo/Felipe popup shows the new `Cargo pretendido`/`% share` fields with plausible values.
2. PSD popup's "Composicao PSD" section expands to real candidate/cargo/vote data.
3. Switch year to one where Felipe or PSD is gated out (per Step 3's findings) — confirm the delta layer doesn't show a phantom marker there when that metric is selected, and the stats panel's Ganhos/Perdas don't include a silent 0.
4. Year legend and delta popup's "Tipo de eleicao" both read "Geral", not "Federal".
5. Region/bairro filtering and boundary highlighting (from the prior migration) still work — this task's changes shouldn't have touched that code path, confirm no regression.

- [ ] **Step 5: Fix any discrepancy found**

If a mismatch turns up, fix it in the relevant file from whichever earlier task owns it, add or extend that task's test to cover the specific case that broke, re-run the relevant test suite, and re-check the specific checklist item before continuing.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "chore: candidacy matrix and delta gating parity pass complete"
```

Stop both local servers.
