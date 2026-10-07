"""Extract voter demographics by seção for Niterói across all years."""

import sys
from pathlib import Path

import pandas as pd
from unidecode import unidecode

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_RAW, DATA_PROCESSED, MUNICIPIO, ALL_YEARS

ENCODINGS = ["latin-1", "utf-8", "cp1252"]

GROUP_COLS = ["NR_ZONA", "NR_SECAO"]
DEMO_COLS = ["DS_GENERO", "DS_FAIXA_ETARIA", "DS_GRAU_ESCOLARIDADE", "DS_RACA_COR", "DS_ESTADO_CIVIL"]
COUNT_COL = "QT_ELEITORES_PERFIL"


def read_csv_safe(path: Path) -> pd.DataFrame:
    for enc in ENCODINGS:
        try:
            return pd.read_csv(path, sep=";", encoding=enc, dtype=str)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    raise ValueError(f"Cannot read {path}")


def normalize(s: str) -> str:
    return unidecode(str(s)).upper().strip()


def process_perfil(year: int) -> pd.DataFrame | None:
    folder = DATA_RAW / f"perfil_eleitor_secao_{year}"
    if not folder.exists():
        print(f"  [skip] {folder} not found")
        return None

    files = sorted(folder.glob("*.csv")) + sorted(folder.glob("*.txt"))
    if not files:
        print(f"  [skip] no CSV in {folder}")
        return None

    df = read_csv_safe(files[0])
    print(f"  Read {files[0].name}: {len(df):,} rows")

    mask = df["NM_MUNICIPIO"].apply(lambda x: normalize(str(x)) == normalize(MUNICIPIO))
    df_nit = df[mask].copy()
    print(f"  Niterói rows: {len(df_nit):,}")

    if df_nit.empty:
        return None

    df_nit[COUNT_COL] = pd.to_numeric(df_nit[COUNT_COL], errors="coerce").fillna(0).astype(int)
    df_nit["ano"] = year
    return df_nit


def build_profile(df: pd.DataFrame) -> pd.DataFrame:
    base = GROUP_COLS + ["ano"]

    # Total eleitores per seção
    totals = df.groupby(base, as_index=False)[COUNT_COL].sum()
    totals = totals.rename(columns={COUNT_COL: "total_eleitores"})

    for demo_col in DEMO_COLS:
        if demo_col not in df.columns:
            continue
        pivot = df.groupby(base + [demo_col], as_index=False)[COUNT_COL].sum()
        pivot = pivot.pivot_table(
            index=base, columns=demo_col, values=COUNT_COL, fill_value=0
        ).reset_index()
        prefix = demo_col.replace("DS_", "").lower()[:3]  # gen, fai, gra
        pivot.columns = [
            f"{prefix}__{normalize(str(c)).lower()}" if c not in base else c
            for c in pivot.columns
        ]
        totals = totals.merge(pivot, on=base, how="left")

    return totals


def main():
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    all_profiles = []

    for year in ALL_YEARS:
        print(f"\n=== {year} ===")
        df = process_perfil(year)
        if df is None:
            continue

        profile = build_profile(df)
        all_profiles.append(profile)
        print(f"  OK: {len(profile)} secoes, {profile['total_eleitores'].sum():,} eleitores")

    if all_profiles:
        combined = pd.concat(all_profiles, ignore_index=True)
        out = DATA_PROCESSED / "voter_profile_by_secao.csv"
        combined.to_csv(out, index=False)
        print(f"\nSaved {out.name} ({len(combined):,} rows, {len(combined.columns)} columns)")
    else:
        print("\nNo voter profile data found")


if __name__ == "__main__":
    main()
