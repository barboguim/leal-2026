# Locais de Votação — Mudanças e Acesso a Ônibus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone side project that (1) diffs Niterói's TSE polling-location roster across 2022→2024→2026 to find locations that appeared or disappeared, (2) ingests all ~56 Niterói bus lines' routes and stops from MobNit's public API, (3) computes each changed location's distance to its nearest bus stop, and (4) renders all of it on one static HTML page.

**Architecture:** Four sequential Python scripts in a new `side_projects/locais_bus_access/` folder, each reading/writing plain GeoJSON files under `data/geo/`. No changes to `app-web`, `DESIGN.md`, or the numbered `scripts/01`–`10` pipeline. The final script assembles a single self-contained HTML file (Leaflet via CDN, data embedded inline) — no server, no build step.

**Tech Stack:** Python (pandas, requests — both already in `requirements.txt`), stdlib `math`/`json`/`datetime` for haversine and date math, Leaflet 1.9.4 via CDN for the static page, pytest for pure-function tests.

**Spec:** `docs/superpowers/specs/2026-09-06-locais-bus-access-design.md`

## Global Constraints

- Do not modify anything under `app-web/`, `DESIGN.md`, or `scripts/01`–`10` — this is explicitly a side project, not a feature of the main React map (spec Context/Scope).
- Reuse `scripts/_pipeline_utils.py` helpers (`find_csv`, `read_tse_csv_safe`, `normalize`, `clean_id_series`, `download_and_extract`, `to_geojson`) rather than reimplementing TSE CSV handling — this repo's established convention (spec §2).
- No new third-party dependencies — `pandas`/`requests` already installed; haversine and date-bounds math use stdlib only (spec §3, §1).
- Cache every MobNit HTTP response to disk under `data/raw/mobnit/` before parsing, so repeat runs don't re-fetch — it's public municipal infrastructure, not to be hammered on every dev run (spec §1).
- Do not write tests for the MobNit network fetch itself or for the static page's visual rendering — only pure/computational functions get unit tests (spec §5). Pure helper functions extracted from each script (date-bounds math, GeoJSON shaping, dedupe, diffing, haversine, nearest-stop selection) do get tests — these are non-trivial logic (loops, branches) independent of network access.
- Locations count as "changed" purely by `NR_LOCAL_VOTACAO` presence/absence between two years — no vote-count, candidate, or winner logic anywhere in this project (spec Scope).
- If TSE hasn't published the 2026 `locais_votacao` file yet, the pipeline must degrade gracefully (log and skip the 2024→2026 pair) rather than fail (spec §2).

---

### Task 1: Bus route + stop ingestion

**Files:**
- Create: `side_projects/locais_bus_access/fetch_bus_routes.py`
- Test: `tests/test_fetch_bus_routes.py`

**Interfaces:**
- Consumes: `config.DATA_RAW`, `config.DATA_GEO` (both already defined in `config.py`).
- Produces:
  - `month_bounds_ms(now: datetime) -> tuple[int, int]`
  - `shapes_to_route_features(numero_linha: str, nome_linha: str, shapes: list[dict]) -> list[dict]` (GeoJSON Feature dicts)
  - `dedupe_stops(raw_stops: list[dict]) -> list[dict]` (each `{"lat": float, "lon": float, "endereco": str, "linhas": list[str]}`)
  - `stops_to_geojson(stops: list[dict]) -> dict` (GeoJSON FeatureCollection)
  - Writes `data/geo/bus_routes.geojson` and `data/geo/bus_stops.geojson` when run as a script.
  - Task 3 consumes `data/geo/bus_stops.geojson`'s feature shape: `properties.linhas: list[str]`, `geometry.coordinates: [lon, lat]`.

- [ ] **Step 1: Write the failing tests for the pure helper functions**

