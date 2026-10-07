"""Export LEAL's processed electoral data (votes, deltas, competitors, voter-profile
shares) to a formatted Excel workbook: one tab per entity (Hugo Leal, Felipe Peixoto,
PSD), each tab stacking a by-local section on top of a by-zona section.

Pure export: reads existing processed/geo files as-is and reshapes them into xlsx.
No pipeline file is modified, and nothing is recomputed that the pipeline hasn't
already computed — with three documented exceptions where a requested value simply
doesn't exist anywhere in processed output, and re-deriving it from raw TSE files
would be new analytical computation the request explicitly ruled out:

- `regiao`: Niterói's administrative "região" boundaries are fetched live from the
  city's own ArcGIS service by the frontend (app-web/src/lib/useBoundaries.js) and
  joined by point-in-polygon in the browser. There is no offline processed source
  for this anywhere in the repo. Left blank.
- `pct_share` on PSD rows, and `pct_share_zona` on every tab: PSD's QT_VOTOS is a
  slate total across multiple cargos with no single "valid votes" denominator in
  processed output (psd_total_por_cargo sums to less than QT_VOTOS -- voto de
  legenda isn't attributable to a cargo). At zona grain, no candidate has a valid-
  votes total anywhere: the existing total_votos_validos field is local-grain only,
  and can't be safely summed to zona grain because most locais (43 of 74) split
  their seções across more than one zona eleitoral. Both are written as "N/A".
- Zona-grain delta gating has no per-local-pair concept to inherit (a zona isn't a
  single local), so it's gated the same way 06_build_vote_deltas.py gates local
  pairs -- both years present in candidacy_matrix.csv with matching tipo_eleicao --
  just applied at (candidate, year) grain instead of (candidate, local, year-pair)
  grain. This reuses the same gating rule and the same candidacy_matrix.csv the
  pipeline already built; it does not introduce a new one.
"""

import json
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_GEO, DATA_PROCESSED, PROJECT_ROOT, PSD_FOUNDING_YEAR  # noqa: E402
from _pipeline_utils import clean_id_series, election_type  # noqa: E402

OUT_PATH = PROJECT_ROOT / "data" / "exports" / "LEAL_dados_eleitorais.xlsx"

# (candidacy_matrix.csv / vote_deltas_by_local.csv key, geojson base filename, tab name)
ENTITIES = [
    ("hugo", "hugo_leal", "Hugo Leal"),
    ("felipe", "felipe_peixoto", "Felipe Peixoto"),
    ("psd", "psd", "PSD"),
]

# Mirrors scripts/09_voter_profile_geojson.py's ALL_METRIC_COLS (gender/age/education
# subset requested here). Numbered pipeline scripts don't import each other in this
# codebase, so this is a small deliberate copy -- keep both in sync if the profile
# dimensions ever change.
PROFILE_RAW_COLS = {
    "pct_mulheres": ["gen__feminino"],
    "pct_jovens_16_24": [
        "fai__16 anos", "fai__17 anos", "fai__18 anos",
        "fai__19 anos", "fai__20 anos", "fai__21 a 24 anos",
    ],
    "pct_60_mais": [
        "fai__60 a 64 anos", "fai__65 a 69 anos", "fai__70 a 74 anos",
        "fai__75 a 79 anos", "fai__80 a 84 anos", "fai__85 a 89 anos",
        "fai__90 a 94 anos", "fai__95 a 99 anos", "fai__100 anos ou mais",
    ],
    "pct_ensino_superior": ["gra__superior completo", "gra__superior incompleto"],
    "pct_ate_fundamental": [
        "gra__analfabeto", "gra__le e escreve",
        "gra__ensino fundamental completo", "gra__ensino fundamental incompleto",
    ],
}
PROFILE_FIELDS = list(PROFILE_RAW_COLS.keys())

