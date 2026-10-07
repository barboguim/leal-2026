"""Rebuild hugo_leal_secao.geojson from hugo_leal_by_secao.csv + locais coords.

Script 05 only emits the local-de-votação layer. This script emits the seção
layer (one point per vote-seção, at the host local's coordinate), which is the
primary layer in the leal-2026 UI.

Added 2026-10-07 as part of the Hugo-only fork; the source repo built the
seção layer by hand once and never rebuilt it. This script makes the rebuild
repeatable so new years (2026, 2028, ...) can be dropped into the UI.
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_PROCESSED, DATA_GEO


def main() -> None:
    votes_csv = DATA_PROCESSED / "hugo_leal_by_secao.csv"
    locais_csv = DATA_GEO / "locais_votacao_niteroi.csv"
    out_path = DATA_GEO / "hugo_leal_secao.geojson"

    votes = pd.read_csv(votes_csv, dtype=str)
    votes["ano"] = pd.to_numeric(votes["ano"]).astype(int)
    votes["QT_VOTOS"] = pd.to_numeric(votes["QT_VOTOS"]).astype(int)
    if "NR_TURNO" in votes.columns:
        votes["NR_TURNO"] = pd.to_numeric(votes["NR_TURNO"], errors="coerce").astype("Int64")
    votes["nr_local"] = votes.get("NR_LOCAL_VOTACAO", "").fillna("").astype(str).str.strip()
    votes["nr_zona"] = votes.get("NR_ZONA", "").fillna("").astype(str).str.strip()

    # Composite (zona, nr_local) lookup, plus a legacy nr_local-only fallback
    # for historic locais without zone data. See scripts/03b_build_locais.
    locais = pd.read_csv(locais_csv, dtype=str)
    locais["nr_local"] = locais["nr_local"].fillna("").astype(str).str.strip()
    locais["nr_zona"] = locais["nr_zona"].fillna("").astype(str).str.strip() if "nr_zona" in locais.columns else ""
    primary_coords = {
        (r["nr_zona"], r["nr_local"]): {"nm_local": r.get("nm_local"), "bairro": r.get("bairro"), "lat": r.get("lat"), "lon": r.get("lon")}
        for _, r in locais[locais["nr_zona"] != ""].drop_duplicates(["nr_zona", "nr_local"]).iterrows()
    }
    legacy_coords = {
        r["nr_local"]: {"nm_local": r.get("nm_local"), "bairro": r.get("bairro"), "lat": r.get("lat"), "lon": r.get("lon")}
        for _, r in locais[locais["nr_zona"] == ""].drop_duplicates("nr_local").iterrows()
    }

    features = []
    dropped = 0
    for _, r in votes.iterrows():
        c = primary_coords.get((r["nr_zona"], r["nr_local"])) or legacy_coords.get(r["nr_local"])
        if not c or pd.isna(c.get("lat")):
            dropped += 1
            continue
        turno = int(r["NR_TURNO"]) if pd.notna(r.get("NR_TURNO")) else None
        features.append({
            "type": "Feature",
            "properties": {
                "ano": int(r["ano"]),
                "NR_ZONA": r.get("NR_ZONA", ""),
                "NR_SECAO": r.get("NR_SECAO", ""),
                "NR_TURNO": turno,
                "QT_VOTOS": int(r["QT_VOTOS"]),
                "label": r.get("label", "HUGO LEAL"),
                "nr_zona": r["nr_zona"],
                "nr_local": r["nr_local"],
                "nm_local": c.get("nm_local"),
                "bairro": c.get("bairro"),
            },
            "geometry": {
                "type": "Point",
                "coordinates": [float(c["lon"]), float(c["lat"])],
            },
        })

    out = {"type": "FeatureCollection", "name": "hugo_leal_secao", "features": features}
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    years = sorted({f["properties"]["ano"] for f in features})
    print(f"Wrote {out_path.name}: {len(features)} features, dropped {dropped} unmatched")
    print(f"Years: {years}")


if __name__ == "__main__":
    main()