```python
# tests/test_fetch_bus_routes.py
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "side_projects" / "locais_bus_access"))
import fetch_bus_routes as fbr


def test_month_bounds_ms_covers_the_full_month():
    now = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)
    from_ms, to_ms = fbr.month_bounds_ms(now)
    expected_start = int(datetime(2026, 9, 1, tzinfo=timezone.utc).timestamp() * 1000)
    expected_end = int(datetime(2026, 9, 30, 23, 59, 59, 999000, tzinfo=timezone.utc).timestamp() * 1000)
    assert from_ms == expected_start
    assert to_ms == expected_end


def test_month_bounds_ms_handles_february_in_a_leap_year():
    now = datetime(2028, 2, 15, tzinfo=timezone.utc)
    _, to_ms = fbr.month_bounds_ms(now)
    expected_end = int(datetime(2028, 2, 29, 23, 59, 59, 999000, tzinfo=timezone.utc).timestamp() * 1000)
    assert to_ms == expected_end


def test_shapes_to_route_features_builds_one_linestring_per_shape():
    shapes = [
        {"sentido": "Ida", "shapeId": "1_I", "coordenadas": [[-43.1, -22.9], [-43.11, -22.91]]},
        {"sentido": "Volta", "shapeId": "1_V", "coordenadas": [[-43.11, -22.91], [-43.1, -22.9]]},
    ]
    features = fbr.shapes_to_route_features("15", "Ilha Conceicao x Centro", shapes)
    assert len(features) == 2
    assert features[0]["properties"] == {
        "numeroLinha": "15", "nomeLinha": "Ilha Conceicao x Centro", "sentido": "Ida", "shapeId": "1_I",
    }
    assert features[0]["geometry"] == {"type": "LineString", "coordinates": [[-43.1, -22.9], [-43.11, -22.91]]}


def test_dedupe_stops_merges_same_physical_stop_across_lines():
    raw_stops = [
        {"latitude": -22.9, "longitude": -43.1, "parada": "Rua A", "numeroLinha": "15"},
        {"latitude": -22.900001, "longitude": -43.100001, "parada": "Rua A", "numeroLinha": "22"},
        {"latitude": -22.95, "longitude": -43.2, "parada": "Rua B", "numeroLinha": "15"},
    ]
    stops = fbr.dedupe_stops(raw_stops)
    assert len(stops) == 2
    merged = next(s for s in stops if s["endereco"] == "Rua A")
    assert merged["linhas"] == ["15", "22"]


def test_stops_to_geojson_builds_point_features():
    stops = [{"lat": -22.9, "lon": -43.1, "endereco": "Rua A", "linhas": ["15"]}]
    geojson = fbr.stops_to_geojson(stops)
    assert geojson["features"][0]["geometry"] == {"type": "Point", "coordinates": [-43.1, -22.9]}
    assert geojson["features"][0]["properties"] == {"endereco": "Rua A", "linhas": ["15"]}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_fetch_bus_routes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fetch_bus_routes'`

- [ ] **Step 3: Write `fetch_bus_routes.py`**

