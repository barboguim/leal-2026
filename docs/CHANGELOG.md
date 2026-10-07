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
- `app-web/src/lib/constants.js` — `BASE_KEYS` narrowed to `['hugo_leal']`.
- `app-web/src/App.jsx` — `LAYER_ORDER`, `TOGGLE_ID_BY_LAYER_KEY`, `CANDIDATE_ROWS`
  all narrowed to Hugo-only.
- `.gitignore` extended for `node_modules/`, `app-web/dist/`, `.vercel/`,
  `.env*`, `eleitorado_local_votacao_*.zip`, and the local tooling dirs.

### Deferred to a follow-up
- Script 06 (vote deltas) + script 07 (top competitors) — not critical for first
  deploy; the Hugo layer renders without them.
- Script 09 (voter profile geojson) — needs TSE's 2026 perfil file (not yet published).
  The 2024 profile is still bundled.
- Deep strip of Felipe + PSD code paths in Python scripts and the remaining React
  components (`PsdBreakdownSection`, Felipe-specific competitor fields). The UI
  no longer displays either, but the modules are still shipped. Low priority.
- Seção-primary rendering in the UI. The seção-grain geojson exists
  (`hugo_leal_secao.geojson` covers 2010 → 2026); wiring the UI to render it as
  the default layer is a follow-up.

## Deployments

Record every production deploy here. Format: `YYYY-MM-DD HH:MM UTC — <sha> — <summary> — <vercel-url>`.

<!-- First deploy entry will go here on initial Vercel release. -->
