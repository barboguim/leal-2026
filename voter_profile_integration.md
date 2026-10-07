# Voter Profile Integration — Spec Request

**Brainstorm via Superpowers first. Do NOT start coding.** Write the spec, confirm scope, then implement with the usual discipline (isolated worktree, tests, review).

This is a **drop-in**, not a data cycle. The profile data is already processed and sitting at `data/processed/voter_profile_by_secao.csv` (10,083 rows, all 8 election years, grain = `ano` + `NR_ZONA` + `NR_SECAO`). It is fully orphaned — nothing downstream reads it today. See `docs/voter_profile_backbone.md` for the full investigation report. There is no half-wired merge code to work around; it's a clean gap.

## Goal

Fill the reserved **"Perfil do eleitorado"** placeholder slot in the CAMADAS section with a working demographic context overlay, so campaign staff can read a candidate's vote share **against** the electorate composition at each location.

## Approach — Option A (aggregate to local de votação grain)

- Aggregate the seção-level profile data **up to local de votação grain**, using the same `nr_local` lookup that `05_build_geojson.py` already builds from `locais_votacao_niteroi.csv`. This matches the grain the map already renders — **no frontend granularity change**.
- Join on `(ano, NR_ZONA, NR_SECAO)`. Column names and types are identical on both sides — direct merge, no transformation.
- Profile data is **turno-invariant** (the electorate's demographic composition doesn't change between rounds), so ignore `NR_TURNO` on the vote side when joining.
- Surface demographics per map marker: **gender, age bands, education, race** — as both raw counts AND as **% of `total_eleitores`** at that local.

## Data cleanup (required before user-facing)

- Merge `fai__invalido` + `fai__invalida` into a single bucket — these are a TSE label-agreement inconsistency across years, not two real categories.
- Fix or exclude the `rac__#ne` column — an unnormalized raw code, not a real race/color category.

## Frontend behavior — profiles are a CONTEXT OVERLAY, not a delta

- Fills the **"Perfil do eleitorado"** placeholder toggle reserved in CAMADAS.
- It's a **switchable overlay** that tints/annotates markers by a chosen demographic dimension (gender / age / education / race), while vote data stays visible. It is **NOT** a gains/losses computation.
- Analytical goal: let the user read a candidate's **vote share against the local's demographic profile** — to spot locais where a candidate under- or over-performs relative to a demographic that "should" favor them.

## FRAMING DISCIPLINE (non-negotiable — build this in from day one)

The Brazilian vote is secret. TSE never links an individual voter's demographics to their vote choice. The tool must therefore **never** imply individual voter tracing.

- ✅ Correct framing: **"% de votos vs. perfil do eleitorado"** — correlating vote outcome with electorate composition at the same location.
- ❌ Forbidden framing: "perfil dos eleitores do candidato" / "quem votou no candidato" — this is factually impossible and would mislead a campaign.
- This is **ecological inference**: suggestive at the aggregate level across many locais, never proof at the individual level (ecological fallacy). A locale being 60% women where Hugo gets 60% does NOT mean women voted for Hugo.
- All UI labels, popups, and legends must use the vote-share-vs-composition framing. No label anywhere may attribute a demographic to a candidate's actual voters.

## Architectural constraints

- Stay in **React + react-leaflet + Tailwind**. No new frameworks, no map-engine swap. (Protects the migration already paid for.)
- Reuse the existing `05` `nr_local` lookup — do NOT rebuild geocoding.
- Keep the candidacy-matrix gating and delta logic exactly as built; this task does not touch vote/delta computation.

## Out of scope (this task)

- Seção-level map rendering — keep local de votação grain.
- The extra TSE fields not currently extracted by `04` (`DS_IDENTIDADE_GENERO`, `DS_QUILOMBOLA`, `DS_INTERPRETE_LIBRAS`, biometric/disability/social-name counts) — documented future layer; pulling them in means re-running the 8-file extraction, which is the big cycle we're avoiding.
- Visual restyling — that's the separate `ui-ux-pro-max` pass that comes after this.

## FUTURE LAYER (do not build now, but don't architect in a way that blocks it)

**"Zonas com potencial"** — a lookalike-targeting model. Once profiles are joined to vote data, a later task will:

1. Profile the demographic fingerprint of locais where a candidate **overperforms**.
2. Find locais with the **same fingerprint** where the candidate **underperforms**.
3. Surface those as ranked **"potential" targets** — demographically they resemble strongholds but the candidate is weak there, suggesting a **fixable gap** (no ground game, local rival) rather than genuine demographic disadvantage.

Framing discipline applies here too: present as **ranked leads to investigate, NOT statistical certainty** (coarse demographic dimensions, ecological inference — suggestive at aggregate, never individual proof). Reserve UI/data room for a per-candidate "similarity score" and a ranked results panel; **do not build the computation yet.**