# leal-2026 — Hugo Leal · Niterói 2026

Standalone electoral map of **Hugo Leal** (dep. federal, PSD-RJ) in Niterói,
section-primary, across every general election cycle 2010 → 2026.

Forked from [`barboguim/mapa-eleitoral`](https://github.com/barboguim/mapa-eleitoral)
on 2026-10-07 — see [`docs/LINEAGE.md`](docs/LINEAGE.md) for the fork point and
rebase policy.

## Golden rules

Governance for this repository:

1. **Document everything.** Every data source, candidacy claim, and deploy step has a
   written trace: [`docs/LINEAGE.md`](docs/LINEAGE.md),
   [`docs/plans/2026-10-07-hugo-leal-only-fork.md`](docs/plans/2026-10-07-hugo-leal-only-fork.md),
   and the per-deploy entries in `docs/CHANGELOG.md` (added on first push).
2. **Never guess, always check.** Hugo's 2026 cargo and party number were
   verified against TSE `consulta_cand_2026` before being written to `config.py`.
   Script `08_candidacy_matrix.py` re-verifies on every run and prints `[WARN]`
   on disagreement — the TSE registry is authoritative over the config.

## Hugo Leal — verified election history

| Year | Office           | Party | Number | Niterói votes |
|------|------------------|-------|--------|---------------|
| 2010 | Dep. Federal     | PSC   | 2055   | (historic data copied from fork) |
| 2014 | Dep. Federal     | PROS  | 2055   | (historic data copied from fork) |
| 2016 | Vice-Prefeito    | PSB   | 40     | — (vice slate, no personal count) |
| 2018 | Dep. Federal     | PSD   | 5555   | (historic data copied from fork) |
| 2022 | Dep. Federal     | PSD   | 5555   | 964 |
| **2026** | **Dep. Federal** | **PSD** | **5510** | **1,902** (1R) |

Numbers come straight from TSE `votacao_secao_<year>_RJ.csv`, filtered to Niterói.
The 2026 row was pulled 2026-10-07 from
`votacao_secao_2026_RJ.zip` (last-modified 2026-10-06 19:32 UTC).

## Data pipeline

```
01 → 02 → 03 → 04 → 05 → 05b → 08 → 09 → 06 → 07
```

Step 05b is new in this fork — it rebuilds `hugo_leal_secao.geojson` from the
processed by-seção CSV so the seção layer stays current as new years are added.
The source repo built that file once by hand; the new script makes the rebuild
repeatable.

Incremental refresh when a new cycle lands:

```powershell
# 1. Pull the raw TSE files for the new year
python scripts/01_download_tse.py

# 2. Add the new year to Hugo's processed CSV (memory-safe, incremental)
python scripts/02_process_votes.py --year 2026

# 3. Rebuild geojson + section layer + candidacy matrix
python scripts/05_build_geojson.py
python scripts/05b_rebuild_hugo_secao_geojson.py
python scripts/08_candidacy_matrix.py

# 4. Deltas + competitors (optional, enriches the UI)
python scripts/06_build_vote_deltas.py
python scripts/07_top_competitors.py

# 5. Sync the data bundle into the web app
cd app-web; npm run prebuild
```

## Web app

React 19 + Vite 7 + react-leaflet 5, in `app-web/`.

```powershell
cd app-web
npm install
npm run dev      # local dev server
npm run build    # production build to app-web/dist
```

Vercel is configured via repo-root `vercel.json`:
- Install: `cd app-web && npm install`
- Build:   `cd app-web && npm run build`
- Output:  `app-web/dist`

See `docs/DEPLOYMENT.md` for the deployment runbook (added on first push).

## Data sources

- **TSE Dados Abertos** — https://dadosabertos.tse.jus.br/
  - `votacao_secao_<year>_RJ.zip` — votes by seção
  - `consulta_cand_<year>.zip` — candidate registrations
  - `perfil_eleitor_secao_<year>_RJ.zip` — voter demographics.
    **Note:** TSE had not yet published the 2026 variant at fork time;
    the app surfaces 2024 demographics with a caveat until 2026 appears.
- **Niterói ArcGIS server** — bairro and polling-location geographies.

## Tech stack

- Python 3.11+ (pandas, geopandas, requests)
- React 19 + Vite 7 + react-leaflet 5
- Vercel for deployment
