"""Rank locais de votacao by electorate-composition similarity to Hugo Leal's
strongest locais, among locais where he currently underperforms -- demographic
lookalike targeting for the "Zonas com Potencial" map layer.

This ranks locais by how similar their registered electorate's composition is
to Hugo's stronghold locais. It does not identify individual voters, predict
votes, or claim causation -- see ZONAS_COM_POTENCIAL.md for the full framing
rules the frontend layer built on this output must follow.

Methodology (see ZONAS_COM_POTENCIAL.md for the full rationale):
1. Use Hugo's most recent election year.
2. Strongholds = locais in the top quartile by pct_share that year.
3. Stronghold profile = mean of the 7-field demographic vector across strongholds.
4. Candidate pool = locais below the median pct_share that year.
5. Rank the pool by Euclidean distance to the stronghold centroid (nearest first).
6. Keep the top 20.
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import DATA_GEO, HUGO_LEAL  # noqa: E402
from _pipeline_utils import rebuild_data_js, to_geojson, APP_GEOJSON_LAYERS  # noqa: E402

DEMOGRAPHIC_FIELDS = [
    "pct_mulheres", "pct_jovens_16_24", "pct_adultos_25_59", "pct_60_mais",
    "pct_ate_fundamental", "pct_ensino_medio", "pct_ensino_superior",
]
# Matches the labels already used for these same 7 fields in
# app-web/src/lib/constants.js's PROFILE_DIMENSIONS -- keep in sync.
FIELD_LABELS = {
    "pct_mulheres": "% Mulheres",
    "pct_jovens_16_24": "% Jovens 16-24",
    "pct_adultos_25_59": "% Adultos 25-59",
    "pct_60_mais": "% 60+",
    "pct_ate_fundamental": "% Ate Fundamental",
    "pct_ensino_medio": "% Ensino Medio",
    "pct_ensino_superior": "% Ensino Superior",
}
TOP_ALIGNED_FIELDS_N = 2
TOP_N = 20
STRONGHOLD_QUANTILE = 0.75


def latest_election_year() -> int:
    return max(HUGO_LEAL["elections"].keys())


def load_hugo_year(geojson: dict, year: int) -> pd.DataFrame:
    rows = []
    for f in geojson.get("features", []):
        props = f["properties"]
        if props.get("ano") != year:
            continue
        row = dict(props)
        coords = (f.get("geometry") or {}).get("coordinates")
        if coords:
            row["lon"], row["lat"] = coords[0], coords[1]
        rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["pct_share"] = df["QT_VOTOS"] / df["total_votos_validos"] * 100
    return df


def stronghold_centroid(df: pd.DataFrame) -> pd.Series:
    threshold = df["pct_share"].quantile(STRONGHOLD_QUANTILE)
    strongholds = df[df["pct_share"] >= threshold]
    return strongholds[DEMOGRAPHIC_FIELDS].mean()


def candidate_pool(df: pd.DataFrame) -> pd.DataFrame:
    median = df["pct_share"].median()
    return df[df["pct_share"] < median].copy()


def most_aligned_fields(abs_diff_row: pd.Series) -> str:
    """The N demographic fields closest to the stronghold centroid for one
    local -- i.e. the dimensions actually driving its similarity ranking,
    not just the aggregate distance. Ascending by gap, so the single closest
    field comes first."""
    closest = abs_diff_row.nsmallest(TOP_ALIGNED_FIELDS_N).index
    return ", ".join(FIELD_LABELS[f] for f in closest)


def rank_by_similarity(pool: pd.DataFrame, centroid: pd.Series) -> pd.DataFrame:
    pool = pool.copy()
    diff = pool[DEMOGRAPHIC_FIELDS].sub(centroid, axis=1)
    pool["distance"] = (diff ** 2).sum(axis=1) ** 0.5
    pool["similarity_score"] = (100 - pool["distance"]).round(1)
    pool["maior_semelhanca"] = diff.abs().apply(most_aligned_fields, axis=1)
    pool = pool.sort_values(["distance", "pct_share"], ascending=[True, True])
    pool["rank"] = range(1, len(pool) + 1)
    return pool.head(TOP_N)


def build_output(ranked: pd.DataFrame, year: int) -> pd.DataFrame:
    out = ranked[["nr_local", "nm_local", "bairro", "lat", "lon", "pct_share", "similarity_score", "rank", "maior_semelhanca"]].copy()
    out["ano"] = year
    out["pct_share"] = out["pct_share"].round(1)
    return out


def main() -> None:
    DATA_GEO.mkdir(parents=True, exist_ok=True)

    hugo_path = DATA_GEO / "hugo_leal.geojson"
    if not hugo_path.exists():
        print("  [skip] hugo_leal.geojson not found; run 05_build_geojson.py first")
        return
    hugo_geojson = json.loads(hugo_path.read_text(encoding="utf-8"))

    year = latest_election_year()
    print(f"Using Hugo's most recent election year: {year}")

    df = load_hugo_year(hugo_geojson, year)
    if df.empty:
        print(f"  [skip] no hugo_leal features for {year}")
        return
    print(f"  {len(df):,} locais with Hugo votes in {year}")

    centroid = stronghold_centroid(df)
    pool = candidate_pool(df)
    print(f"  Candidate pool (below median pct_share): {len(pool):,} locais")

    ranked = rank_by_similarity(pool, centroid)
    out = build_output(ranked, year)

    geojson = to_geojson(out, "potential_hugo")
    out_path = DATA_GEO / "potential_hugo.geojson"
    out_path.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Saved {out_path.name}: {len(geojson['features']):,} features")

    print("\nUpdating app bundle ...")
    layers = APP_GEOJSON_LAYERS + ["potential_hugo"]
    rebuild_data_js(DATA_GEO, DATA_GEO.parent.parent / "app", layers)

    print("Done.")


if __name__ == "__main__":
    main()
