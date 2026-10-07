# Deployment runbook — leal-2026

Target: Vercel. Hosting pattern mirrors `locais-bus-access` and
`mobi-pleito-2026` (per the owner's memory). Keep this file and
`docs/CHANGELOG.md` current on every production deploy.

## Hosts

| Thing | Value |
|---|---|
| GitHub repo | `barboguim/leal-2026` (public) |
| Default branch | `main` |
| Vercel project | `leal-2026` (production domain: `leal-2026.vercel.app`, final name confirmed at first deploy) |
| Vercel build | `vercel.json` at repo root — `install: cd app-web && npm install`, `build: cd app-web && npm run build`, `output: app-web/dist` |

## First-time setup

Run from `D:/leal-2026/`:

```powershell
# 1. Create the GitHub repo
gh repo create barboguim/leal-2026 --public --source=. --remote=origin --push

# 2. Connect Vercel to the repo via the Vercel dashboard
#    (CLI alternative: `npx vercel link` then `npx vercel --prod`)
#    Framework preset: Other
#    Install Command: inherited from vercel.json
#    Build Command: inherited from vercel.json
#    Output Directory: inherited from vercel.json

# 3. Record the production domain in this file (table above) and in
#    docs/CHANGELOG.md.
```

## Routine deploy

```powershell
# From a clean working tree with the pipeline refreshed and the web app built
git status                             # nothing uncommitted
cd app-web; npm run build; cd ..       # confirms vite build is green
git push origin main                   # Vercel builds and deploys automatically
```

Deploy is live within ~2 minutes of the push. Record the result in
`docs/CHANGELOG.md` (commit sha, Vercel URL of the deployment, summary).

## Rollback

```powershell
# Fast path: redeploy a prior Vercel build from the dashboard
# (Project → Deployments → three-dot menu on a green build → Promote).

# Code-level revert
git revert <bad-sha>
git push origin main
```

The Vercel dashboard rollback is always safer when the bad build was data-only
(no code change the next release depends on). Prefer it.

## Promotion gates

Before pushing to `main`:

1. **Pipeline freshness.** `data/raw/<cycle>/.FETCHED_AT` must be present
   and recent enough that TSE wouldn't have changed numbers since. Re-run
   `scripts/02_process_votes.py --year <cycle>` if in doubt — it is
   idempotent per-year.
2. **Hugo totals sanity.** Hugo's Niterói total votes for every cycle must
   match TSE's own portal number. The current baseline is:
   - 2022: 964
   - 2026: 1,902 (1R only until 2R is apportioned by TSE)
3. **`npm run build` green locally.** vite build must succeed. If it emits
   warnings, read them.
4. **Golden rules check.** Any new candidacy claim must be sourced from
   `consulta_cand_<year>` and cross-checked by `scripts/08_candidacy_matrix.py`
   (which prints `[WARN]` on disagreement). Nothing hardcoded from memory.
