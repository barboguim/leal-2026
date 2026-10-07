New task: export all LEAL pipeline data to a structured Excel workbook. This is a data export task only — no pipeline logic changes, no new analytical computation beyond what already exists in the processed files. Read the data as-is and reshape it into xlsx.

Output file: data/exports/LEAL_dados_eleitorais.xlsx

Three tabs — one per entity:
- "Hugo Leal"
- "Felipe Peixoto"  
- "PSD"

Each tab has TWO sections side by side or stacked (your call on layout — whichever reads more clearly):

SECTION 1 — By local de votação (one row per local × year combination):
Columns: NR_LOCAL_VOTACAO, NM_LOCAL_VOTACAO, bairro, regiao, NR_ZONA, ano, tipo_eleicao (Municipal/Geral), cargo_pretendido, candidacy_status (concorreu/não concorreu/partido inexistente), QT_VOTOS, pct_share (%), delta_vs_prior_comparable (N/A if no valid same-type+cargo prior year exists — use the candidacy matrix gating already built in 06_build_vote_deltas.py, don't recompute), cargo_diferente (boolean — True if delta spans different cargos, already flagged in the pipeline), top_competitor_name, top_competitor_cargo, top_competitor_votes, total_eleitores (from voter profile), pct_mulheres, pct_jovens_16_24, pct_60_plus, pct_ensino_superior, pct_ate_fundamental.

SECTION 2 — By zona (aggregated up from local, one row per zona × year):
Columns: NR_ZONA, ano, tipo_eleicao, cargo_pretendido, candidacy_status, QT_VOTOS_total (sum across locais in this zona), pct_share_zona (candidate votes / total valid votes in zona), delta_vs_prior_comparable (N/A if not valid), num_locais_in_zona, total_eleitores_zona, pct_mulheres_zona, pct_jovens_16_24_zona, pct_60_plus_zona, pct_ensino_superior_zona, pct_ate_fundamental_zona.

Data sources to read (do not modify these files):
- data/processed/voter_profile_by_secao.csv (already aggregated to local grain in the profile integration — use app-web's aggregation logic or replicate it simply)
- The GeoJSON files in data/geo/ (already have votes + coordinates + competitor data + profile metrics per local)
- scripts/06_build_vote_deltas.py candidacy matrix (for candidacy_status and delta gating)
- scripts/07_top_competitors.py output (for top competitor per local per year)

For PSD tab: PSD is a party slate, not an individual. candidacy_status = "concorreu" for any year PSD fielded candidates in Niterói. cargo_pretendido = "AGREGADO (múltiplos cargos)". Include top_3_candidates_names and their cargos as additional columns instead of a single top_competitor.

Formatting requirements:
- Freeze the header row on each tab
- Bold headers
- Number format: votes as integers with thousand separators, percentages as X.X% (one decimal), delta as +X.X% or -X.X% or "N/A"
- Conditional formatting on delta column: red for losses, green for gains, gray for N/A
- Conditional formatting on candidacy_status: yellow highlight for "não concorreu" and "partido inexistente" rows so they're visually distinct from real data rows
- Auto-fit column widths

Write a new standalone script scripts/export_xlsx.py that reads the existing processed data and produces this file. Do not modify any existing pipeline scripts. Use openpyxl for formatting (already likely in requirements or easy to add). Run it and confirm the output file opens cleanly with correct row counts.