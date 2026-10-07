# Lineage — leal-2026

This repository is a derivative of [`barboguim/mapa-eleitoral`](https://github.com/barboguim/mapa-eleitoral)
("the source repo"), stripped to a single-candidate focus and extended with the 2026 Brazilian general election.

## Fork point

| Field | Value |
|---|---|
| Source repo | `barboguim/mapa-eleitoral` |
| Source branch | `delta-control-collapse` |
| Source commit | `25d1be391d74d4c586b24a165185d35043bac4eb` |
| Fork date | 2026-10-07 |
| Fork method | Working-tree copy via `robocopy` (excluded `.git`, `.claude`, `node_modules`, `__pycache__`, `dist`), then fresh `git init`. The working tree at fork time included 15 uncommitted files on top of the source commit; they are considered part of this product's baseline. |

A clean HEAD-only fork would have missed the 2026 voter-profile zip and the design drafts
the user had in flight; those are now part of this product's baseline, documented in the
first commit's message.

## What was removed vs. source repo

The source repo tracks three subjects — Hugo Leal, Felipe Peixoto, and PSD party-wide — across
general and municipal elections 2010–2024. This fork keeps only Hugo Leal, general elections.

Removals follow the plan at `docs/plans/2026-10-07-hugo-leal-only-fork.md`:

- `config.FELIPE_PEIXOTO`, `config.PARTY`, `config.PARTY_NUMBERS`, `config.PSD_FOUNDING_YEAR`
- `MUNICIPAL_YEARS` references in the download pipeline (municipal cycles were kept in config for the
  historical candidacy matrix, but no vote data is pulled for them)
- All Felipe/PSD code paths in `scripts/02_process_votes.py` through `scripts/09_voter_profile_geojson.py`
- Data outputs: `felipe_peixoto*.geojson`, `psd*.geojson`, `felipe_peixoto_by_secao.csv`, `psd_by_secao.csv`
- UI: candidate switcher, PSD slate panel

## What was added vs. source repo

- 2026 TSE download target in `scripts/01_download_tse.py` (`votacao_secao_2026_RJ.zip`, `consulta_cand_2026.zip`).
  Perfil eleitorado 2026 is **not yet published by TSE** at fork time — the most recent available (2024)
  is used, and the UI surfaces a caveat.
- `config.HUGO_LEAL.elections[2026]` — cargo/partido verified against `consulta_cand_2026` before being set.
  No value is hardcoded from memory. If `consulta_cand` disagrees with any entry in this dict for any
  year, `scripts/08_candidacy_matrix.py` prints a `[WARN]`; the matrix is authoritative.
- `docs/LINEAGE.md` (this file).

## Rebase-with-upstream policy

The source repo continues to evolve. Shared improvements (pipeline bugfixes, UI primitives, demographic
logic) are brought over by **manual cherry-pick**, not by git merge. Every cherry-pick is recorded in
`docs/CHANGELOG.md` with the source commit sha so provenance stays intact.

## Verification snapshot

TSE CDN probe at fork time (2026-10-07):

| Dataset | Status | Last-Modified |
|---|---|---|
| `votacao_secao_2026_RJ.zip` | 200 OK | 2026-10-06 19:32 UTC |
| `consulta_cand_2026.zip` | 200 OK | 2026-10-07 19:35 UTC |
| `detalhe_votacao_secao_2026.zip` | 200 OK | 2026-10-06 17:18 UTC |
| `perfil_eleitor_secao_2026_RJ.zip` | 404 Not Found | — |

Snapshot date is recorded in `data/raw/.FETCHED_AT` after each download so staleness is detectable.
