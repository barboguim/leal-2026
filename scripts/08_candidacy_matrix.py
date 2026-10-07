"""Build the candidacy matrix: for Hugo Leal, Felipe Peixoto, and PSD, which
years did they actually run, for which cargo, in which election type —
confirmed from TSE's consulta_cand registration files (Hugo/Felipe) or
derived from party existence + processed vote presence (PSD)."""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_GEO, DATA_PROCESSED, DATA_RAW, FELIPE_PEIXOTO, HUGO_LEAL, MUNICIPIO, PARTY_NUMBERS, PSD_FOUNDING_YEAR, url_consulta_cand
from _pipeline_utils import (
    clean_id_series, download_and_extract, election_type, find_csv,
    normalize, read_csv_safe, read_tse_chunks_safe,
)

RJ_CONSULTA_CAND_COLUMNS = [
    "ANO_ELEICAO", "DS_CARGO", "NM_CANDIDATO", "NM_URNA_CANDIDATO",
    "SG_PARTIDO", "NR_PARTIDO", "DS_SITUACAO_CANDIDATURA",
]

PEOPLE = {"hugo": HUGO_LEAL, "felipe": FELIPE_PEIXOTO}


def download_consulta_cand(year: int) -> bool:
    dest = DATA_RAW / f"consulta_cand_{year}"
    return download_and_extract(url_consulta_cand(year), dest, f"consulta_cand {year}")


def load_consulta_cand_rj(year: int) -> pd.DataFrame:
    folder = DATA_RAW / f"consulta_cand_{year}"
    rj_file = folder / f"consulta_cand_{year}_RJ.csv"
    if not rj_file.exists():
        return pd.DataFrame()
    df = read_csv_safe(rj_file, sep=";", dtype=str, usecols=RJ_CONSULTA_CAND_COLUMNS)
    return df


# Matches on name identity across the WHOLE state of RJ, not scoped to
# Niterói — a candidate's matrix row can therefore reflect a real candidacy
# in a different RJ municipality (this happens for real: Hugo Leal's 2016
# row is a genuine Vice-Prefeito candidacy in Rio de Janeiro city, confirmed
# via CPF cross-reference, and is intentionally NOT filtered out — a
# municipality filter would have wrongly excluded that real candidacy). A
# second same-type candidacy anywhere in RJ under the same matched name
# would be picked up too; that's correct per the name/CPF-anchored design,
# just worth knowing.
def match_candidate(df_year: pd.DataFrame, name: str) -> pd.DataFrame:
    if df_year.empty:
        return df_year
    target = normalize(name)
    mask = df_year["NM_CANDIDATO"].apply(normalize).str.contains(target, regex=False)
    return df_year[mask]


def build_person_matrix_rows(candidate_key: str, person: dict) -> list[dict]:
    rows = []
    known_years = sorted(person["elections"].keys())
    all_registration_years = sorted(set(known_years) | {y for y in range(2010, 2025) if y % 2 == 0})

    for year in all_registration_years:
        df_year = load_consulta_cand_rj(year)
        matched = match_candidate(df_year, person["name"])
        config_entry = person["elections"].get(year)

        if matched.empty:
            if config_entry is not None:
                print(
                    f"  [WARN] {person['name']}: config.py has a {year} entry "
                    f"({config_entry['cargo']}), but consulta_cand_{year}_RJ.csv "
                    f"shows no matching registration. Matrix will treat {year} "
                    f"as not confirmed running. Review config.py or the raw file."
                )
            continue

        candidacy_row = matched.iloc[0]
        cargo = candidacy_row["DS_CARGO"].strip().upper()
        if config_entry is not None and normalize(config_entry["cargo"]) != normalize(cargo):
            print(
                f"  [WARN] {person['name']} {year}: config.py says cargo "
                f"'{config_entry['cargo']}', consulta_cand says '{cargo}'. "
                f"Matrix uses consulta_cand's value."
            )
        if config_entry is None:
            print(
                f"  [WARN] {person['name']}: config.py has no {year} entry, "
                f"but consulta_cand_{year}_RJ.csv shows a registered candidacy "
                f"(cargo: {cargo}, situacao: {candidacy_row['DS_SITUACAO_CANDIDATURA']}). "
                f"Matrix will treat {year} as 'concorreu' for gating. "
                f"Review and update config.py if this is confirmed real."
            )

        rows.append({
            "candidate_key": candidate_key,
            "ano": year,
            "cargo": cargo,
            "tipo_eleicao": election_type(year),
            "partido": candidacy_row["SG_PARTIDO"],
            "situacao_candidatura": candidacy_row["DS_SITUACAO_CANDIDATURA"],
        })
    return rows


