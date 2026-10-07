"""Merge votes + geocoded locations + voter profiles into GeoJSON for the web map."""

import sys, json
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_PROCESSED, DATA_GEO, FELIPE_PEIXOTO, HUGO_LEAL


def load_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        print(f"  [skip] {path.name} not found")
        return None
    df = pd.read_csv(path)
    print(f"  Loaded {path.name}: {len(df)} rows")
    return df


def get_local_coords(locais: pd.DataFrame) -> pd.DataFrame:
    """Build (nr_zona, nr_local) -> lat/lon/nm_local/bairro lookup. nr_local
    alone collides across zonas in Niterói (verified ~58 collisions in 2026);
    the identity key is the pair. Legacy rows (nr_zona == '') serve as the
    coord fallback for historic years whose zone data we don't have."""
    locais = locais.copy()

    def clean_id(series: pd.Series) -> pd.Series:
        # Pandas inferred the column as float on read (load_csv doesn't pass
        # dtype=str), so "71" came in as 71.0. Round-trip through Int64 to get
        # a plain integer string, with NaN -> "". str.strip() handles the
        # cases where the column was already string.
        numeric = pd.to_numeric(series, errors="coerce")
        return numeric.astype("Int64").astype(str).replace("<NA>", "").str.strip()

    locais["nr_local"] = clean_id(locais["nr_local"])
    locais["nr_zona"] = clean_id(locais["nr_zona"]) if "nr_zona" in locais.columns else ""
    unique = locais.drop_duplicates(subset=["nr_zona", "nr_local"])
    cols = [c for c in ["nr_zona", "nr_local", "nm_local", "bairro", "lat", "lon"] if c in unique.columns]
    return unique[cols].copy()


def merge_votes_to_locais(votes: pd.DataFrame, local_coords: pd.DataFrame) -> pd.DataFrame:
    """Join votes to locations on (NR_ZONA, NR_LOCAL_VOTACAO). Falls back to
    the legacy nr_local-only lookup for historic locais whose zone wasn't in
    the TSE locais csv (legacy rows carry nr_zona='')."""
    if "NR_LOCAL_VOTACAO" not in votes.columns:
        return pd.DataFrame()
    votes = votes.copy()

    def clean_id(series: pd.Series) -> pd.Series:
        numeric = pd.to_numeric(series, errors="coerce")
        return numeric.astype("Int64").astype(str).replace("<NA>", "").str.strip()

    votes["nr_local"] = clean_id(votes["NR_LOCAL_VOTACAO"])
    votes["nr_zona"] = clean_id(votes["NR_ZONA"]) if "NR_ZONA" in votes.columns else ""

    # Composite-key merge first.
    primary = local_coords[local_coords["nr_zona"] != ""] if "nr_zona" in local_coords.columns else local_coords
    merged = votes.merge(primary, on=["nr_zona", "nr_local"], how="left")

    # Fallback for rows that didn't match: legacy coords keyed on nr_local only.
    legacy = local_coords[local_coords["nr_zona"] == ""] if "nr_zona" in local_coords.columns else pd.DataFrame()
    if not legacy.empty:
        legacy_lookup = legacy.drop(columns=["nr_zona"]).drop_duplicates("nr_local").set_index("nr_local")
        for idx, row in merged[merged["lat"].isna()].iterrows():
            fallback = legacy_lookup.loc[row["nr_local"]] if row["nr_local"] in legacy_lookup.index else None
            if fallback is not None:
                for col in ("nm_local", "bairro", "lat", "lon"):
                    if col in legacy_lookup.columns:
                        merged.at[idx, col] = fallback[col]

    return merged.dropna(subset=["lat", "lon"])


def aggregate_to_local(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-secao votes up to (zona, local) grain. zona is now part
    of the identity so distinct buildings sharing nr_local across zonas stay
    distinct features."""
    if df.empty or "nr_local" not in df.columns:
        return df

    group_cols = ["ano", "nr_zona", "nr_local", "label"]

    agg = df.groupby(group_cols, as_index=False).agg(
        QT_VOTOS=("QT_VOTOS", "sum"),
        n_secoes=("NR_SECAO", "nunique"),
    )

    info_cols = [c for c in ["nm_local", "bairro", "lat", "lon"] if c in df.columns]
    info = df.drop_duplicates(subset=["nr_zona", "nr_local"])[["nr_zona", "nr_local"] + info_cols]
    agg = agg.merge(info, on=["nr_zona", "nr_local"], how="left")
    return agg


PEOPLE_CONFIG = {"hugo_leal": HUGO_LEAL, "felipe_peixoto": FELIPE_PEIXOTO}


def add_cargo_column(by_local: pd.DataFrame, name: str) -> pd.DataFrame:
    person = PEOPLE_CONFIG.get(name)
    if person is None or by_local.empty:
        return by_local
    by_local = by_local.copy()
    by_local["cargo"] = by_local["ano"].map(
        lambda ano: person["elections"].get(int(ano), {}).get("cargo")
    )
    return by_local


def to_geojson(df: pd.DataFrame, layer_name: str) -> dict:
    features = []
    for _, row in df.iterrows():
        props = {}
        for k, v in row.items():
            if k in ("lat", "lon"):
                continue
            if pd.isna(v):
                props[k] = None
            elif isinstance(v, (int, float)):
                props[k] = int(v) if v == int(v) else round(v, 4)
            else:
                props[k] = str(v)
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["lon"]), float(row["lat"])]
            }
        })
    return {
        "type": "FeatureCollection",
        "name": layer_name,
        "features": features,
    }


def main():
    DATA_GEO.mkdir(parents=True, exist_ok=True)

    locais = load_csv(DATA_GEO / "locais_votacao_niteroi.csv")
    if locais is None:
        print("Run 03_geocode_locais.py first")
        return

    local_coords = get_local_coords(locais)
    print(f"  {len(local_coords)} unique locais with coordinates")

    datasets = {
        "hugo_leal": DATA_PROCESSED / "hugo_leal_by_secao.csv",
        "felipe_peixoto": DATA_PROCESSED / "felipe_peixoto_by_secao.csv",
        "psd": DATA_PROCESSED / "psd_by_secao.csv",
    }

    for name, path in datasets.items():
        votes = load_csv(path)
        if votes is None:
            continue

        merged = merge_votes_to_locais(votes, local_coords)
        total_votes_raw = votes["QT_VOTOS"].sum()
        total_votes_matched = merged["QT_VOTOS"].sum() if not merged.empty else 0
        pct = 100 * total_votes_matched / total_votes_raw if total_votes_raw else 0
        print(f"  {name}: {total_votes_matched:,.0f}/{total_votes_raw:,.0f} votes matched ({pct:.0f}%)")

        by_local = aggregate_to_local(merged)
        by_local = add_cargo_column(by_local, name)

        geojson = to_geojson(by_local, name)
        out = DATA_GEO / f"{name}.geojson"
        out.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Saved {out.name} ({len(geojson['features'])} features)")

    # Rebuild data.js for the web map. Use the full APP_GEOJSON_LAYERS list
    # (not just this script's `datasets`) so vote_deltas and voter_profile
    # stay in the bundle when 05 is re-run; otherwise 05 wipes them and the
    # UI's "Comparar dois anos" and profile sections silently go empty until
    # 06 and 09 run again.
    from _pipeline_utils import APP_GEOJSON_LAYERS, rebuild_data_js
    rebuild_data_js(DATA_GEO, DATA_GEO.parent.parent / "app", APP_GEOJSON_LAYERS)
    print("Done.")


if __name__ == "__main__":
    main()
