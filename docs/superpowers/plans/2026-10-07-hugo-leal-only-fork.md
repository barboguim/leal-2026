# Plan — Hugo Leal–only fork of mapa-eleitoral (new product, 2026 focus)

**Author:** Guilherme Barbosa (with Claude Opus 4.7)
**Date:** 2026-10-07
**Status:** Draft, pending user approval of repo name + launch

## 0. Golden rules governing this plan

1. **Document everything.** Every architectural choice, data source, candidacy claim, and deployment step has a written trace. No undocumented magic.
2. **Never guess, always check.** Candidacies cross-referenced against TSE `consulta_cand`. 2026 vote totals cross-referenced against TSE's own portal summary. Nothing hardcoded from memory.
3. **Preserve lineage.** The new repo documents the exact commit of `mapa-eleitoral` it was forked from, so any future question "where did this logic come from?" has a one-click answer.

## 1. Scope

**Product one-liner:** A standalone map of Hugo Leal's electoral performance in Niterói, seção-primary, across 2010 → 2026 Geral cycles.

**In scope**
- Hugo Leal votes at seção and local-de-votação grain (2010, 2014, 2018, 2022, **2026**).
- Top-3 competing candidates per local/year (same cargo).
- Voter demographic overlay per seção (gender, age, education).
- Vote deltas between consecutive Geral cycles.
- Candidacy matrix (TSE-authoritative) proving Hugo ran each listed year.

**Out of scope (deliberately dropped from source repo)**
- Felipe Peixoto — belongs to a different product.
- PSD party-wide — belongs to a different product.
- Municipal elections (2012, 2016, 2020, 2024) — Hugo doesn't run municipal; the data adds noise without signal. Can be re-added later if a specific use case appears.

## 2. Repo architecture

| | Choice | Why |
|---|---|---|
| GitHub repo | **New: `barboguim/mapa-hugo-leal`** (name pending user confirm) | User said "new product → github page and all" |
| Local path | `D:/mapa-hugo-leal/` (sibling of `D:/LEAL`) | User said "dedicated worktree"; separate GitHub repo makes a git worktree inappropriate; sibling dir is the equivalent intent |
| Vercel | New Vercel project pointing at `app-web/` | Fresh deployment URL (proposed: `mapa-hugo-leal.vercel.app`) |
| Source lineage | Copy of `D:/LEAL` at commit `<pin-at-fork-time>`, re-initialized git | Preserves working code; records exact ancestor commit in `docs/LINEAGE.md` |

**Lineage record** — `docs/LINEAGE.md` in the new repo will record:
- Source: `barboguim/mapa-eleitoral`
- Fork commit: `<sha>` on branch `<branch>` at `<timestamp>`
- Files intentionally removed vs source
- Files intentionally added vs source
- Rebase-with-upstream policy (manual cherry-pick for shared pipeline fixes)

## 3. Spatial grain

**Default UI layer:** `hugo_leal_secao.geojson`.

Niterói seções have no official polygons published by TSE/TRE-RJ, so section-grain visualization uses **point markers at the host local's coordinate**, one per seção, rendered with:
- Color = Hugo's vote share at that seção
- Size = total Hugo votes at that seção
- Deterministic small-radius offset per seção index within the local, so overlapping markers at the same local are visually resolvable (`ponytail: deterministic jitter, cluster-expand on zoom if it bites`)
- Hover tooltip: `Seção NNNN — Local <name> — Hugo: X votos (Y%)`

**Zoom-out fallback:** Below zoom level 14, cluster seção markers up to local-de-votação grain (`hugo_leal.geojson`) to avoid dot soup. This happens visually; the data layer is still seção-primary.

## 4. Pipeline deltas vs source repo

Source scripts (01–09) stay. Deltas:

