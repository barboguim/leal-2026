"""Aggregate seção-level voter demographics (04's output) up to local de
votação grain, collapsing TSE's raw category columns into a fixed set of
11 mutually-exclusive shares across three dimensions (gender, age,
education). Race/cor is deliberately not included — confirmed against the
real raw TSE files that it is structurally unpopulated for Niterói across
the whole 2010-2024 span (100% "#NE"/not-informed in 2010-2022, 93%+
not-informed even in 2024) — see docs/voter_profile_backbone.md.

The same 11 fields feed both this script's standalone voter_profile.geojson
(for the map's ProfileLayer) and the fields merged onto the three candidate
geojson files (for the popup breakdown) — one data model, computed once.
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import ALL_YEARS, DATA_GEO, DATA_PROCESSED, DATA_RAW, MUNICIPIO
from _pipeline_utils import clean_id_series, load_local_info, load_section_roster, to_geojson

GENDER_COLS = {
    "pct_mulheres": ["gen__feminino"],
    "pct_homens": ["gen__masculino"],
    "pct_genero_nao_informado": ["gen__nao informado"],
}

AGE_COLS = {
    "pct_jovens_16_24": [
        "fai__16 anos", "fai__17 anos", "fai__18 anos",
        "fai__19 anos", "fai__20 anos", "fai__21 a 24 anos",
    ],
    "pct_adultos_25_59": [
        "fai__25 a 29 anos", "fai__30 a 34 anos", "fai__35 a 39 anos",
        "fai__40 a 44 anos", "fai__45 a 49 anos", "fai__50 a 54 anos", "fai__55 a 59 anos",
    ],
    "pct_60_mais": [
        "fai__60 a 64 anos", "fai__65 a 69 anos", "fai__70 a 74 anos",
        "fai__75 a 79 anos", "fai__80 a 84 anos", "fai__85 a 89 anos",
        "fai__90 a 94 anos", "fai__95 a 99 anos", "fai__100 anos ou mais",
    ],
    # fai__invalido / fai__invalida are the same category under two raw
    # labels — a TSE label-agreement inconsistency across years. Real
    # volume is 43 people across all 8 years of Niterói data; merging
    # costs nothing and keeps the dimension exhaustive.
    "pct_idade_nao_informado": ["fai__invalido", "fai__invalida"],
}

EDUCATION_COLS = {
    "pct_ate_fundamental": [
        "gra__analfabeto", "gra__le e escreve",
        "gra__ensino fundamental completo", "gra__ensino fundamental incompleto",
    ],
    "pct_ensino_medio": ["gra__ensino medio completo", "gra__ensino medio incompleto"],
    "pct_ensino_superior": ["gra__superior completo", "gra__superior incompleto"],
    "pct_escolaridade_nao_informado": ["gra__nao informado"],
}

ALL_METRIC_COLS = {**GENDER_COLS, **AGE_COLS, **EDUCATION_COLS}

# Only these columns are published to voter_profile.geojson (and therefore
# app/data.js) — the raw fai__/gen__/gra__ intermediate count columns that
# compute_shares() needs internally for the percentage math must not leak
# into the shipped output.
PUBLISHED_COLS = ["ano", "nr_local", "nm_local", "bairro", "lat", "lon", "total_eleitores"] + list(
    ALL_METRIC_COLS.keys()
)


def select_published_columns(merged: pd.DataFrame) -> pd.DataFrame:
    return merged[[c for c in PUBLISHED_COLS if c in merged.columns]]


def aggregate_profile_to_local(profile: pd.DataFrame, roster: pd.DataFrame) -> pd.DataFrame:
    """Join seção-grain profile counts to nr_local via the roster, then sum
    raw counts (not pre-computed percentages) up to (ano, nr_local) — summing
    raw counts first avoids compounding rounding error from averaging
    already-rounded percentages."""
    empty_cols = ["ano", "nr_local", "total_eleitores"] + [c for cols in ALL_METRIC_COLS.values() for c in cols]
    if profile.empty or roster.empty:
        return pd.DataFrame(columns=empty_cols)

    # roster's NR_ZONA/NR_SECAO are always str (via clean_id_series), but a
    # profile loaded straight from CSV (e.g. pd.read_csv with no dtype hint)
    # infers them as int64 — cast here so the merge below can't hit pandas'
    # "trying to merge on int64 and str columns" ValueError regardless of
    # how the caller loaded profile.
    profile = profile.copy()
    profile["NR_ZONA"] = clean_id_series(profile["NR_ZONA"])
    profile["NR_SECAO"] = clean_id_series(profile["NR_SECAO"])

    crosswalk = roster[["ano", "NR_ZONA", "NR_SECAO", "nr_local"]].drop_duplicates()
    joined = profile.merge(crosswalk, on=["ano", "NR_ZONA", "NR_SECAO"], how="inner")
    joined = joined[joined["nr_local"] != ""]
    if joined.empty:
        return pd.DataFrame(columns=empty_cols)

    raw_cols = [c for cols in ALL_METRIC_COLS.values() for c in cols if c in joined.columns]
    sum_cols = ["total_eleitores"] + raw_cols
    grouped = joined.groupby(["ano", "nr_local"], as_index=False)[sum_cols].sum()
    return grouped


def compute_shares(grouped: pd.DataFrame) -> pd.DataFrame:
    """Turn summed raw counts into the 11 published percentage fields."""
    grouped = grouped.copy()
    # float("nan") (not pd.NA) — pandas 3.x's replace(0, pd.NA) upcasts a
    # float64 series to object dtype, and Series.round() can't round pd.NA.
    safe_total = grouped["total_eleitores"].astype(float).replace(0, float("nan"))
    for field, cols in ALL_METRIC_COLS.items():
        present = [c for c in cols if c in grouped.columns]
        numerator = grouped[present].sum(axis=1) if present else pd.Series(0, index=grouped.index)
        grouped[field] = (numerator / safe_total * 100).round(1)
    return grouped


def profile_lookup(shares: pd.DataFrame) -> dict[tuple[int, str], dict]:
    fields = ["total_eleitores"] + list(ALL_METRIC_COLS)
    lookup = {}
    for _, row in shares.iterrows():
        lookup[(int(row["ano"]), row["nr_local"])] = {
            f: (None if pd.isna(row[f]) else row[f]) for f in fields
        }
    return lookup


def merge_profile_onto_layer(geojson: dict, lookup: dict[tuple[int, str], dict]) -> dict:
    for feature in geojson.get("features", []):
        props = feature["properties"]
        year = props.get("ano")
        nr_local = str(props.get("nr_local", "")).strip()
        fields = lookup.get((year, nr_local))
        if fields:
            props.update(fields)
    return geojson


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    DATA_GEO.mkdir(parents=True, exist_ok=True)

    print("Loading voter_profile_by_secao.csv ...")
    profile_path = DATA_PROCESSED / "voter_profile_by_secao.csv"
    if not profile_path.exists():
        print("  [skip] voter_profile_by_secao.csv not found; run 04_voter_profile.py first")
        return
    profile = pd.read_csv(profile_path)
    print(f"  {len(profile):,} seção-grain rows")

    print("\nLoading polling-place coordinates ...")
    locais = load_local_info(DATA_GEO)

    print("\nBuilding section/local roster ...")
    # 09 has no votes_by_secao of its own to offer the roster's raw-file-read
    # fallback path — passing {} is correct, not a placeholder: the real raw
    # votacao_secao files are already present for every year in this
    # project, so load_section_roster_from_raw() succeeds directly and the
    # fallback is never exercised.
    roster = load_section_roster({}, ALL_YEARS, DATA_RAW, MUNICIPIO)

    print("\nAggregating profile to local grain ...")
    grouped = aggregate_profile_to_local(profile, roster)
    shares = compute_shares(grouped)
    print(f"  {len(shares):,} (ano, nr_local) rows with demographic shares")
    lookup = profile_lookup(shares)

    print("\nBuilding standalone voter_profile.geojson ...")
    merged = shares.merge(locais, on="nr_local", how="left")
    merged = select_published_columns(merged)
    geojson = to_geojson(merged, "voter_profile")
    out = DATA_GEO / "voter_profile.geojson"
    out.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Saved {out.name}: {len(geojson['features']):,} features")

    print("\nMerging profile fields onto candidate layers ...")
    for name in ("hugo_leal", "felipe_peixoto", "psd"):
        path = DATA_GEO / f"{name}.geojson"
        if not path.exists():
            print(f"  [skip] {path.name} not found; run 05_build_geojson.py first")
            continue
        cand_geojson = json.loads(path.read_text(encoding="utf-8"))
        merge_profile_onto_layer(cand_geojson, lookup)
        path.write_text(json.dumps(cand_geojson, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Updated {path.name}")

    print("Done.")


if __name__ == "__main__":
    main()