```python
# side_projects/locais_bus_access/fetch_bus_routes.py
"""Fetches all Niterói bus lines' route geometry and stops from MobNit's
public API (mobnit.niteroi.rj.gov.br) and writes them as GeoJSON for the
locais-bus-access side project. Caches every raw response to disk so
re-runs don't re-fetch — this is public municipal infrastructure."""

import calendar
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from config import DATA_GEO, DATA_RAW  # noqa: E402

BASE = "https://mobnit.niteroi.rj.gov.br/api/website/v1/conteudo/dados/area-publica/itinerarios"
LINHAS_URL = f"{BASE}/linhas"
DETALHES_URL = f"{BASE}/detalhes-linha"
PARADAS_URL = f"{BASE}/paradas"
REQUEST_DELAY_S = 0.2
CACHE_DIR = DATA_RAW / "mobnit"


def month_bounds_ms(now: datetime) -> tuple[int, int]:
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    last_day = calendar.monthrange(now.year, now.month)[1]
    end = datetime(now.year, now.month, last_day, 23, 59, 59, 999000, tzinfo=timezone.utc)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def shapes_to_route_features(numero_linha: str, nome_linha: str, shapes: list[dict]) -> list[dict]:
    return [
        {
            "type": "Feature",
            "properties": {
                "numeroLinha": numero_linha,
                "nomeLinha": nome_linha,
                "sentido": shape["sentido"],
                "shapeId": shape["shapeId"],
            },
            "geometry": {"type": "LineString", "coordinates": shape["coordenadas"]},
        }
        for shape in shapes
    ]


def dedupe_stops(raw_stops: list[dict]) -> list[dict]:
    merged: dict[tuple[float, float], dict] = {}
    for stop in raw_stops:
        key = (round(stop["latitude"], 5), round(stop["longitude"], 5))
        if key not in merged:
            merged[key] = {"lat": key[0], "lon": key[1], "endereco": stop["parada"], "linhas": set()}
        merged[key]["linhas"].add(stop["numeroLinha"])
    return [
        {"lat": entry["lat"], "lon": entry["lon"], "endereco": entry["endereco"], "linhas": sorted(entry["linhas"])}
        for entry in merged.values()
    ]


def stops_to_geojson(stops: list[dict]) -> dict:
    features = [
        {
            "type": "Feature",
            "properties": {"endereco": s["endereco"], "linhas": s["linhas"]},
            "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
        }
        for s in stops
    ]
    return {"type": "FeatureCollection", "name": "bus_stops", "features": features}


def fetch_json_cached(url: str, params: dict, cache_path: Path) -> dict:
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(data), encoding="utf-8")
    time.sleep(REQUEST_DELAY_S)
    return data


def main():
    now = datetime.now(timezone.utc)
    from_ms, to_ms = month_bounds_ms(now)

    linhas_raw = fetch_json_cached(LINHAS_URL, {"from": from_ms, "to": to_ms}, CACHE_DIR / "linhas.json")
    linhas = {item["numeroLinha"]: item["nomeLinha"] for item in linhas_raw}
    print(f"Found {len(linhas)} unique bus lines")

    route_features = []
    all_stops = []
    for numero_linha, nome_linha in linhas.items():
        line_dir = CACHE_DIR / numero_linha
        detalhes = fetch_json_cached(
            DETALHES_URL,
            {"from": from_ms, "to": to_ms, "numeroLinha": f"'{numero_linha}'"},
            line_dir / "detalhes.json",
        )
        route_features.extend(shapes_to_route_features(numero_linha, nome_linha, detalhes))

        for shape in detalhes:
            shape_id = shape["shapeId"]
            safe_shape_id = shape_id.replace("/", "_")
            paradas = fetch_json_cached(
                PARADAS_URL,
                {"from": from_ms, "to": to_ms, "numeroLinha": f"'{numero_linha}'", "shapeId": f"'{shape_id}'"},
                line_dir / f"paradas_{safe_shape_id}.json",
            )
            all_stops.extend({**stop, "numeroLinha": numero_linha} for stop in paradas)

        print(f"  {numero_linha}: {len(detalhes)} shapes")

    stops = dedupe_stops(all_stops)
    print(f"Total stops after dedupe: {len(stops)}")

    DATA_GEO.mkdir(parents=True, exist_ok=True)
    routes_geojson = {"type": "FeatureCollection", "name": "bus_routes", "features": route_features}
    (DATA_GEO / "bus_routes.geojson").write_text(json.dumps(routes_geojson, ensure_ascii=False), encoding="utf-8")
    (DATA_GEO / "bus_stops.geojson").write_text(
        json.dumps(stops_to_geojson(stops), ensure_ascii=False), encoding="utf-8"
    )
    print("Wrote data/geo/bus_routes.geojson and data/geo/bus_stops.geojson")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_fetch_bus_routes.py -v`
Expected: PASS (all 5 tests)

- [ ] **Step 5: Run the script for real to populate the cache and outputs**

Run: `python side_projects/locais_bus_access/fetch_bus_routes.py`
Expected: prints line-by-line progress for ~56 lines, ends with "Wrote data/geo/bus_routes.geojson and data/geo/bus_stops.geojson". Verify both files exist and are non-trivial in size (`ls -la data/geo/bus_routes.geojson data/geo/bus_stops.geojson`). A second run should complete almost instantly (cache hits) and print the same summary.

- [ ] **Step 6: Commit**

```bash
git add side_projects/locais_bus_access/fetch_bus_routes.py tests/test_fetch_bus_routes.py data/geo/bus_routes.geojson data/geo/bus_stops.geojson
git commit -m "feat: ingest MobNit bus routes and stops for locais-bus-access side project"
```

---

### Task 2: Location-change diff

**Files:**
- Create: `side_projects/locais_bus_access/location_changes.py`
- Test: `tests/test_location_changes.py`

