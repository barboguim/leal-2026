"""Filter TSE voting data to Niterói and extract candidate/party votes by seção."""

import sys
from pathlib import Path

import pandas as pd
from unidecode import unidecode

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (
    DATA_RAW, DATA_PROCESSED, MUNICIPIO, UF,
    ALL_YEARS, HUGO_LEAL, FELIPE_PEIXOTO, PARTY, PARTY_NUMBERS,
)

ENCODINGS = ["latin-1", "utf-8", "cp1252"]


def read_csv_safe(path: Path) -> pd.DataFrame:
    for enc in ENCODINGS:
        try:
            return pd.read_csv(path, sep=";", encoding=enc, dtype=str)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    raise ValueError(f"Cannot read {path} with any encoding")


def find_csv(folder: Path) -> Path | None:
    for pattern in ["*.csv", "*.txt"]:
        files = sorted(folder.glob(pattern))
        if files:
            return files[0]
    return None


def normalize(s: str) -> str:
    return unidecode(str(s)).upper().strip()


def process_votacao_secao(year: int) -> pd.DataFrame | None:
    folder = DATA_RAW / f"votacao_secao_{year}"
    if not folder.exists():
        print(f"  [skip] {folder} not found")
        return None

    csv_file = find_csv(folder)
    if csv_file is None:
        print(f"  [skip] no CSV in {folder}")
        return None

    print(f"  Reading {csv_file.name} ...")
    df = read_csv_safe(csv_file)
    print(f"  Total rows: {len(df):,}")

    # Filter to Niterói
    mask = df["NM_MUNICIPIO"].apply(lambda x: normalize(str(x)) == normalize(MUNICIPIO))
    df_nit = df[mask].copy()
    print(f"  Niterói rows: {len(df_nit):,}")

    if df_nit.empty:
        return None

    df_nit["QT_VOTOS"] = pd.to_numeric(df_nit["QT_VOTOS"], errors="coerce").fillna(0).astype(int)
    df_nit["ano"] = year

    return df_nit


def extract_candidate_votes(df: pd.DataFrame, candidate: dict, year: int) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    name = candidate["name"]
    info = candidate.get("elections", {}).get(year)
    if info is None:
        return pd.DataFrame()

    # Match by name
    mask = df["NM_VOTAVEL"].apply(lambda x: normalize(name) in normalize(str(x)))

    # Also filter by cargo if specified
    if "cargo" in info and "DS_CARGO" in df.columns:
        cargo_norm = normalize(info["cargo"])
        cargo_mask = df["DS_CARGO"].apply(lambda x: cargo_norm in normalize(str(x)))
        mask = mask & cargo_mask

    result = df[mask].copy()
    if not result.empty:
        result = result.assign(candidato=name)
    return result


def extract_party_votes(df: pd.DataFrame, party: str, year: int) -> pd.DataFrame:
    """Extract all votes for a party: legenda + all candidates whose NR_VOTAVEL starts with party number."""
    if df is None or df.empty:
        return pd.DataFrame()

    party_nr = PARTY_NUMBERS.get(party)
    if party_nr is None:
        print(f"  [warn] Unknown party number for {party}")
        return pd.DataFrame()

    mask = df["NR_VOTAVEL"].astype(str).str.startswith(party_nr)
    result = df[mask].copy()
    if not result.empty:
        result = result.assign(partido_filtro=party)
    return result


