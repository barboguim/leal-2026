# Locais de Votação — Mudanças e Acesso a Ônibus — Design Spec

## Context

Two questions, previously unrelated, turn out to be one side project:

1. Which polling locations (locais de votação) appeared or disappeared between
   consecutive elections — 2022 → 2024 → 2026 — independent of who won or how
   many votes were cast there. This is a *location* diagnostic, not a vote
   diagnostic; it is distinct from the existing `DeltaLayer` in `app-web`,
   which compares vote counts at locations that exist in both years being
   compared.
2. Whether those changed locations have bus access, using Niterói's public
   itinerary data (MobNit, `https://mobnit.niteroi.rj.gov.br`) — all bus
   lines, not just one.

This is explicitly **not** a feature of the main `app-web` React map — it does
not touch `DESIGN.md`'s Phase B contract, the candidate/delta/profile layers,
or any of their tests. It is a standalone side project that reuses this
repo's existing pipeline conventions and data.

## Scope

**In scope:**
- A new `side_projects/locais_bus_access/` folder: three Python pipeline
  scripts (bus ingestion, location diff, nearest-stop) plus a static HTML
  page generator.
- Fetching and caching all ~56 MobNit bus lines' route geometry and stops.
- Diffing Niterói's TSE `locais_votacao` datasets across 2022→2024 and
  2024→2026 (2026 fetched best-effort; TSE may not have published it yet).
- Nearest-stop distance + serving line(s) for every appeared/disappeared
  location.
- One static, self-contained HTML page (Leaflet via CDN, embedded JSON,
  no server, no build step) rendering routes, stops, and changed locations.
- One pytest file covering the diff logic.

**Out of scope:**
- Any change to `app-web`, `DESIGN.md`, or the numbered `scripts/01`–`10`
  pipeline.
- Winning-candidate or vote-share analysis of any kind — locations only.
- Real-time schedule display (`horarios`/`dias` from MobNit) — only route
  geometry and stop locations are needed for "does a bus reach here."
- Tracking a location that kept its `NR_LOCAL_VOTACAO` but moved address
  (TSE's `NR_LOCAL_VOTACAO_ORIGINAL` hints at this but modeling it is a
  separate, harder problem) — a location counts as appeared/disappeared
  purely by `NR_LOCAL_VOTACAO` presence/absence between the two years.

## §1 Bus route ingestion (`side_projects/locais_bus_access/fetch_bus_routes.py`)

MobNit's frontend (`mobnit.niteroi.rj.gov.br/itinerarios?linha=<N>`) calls a
public JSON API directly — confirmed via live network inspection, no auth,
no CORS-blocking observed from a plain `fetch`:

- `GET /api/website/v1/conteudo/dados/area-publica/itinerarios/linhas?from=<ms>&to=<ms>`
  → `[{numeroLinha, nomeLinha}, ...]`, all lines (56 unique `numeroLinha`
  values as of this writing; a couple of duplicate rows with the same
  `numeroLinha` observed — dedupe on `numeroLinha`).