def build_psd_matrix_rows() -> list[dict]:
    path = DATA_PROCESSED / "psd_by_secao.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path, dtype=str)
    if df.empty or "ano" not in df.columns:
        return []
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
    years = sorted(int(y) for y in df["ano"].dropna().unique() if int(y) >= PSD_FOUNDING_YEAR)
    return [
        {
            "candidate_key": "psd",
            "ano": year,
            "cargo": "AGREGADO",
            "tipo_eleicao": election_type(year),
            "partido": "PSD",
            "situacao_candidatura": "PARTIDO_ATIVO",
        }
        for year in years
    ]


def build_candidacy_matrix() -> pd.DataFrame:
    rows = []
    for candidate_key, person in PEOPLE.items():
        rows.extend(build_person_matrix_rows(candidate_key, person))
    rows.extend(build_psd_matrix_rows())
    return pd.DataFrame(rows, columns=[
        "candidate_key", "ano", "cargo", "tipo_eleicao", "partido", "situacao_candidatura",
    ])


PSD_RAW_COLUMNS = ["NM_MUNICIPIO", "DS_CARGO", "NR_VOTAVEL", "NM_VOTAVEL", "QT_VOTOS", "NR_LOCAL_VOTACAO"]
PSD_TOP_N = 3

# The only cargos where a bare party-number ballot is a voto de legenda
# (party-list vote, not a real candidate) — Brazil's three proportional
# races. Everything else (Prefeito, Governador, Senador, Presidente) is
# majoritarian: the bare party number IS the actual candidate's number.
PROPORTIONAL_CARGOS = {"VEREADOR", "DEPUTADO ESTADUAL", "DEPUTADO FEDERAL"}


def load_niteroi_psd_year(year: int) -> pd.DataFrame:
    # ponytail: votacao_secao files carry no SG_PARTIDO column (confirmed against
    # actual 2012-2024 RJ files); party is identified by NR_VOTAVEL prefix, same
    # convention 02_process_votes.py::extract_party_votes already uses.
    folder = DATA_RAW / f"votacao_secao_{year}"
    csv_file = find_csv(folder)
    if csv_file is None:
        return pd.DataFrame()

    party_nr = PARTY_NUMBERS["PSD"]
    pieces = []
    for chunk in read_tse_chunks_safe(csv_file, usecols=PSD_RAW_COLUMNS):
        mask = (
            chunk["NM_MUNICIPIO"].apply(lambda x: normalize(x) == normalize(MUNICIPIO))
            & chunk["NR_VOTAVEL"].astype(str).str.startswith(party_nr)
        )
        nit = chunk.loc[mask].copy()
        if not nit.empty:
            pieces.append(nit)
    if not pieces:
        return pd.DataFrame()

    df = pd.concat(pieces, ignore_index=True)
    df["QT_VOTOS"] = pd.to_numeric(df["QT_VOTOS"], errors="coerce").fillna(0).astype(int)
    df["nr_local"] = clean_id_series(df["NR_LOCAL_VOTACAO"])
    df["cargo_norm"] = df["DS_CARGO"].apply(normalize)

    # A bare party-number ballot ("55", no candidate digits appended) on a
    # proportional race (Vereador, Deputado Estadual/Federal) is a voto de
    # legenda — a party-list vote, not a real candidacy — so NM_VOTAVEL is
    # the party's own name. On a majoritarian race (Prefeito, Governador,
    # Senador, Presidente) NR_VOTAVEL == party_nr IS the actual candidate's
    # number — there's no legend concept there — so only exclude the
    # bare-number row for the proportional cargos.
    is_legenda = df["cargo_norm"].isin(PROPORTIONAL_CARGOS) & (df["NR_VOTAVEL"].astype(str) == party_nr)
    df = df[~is_legenda]
    return df