HEADER_FILL = PatternFill("solid", fgColor="D9E2F3")
STATUS_FILL = PatternFill("solid", fgColor="FFF2CC")
DELTA_GAIN_FILL = PatternFill("solid", fgColor="C6E0B4")
DELTA_LOSS_FILL = PatternFill("solid", fgColor="F8CBAD")
DELTA_NA_FILL = PatternFill("solid", fgColor="D9D9D9")

INT_FMT = "#,##0"
PCT_FMT = '0.0"%"'
DELTA_FMT = '+0.0"%";-0.0"%"'
COORD_FMT = "0.000000"

INT_COLS = {"QT_VOTOS", "QT_VOTOS_total", "total_eleitores", "total_eleitores_zona", "num_locais_in_zona"}


# --------------------------------------------------------------------------- #
# Loaders
# --------------------------------------------------------------------------- #

def load_geojson_df(name: str) -> pd.DataFrame:
    path = DATA_GEO / f"{name}.geojson"
    data = json.loads(path.read_text(encoding="utf-8"))
    df = pd.DataFrame([f["properties"] for f in data["features"]])
    df["nr_local"] = clean_id_series(df["nr_local"])
    return df


def load_secao_votes(name: str) -> pd.DataFrame:
    path = DATA_GEO / f"{name}_secao.geojson"
    data = json.loads(path.read_text(encoding="utf-8"))
    df = pd.DataFrame([f["properties"] for f in data["features"]])
    df["nr_local"] = clean_id_series(df["nr_local"])
    df["NR_ZONA"] = clean_id_series(df["NR_ZONA"])
    return df


def load_candidacy_matrix() -> pd.DataFrame:
    return pd.read_csv(DATA_PROCESSED / "candidacy_matrix.csv")


def load_vote_deltas_local() -> pd.DataFrame:
    df = pd.read_csv(DATA_PROCESSED / "vote_deltas_by_local.csv", dtype={"nr_local": str})
    df["nr_local"] = clean_id_series(df["nr_local"])
    return df


def load_voter_profile_secao() -> pd.DataFrame:
    df = pd.read_csv(DATA_PROCESSED / "voter_profile_by_secao.csv")
    df["NR_ZONA"] = clean_id_series(df["NR_ZONA"])
    return df