def aggregate_by_secao(df: pd.DataFrame, label: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    group_cols = ["ano", "NR_ZONA", "NR_SECAO"]
    if "NR_TURNO" in df.columns:
        group_cols.append("NR_TURNO")

    agg = df.groupby(group_cols, as_index=False)["QT_VOTOS"].sum()
    agg["label"] = label

    # Also capture polling place info if available (2022+)
    if "NR_LOCAL_VOTACAO" in df.columns:
        local_info = df.drop_duplicates(subset=["NR_ZONA", "NR_SECAO"])[
            ["NR_ZONA", "NR_SECAO"] +
            [c for c in ["NR_LOCAL_VOTACAO", "NM_LOCAL_VOTACAO", "DS_LOCAL_VOTACAO_ENDERECO"] if c in df.columns]
        ]
        agg = agg.merge(local_info, on=["NR_ZONA", "NR_SECAO"], how="left")

    return agg


def save_all_niteroi_raw(dfs: list[pd.DataFrame]):
    """Save a summary of all Niterói voting data with unique candidates per year."""
    if not dfs:
        return

    summary_rows = []
    for df in dfs:
        year = df["ano"].iloc[0]
        for cargo in df["DS_CARGO"].unique():
            cargo_df = df[df["DS_CARGO"] == cargo]
            # Get unique candidates (exclude special votes like nulo/branco)
            candidates = cargo_df.groupby(["NR_VOTAVEL", "NM_VOTAVEL"], as_index=False)["QT_VOTOS"].sum()
            candidates = candidates.sort_values("QT_VOTOS", ascending=False)
            top = candidates.head(3)
            summary_rows.append({
                "ano": year,
                "cargo": cargo,
                "total_votos": cargo_df["QT_VOTOS"].sum(),
                "n_candidatos": len(candidates),
                "top1": f"{top.iloc[0]['NM_VOTAVEL']} ({top.iloc[0]['QT_VOTOS']:,})" if len(top) > 0 else "",
                "top2": f"{top.iloc[1]['NM_VOTAVEL']} ({top.iloc[1]['QT_VOTOS']:,})" if len(top) > 1 else "",
                "top3": f"{top.iloc[2]['NM_VOTAVEL']} ({top.iloc[2]['QT_VOTOS']:,})" if len(top) > 2 else "",
            })

    pd.DataFrame(summary_rows).to_csv(DATA_PROCESSED / "niteroi_summary.csv", index=False)
    print(f"\nSaved niteroi_summary.csv")


def merge_year(path: Path, new_rows: pd.DataFrame, year: int) -> pd.DataFrame:
    """Idempotent per-year merge: drop any existing rows for `year`, append new, return."""
    if path.exists():
        existing = pd.read_csv(path, dtype=str)
        existing["ano"] = pd.to_numeric(existing["ano"], errors="coerce").astype("Int64")
        existing = existing[existing["ano"] != year]
        combined = pd.concat([existing, new_rows], ignore_index=True)
    else:
        combined = new_rows
    return combined


def main():
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    # --year N: process only that year, merge into existing output CSVs.
    # Default: process all ALL_YEARS and overwrite (full-rebuild mode).
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=None,
                        help="Process only this year, merge into existing CSVs (memory-safe, incremental)")
    args = parser.parse_args()

    years = [args.year] if args.year is not None else ALL_YEARS
    incremental = args.year is not None

    all_hugo = []
    all_felipe = []
    all_psd = []
    all_raw = []

    for year in years:
        print(f"\n=== {year} ===")
        df = process_votacao_secao(year)
        if df is None:
            continue

        if not incremental:
            all_raw.append(df)

        # Hugo Leal
        hugo = extract_candidate_votes(df, HUGO_LEAL, year)
        if not hugo.empty:
            agg = aggregate_by_secao(hugo, "HUGO LEAL")
            all_hugo.append(agg)
            print(f"  Hugo Leal: {agg['QT_VOTOS'].sum():,} votes in {len(agg)} seções")
        else:
            print(f"  Hugo Leal: not found in {year}")

        # Felipe Peixoto
        felipe = extract_candidate_votes(df, FELIPE_PEIXOTO, year)
        if not felipe.empty:
            agg = aggregate_by_secao(felipe, "FELIPE PEIXOTO")
            all_felipe.append(agg)
            print(f"  Felipe Peixoto: {agg['QT_VOTOS'].sum():,} votes in {len(agg)} seções")
        else:
            print(f"  Felipe Peixoto: not found in {year}")

        # PSD party (all candidates + legenda)
        psd = extract_party_votes(df, PARTY, year)
        if not psd.empty:
            agg = aggregate_by_secao(psd, "PSD")
            all_psd.append(agg)
            print(f"  PSD total: {agg['QT_VOTOS'].sum():,} votes in {len(agg)} seções")
        else:
            print(f"  PSD: not found in {year}")

        # Release the big raw df before next iteration
        del df
        if incremental:
            # ponytail: in incremental mode we merge-and-save per year
            if all_hugo:
                out = merge_year(DATA_PROCESSED / "hugo_leal_by_secao.csv", all_hugo[-1], year)
                out.to_csv(DATA_PROCESSED / "hugo_leal_by_secao.csv", index=False)
                print(f"  Merged into hugo_leal_by_secao.csv ({len(out)} rows total)")
            if all_felipe:
                out = merge_year(DATA_PROCESSED / "felipe_peixoto_by_secao.csv", all_felipe[-1], year)
                out.to_csv(DATA_PROCESSED / "felipe_peixoto_by_secao.csv", index=False)
                print(f"  Merged into felipe_peixoto_by_secao.csv ({len(out)} rows total)")
            if all_psd:
                out = merge_year(DATA_PROCESSED / "psd_by_secao.csv", all_psd[-1], year)
                out.to_csv(DATA_PROCESSED / "psd_by_secao.csv", index=False)
                print(f"  Merged into psd_by_secao.csv ({len(out)} rows total)")

    # Full-rebuild mode: write consolidated CSVs after loop
    if not incremental:
        if all_hugo:
            out = pd.concat(all_hugo, ignore_index=True)
            out.to_csv(DATA_PROCESSED / "hugo_leal_by_secao.csv", index=False)
            print(f"\nSaved hugo_leal_by_secao.csv ({len(out)} rows)")

        if all_felipe:
            out = pd.concat(all_felipe, ignore_index=True)
            out.to_csv(DATA_PROCESSED / "felipe_peixoto_by_secao.csv", index=False)
            print(f"Saved felipe_peixoto_by_secao.csv ({len(out)} rows)")

        if all_psd:
            out = pd.concat(all_psd, ignore_index=True)
            out.to_csv(DATA_PROCESSED / "psd_by_secao.csv", index=False)
            print(f"Saved psd_by_secao.csv ({len(out)} rows)")

        save_all_niteroi_raw(all_raw)

    print("\nDone.")


if __name__ == "__main__":
    main()
