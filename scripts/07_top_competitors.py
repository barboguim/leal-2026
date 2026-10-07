"""Rank the top-3 competing candidates per (year, cargo, local), excluding
Hugo Leal and Felipe Peixoto, and merge them onto hugo_leal.geojson /
felipe_peixoto.geojson."""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_GEO, DATA_RAW, FELIPE_PEIXOTO, HUGO_LEAL, MUNICIPIO
from _pipeline_utils import clean_id_series, find_csv, normalize, read_tse_chunks_safe, rebuild_data_js

TOP_N = 3
BLANK_NULL_CODES = {"95", "96"}
# Cargos where a bare 1-2 digit party-number ballot can be a voto de legenda
# (used to build the legenda party-name lookup and to exclude legenda rows
# from the ranked-candidate list in is_real_candidate/rank_top3_by_local).
# Not the same constant as 08_candidacy_matrix.py's PROPORTIONAL_CARGOS,
# which serves an unrelated purpose (PSD legenda-vote exclusion there).
LEGENDA_ELIGIBLE_CARGOS = {"DEPUTADO FEDERAL", "DEPUTADO ESTADUAL"}
LEGENDA_CARGOS = LEGENDA_ELIGIBLE_CARGOS | {"VEREADOR"}
PEOPLE = {"hugo_leal": HUGO_LEAL, "felipe_peixoto": FELIPE_PEIXOTO}
EXCLUDED_NAMES = {normalize(p["name"]) for p in PEOPLE.values()}


def is_real_candidate(nr_votavel: str, cargo_norm: str) -> bool:
    code = str(nr_votavel).strip()
    if code in BLANK_NULL_CODES:
        return False
    if cargo_norm in LEGENDA_ELIGIBLE_CARGOS and len(code) <= 2:
        return False
    return True


def build_party_lookup(df_year: pd.DataFrame) -> dict[str, str]:
    prop = df_year[df_year["cargo_norm"].isin(LEGENDA_CARGOS)]
    legenda = prop[prop["NR_VOTAVEL"].str.len() <= 2]
    legenda = legenda[~legenda["NR_VOTAVEL"].isin(BLANK_NULL_CODES)]
    legenda = legenda[~legenda["NM_VOTAVEL"].str.startswith("#")]
    pairs = legenda[["NR_VOTAVEL", "NM_VOTAVEL"]].drop_duplicates()
    return dict(zip(pairs["NR_VOTAVEL"], pairs["NM_VOTAVEL"]))


def party_for(nr_votavel: str, party_lookup: dict[str, str]) -> str:
    prefix = str(nr_votavel).strip()[:2]
    return party_lookup.get(prefix, prefix)


def rank_top3_by_local(
    df_cargo: pd.DataFrame, exclude: set[str], party_lookup: dict[str, str]
) -> dict[str, list[dict]]:
    if df_cargo.empty:
        return {}

    keep_mask = df_cargo.apply(
        lambda r: is_real_candidate(r["NR_VOTAVEL"], r["cargo_norm"]), axis=1
    )
    candidates = df_cargo[keep_mask]
    candidates = candidates[~candidates["NM_VOTAVEL"].apply(normalize).isin(exclude)]
    candidates = candidates[candidates["nr_local"] != ""]
    if candidates.empty:
        return {}

    grouped = candidates.groupby(
        ["nr_local", "NR_VOTAVEL", "NM_VOTAVEL"], as_index=False
    )["QT_VOTOS"].sum()

    result: dict[str, list[dict]] = {}
    for nr_local, group in grouped.groupby("nr_local"):
        top = group.sort_values("QT_VOTOS", ascending=False).head(TOP_N)
        result[nr_local] = [
            {
                "nome": row["NM_VOTAVEL"],
                "partido": party_for(row["NR_VOTAVEL"], party_lookup),
                "votos": int(row["QT_VOTOS"]),
            }
            for _, row in top.iterrows()
        ]
    return result


def is_valid_vote(nr_votavel: str) -> bool:
    """Looser than is_real_candidate: excludes only voto branco/nulo (95/96).

    Unlike is_real_candidate, this keeps voto de legenda rows — legenda
    votes are valid votes under TSE's own convention, just not attributed
    to an individual candidate, so they belong in the vote-share
    denominator even though they're excluded from the ranked-candidate list.
    """
    return str(nr_votavel).strip() not in BLANK_NULL_CODES


def total_valid_votes_by_local(df_cargo: pd.DataFrame) -> dict[str, int]:
    if df_cargo.empty:
        return {}
    keep_mask = df_cargo["NR_VOTAVEL"].apply(is_valid_vote)
    candidates = df_cargo[keep_mask]
    candidates = candidates[candidates["nr_local"] != ""]
    if candidates.empty:
        return {}
    totals = candidates.groupby("nr_local")["QT_VOTOS"].sum()
    return {nr_local: int(total) for nr_local, total in totals.items()}


