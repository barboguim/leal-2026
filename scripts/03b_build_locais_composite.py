"""Build locais_votacao_niteroi.csv keyed by (nr_zona, nr_local).

In Niterói, nr_local alone collides across zonas (verified ~58 collisions in
2026 — e.g. nr_local 1295 is 'COLÉGIO SALESIANO SANTA ROSA' in zona 71 and
'UMEI PROFA ODETE' in zona 199, two entirely different buildings). The
earlier csv was keyed on nr_local alone, silently merging distinct locais.

Source: TSE `eleitorado_local_votacao_YYYY_RJ.csv`, which carries NR_ZONA,
NR_LOCAL_VOTACAO, NM_LOCAL_VOTACAO, DS_ENDERECO, NM_BAIRRO, NR_LATITUDE,
NR_LONGITUDE. Prefers the newest available file so that locais renamed /
relocated in 2026 show their current identity; falls back to older files
(2024, 2022) for locais that no longer exist in 2026 but Hugo had votes at.

Mirrors mobi-pleito-2026's load_year_locations() pattern.
"""

import sys
from pathlib import Path

import pandas as pd
from unidecode import unidecode

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_RAW, DATA_GEO, MUNICIPIO, UF


def normalize(s: str) -> str:
    return unidecode(str(s)).upper().strip()


def load_year(year: int) -> pd.DataFrame | None:
    folder = DATA_RAW / f"locais_votacao_{year}"
    uf_specific = sorted(folder.glob(f"*_{UF}.csv"))
    if not uf_specific:
        return None
    df = pd.read_csv(
        uf_specific[0], sep=";", encoding="latin-1", dtype=str, low_memory=False,
        usecols=[
            "SG_UF", "NM_MUNICIPIO", "NR_ZONA", "NR_LOCAL_VOTACAO",
            "NM_LOCAL_VOTACAO", "DS_ENDERECO", "NM_BAIRRO",
            "NR_LATITUDE", "NR_LONGITUDE",
        ],
    )
    df = df[df["NM_MUNICIPIO"].apply(lambda x: normalize(x) == normalize(MUNICIPIO))].copy()
    df["nr_zona"] = df["NR_ZONA"].astype(str).str.strip()
    df["nr_local"] = df["NR_LOCAL_VOTACAO"].astype(str).str.strip()
    df["nm_local"] = df["NM_LOCAL_VOTACAO"].astype(str).str.strip()
    df["endereco"] = df["DS_ENDERECO"].astype(str).str.strip()
    df["bairro"] = df["NM_BAIRRO"].astype(str).str.strip()
    df["lat"] = pd.to_numeric(df["NR_LATITUDE"].str.replace(",", ".", regex=False), errors="coerce")
    df["lon"] = pd.to_numeric(df["NR_LONGITUDE"].str.replace(",", ".", regex=False), errors="coerce")
    df = df.drop_duplicates(subset=["nr_zona", "nr_local"])
    df["year_source"] = year
    return df[["nr_zona", "nr_local", "nm_local", "endereco", "bairro", "lat", "lon", "year_source"]]


def main() -> None:
    # Prefer newest file (2026) so renamed/relocated locais show 2026 identity.
    frames = []
    for year in (2026, 2024, 2022):
        df = load_year(year)
        if df is None:
            print(f"  [skip] locais_votacao_{year} folder not found")
            continue
        print(f"  Loaded {year}: {len(df)} unique (zona, nr_local) pairs")
        frames.append(df)
    if not frames:
        raise SystemExit("No locais files available")

    combined = pd.concat(frames, ignore_index=True)
    # Keep newest row per (zona, nr_local) — newer sources take priority.
    combined = combined.drop_duplicates(subset=["nr_zona", "nr_local"], keep="first")

    # Carry the OLD csv's coords/overrides as a last-resort fallback for
    # locais that only existed in 2010-2018 (we don't have TSE locais files
    # for those years — the csv was geocoded).
    old_path = DATA_GEO / "locais_votacao_niteroi.csv"
    if old_path.exists():
        old = pd.read_csv(old_path, dtype=str)
        if "nr_local" in old.columns:
            old["nr_local"] = old["nr_local"].astype(str).str.strip()
            # The old csv has no zona — stamp as "legacy" so we don't collide
            # with real-zone rows above. Those legacy rows are retained only
            # if their nr_local doesn't appear in any newer file at all.
            seen_locals = set(combined["nr_local"])
            legacy = old[~old["nr_local"].isin(seen_locals)].copy()
            if not legacy.empty:
                legacy["nr_zona"] = ""
                legacy["year_source"] = "legacy"
                legacy = legacy.rename(columns={})
                for col in ("endereco",):
                    if col not in legacy.columns:
                        legacy[col] = ""
                for col in ("lat", "lon"):
                    legacy[col] = pd.to_numeric(legacy[col], errors="coerce")
                legacy = legacy[["nr_zona", "nr_local", "nm_local", "endereco", "bairro", "lat", "lon", "year_source"]]
                combined = pd.concat([combined, legacy], ignore_index=True)
                print(f"  Carried {len(legacy)} legacy rows from the old csv")

    out = DATA_GEO / "locais_votacao_niteroi.csv"
    combined.to_csv(out, index=False)
    print(f"\nWrote {out.name}: {len(combined)} rows (one per (zona, nr_local))")


if __name__ == "__main__":
    main()