**Interfaces:**
- Consumes: `config.DATA_RAW`, `config.DATA_GEO`, `config.MUNICIPIO`, `config.UF`, `config.url_locais_votacao` (all already in `config.py`); `_pipeline_utils.find_csv`, `read_tse_csv_safe`, `normalize`, `clean_id_series`, `download_and_extract`, `to_geojson` (all already in `scripts/_pipeline_utils.py`).
- Produces:
  - `load_year_locations(year: int, data_raw: Path, municipio: str, uf: str) -> pd.DataFrame` with columns `nr_local, nm_local, endereco, bairro, lat, lon`.
  - `diff_locations(before: pd.DataFrame, after: pd.DataFrame, pair: str) -> pd.DataFrame` with columns `nr_local, nm_local, endereco, bairro, lat, lon, pair, status` (`status` is `"appeared"` or `"disappeared"`).
  - Writes `data/geo/location_changes.geojson` when run as a script. Task 3 consumes this file's feature shape: `properties.lat`/`lon` are NOT present as properties (they're the geometry, per `to_geojson`'s convention) — `geometry.coordinates: [lon, lat]`, and `properties` carries `nr_local, nm_local, endereco, bairro, pair, status`.

- [ ] **Step 1: Write the failing tests for `diff_locations`**

```python
# tests/test_location_changes.py
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "side_projects" / "locais_bus_access"))
import location_changes as lc


def make_locations(rows):
    return pd.DataFrame(rows, columns=["nr_local", "nm_local", "endereco", "bairro", "lat", "lon"])


def test_diff_locations_finds_appeared_and_disappeared():
    before = make_locations([
        ["1", "Escola A", "Rua A", "Centro", -22.90, -43.10],
        ["2", "Escola B", "Rua B", "Centro", -22.91, -43.11],
    ])
    after = make_locations([
        ["2", "Escola B", "Rua B", "Centro", -22.91, -43.11],
        ["3", "Escola C", "Rua C", "Icarai", -22.92, -43.12],
    ])
    result = lc.diff_locations(before, after, "2022-2024")

    appeared = result[result["status"] == "appeared"]
    disappeared = result[result["status"] == "disappeared"]
    assert appeared["nr_local"].tolist() == ["3"]
    assert disappeared["nr_local"].tolist() == ["1"]
    assert (result["pair"] == "2022-2024").all()


def test_diff_locations_no_false_positive_for_unchanged_location():
    before = make_locations([["1", "Escola A", "Rua A", "Centro", -22.90, -43.10]])
    after = make_locations([
        ["1", "Escola A", "Rua A", "Centro", -22.90, -43.10],
        ["2", "Escola B", "Rua B", "Centro", -22.91, -43.11],
    ])
    result = lc.diff_locations(before, after, "2022-2024")
    assert "1" not in result["nr_local"].tolist()
    assert result["nr_local"].tolist() == ["2"]


def test_diff_locations_ignores_locations_absent_from_both_years():
    before = make_locations([["1", "Escola A", "Rua A", "Centro", -22.90, -43.10]])
    after = make_locations([["1", "Escola A", "Rua A", "Centro", -22.90, -43.10]])
    result = lc.diff_locations(before, after, "2022-2024")
    assert result.empty
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_location_changes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'location_changes'`

- [ ] **Step 3: Write `location_changes.py`**

