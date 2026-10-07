"""Extract polling place coordinates from TSE locais de votação.

Merges multiple years of locais files (2024, 2022) so that historical
polling places closed between elections are still covered.  For any
locais that appear in voting data but have no coordinates, pulls names
and addresses from voting CSVs and geocodes via Nominatim.
"""

import glob as globmod
import sys
import time
from pathlib import Path

import pandas as pd
from geopy.geocoders import Nominatim
from unidecode import unidecode

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_RAW, DATA_GEO, DATA_PROCESSED, MUNICIPIO, ALL_YEARS

ENCODINGS = ["latin-1", "utf-8", "cp1252"]


def read_csv_safe(path: Path, **kwargs) -> pd.DataFrame:
    for enc in ENCODINGS:
        try:
            return pd.read_csv(path, sep=";", encoding=enc, dtype=str, **kwargs)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    raise ValueError(f"Cannot read {path}")


def normalize(s: str) -> str:
    return unidecode(str(s)).upper().strip()


def load_locais(year: int) -> pd.DataFrame | None:
    folder = DATA_RAW / f"locais_votacao_{year}"
    if not folder.exists():
        return None
    files = sorted(folder.glob("*.csv")) + sorted(folder.glob("*.txt"))
    if not files:
        return None
    df = read_csv_safe(files[0])
    mask = df["NM_MUNICIPIO"].apply(lambda x: normalize(str(x)) == normalize(MUNICIPIO))
    nit = df[mask].copy()
    if nit.empty:
        return None
    print(f"  {year} locais file: {len(nit)} rows")
    return nit


def extract_locais(df: pd.DataFrame) -> pd.DataFrame:
    cols = {
        "NR_ZONA": "zona",
        "NR_SECAO": "secao",
        "NR_LOCAL_VOTACAO": "nr_local",
        "NM_LOCAL_VOTACAO": "nm_local",
        "DS_ENDERECO": "endereco",
        "NM_BAIRRO": "bairro",
        "NR_CEP": "cep",
        "NR_LATITUDE": "lat",
        "NR_LONGITUDE": "lon",
        "QT_ELEITOR_SECAO": "qt_eleitores_secao",
    }
    present = {k: v for k, v in cols.items() if k in df.columns}
    out = df[list(present.keys())].rename(columns=present).copy()

    if "lat" in out.columns:
        out["lat"] = pd.to_numeric(out["lat"].str.replace(",", "."), errors="coerce")
        out["lon"] = pd.to_numeric(out["lon"].str.replace(",", "."), errors="coerce")

    return out


def deduplicate_locais(df: pd.DataFrame) -> pd.DataFrame:
    """One row per nr_local, keeping the first row with valid coords."""
    df = df.copy()
    df["nr_local"] = df["nr_local"].astype(str).str.strip()
    df["has_coords"] = df["lat"].notna() & df["lon"].notna()
    df = df.sort_values("has_coords", ascending=False)
    keep_cols = [c for c in ["nr_local", "nm_local", "endereco", "bairro", "cep", "lat", "lon"] if c in df.columns]
    return df[keep_cols].drop_duplicates(subset=["nr_local"]).reset_index(drop=True)


def find_missing_locais(known_nrs: set) -> set:
    """Find NR_LOCAL_VOTACAO values in voting data that aren't in our locais set."""
    all_local_ids = set()
    for name in ["hugo_leal_by_secao.csv", "felipe_peixoto_by_secao.csv", "psd_by_secao.csv"]:
        path = DATA_PROCESSED / name
        if path.exists():
            df = pd.read_csv(path)
            ids = set(df["NR_LOCAL_VOTACAO"].astype(str).str.strip().unique())
            all_local_ids |= ids
    return all_local_ids - known_nrs


