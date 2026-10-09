"""Rebuild hugo_leal_secao.geojson including zero-vote seções.

Hugo's by-seção CSV only has seções where he got votes. For a complete
roster view (which the user asked for), we also need the seções where he
got 0 — e.g. CIEP 251 has 8 seções in TSE 2026 but Hugo only showed up
at 1. The popup now wants to show all 8.

Roster source: the raw votacao_secao_YYYY_RJ.csv files (chunked read to
stay memory-safe). We extract unique (zona, nr_local, secao) tuples in
Niteroi per year, then emit a feature per tuple with Hugo's votes
(from the processed CSV) OR 0.
"""

import json
import sys
from pathlib import Path

import pandas as pd
from unidecode import unidecode

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import ALL_YEARS, DATA_PROCESSED, DATA_GEO, DATA_RAW, MUNICIPIO


def normalize(s: str) -> str:
    return unidecode(str(s)).upper().strip()


def load_year_roster(year: int) -> pd.DataFrame:
    """Returns one row per (zona, nr_local, secao) in Niteroi for the year.
    Reads the TSE votacao_secao raw file in chunks to keep memory bounded."""
    folder = DATA_RAW / f"votacao_secao_{year}"
    csvs = sorted(folder.glob("*.csv"))
    if not csvs:
        return pd.DataFrame(columns=["ano", "nr_zona", "nr_local", "secao"])

    required = ["NM_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO"]
    header = pd.read_csv(csvs[0], sep=";", encoding="latin-1", dtype=str, nrows=0, low_memory=False)
    if any(c not in header.columns for c in required):
        return pd.DataFrame(columns=["ano", "nr_zona", "nr_local", "secao"])

    pieces = []
    for chunk in pd.read_csv(
        csvs[0], sep=";", encoding="latin-1", dtype=str, low_memory=False,
        usecols=required, chunksize=200_000,
    ):
        mask = chunk["NM_MUNICIPIO"].apply(lambda x: normalize(x) == normalize(MUNICIPIO))
        sub = chunk.loc[mask, ["NR_ZONA", "NR_LOCAL_VOTACAO", "NR_SECAO"]].copy()
        if sub.empty:
            continue
        sub = sub.drop_duplicates()
        pieces.append(sub)

    if not pieces:
        return pd.DataFrame(columns=["ano", "nr_zona", "nr_local", "secao"])

    df = pd.concat(pieces, ignore_index=True).drop_duplicates()
    df = df.rename(columns={"NR_ZONA": "nr_zona", "NR_LOCAL_VOTACAO": "nr_local", "NR_SECAO": "secao"})
    df["ano"] = year
    return df[["ano", "nr_zona", "nr_local", "secao"]]


def main() -> None:
    votes_csv = DATA_PROCESSED / "hugo_leal_by_secao.csv"
    locais_csv = DATA_GEO / "locais_votacao_niteroi.csv"
    out_path = DATA_GEO / "hugo_leal_secao.geojson"

    votes = pd.read_csv(votes_csv, dtype=str)
    votes["ano"] = pd.to_numeric(votes["ano"]).astype(int)
    votes["QT_VOTOS"] = pd.to_numeric(votes["QT_VOTOS"]).astype(int)
    votes["nr_local"] = votes["NR_LOCAL_VOTACAO"].fillna("").astype(str).str.strip()
    votes["nr_zona"] = votes["NR_ZONA"].fillna("").astype(str).str.strip()
    votes["secao"] = votes["NR_SECAO"].fillna("").astype(str).str.strip()
    hugo_lookup = {
        (int(r["ano"]), r["nr_zona"], r["nr_local"], r["secao"]): int(r["QT_VOTOS"])
        for _, r in votes.iterrows()
    }

    locais = pd.read_csv(locais_csv, dtype=str)
    locais["nr_local"] = locais["nr_local"].fillna("").astype(str).str.strip()
    locais["nr_zona"] = locais["nr_zona"].fillna("").astype(str).str.strip() if "nr_zona" in locais.columns else ""
    primary = {
        (r["nr_zona"], r["nr_local"]): {"nm_local": r.get("nm_local"), "bairro": r.get("bairro"), "lat": r.get("lat"), "lon": r.get("lon")}
        for _, r in locais[locais["nr_zona"] != ""].drop_duplicates(["nr_zona", "nr_local"]).iterrows()
    }
    legacy = {
        r["nr_local"]: {"nm_local": r.get("nm_local"), "bairro": r.get("bairro"), "lat": r.get("lat"), "lon": r.get("lon")}
        for _, r in locais[locais["nr_zona"] == ""].drop_duplicates("nr_local").iterrows()
    }

    features = []
    dropped = 0
    zero_added = 0

    for year in sorted(int(y) for y in (set(ALL_YEARS) & set(votes["ano"].unique()))):
        print(f"  Loading roster {year} ...")
        roster = load_year_roster(year)
        if roster.empty:
            print(f"    [warn] no roster, falling back to Hugo-only features for {year}")
            sub = votes[votes["ano"] == year]
            roster_tuples = {(int(r["ano"]), r["nr_zona"], r["nr_local"], r["secao"]) for _, r in sub.iterrows()}
        else:
            roster_tuples = {(year, r["nr_zona"], r["nr_local"], r["secao"]) for _, r in roster.iterrows()}

        for t in roster_tuples:
            yr, zona, nr_local, secao = t
            qt = int(hugo_lookup.get(t, 0))
            if qt == 0:
                zero_added += 1
            c = primary.get((zona, nr_local)) or legacy.get(nr_local)
            if not c or pd.isna(c.get("lat")):
                dropped += 1
                continue
            features.append({
                "type": "Feature",
                "properties": {
                    "ano": int(yr),
                    "NR_ZONA": str(zona),
                    "nr_zona": str(zona),
                    "NR_SECAO": str(secao),
                    "QT_VOTOS": qt,
                    "label": "HUGO LEAL",
                    "nr_local": str(nr_local),
                    "nm_local": c.get("nm_local"),
                    "bairro": c.get("bairro"),
                },
                "geometry": {"type": "Point", "coordinates": [float(c["lon"]), float(c["lat"])]},
            })

    out = {"type": "FeatureCollection", "name": "hugo_leal_secao", "features": features}
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    years = sorted({f["properties"]["ano"] for f in features})
    nonzero = sum(1 for f in features if f["properties"]["QT_VOTOS"] > 0)
    print(f"\nWrote {out_path.name}: {len(features)} features ({nonzero} with votes, {zero_added} zero-vote), dropped {dropped} unmatched")
    print(f"Years: {years}")


if __name__ == "__main__":
    main()