```python
# side_projects/locais_bus_access/location_changes.py
"""Diffs Niterói's TSE polling-location roster (locais_votacao) across
consecutive elections to find locations that appeared or disappeared.
Location-only: no vote counts, candidates, or winners anywhere here."""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from config import DATA_GEO, DATA_RAW, MUNICIPIO, UF, url_locais_votacao  # noqa: E402
from _pipeline_utils import (  # noqa: E402
    clean_id_series, download_and_extract, find_csv, normalize, read_tse_csv_safe, to_geojson,
)

COLUMN_MAP = {
    "NR_LOCAL_VOTACAO": "nr_local",
    "NM_LOCAL_VOTACAO": "nm_local",
    "DS_ENDERECO": "endereco",
    "NM_BAIRRO": "bairro",
    "NR_LATITUDE": "lat",
    "NR_LONGITUDE": "lon",
}


def load_year_locations(year: int, data_raw: Path, municipio: str, uf: str) -> pd.DataFrame:
    folder = data_raw / f"locais_votacao_{year}"
    csv_file = find_csv(folder)
    if csv_file is None:
        return pd.DataFrame(columns=list(COLUMN_MAP.values()))

    df = read_tse_csv_safe(csv_file, usecols=["SG_UF", "NM_MUNICIPIO", *COLUMN_MAP.keys()])
    mask = (df["SG_UF"] == uf) & df["NM_MUNICIPIO"].apply(lambda x: normalize(x) == normalize(municipio))
    df = df.loc[mask].rename(columns=COLUMN_MAP).copy()
    df["nr_local"] = clean_id_series(df["nr_local"])
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    return df.drop_duplicates(subset=["nr_local"]).reset_index(drop=True)


def diff_locations(before: pd.DataFrame, after: pd.DataFrame, pair: str) -> pd.DataFrame:
    before_ids = set(before["nr_local"])
    after_ids = set(after["nr_local"])

    appeared = after[~after["nr_local"].isin(before_ids)].copy()
    appeared["status"] = "appeared"

    disappeared = before[~before["nr_local"].isin(after_ids)].copy()
    disappeared["status"] = "disappeared"

    result = pd.concat([appeared, disappeared], ignore_index=True)
    result["pair"] = pair
    return result[["nr_local", "nm_local", "endereco", "bairro", "lat", "lon", "pair", "status"]]


def main():
    locations_by_year = {}
    for year in (2022, 2024):
        locations_by_year[year] = load_year_locations(year, DATA_RAW, MUNICIPIO, UF)
        print(f"{year}: {len(locations_by_year[year])} locais em {MUNICIPIO}")

    dest_2026 = DATA_RAW / "locais_votacao_2026"
    if download_and_extract(url_locais_votacao(2026), dest_2026, "locais_votacao 2026"):
        locations_by_year[2026] = load_year_locations(2026, DATA_RAW, MUNICIPIO, UF)
        print(f"2026: {len(locations_by_year[2026])} locais em {MUNICIPIO}")
    else:
        print("2026 locais_votacao not yet published by TSE — skipping the 2024-2026 pair")

    pairs = [(2022, 2024)]
    if 2026 in locations_by_year:
        pairs.append((2024, 2026))

    diffs = [
        diff_locations(locations_by_year[before_year], locations_by_year[after_year], f"{before_year}-{after_year}")
        for before_year, after_year in pairs
    ]
    changes = pd.concat(diffs, ignore_index=True)
    print(f"Total changed locations: {len(changes)}")

    geojson = to_geojson(changes, "location_changes")
    DATA_GEO.mkdir(parents=True, exist_ok=True)
    (DATA_GEO / "location_changes.geojson").write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    print("Wrote data/geo/location_changes.geojson")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_location_changes.py -v`
Expected: PASS (all 3 tests)

- [ ] **Step 5: Run the script for real**

Run: `python side_projects/locais_bus_access/location_changes.py`
Expected: prints location counts for 2022/2024, attempts 2026 (likely prints "not yet published" — this is expected, not a failure), prints total changed locations, ends with "Wrote data/geo/location_changes.geojson". Verify the file exists and open it to confirm `features[].properties.status` values are only `"appeared"`/`"disappeared"`.

- [ ] **Step 6: Commit**

```bash
git add side_projects/locais_bus_access/location_changes.py tests/test_location_changes.py data/geo/location_changes.geojson
git commit -m "feat: diff Niteroi polling locations across 2022-2024-2026"
```

---

### Task 3: Nearest-stop distance

**Files:**
- Create: `side_projects/locais_bus_access/nearest_stop.py`
- Test: `tests/test_nearest_stop.py`

**Interfaces:**
- Consumes: `config.DATA_GEO`; `data/geo/bus_stops.geojson` (Task 1's output: `properties.linhas: list[str]`, `geometry.coordinates: [lon, lat]`); `data/geo/location_changes.geojson` (Task 2's output).
- Produces:
  - `haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float`
  - `nearest_stop_for(lat: float, lon: float, stops: list[dict]) -> tuple[float | None, list[str]]` where each `stops` entry is `{"lat": float, "lon": float, "linhas": list[str]}`.
  - Rewrites `data/geo/location_changes.geojson` in place, adding `properties.nearest_stop_m: float | None` and `properties.nearest_stop_linhas: list[str]` to every feature. Task 4 consumes these two new properties.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_nearest_stop.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "side_projects" / "locais_bus_access"))
import nearest_stop as ns


def test_haversine_m_zero_for_same_point():
    assert ns.haversine_m(-22.9, -43.1, -22.9, -43.1) == 0.0