def load_local_geo() -> pd.DataFrame:
    """nr_local -> endereco/lat/lon -- the join key for cross-referencing against
    external geodata (e.g. IBGE 2022 setor censitário shapefiles) on your own.
    Kept separate from _pipeline_utils.load_local_info(), which drops endereco."""
    df = pd.read_csv(DATA_GEO / "locais_votacao_niteroi.csv", dtype=str)
    df["nr_local"] = clean_id_series(df["nr_local"])
    for col in ("lat", "lon"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df[["nr_local", "endereco", "lat", "lon"]].drop_duplicates(subset=["nr_local"])


def load_zona_crosswalk() -> dict[str, str]:
    """nr_local -> comma-joined zonas it has seções in. A local can span more than
    one zona eleitoral (43 of Niterói's 74 locais do), so this is a set, not a
    single value -- roster is year-invariant (secoes_niteroi.csv carries no ano)."""
    df = pd.read_csv(DATA_GEO / "secoes_niteroi.csv", dtype=str)
    df["nr_local"] = clean_id_series(df["nr_local"])
    df["zona"] = clean_id_series(df["zona"])
    grouped = df.groupby("nr_local")["zona"].apply(lambda s: ",".join(sorted(set(s), key=int)))
    return grouped.to_dict()


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #

def candidacy_label(candidate_key: str, ano: int, matrix: pd.DataFrame) -> str:
    match = matrix[(matrix["candidate_key"] == candidate_key) & (matrix["ano"] == ano)]
    if not match.empty:
        return "concorreu"
    if candidate_key == "psd" and ano < PSD_FOUNDING_YEAR:
        return "partido inexistente"
    return "não concorreu"


def cargo_for_year(candidate_key: str, ano: int, matrix: pd.DataFrame) -> str:
    match = matrix[(matrix["candidate_key"] == candidate_key) & (matrix["ano"] == ano)]
    return match.iloc[0]["cargo"] if not match.empty else ""


def canonical_pairs(vote_deltas: pd.DataFrame) -> list[tuple[int, int]]:
    """The same year-pairs 06_build_vote_deltas.py already built deltas for --
    read back from its output rather than re-deriving the pairing logic."""
    pairs = vote_deltas[["ano_inicio", "ano_fim"]].drop_duplicates()
    return sorted(zip(pairs["ano_inicio"].tolist(), pairs["ano_fim"].tolist()))


def local_prior_delta_lookup(vote_deltas: pd.DataFrame, key: str) -> dict[tuple[str, int], dict]:
    """(nr_local, ano_fim) -> nearest gated prior-year delta, straight from
    06_build_vote_deltas.py's own output -- no gating recomputed here."""
    status_col, pct_col, cargo_col = f"candidacy_status_{key}", f"pct_delta_{key}", f"cargo_diferente_{key}"
    gated = vote_deltas[vote_deltas[status_col] == "concorreu"]
    lookup: dict[tuple[str, int], dict] = {}
    for (nr_local, ano_fim), group in gated.groupby(["nr_local", "ano_fim"]):
        best = group.loc[group["ano_inicio"].idxmax()]
        lookup[(nr_local, int(ano_fim))] = {
            "pct_delta": best[pct_col],
            "cargo_diferente": bool(best[cargo_col]),
        }
    return lookup


def zona_prior_delta_lookup(
    matrix: pd.DataFrame, key: str, pairs: list[tuple[int, int]]
) -> dict[int, tuple[int, bool]]:
    """ano_fim -> (nearest valid ano_inicio, cargo_diferente), gated the same way
    06_build_vote_deltas.py gates local pairs (both years in the candidacy matrix,
    matching tipo_eleicao) but applied at (candidate, year) grain since zona has no
    per-local pair to inherit gating from."""
    cand = matrix[matrix["candidate_key"] == key].set_index("ano")
    result: dict[int, tuple[int, bool]] = {}
    for ano_inicio, ano_fim in pairs:
        if ano_inicio not in cand.index or ano_fim not in cand.index:
            continue
        row_i, row_f = cand.loc[ano_inicio], cand.loc[ano_fim]
        if row_i["tipo_eleicao"] != row_f["tipo_eleicao"]:
            continue
        prev = result.get(ano_fim)
        if prev is None or ano_inicio > prev[0]:
            result[ano_fim] = (ano_inicio, row_i["cargo"] != row_f["cargo"])
    return result


def zona_profile_shares(profile_secao: pd.DataFrame) -> pd.DataFrame:
    """Same formula as 09_voter_profile_geojson.py's aggregate_profile_to_local +
    compute_shares (sum raw counts first, then divide) -- grouped by NR_ZONA
    instead of nr_local, since voter_profile_by_secao.csv already carries NR_ZONA
    directly (no crosswalk needed, unlike the local-grain version)."""
    raw_cols = [c for cols in PROFILE_RAW_COLS.values() for c in cols if c in profile_secao.columns]
    sum_cols = ["total_eleitores"] + raw_cols
    grouped = profile_secao.groupby(["ano", "NR_ZONA"], as_index=False)[sum_cols].sum()
    safe_total = grouped["total_eleitores"].astype(float).replace(0, float("nan"))
    for field, cols in PROFILE_RAW_COLS.items():
        present = [c for c in cols if c in grouped.columns]
        numerator = grouped[present].sum(axis=1) if present else pd.Series(0, index=grouped.index)
        grouped[field] = (numerator / safe_total * 100).round(1)
    return grouped[["ano", "NR_ZONA", "total_eleitores"] + PROFILE_FIELDS]


# --------------------------------------------------------------------------- #
# Section builders
# --------------------------------------------------------------------------- #

def build_section1(
    key: str,
    geojson_name: str,
    matrix: pd.DataFrame,
    zona_crosswalk: dict[str, str],
    prior_lookup: dict[tuple[str, int], dict],
    local_geo: pd.DataFrame,
) -> pd.DataFrame:
    df = load_geojson_df(geojson_name)
    df["ano"] = df["ano"].astype(int)
    df["tipo_eleicao"] = df["ano"].apply(election_type)
    df["NR_ZONA"] = df["nr_local"].map(zona_crosswalk).fillna("")
    df["regiao"] = ""  # not available offline -- see module docstring
    df = df.merge(local_geo, on="nr_local", how="left")
    df["candidacy_status"] = df["ano"].apply(lambda a: candidacy_label(key, int(a), matrix))

    if key == "psd":
        df["cargo_pretendido"] = "AGREGADO (múltiplos cargos)"
        df["pct_share"] = "N/A"  # no single valid-votes denominator across cargos -- see module docstring
        for i in (1, 2, 3):
            for suf in ("nome", "cargo", "votos"):
                src = f"psd_top{i}_{suf}"
                df[f"top{i}_{suf}"] = df[src] if src in df.columns else None
        competitor_cols = [f"top{i}_{suf}" for i in (1, 2, 3) for suf in ("nome", "cargo", "votos")]
    else:
        df["cargo_pretendido"] = df["cargo"]
        df["pct_share"] = (df["QT_VOTOS"] / df["total_votos_validos"] * 100).round(1)
        df["top_competitor_name"] = df.get("top1_nome")
        df["top_competitor_cargo"] = df["cargo"]  # top-N are ranked within the candidate's own cargo
        df["top_competitor_votes"] = df.get("top1_votos")
        competitor_cols = ["top_competitor_name", "top_competitor_cargo", "top_competitor_votes"]

    def lookup(row, field):
        entry = prior_lookup.get((row["nr_local"], int(row["ano"])))
        return entry[field] if entry is not None else "N/A"

    df["delta_vs_prior_comparable"] = df.apply(lambda r: lookup(r, "pct_delta"), axis=1)
    df["cargo_diferente"] = df.apply(lambda r: lookup(r, "cargo_diferente"), axis=1)

    base_cols = {
        "nr_local": "NR_LOCAL_VOTACAO",
        "nm_local": "NM_LOCAL_VOTACAO",
        "bairro": "bairro",
        "endereco": "endereco",
        "lat": "lat",
        "lon": "lon",
        "regiao": "regiao",
        "NR_ZONA": "NR_ZONA",
        "ano": "ano",
        "tipo_eleicao": "tipo_eleicao",
        "cargo_pretendido": "cargo_pretendido",
        "candidacy_status": "candidacy_status",
        "QT_VOTOS": "QT_VOTOS",
        "pct_share": "pct_share",
        "delta_vs_prior_comparable": "delta_vs_prior_comparable",
        "cargo_diferente": "cargo_diferente",
    }
    profile_cols = {"total_eleitores": "total_eleitores", **{f: f for f in PROFILE_FIELDS}}
    ordered = list(base_cols) + competitor_cols + list(profile_cols)
    out = df[ordered].rename(columns=base_cols)
    out = out.assign(_sort=out["NR_LOCAL_VOTACAO"].astype(int)).sort_values(["ano", "_sort"])
    return out.drop(columns="_sort").reset_index(drop=True)


def build_section2(
    key: str,
    matrix: pd.DataFrame,
    secao_votes: pd.DataFrame,
    zona_profile: pd.DataFrame,
    pairs: list[tuple[int, int]],
) -> pd.DataFrame:
    zona = (
        secao_votes.groupby(["ano", "NR_ZONA"], as_index=False)
        .agg(QT_VOTOS_total=("QT_VOTOS", "sum"), num_locais_in_zona=("nr_local", "nunique"))
    )
    zona["ano"] = zona["ano"].astype(int)
    zona["tipo_eleicao"] = zona["ano"].apply(election_type)
    zona["candidacy_status"] = zona["ano"].apply(lambda a: candidacy_label(key, int(a), matrix))
    if key == "psd":
        zona["cargo_pretendido"] = "AGREGADO (múltiplos cargos)"
    else:
        zona["cargo_pretendido"] = zona["ano"].apply(lambda a: cargo_for_year(key, int(a), matrix))
    zona["pct_share_zona"] = "N/A"  # no zona-grain valid-votes total anywhere -- see module docstring

    delta_map = zona_prior_delta_lookup(matrix, key, pairs)
    votes_index = zona.set_index(["ano", "NR_ZONA"])["QT_VOTOS_total"]

    def delta_for(row):
        entry = delta_map.get(int(row["ano"]))
        if entry is None:
            return "N/A"
        ano_inicio, _cargo_dif = entry
        try:
            prior = votes_index[(ano_inicio, row["NR_ZONA"])]
        except KeyError:
            return "N/A"
        if not prior:
            return "N/A"
        return round((row["QT_VOTOS_total"] - prior) / prior * 100, 2)

    zona["delta_vs_prior_comparable"] = zona.apply(delta_for, axis=1)

    merged = zona.merge(zona_profile, on=["ano", "NR_ZONA"], how="left")
    merged = merged.rename(columns={"total_eleitores": "total_eleitores_zona", **{f: f"{f}_zona" for f in PROFILE_FIELDS}})

    ordered = [
        "NR_ZONA", "ano", "tipo_eleicao", "cargo_pretendido", "candidacy_status",
        "QT_VOTOS_total", "pct_share_zona", "delta_vs_prior_comparable", "num_locais_in_zona",
        "total_eleitores_zona",
    ] + [f"{f}_zona" for f in PROFILE_FIELDS]
    out = merged[ordered]
    out = out.assign(_sort=out["NR_ZONA"].astype(int)).sort_values(["ano", "_sort"])
    return out.drop(columns="_sort").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Workbook writing / formatting
# --------------------------------------------------------------------------- #

def col_category(col: str) -> str:
    if col == "delta_vs_prior_comparable":
        return "delta"
    if col.startswith("pct_"):
        return "pct"
    if col in INT_COLS or col.endswith("_votos"):
        return "int"
    if col in ("lat", "lon"):
        return "coord"
    if col == "candidacy_status":
        return "status"
    return "text"


def clean_value(v):
    if isinstance(v, float) and pd.isna(v):
        return None
    return v


def write_section(ws, df: pd.DataFrame, start_row: int, title: str) -> tuple[int, int, int]:
    ws.cell(row=start_row, column=1, value=title).font = Font(bold=True, size=12)
    header_row = start_row + 1
    for j, col in enumerate(df.columns, start=1):
        cell = ws.cell(row=header_row, column=j, value=col)
        cell.font = Font(bold=True)
        cell.fill = HEADER_FILL

    categories = [col_category(c) for c in df.columns]
    for i, (_, row) in enumerate(df.iterrows()):
        r = header_row + 1 + i
        for j, col in enumerate(df.columns, start=1):
            value = clean_value(row[col])
            cell = ws.cell(row=r, column=j, value=value)
            cat = categories[j - 1]
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if cat == "int":
                    cell.number_format = INT_FMT
                elif cat == "pct":
                    cell.number_format = PCT_FMT
                elif cat == "delta":
                    cell.number_format = DELTA_FMT
                elif cat == "coord":
                    cell.number_format = COORD_FMT

    data_first, data_last = header_row + 1, header_row + len(df)
    return header_row, data_first, data_last


def apply_conditional_formats(ws, df: pd.DataFrame, header_row: int, data_first: int, data_last: int) -> None:
    if data_last < data_first:
        return
    for j, col in enumerate(df.columns, start=1):
        letter = get_column_letter(j)
        rng = f"{letter}{data_first}:{letter}{data_last}"
        cat = col_category(col)
        if cat == "delta":
            ws.conditional_formatting.add(rng, CellIsRule(operator="greaterThan", formula=["0"], fill=DELTA_GAIN_FILL))
            ws.conditional_formatting.add(rng, CellIsRule(operator="lessThan", formula=["0"], fill=DELTA_LOSS_FILL))
            ws.conditional_formatting.add(
                rng, FormulaRule(formula=[f'{letter}{data_first}="N/A"'], fill=DELTA_NA_FILL)
            )
        elif cat == "status":
            for label in ("não concorreu", "partido inexistente"):
                ws.conditional_formatting.add(
                    rng, CellIsRule(operator="equal", formula=[f'"{label}"'], fill=STATUS_FILL)
                )


def autofit_columns(ws, ncols: int, first_row: int, last_row: int) -> None:
    for j in range(1, ncols + 1):
        letter = get_column_letter(j)
        maxlen = 0
        for r in range(first_row, last_row + 1):
            v = ws.cell(row=r, column=j).value
            if v is not None:
                maxlen = max(maxlen, len(str(v)))
        ws.column_dimensions[letter].width = min(maxlen + 2, 40)


def write_tab(ws, section1: pd.DataFrame, section2: pd.DataFrame) -> None:
    header1, first1, last1 = write_section(ws, section1, start_row=1, title="SEÇÃO 1 — Por Local de Votação")
    apply_conditional_formats(ws, section1, header1, first1, last1)

    start2 = last1 + 3
    header2, first2, last2 = write_section(ws, section2, start_row=start2, title="SEÇÃO 2 — Por Zona Eleitoral")
    apply_conditional_formats(ws, section2, header2, first2, last2)

    ws.freeze_panes = f"A{first1}"
    autofit_columns(ws, max(section1.shape[1], section2.shape[1]), 1, last2)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def verify_output(path: Path, expected_sheets: list[str]) -> None:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True)
    assert wb.sheetnames == expected_sheets, f"sheet names mismatch: {wb.sheetnames} != {expected_sheets}"
    for name in expected_sheets:
        ws = wb[name]
        assert ws.max_row > 5, f"{name}: suspiciously few rows ({ws.max_row})"
        print(f"  Verified '{name}': {ws.max_row} rows x {ws.max_column} cols")
    wb.close()


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print("Loading shared sources ...")
    matrix = load_candidacy_matrix()
    vote_deltas = load_vote_deltas_local()
    zona_crosswalk = load_zona_crosswalk()
    local_geo = load_local_geo()
    pairs = canonical_pairs(vote_deltas)
    zona_profile = zona_profile_shares(load_voter_profile_secao())

    wb = Workbook()
    wb.remove(wb.active)

    for key, geojson_name, tab_name in ENTITIES:
        print(f"\nBuilding tab '{tab_name}' ...")
        prior_lookup = local_prior_delta_lookup(vote_deltas, key)
        section1 = build_section1(key, geojson_name, matrix, zona_crosswalk, prior_lookup, local_geo)

        secao_votes = load_secao_votes(geojson_name)
        section2 = build_section2(key, matrix, secao_votes, zona_profile, pairs)

        ws = wb.create_sheet(title=tab_name)
        write_tab(ws, section1, section2)
        print(f"  Section 1 (por local): {len(section1):,} rows")
        print(f"  Section 2 (por zona):  {len(section2):,} rows")

    wb.save(OUT_PATH)
    print(f"\nSaved {OUT_PATH}")

    print("\nVerifying output opens cleanly ...")
    verify_output(OUT_PATH, [name for _, _, name in ENTITIES])
    print("Done.")


if __name__ == "__main__":
    main()
