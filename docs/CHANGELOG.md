# Changelog — leal-2026

Every production deploy and material change is recorded here. See
`docs/DEPLOYMENT.md` for the deploy runbook.

## [Unreleased]

### Added
- Repository forked from `barboguim/mapa-eleitoral@25d1be3` on 2026-10-07.
  Fork point + policy in `docs/LINEAGE.md`.
- 2026 TSE data integrated:
  - `votacao_secao_2026_RJ.zip` (288 MB, mod 2026-10-06 19:32 UTC) — fetched 2026-10-07
  - `consulta_cand_2026.zip` (3 MB, mod 2026-10-07 19:35 UTC) — fetched 2026-10-07
  - `perfil_eleitor_secao_2026_RJ.zip` — **not yet published by TSE at fork time (HTTP 404)**;
    app surfaces 2024 demographics in the interim.
- `config.HUGO_LEAL.elections[2026] = {cargo: DEPUTADO FEDERAL, partido: PSD, nr: 5510}`,
  verified against `consulta_cand_2026`.
- `scripts/02_process_votes.py --year <N>`: new incremental mode. Memory-safe
  per-year processing with idempotent CSV merge.
- `scripts/05b_rebuild_hugo_secao_geojson.py`: new. Rebuilds `hugo_leal_secao.geojson`
  from the by-seção CSV. The source repo built this file once by hand; the new
  script makes the rebuild part of the pipeline.
- Niterói 2026 numbers measured directly from TSE CSVs:
  - Hugo Leal: 1,902 votos / 892 seções (1R only). Compare to 964 / 607 in 2022 — doubled.
- Documentation: `docs/LINEAGE.md`, `docs/plans/2026-10-07-hugo-leal-only-fork.md`,
  `docs/DEPLOYMENT.md` (this file).

### Changed
- `app-web/index.html` title → `Hugo Leal · Niterói 2026`.
- `app-web/package.json` name → `leal-2026-web`.
- `README.md` rewritten for the new product.
- Full UI redesign pass (matches mobi-pleito-2026 sibling site):
  - Header: `h1 Mapa eleitoral` + `subtitle Hugo Leal`.
  - Sidebar: two independent `<details class="group">` layers — **Ano a ano**
    (year selector) and **Comparativo** (pair chips + inline Resumo), each
    with an eye-icon visibility toggle. Standalone Resumo panel removed.
  - Intensity legend at the bottom of the sidebar; 5 classes with lower/upper
    bound percentages per class.
- Map rendering:
  - Esri `World_Light_Gray_Base` basemap (Carto's cdn now requires an API key).
  - Hugo marker fill = ColorBrewer YlOrRd heat palette, 5 classes.
    Breaks are quintiles over the selected year's share distribution.
  - Markers are fixed size (6 px). The color carries the signal.
- Pipeline bundle:
  - `scripts/05_build_geojson.py` now uses `APP_GEOJSON_LAYERS` for its
    `data.js` rebuild, so re-running 05 no longer silently drops
    `vote_deltas` and `voter_profile` from the bundle.
- `.gitignore` extended for `node_modules/`, `app-web/dist/`, `.vercel/`,
  `.env*`, `eleitorado_local_votacao_*.zip`, and the local tooling dirs.

### Pipeline enrichment (post-fork runs)
- `scripts/06_build_vote_deltas.py`: new pair **2022-2026** (75 locais with
  Hugo gated-non-null). Comparativo now defaults to this pair.
- `scripts/07_top_competitors.py`: `top1/2/3_*` + `total_votos_validos`
  merged onto `hugo_leal.geojson`. Popup's Concorrência section populates;
  the `% dos votos válidos` row appears.
- `scripts/09_voter_profile_geojson.py`: 11 demographic share fields
  (`pct_mulheres`/`homens`/`genero_nao_informado`, `pct_jovens_16_24`/
  `adultos_25_59`/`60_mais`/`idade_nao_informado`, `pct_ate_fundamental`/
  `ensino_medio`/`ensino_superior`/`escolaridade_nao_informado`) +
  `total_eleitores` merged onto `hugo_leal.geojson`. Popup's Perfil
  section populates. Data is from 2024 (TSE's 2026 perfil file is still
  not published; re-run 09 when it lands).

### Deferred to a follow-up
- Deep strip of Felipe + PSD code paths in Python scripts and the remaining
  React components. The UI no longer displays either, but their modules
  still ship with the bundle. Low priority.
- Seção-primary rendering in the UI. `hugo_leal_secao.geojson` covers
  2010 → 2026 and is pipelined; wiring the UI to render it as the default
  layer is a follow-up.

## Deployments

Record every production deploy here. Format: `YYYY-MM-DD HH:MM UTC — <sha> — <summary> — <vercel-url>`.

<!-- First deploy entry will go here on initial Vercel release. -->