def top3_fields(entries: list[dict]) -> dict:
    fields = {}
    for i in range(TOP_N):
        n = i + 1
        entry = entries[i] if i < len(entries) else None
        fields[f"top{n}_nome"] = entry["nome"] if entry else None
        fields[f"top{n}_partido"] = entry["partido"] if entry else None
        fields[f"top{n}_votos"] = entry["votos"] if entry else None
    return fields


RAW_COLUMNS = ["NM_MUNICIPIO", "DS_CARGO", "NR_VOTAVEL", "NM_VOTAVEL", "QT_VOTOS", "NR_LOCAL_VOTACAO"]


def load_niteroi_year(year: int) -> pd.DataFrame:
    folder = DATA_RAW / f"votacao_secao_{year}"
    csv_file = find_csv(folder)
    if csv_file is None:
        return pd.DataFrame()

    pieces = []
    for chunk in read_tse_chunks_safe(csv_file, usecols=RAW_COLUMNS):
        mask = chunk["NM_MUNICIPIO"].apply(lambda x: normalize(x) == normalize(MUNICIPIO))
        nit = chunk.loc[mask].copy()
        if not nit.empty:
            pieces.append(nit)
    if not pieces:
        return pd.DataFrame()

    df = pd.concat(pieces, ignore_index=True)
    df["QT_VOTOS"] = pd.to_numeric(df["QT_VOTOS"], errors="coerce").fillna(0).astype(int)
    df["nr_local"] = clean_id_series(df["NR_LOCAL_VOTACAO"])
    df["cargo_norm"] = df["DS_CARGO"].apply(normalize)
    return df


def year_cargo_pairs() -> set[tuple[int, str]]:
    pairs = set()
    for person in PEOPLE.values():
        for year, info in person["elections"].items():
            pairs.add((year, normalize(info["cargo"])))
    return pairs


def build_all_rankings() -> tuple[dict[tuple[int, str], dict[str, list[dict]]], dict[tuple[int, str], dict[str, int]]]:
    pairs = year_cargo_pairs()
    years = sorted({year for year, _ in pairs})
    rankings = {}
    totals = {}
    for year in years:
        print(f"  Reading {year} ...")
        df_year = load_niteroi_year(year)
        if df_year.empty:
            print(f"    [skip] no Niteroi rows for {year}")
            continue
        party_lookup = build_party_lookup(df_year)
        cargos = {cargo for y, cargo in pairs if y == year}
        for cargo in cargos:
            df_cargo = df_year[df_year["cargo_norm"] == cargo]
            rankings[(year, cargo)] = rank_top3_by_local(df_cargo, EXCLUDED_NAMES, party_lookup)
            totals[(year, cargo)] = total_valid_votes_by_local(df_cargo)
            print(f"    {cargo}: {len(rankings[(year, cargo)])} locais ranked")
    return rankings, totals


def rankings_for_person(person_key: str, all_rankings: dict) -> dict[int, dict[str, list[dict]]]:
    person = PEOPLE[person_key]
    result = {}
    for year, info in person["elections"].items():
        cargo = normalize(info["cargo"])
        result[year] = all_rankings.get((year, cargo), {})
    return result


def totals_for_person(person_key: str, all_totals: dict) -> dict[int, dict[str, int]]:
    person = PEOPLE[person_key]
    result = {}
    for year, info in person["elections"].items():
        cargo = normalize(info["cargo"])
        result[year] = all_totals.get((year, cargo), {})
    return result


def merge_top_competitors(
    geojson: dict,
    rankings_by_year: dict[int, dict[str, list[dict]]],
    totals_by_year: dict[int, dict[str, int]],
) -> dict:
    for feature in geojson.get("features", []):
        props = feature["properties"]
        year = props.get("ano")
        nr_local = str(props.get("nr_local", "")).strip()
        entries = rankings_by_year.get(year, {}).get(nr_local, [])
        props.update(top3_fields(entries))
        props["total_votos_validos"] = totals_by_year.get(year, {}).get(nr_local)
    return geojson


def main() -> None:
    DATA_GEO.mkdir(parents=True, exist_ok=True)

    print("Building competitor rankings from raw TSE files ...")
    all_rankings, all_totals = build_all_rankings()

    for person_key in PEOPLE:
        path = DATA_GEO / f"{person_key}.geojson"
        if not path.exists():
            print(f"  [skip] {path.name} not found; run 05_build_geojson.py first")
            continue
        geojson = json.loads(path.read_text(encoding="utf-8"))
        rankings = rankings_for_person(person_key, all_rankings)
        totals = totals_for_person(person_key, all_totals)
        merge_top_competitors(geojson, rankings, totals)
        path.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Updated {path.name}")

    print("\nUpdating app bundle ...")
    rebuild_data_js(DATA_GEO, DATA_GEO.parent.parent / "app")
    print("Done.")


if __name__ == "__main__":
    main()