def rank_psd_breakdown_by_local(df_year: pd.DataFrame) -> dict[str, dict]:
    if df_year.empty:
        return {}
    df_year = df_year[df_year["nr_local"] != ""]
    if df_year.empty:
        return {}

    grouped = df_year.groupby(
        ["nr_local", "NR_VOTAVEL", "NM_VOTAVEL", "cargo_norm"], as_index=False
    )["QT_VOTOS"].sum()

    result: dict[str, dict] = {}
    for nr_local, group in grouped.groupby("nr_local"):
        top = group.sort_values("QT_VOTOS", ascending=False).head(PSD_TOP_N)
        total_por_cargo = group.groupby("cargo_norm")["QT_VOTOS"].sum().to_dict()
        result[nr_local] = {
            "top3": [
                {
                    "nome": row["NM_VOTAVEL"],
                    "cargo": row["cargo_norm"],
                    "votos": int(row["QT_VOTOS"]),
                    "share": round(row["QT_VOTOS"] / total_por_cargo[row["cargo_norm"]] * 100, 1),
                }
                for _, row in top.iterrows()
            ],
            "candidate_count": len(group),
            "total_por_cargo": {k: int(v) for k, v in total_por_cargo.items()},
        }
    return result


def psd_breakdown_fields(breakdown: dict) -> dict:
    fields = {
        "psd_candidate_count": breakdown["candidate_count"],
        "psd_total_por_cargo": json.dumps(breakdown["total_por_cargo"]),
    }
    top3 = breakdown["top3"]
    for i in range(PSD_TOP_N):
        n = i + 1
        entry = top3[i] if i < len(top3) else None
        fields[f"psd_top{n}_nome"] = entry["nome"] if entry else None
        fields[f"psd_top{n}_cargo"] = entry["cargo"] if entry else None
        fields[f"psd_top{n}_votos"] = entry["votos"] if entry else None
        fields[f"psd_top{n}_share"] = entry["share"] if entry else None
    return fields


def build_psd_breakdown_by_year() -> dict[int, dict[str, dict]]:
    path = DATA_PROCESSED / "psd_by_secao.csv"
    if not path.exists():
        return {}
    existing = pd.read_csv(path, dtype=str)
    if existing.empty or "ano" not in existing.columns:
        return {}
    years = sorted(int(y) for y in pd.to_numeric(existing["ano"], errors="coerce").dropna().unique())

    breakdown_by_year = {}
    for year in years:
        print(f"  Reading {year} for PSD breakdown ...")
        df_year = load_niteroi_psd_year(year)
        breakdown_by_year[year] = rank_psd_breakdown_by_local(df_year)
        print(f"    {len(breakdown_by_year[year])} locais with PSD breakdown data")
    return breakdown_by_year


def merge_psd_breakdown(geojson: dict, breakdown_by_year: dict[int, dict[str, dict]]) -> dict:
    for feature in geojson.get("features", []):
        props = feature["properties"]
        year = props.get("ano")
        nr_local = str(props.get("nr_local", "")).strip()
        breakdown = breakdown_by_year.get(year, {}).get(nr_local)
        if breakdown:
            props.update(psd_breakdown_fields(breakdown))
    return geojson


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    print("Downloading consulta_cand (candidate registration) files ...")
    all_years = sorted({y for y in range(2010, 2025) if y % 2 == 0})
    for year in all_years:
        download_consulta_cand(year)

    print("\nBuilding candidacy matrix ...")
    matrix = build_candidacy_matrix()
    out_path = DATA_PROCESSED / "candidacy_matrix.csv"
    matrix.to_csv(out_path, index=False)
    print(f"  Saved {out_path.name}: {len(matrix):,} rows")

    print("\nBuilding PSD slate breakdown ...")
    breakdown_by_year = build_psd_breakdown_by_year()
    psd_path = DATA_GEO / "psd.geojson"
    if psd_path.exists():
        geojson = json.loads(psd_path.read_text(encoding="utf-8"))
        merge_psd_breakdown(geojson, breakdown_by_year)
        psd_path.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Updated {psd_path.name}")
    else:
        print(f"  [skip] {psd_path.name} not found; run 05_build_geojson.py first")

    print("Done.")


if __name__ == "__main__":
    main()