- `GET /api/website/v1/conteudo/dados/area-publica/itinerarios/detalhes-linha?from=<ms>&to=<ms>&numeroLinha='<N>'`
  → array of shapes: `{sentido: "Ida"|"Volta", shapeId, coordenadas: [[lng,lat],...], dias, horarios}`.
  Keep `sentido`, `shapeId`, `coordenadas`; drop `dias`/`horarios` (out of
  scope, and bulky — this is most of each response's size).
- `GET /api/website/v1/conteudo/dados/area-publica/itinerarios/paradas?from=<ms>&to=<ms>&numeroLinha='<N>'&shapeId='<shapeId>'`
  → `[{latitude, longitude, parada: "<address string>"}, ...]`, one call per
  shape.

`from`/`to` are epoch-ms and appear to be the current month's boundaries
(observed values matched "now" when captured) — compute them as the first
and last moment of the current month at fetch time rather than hardcoding,
so the script doesn't silently start failing months from now.

**Process:** fetch `linhas` once; for each unique `numeroLinha`, fetch
`detalhes-linha`, then `paradas` for each returned `shapeId`. Cache every raw
JSON response under `data/raw/mobnit/<numeroLinha>/` (one file per endpoint
call) so a re-run skips already-fetched lines — this is public
infrastructure data, not ours to hammer repeatedly. A small delay
(e.g. 200ms) between requests. Roughly 56 + 112 + 112 ≈ 280 requests total
on a cold run.

**Output:**
- `data/geo/bus_routes.geojson` — one `LineString` feature per
  `(numeroLinha, shapeId)`, properties `{numeroLinha, nomeLinha, sentido, shapeId}`.
- `data/geo/bus_stops.geojson` — one `Point` feature per unique stop
  (dedupe by rounding lat/lon to 5 decimals, ~1m), properties
  `{endereco, linhas: [numeroLinha, ...]}` listing every line serving that
  physical stop.

## §2 Location-change diff (`side_projects/locais_bus_access/location_changes.py`)

**Source:** `data/raw/locais_votacao_<year>/eleitorado_local_votacao_<year>.csv`
— already present for 2016/2022/2024. This dataset carries
`NR_LATITUDE`/`NR_LONGITUDE` directly (no geocoding step needed, unlike the
vote-results pipeline). Read via the existing
`_pipeline_utils.read_tse_csv_safe` (handles TSE's semicolon-delimited,
latin1-with-mojibake CSVs, the same helper `02`–`04` already use).

For 2026: attempt `download_and_extract(url_locais_votacao(2026), ...)`
(both already defined in `config.py`). If the file isn't published yet
(request fails or 403s), log a clear warning and proceed with whatever years
succeeded — this must not be a hard failure, since the 2026 general election
is still months out at the time this is being built.

**Filter:** `NM_MUNICIPIO` normalized-equals `MUNICIPIO` from `config.py`
(`normalize()` from `_pipeline_utils`, same convention as every other
script).

**Diff, per consecutive pair (2022→2024, 2024→2026 if available):**
- *Appeared*: `NR_LOCAL_VOTACAO` present in the later year, absent in the
  earlier year.
- *Disappeared*: present in the earlier year, absent in the later year.
- Each output row: `nr_local, nm_local, endereco, bairro, lat, lon, pair, status ("appeared"|"disappeared")`.

**Output:** `data/geo/location_changes.geojson` — Point features, one per
changed location per pair (a location that disappeared after 2022→2024 and
reappeared by 2026 would legitimately get two rows, one per pair — this is
correct, not a dedup bug).

## §3 Nearest-stop distance (`side_projects/locais_bus_access/nearest_stop.py`)

For each feature in `location_changes.geojson`, compute haversine distance
(plain function — a dozen lines of `math`, no new geo dependency justified
for one calculation) to every point in `bus_stops.geojson`, keep the closest
stop's distance in meters and its `linhas` list.

**Output:** adds `nearest_stop_m` and `nearest_stop_linhas` properties
directly onto `location_changes.geojson`'s features (single output file,
no separate join needed downstream).

## §4 Static page (`side_projects/locais_bus_access/build_page.py` → `index.html`)

Generates one self-contained HTML file: Leaflet loaded from a CDN
(matching `design-mockups.html`'s existing pattern of a zero-build static
page in this repo), with `bus_routes.geojson`, `bus_stops.geojson`, and
`location_changes.geojson` embedded inline as a `<script>` JSON blob (same
technique `app-web`'s `data.js` uses — no fetch, no CORS concerns, opens
straight from the filesystem).

**Rendering:**
- Bus routes: thin gray polylines, one per shape (both directions per line
  visually indistinguishable is fine — this is a coverage backdrop, not a
  route-planner).
- Changed locations: circle markers, color by `status`
  (appeared vs. disappeared), popup shows name/address/bairro/pair/
  nearest-stop distance/serving line(s).
- A plain HTML list alongside the map (grouped by pair, then status) for
  scanning without clicking every marker — sorted by `nearest_stop_m`
  descending, so the worst-served new locations surface first.

## §5 Testing

`tests/test_location_changes.py` (pytest, matching existing style): small
synthetic two-year fixture asserting appeared/disappeared sets are computed
correctly, including the case where a location exists in both years (no
false positive) and a location absent from both (correctly ignored, not
listed as "disappeared" from a year it was never in).

No test for the MobNit fetch (network-dependent, would need a fixture of a
live external API — not worth the maintenance burden for a one-time/rarely
re-run ingestion script) or the static page rendering (visually verified by
opening it, same as `design-mockups.html`).

## §6 Open items carried into implementation, not blocking design approval

- Exact 2026 TSE publication status is unknown as of this writing; the
  pipeline is designed to degrade gracefully (§2) rather than assume either
  outcome.