def test_haversine_m_known_short_distance():
    # ~0.0009 degrees latitude apart is roughly 100m at this latitude
    distance = ns.haversine_m(-22.9000, -43.1000, -22.9009, -43.1000)
    assert 90 < distance < 110


def test_nearest_stop_for_picks_closest_and_returns_its_lines():
    stops = [
        {"lat": -22.90, "lon": -43.10, "linhas": ["15"]},
        {"lat": -22.95, "lon": -43.20, "linhas": ["22", "26"]},
    ]
    distance, linhas = ns.nearest_stop_for(-22.9001, -43.1001, stops)
    assert linhas == ["15"]
    assert distance < 100


def test_nearest_stop_for_empty_stops_returns_none():
    distance, linhas = ns.nearest_stop_for(-22.9, -43.1, [])
    assert distance is None
    assert linhas == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_nearest_stop.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'nearest_stop'`

- [ ] **Step 3: Write `nearest_stop.py`**

```python
# side_projects/locais_bus_access/nearest_stop.py
"""Computes, for every changed polling location, the distance to its
nearest MobNit bus stop and which line(s) serve it."""

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from config import DATA_GEO  # noqa: E402

EARTH_RADIUS_M = 6371000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def nearest_stop_for(lat: float, lon: float, stops: list[dict]) -> tuple[float | None, list[str]]:
    best_distance = None
    best_linhas: list[str] = []
    for stop in stops:
        distance = haversine_m(lat, lon, stop["lat"], stop["lon"])
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_linhas = stop["linhas"]
    return best_distance, best_linhas


def main():
    stops_geojson = json.loads((DATA_GEO / "bus_stops.geojson").read_text(encoding="utf-8"))
    stops = [
        {
            "lat": f["geometry"]["coordinates"][1],
            "lon": f["geometry"]["coordinates"][0],
            "linhas": f["properties"]["linhas"],
        }
        for f in stops_geojson["features"]
    ]

    changes_path = DATA_GEO / "location_changes.geojson"
    changes_geojson = json.loads(changes_path.read_text(encoding="utf-8"))
    for feature in changes_geojson["features"]:
        lon, lat = feature["geometry"]["coordinates"]
        distance, linhas = nearest_stop_for(lat, lon, stops)
        feature["properties"]["nearest_stop_m"] = round(distance, 1) if distance is not None else None
        feature["properties"]["nearest_stop_linhas"] = linhas

    changes_path.write_text(json.dumps(changes_geojson, ensure_ascii=False), encoding="utf-8")
    print(f"Augmented {len(changes_geojson['features'])} changed locations with nearest-stop distance")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_nearest_stop.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Run the script for real**

Run: `python side_projects/locais_bus_access/nearest_stop.py`
Expected: "Augmented N changed locations with nearest-stop distance". Open `data/geo/location_changes.geojson` and confirm every feature now has `nearest_stop_m` and `nearest_stop_linhas`.

- [ ] **Step 6: Commit**

```bash
git add side_projects/locais_bus_access/nearest_stop.py tests/test_nearest_stop.py data/geo/location_changes.geojson
git commit -m "feat: compute nearest-bus-stop distance for changed polling locations"
```

---

### Task 4: Static page

**Files:**
- Create: `side_projects/locais_bus_access/build_page.py`
- Create (generated, not hand-edited): `side_projects/locais_bus_access/index.html`