def extract_local_info_from_voting(missing_nrs: set) -> dict:
    """Pull NM_LOCAL_VOTACAO and address from voting CSVs (2016+ have these columns)."""
    info = {}
    for year in sorted(ALL_YEARS, reverse=True):
        if not missing_nrs - set(info.keys()):
            break
        folder = DATA_RAW / f"votacao_secao_{year}"
        files = sorted(folder.glob("*.csv")) + sorted(folder.glob("*.txt"))
        if not files:
            continue
        header = pd.read_csv(files[0], sep=";", encoding="latin-1", dtype=str, nrows=0)
        if "NM_LOCAL_VOTACAO" not in header.columns:
            continue

        use_cols = ["NM_MUNICIPIO", "NR_LOCAL_VOTACAO", "NM_LOCAL_VOTACAO"]
        if "DS_LOCAL_VOTACAO_ENDERECO" in header.columns:
            use_cols.append("DS_LOCAL_VOTACAO_ENDERECO")

        for chunk in pd.read_csv(files[0], sep=";", encoding="latin-1", dtype=str, chunksize=200000, usecols=use_cols):
            mask = chunk["NM_MUNICIPIO"].apply(lambda x: normalize(str(x)) == normalize(MUNICIPIO))
            nit = chunk[mask]
            for nr in missing_nrs - set(info.keys()):
                rows = nit[nit["NR_LOCAL_VOTACAO"].astype(str).str.strip() == nr]
                if len(rows) > 0:
                    r = rows.iloc[0]
                    info[nr] = {
                        "nm_local": r.get("NM_LOCAL_VOTACAO", ""),
                        "endereco": r.get("DS_LOCAL_VOTACAO_ENDERECO", ""),
                    }
    return info


def geocode_address(address: str, name: str) -> tuple[float, float] | None:
    geolocator = Nominatim(user_agent="leal_niteroi_research")
    loc = geolocator.geocode(f"{address}, Niteroi, RJ, Brasil")
    if loc:
        return loc.latitude, loc.longitude
    time.sleep(1.5)
    loc = geolocator.geocode(f"{name}, Niteroi, RJ, Brasil")
    if loc:
        return loc.latitude, loc.longitude
    return None


def main():
    DATA_GEO.mkdir(parents=True, exist_ok=True)

    # --- Step 1: Merge locais from all available years (newest first) ---
    all_locais = []
    for year in [2024, 2022]:
        raw = load_locais(year)
        if raw is not None:
            all_locais.append(extract_locais(raw))

    if not all_locais:
        print("No locais de votacao data found")
        return

    merged = pd.concat(all_locais, ignore_index=True)
    locais = deduplicate_locais(merged)
    known_nrs = set(locais["nr_local"].unique())
    print(f"  After merging locais files: {len(locais)} unique locais")

    # --- Step 2: Find locais referenced in voting data but missing from locais files ---
    missing = find_missing_locais(known_nrs)
    if missing:
        print(f"  {len(missing)} locais in voting data but missing from locais files: {sorted(missing)}")
        local_info = extract_local_info_from_voting(missing)

        new_rows = []
        for nr in sorted(missing):
            info = local_info.get(nr, {})
            nm = info.get("nm_local", f"Local {nr}")
            addr = info.get("endereco", "")
            coords = geocode_address(addr, nm) if addr else None
            time.sleep(1.5)

            if coords:
                print(f"    {nr}: {nm} -> {coords[0]:.6f}, {coords[1]:.6f}")
                new_rows.append({
                    "nr_local": nr,
                    "nm_local": nm,
                    "endereco": addr,
                    "bairro": "",
                    "cep": "",
                    "lat": coords[0],
                    "lon": coords[1],
                })
            else:
                print(f"    {nr}: {nm} -> GEOCODE FAILED")

        if new_rows:
            locais = pd.concat([locais, pd.DataFrame(new_rows)], ignore_index=True)
            print(f"  After geocoding: {len(locais)} unique locais")
    else:
        print("  All voting-data locais are covered")

    # --- Step 3: Build seções file from 2024 locais (for seção-level data) ---
    raw_2024 = load_locais(2024)
    secoes = extract_locais(raw_2024) if raw_2024 is not None else pd.DataFrame()

    # --- Step 4: Save ---
    if not secoes.empty:
        secoes.to_csv(DATA_GEO / "secoes_niteroi.csv", index=False)

    locais.to_csv(DATA_GEO / "locais_votacao_niteroi.csv", index=False)

    has_coords = locais["lat"].notna().sum()
    print(f"\nSaved locais_votacao_niteroi.csv: {len(locais)} locais, {has_coords} with coords")


if __name__ == "__main__":
    main()