| Script | Change |
|---|---|
| `01_download_tse.py` | Add `2026` to `FEDERAL_YEARS`. Drop municipal downloads (narrower scope). Confirmed TSE CDN has `votacao_secao_2026_RJ.zip` (288 MB, mod 2026-10-06) and `consulta_cand_2026.zip` (mod 2026-10-07). Perfil eleitorado 2026 is NOT yet published; keep most recent snapshot (2024). |
| `02_process_votes.py` | Delete Felipe / PSD branches. Only emit `hugo_leal_by_secao.csv`. |
| `03_geocode_locais.py` | Unchanged (universal). |
| `04_voter_profile.py` | Unchanged. |
| `05_build_geojson.py` | Only emit `hugo_leal.geojson` + `hugo_leal_secao.geojson`. |
| `06_build_vote_deltas.py` | Hugo-only; drops `candidacy_status_felipe` / `_psd`. |
| `07_top_competitors.py` | Unchanged logic (already excludes Hugo); only merges onto `hugo_leal.geojson`. |
| `08_candidacy_matrix.py` | Keep (matrix stays Hugo-authoritative). Drop PSD slate breakdown. |
| `09_voter_profile_geojson.py` | Only merge onto `hugo_leal.geojson`/`_secao.geojson`. |

`config.py` → delete `FELIPE_PEIXOTO`, `PARTY`, `PARTY_NUMBERS`, `PSD_FOUNDING_YEAR`. Add `2026` to `FEDERAL_YEARS` and extend `HUGO_LEAL.elections` with the 2026 entry (to be filled from `consulta_cand_2026` — not hardcoded from memory).

## 5. UI deltas vs source repo

- Remove candidate switcher (only Hugo now).
- Remove PSD slate panel.
- Default layer = seção.
- Keep: delta visualization, Zonas com Potencial, voter profile overlay, top-competitor popups.
- Rename app title and all branding.

## 6. 2026-specific risks

1. **`DEPUTADO FEDERAL` only** — if Hugo ran a different cargo in 2026 (e.g. senador), `02_process_votes.py` filter breaks silently. Mitigation: read `consulta_cand_2026` *first*, verify cargo, then update `config.HUGO_LEAL.elections[2026]`. Fail loud if `consulta_cand` says one cargo and config says another.
2. **TSE still updating CSVs** — election was 2026-10-04, data was last-modified 2026-10-06/07. Numbers may still shift. Snapshot date into `data/raw/.FETCHED_AT` so we can detect staleness.
3. **PSD membership in 2026** — not asserted; sourced from `consulta_cand`.
4. **Perfil eleitorado 2026 not yet published** — use most recent available (2024) and surface a caveat in the UI.

## 7. Deployment

Mirror the `locais-bus-access` / `nitbike` precedent (per memory):
- `docs/DEPLOYMENT.md` — Vercel project ID, GitHub repo, deploy branch, rollback command.
- `docs/CHANGELOG.md` — every production deploy logged with commit sha and summary.
- Vercel build command: `cd app-web && npm install && npm run build`; output: `app-web/dist`.

## 8. Milestones

1. Plan approved by user + repo name confirmed.
2. `D:/mapa-hugo-leal/` created, source copied, git re-initialized.
3. Felipe/PSD stripped; `pytest` green.
4. `consulta_cand_2026` downloaded; Hugo's 2026 cargo/partido verified; `config.HUGO_LEAL.elections[2026]` populated.
5. Full pipeline re-run through script 09; 2026 totals cross-checked against TSE portal.
6. UI switched to seção-primary.
7. GitHub repo created, pushed. Vercel project connected. First production deploy. `docs/DEPLOYMENT.md` + `docs/CHANGELOG.md` written.
8. Smoke-test the live URL. Share with user.

## 9. Open decisions (surfaced to user)

- **Repo name.** Proposing `mapa-hugo-leal`. Alternatives: `hugo-leal-2026`, `mapa-hugo`, `leal-2026`.
- **Keep historical cycles (2010–2022) or 2026-only?** Plan assumes keep (continuity story is valuable); say so if you want 2026-only.
- **Public or private repo?** Defaulting to public to match `mapa-eleitoral`; say so if private.