**Interfaces:**
- Consumes: `config.DATA_GEO`; `data/geo/bus_routes.geojson`, `data/geo/bus_stops.geojson`, `data/geo/location_changes.geojson` (all three prior tasks' outputs).
- Produces: `build_page(bus_routes: dict, bus_stops: dict, location_changes: dict) -> str` (returns the full HTML document as a string); writes `side_projects/locais_bus_access/index.html` when run as a script.

No test for this task (spec §5 — static-page rendering is visually verified, not unit tested).

- [ ] **Step 1: Write `build_page.py`**

```python
# side_projects/locais_bus_access/build_page.py
"""Assembles the standalone locais-bus-access page: one self-contained
HTML file (Leaflet via CDN, data embedded inline, no server/build step)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from config import DATA_GEO  # noqa: E402

OUTPUT_PATH = Path(__file__).resolve().parent / "index.html"

HTML_TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Locais de Votação — Mudanças e Acesso a Ônibus</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<style>
  body { margin: 0; font-family: system-ui, sans-serif; display: flex; height: 100vh; }
  #map { flex: 2; }
  #list { flex: 1; overflow-y: auto; padding: 12px; border-left: 1px solid #ccc; }
  .item { padding: 8px; border-bottom: 1px solid #eee; }
  .appeared { border-left: 4px solid #1b7f3a; }
  .disappeared { border-left: 4px solid #b3261e; }
  h2 { margin-top: 0; }
</style>
</head>
<body>
<div id="map"></div>
<div id="list"><h2>Locais alterados</h2><div id="list-items"></div></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const DATA = __DATA_JSON__;

const map = L.map('map').setView([-22.895, -43.12], 13);
L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap &copy; CARTO'
}).addTo(map);

L.geoJSON(DATA.bus_routes, { style: { color: '#888', weight: 1.5, opacity: 0.6 } }).addTo(map);

const statusColor = { appeared: '#1b7f3a', disappeared: '#b3261e' };

L.geoJSON(DATA.location_changes, {
  pointToLayer: (feature, latlng) => L.circleMarker(latlng, {
    radius: 7,
    color: statusColor[feature.properties.status] || '#333',
    fillColor: statusColor[feature.properties.status] || '#333',
    fillOpacity: 0.8,
  }),
  onEachFeature: (feature, layer) => {
    const p = feature.properties;
    const linhas = (p.nearest_stop_linhas && p.nearest_stop_linhas.length)
      ? ` (linhas ${p.nearest_stop_linhas.join(', ')})` : '';
    const dist = p.nearest_stop_m != null ? `${p.nearest_stop_m.toFixed(0)}m` : 'n/d';
    layer.bindPopup(
      `<b>${p.nm_local}</b><br>${p.endereco}, ${p.bairro}<br>` +
      `Par: ${p.pair} (${p.status})<br>` +
      `Parada mais próxima: ${dist}${linhas}`
    );
  },
}).addTo(map);

const listItems = document.getElementById('list-items');
const sorted = [...DATA.location_changes.features].sort(
  (a, b) => (b.properties.nearest_stop_m ?? 0) - (a.properties.nearest_stop_m ?? 0)
);
for (const f of sorted) {
  const p = f.properties;
  const linhas = (p.nearest_stop_linhas && p.nearest_stop_linhas.length)
    ? ` (linhas ${p.nearest_stop_linhas.join(', ')})` : '';
  const dist = p.nearest_stop_m != null ? `${p.nearest_stop_m.toFixed(0)}m` : 'n/d';
  const div = document.createElement('div');
  div.className = `item ${p.status}`;
  div.innerHTML = `<b>${p.nm_local}</b> — ${p.pair} (${p.status})<br>` +
    `${p.endereco}, ${p.bairro}<br>Parada mais próxima: ${dist}${linhas}`;
  listItems.appendChild(div);
}
</script>
</body>
</html>
"""


def build_page(bus_routes: dict, bus_stops: dict, location_changes: dict) -> str:
    data = {"bus_routes": bus_routes, "bus_stops": bus_stops, "location_changes": location_changes}
    return HTML_TEMPLATE.replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False))


def main():
    bus_routes = json.loads((DATA_GEO / "bus_routes.geojson").read_text(encoding="utf-8"))
    bus_stops = json.loads((DATA_GEO / "bus_stops.geojson").read_text(encoding="utf-8"))
    location_changes = json.loads((DATA_GEO / "location_changes.geojson").read_text(encoding="utf-8"))

    html = build_page(bus_routes, bus_stops, location_changes)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the script**

Run: `python side_projects/locais_bus_access/build_page.py`
Expected: "Wrote .../side_projects/locais_bus_access/index.html"

- [ ] **Step 3: Manually verify the page**

Open `side_projects/locais_bus_access/index.html` directly in a browser (double-click or `file://` path — no server needed). Confirm: the map centers on Niterói with gray bus-route lines visible, colored circle markers for changed locations, clicking a marker shows a popup with address/pair/status/nearest-stop distance, and the right-hand list is populated and sorted by distance descending.

- [ ] **Step 4: Commit**

```bash
git add side_projects/locais_bus_access/build_page.py side_projects/locais_bus_access/index.html
git commit -m "feat: generate standalone map page for locais-bus-access side project"
```
