"""Build vote-delta GeoJSON layers between paired elections.

Each candidate is paired with their own nearest-matching election cycle of
the same type (Geral or Municipal) — not necessarily the next calendar
year — per candidate, based on the candidacy matrix built by
08_candidacy_matrix.py. Pairs can skip years (e.g. 2010-2018) when a
candidate has a gap in that type.

The local-level layer is the main map layer.  The section-level layer is a
diagnostic companion that helps spot section moves between polling places.
"""

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

_script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_script_dir))
sys.path.insert(0, str(_script_dir.parent))
from config import ALL_YEARS, DATA_GEO, DATA_PROCESSED, DATA_RAW, MUNICIPIO, PSD_FOUNDING_YEAR
from _pipeline_utils import (
    build_section_id,
    clean_id_series,
    election_type,
    load_local_info,
    load_section_roster,
    rebuild_data_js as _rebuild_data_js,
    section_local_lookup,
    to_geojson,
)

DATASETS = {
    "hugo": {
        "path": DATA_PROCESSED / "hugo_leal_by_secao.csv",
        "label": "Hugo Leal",
    },
    "felipe": {
        "path": DATA_PROCESSED / "felipe_peixoto_by_secao.csv",
        "label": "Felipe Peixoto",
    },
    "psd": {
        "path": DATA_PROCESSED / "psd_by_secao.csv",
        "label": "PSD",
    },
}


def load_votes_by_secao() -> dict[str, pd.DataFrame]:
    votes = {}
    for key, meta in DATASETS.items():
        path = meta["path"]
        if not path.exists():
            print(f"  [skip] {path.name} not found")
            votes[key] = pd.DataFrame()
            continue

        df = pd.read_csv(path, dtype=str)
        if df.empty:
            votes[key] = df
            continue

        df = df.copy()
        df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
        df["QT_VOTOS"] = pd.to_numeric(df["QT_VOTOS"], errors="coerce").fillna(0).astype(int)
        for col in ("NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO"):
            if col in df.columns:
                df[col] = clean_id_series(df[col])
        if "NR_LOCAL_VOTACAO" not in df.columns:
            df["NR_LOCAL_VOTACAO"] = ""
        df["nr_local"] = clean_id_series(df["NR_LOCAL_VOTACAO"])
        df["nr_zona"] = clean_id_series(df["NR_ZONA"]) if "NR_ZONA" in df.columns else ""
        # Composite identity key: Niteroi's nr_local collides across zonas,
        # so (zona, nr_local) is the only correct identity. See script 05.
        df["local_key"] = df["nr_zona"].astype(str) + "-" + df["nr_local"].astype(str)
        df["section_id"] = build_section_id(df)
        votes[key] = df
        print(f"  Loaded {path.name}: {len(df):,} rows")
    return votes


def aggregate_local_votes(votes_by_secao: dict[str, pd.DataFrame]) -> dict[str, dict[tuple[int, str], int]]:
    """Keyed by (year, local_key) where local_key = f'{zona}-{nr_local}'."""
    lookups = {}
    for key, df in votes_by_secao.items():
        if df.empty:
            lookups[key] = {}
            continue
        grouped = (
            df[df["nr_local"] != ""]
            .groupby(["ano", "local_key"], as_index=False)["QT_VOTOS"]
            .sum()
        )
        lookups[key] = {
            (int(row["ano"]), row["local_key"]): int(row["QT_VOTOS"])
            for _, row in grouped.iterrows()
        }
    return lookups


def aggregate_section_votes(votes_by_secao: dict[str, pd.DataFrame]) -> dict[str, dict[tuple[int, str], int]]:
    lookups = {}
    for key, df in votes_by_secao.items():
        if df.empty:
            lookups[key] = {}
            continue
        grouped = df.groupby(["ano", "section_id"], as_index=False)["QT_VOTOS"].sum()
        lookups[key] = {
            (int(row["ano"]), row["section_id"]): int(row["QT_VOTOS"])
            for _, row in grouped.iterrows()
        }
    return lookups


def pct_delta(start: int, delta: int) -> float | None:
    if start == 0:
        return None
    return round((delta / start) * 100, 2)


def load_candidacy_matrix() -> pd.DataFrame:
    path = DATA_PROCESSED / "candidacy_matrix.csv"
    if not path.exists():
        return pd.DataFrame(columns=["candidate_key", "ano", "cargo", "tipo_eleicao", "partido", "situacao_candidatura"])
    df = pd.read_csv(path, dtype=str)
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce").astype("Int64")
    return df


def candidacy_lookup(matrix: pd.DataFrame) -> dict[tuple[str, int], dict]:
    lookup = {}
    for _, row in matrix.iterrows():
        if pd.isna(row["ano"]):
            continue
        lookup[(row["candidate_key"], int(row["ano"]))] = {"tipo_eleicao": row["tipo_eleicao"], "cargo": row["cargo"]}
    return lookup


def candidate_pairs_from_matrix(lookup: dict, candidate_key: str) -> list[tuple[int, int]]:
    years_by_type: dict[str, list[int]] = {}
    for (key, year), info in lookup.items():
        if key != candidate_key:
            continue
        years_by_type.setdefault(info["tipo_eleicao"], []).append(year)

    pairs = []
    for years in years_by_type.values():
        years = sorted(set(years))
        pairs.extend(zip(years[:-1], years[1:]))
    return sorted(set(pairs))


def all_candidate_pairs(lookup: dict) -> list[tuple[int, int]]:
    all_pairs: set[tuple[int, int]] = set()
    for candidate_key in DATASETS:
        all_pairs.update(candidate_pairs_from_matrix(lookup, candidate_key))
    return sorted(all_pairs)


def add_delta_fields(row: dict, get_votes, lookup: dict) -> None:
    start_year = row["ano_inicio"]
    end_year = row["ano_fim"]
    row["tipo_inicio"] = election_type(start_year)
    row["tipo_fim"] = election_type(end_year)
    row["tipo_par"] = f"{row['tipo_inicio']} -> {row['tipo_fim']}"

    for key in DATASETS:
        start_info = lookup.get((key, start_year))
        end_info = lookup.get((key, end_year))
        gated = (
            start_info is not None
            and end_info is not None
            and start_info["tipo_eleicao"] == end_info["tipo_eleicao"]
        )

        if not gated:
            row[f"votos_{key}_inicio"] = None
            row[f"votos_{key}_fim"] = None
            row[f"delta_{key}"] = None
            row[f"pct_delta_{key}"] = None
            if key == "psd" and start_info is None and start_year < PSD_FOUNDING_YEAR:
                row[f"candidacy_status_{key}"] = "partido_inexistente"
            elif key == "psd" and end_info is None and end_year < PSD_FOUNDING_YEAR:
                row[f"candidacy_status_{key}"] = "partido_inexistente"
            elif start_info is None and end_info is None:
                row[f"candidacy_status_{key}"] = "nao_concorreu"
            elif start_info is None:
                row[f"candidacy_status_{key}"] = "nao_concorreu_inicio"
            elif end_info is None:
                row[f"candidacy_status_{key}"] = "nao_concorreu_fim"
            else:
                row[f"candidacy_status_{key}"] = "tipo_incompativel"
            row[f"cargo_diferente_{key}"] = None
            continue

        start_votes = int(get_votes(key, start_year) or 0)
        end_votes = int(get_votes(key, end_year) or 0)
        delta = end_votes - start_votes
        row[f"votos_{key}_inicio"] = start_votes
        row[f"votos_{key}_fim"] = end_votes
        row[f"delta_{key}"] = delta
        row[f"pct_delta_{key}"] = pct_delta(start_votes, delta)
        row[f"candidacy_status_{key}"] = "concorreu"
        row[f"cargo_diferente_{key}"] = start_info["cargo"] != end_info["cargo"]

    row["map_delta"] = row["delta_hugo"]
    row["map_abs_delta"] = abs(row["delta_hugo"]) if row["delta_hugo"] is not None else None


def section_sets_by_local(roster: pd.DataFrame, year: int) -> dict[str, set[str]]:
    """Keyed by local_key (zona-nrlocal composite). Builds it on the fly
    from the roster's NR_ZONA + nr_local columns."""
    sub = roster[roster["ano"] == year].copy()
    sub["local_key"] = sub["NR_ZONA"].astype(str) + "-" + sub["nr_local"].astype(str)
    return {
        local_key: set(group["section_id"])
        for local_key, group in sub.groupby("local_key")
        if local_key and not local_key.startswith("-")
    }


def section_local_lookup_composite(roster: pd.DataFrame, year: int) -> dict[str, str]:
    """section_id -> local_key (zona-nrlocal). Composite replaces the
    nr_local-only lookup from _pipeline_utils."""
    sub = roster[roster["ano"] == year].copy()
    sub["local_key"] = sub["NR_ZONA"].astype(str) + "-" + sub["nr_local"].astype(str)
    deduped = sub.drop_duplicates(subset=["section_id"])
    return dict(zip(deduped["section_id"], deduped["local_key"]))


def movement_counts(roster: pd.DataFrame, start_year: int, end_year: int) -> tuple[Counter, Counter]:
    start_lookup = section_local_lookup_composite(roster, start_year)
    end_lookup = section_local_lookup_composite(roster, end_year)
    moved_in = Counter()
    moved_out = Counter()
    for section_id in set(start_lookup).intersection(end_lookup):
        start_local = start_lookup[section_id]
        end_local = end_lookup[section_id]
        if start_local and end_local and start_local != end_local:
            moved_out[start_local] += 1
            moved_in[end_local] += 1
    return moved_in, moved_out


def section_lineage(
    roster: pd.DataFrame, start_year: int, end_year: int, name_by_local: dict[str, str],
) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """For each local, enumerate the other locais its sections came from
    (received) and went to (sent). Each entry: {nr_local, nm_local, count,
    secoes: ["42", "43", ...]}. Only sections whose hosting nr_local actually
    changed between start_year and end_year are included — continuity is not
    a transfer. Pattern mirrors mobi-pleito-2026's `compute_secao_transfers`
    (same owner, sibling site)."""
    start_lookup = section_local_lookup_composite(roster, start_year)
    end_lookup = section_local_lookup_composite(roster, end_year)

    # Build raw per-pair transfer lists: (other_local_key, section_number).
    received_raw: dict[str, list[tuple[str, str]]] = {}
    sent_raw: dict[str, list[tuple[str, str]]] = {}
    for section_id, before_local in start_lookup.items():
        after_local = end_lookup.get(section_id)
        if not before_local or not after_local:
            continue
        if after_local == before_local:
            continue
        # section_id is "zona-secao"; we want just the secao number for display
        secao_part = section_id.split("-", 1)[1] if "-" in section_id else section_id
        sent_raw.setdefault(before_local, []).append((after_local, secao_part))
        received_raw.setdefault(after_local, []).append((before_local, secao_part))

    def summarize(transfers: list[tuple[str, str]]) -> list[dict]:
        groups: dict[str, list[str]] = {}
        for other_local_key, secao in transfers:
            groups.setdefault(other_local_key, []).append(secao)
        result = []
        for other_key, secs in sorted(groups.items(), key=lambda kv: -len(set(kv[1]))):
            # other_key = "zona-nrlocal"
            _zona, _nr = other_key.split("-", 1) if "-" in other_key else ("", other_key)
            result.append({
                "nr_zona": _zona,
                "nr_local": _nr,
                "nm_local": name_by_local.get(other_key, ""),
                "count": len(set(secs)),
                "secoes": sorted(set(secs), key=lambda s: (len(s), s)),
            })
        return result

    received = {local: summarize(items) for local, items in received_raw.items()}
    sent = {local: summarize(items) for local, items in sent_raw.items()}
    return received, sent


def local_churn_rows(
    roster: pd.DataFrame, start_year: int, end_year: int, name_by_local: dict[str, str] | None = None,
) -> dict[str, dict]:
    start_sets = section_sets_by_local(roster, start_year)
    end_sets = section_sets_by_local(roster, end_year)
    moved_in, moved_out = movement_counts(roster, start_year, end_year)
    received_lineage, sent_lineage = section_lineage(
        roster, start_year, end_year, name_by_local or {}
    )
    rows = {}

    for local_key in sorted(set(start_sets).union(end_sets)):
        start_sections = start_sets.get(local_key, set())
        end_sections = end_sets.get(local_key, set())
        common = start_sections.intersection(end_sections)
        added = end_sections - start_sections
        removed = start_sections - end_sections
        denom = max(len(start_sections), len(end_sections), 1)
        if start_sections and end_sections:
            status = "both"
        elif start_sections:
            status = "start_only"
        else:
            status = "end_only"

        recebidas = received_lineage.get(local_key, [])
        enviadas = sent_lineage.get(local_key, [])
        nr_zona, nr_local = local_key.split("-", 1) if "-" in local_key else ("", local_key)

        rows[local_key] = {
            "nr_zona": nr_zona,
            "nr_local": nr_local,
            "local_status": status,
            "secoes_inicio": len(start_sections),
            "secoes_fim": len(end_sections),
            "secoes_comuns": len(common),
            "secoes_adicionadas": len(added),
            "secoes_removidas": len(removed),
            "secoes_movidas_in": int(moved_in[local_key]),
            "secoes_movidas_out": int(moved_out[local_key]),
            "secao_churn": round((len(added) + len(removed)) / denom, 4),
            "secoes_recebidas": json.dumps(recebidas, ensure_ascii=False) if recebidas else None,
            "secoes_enviadas": json.dumps(enviadas, ensure_ascii=False) if enviadas else None,
        }
    return rows


def build_local_delta_frame(
    votes_by_secao: dict[str, pd.DataFrame],
    roster: pd.DataFrame,
    locais: pd.DataFrame,
    candidacy: dict,
) -> pd.DataFrame:
    vote_lookup = aggregate_local_votes(votes_by_secao)
    # locais now carries nr_zona; key info_lookup by local_key composite.
    locais = locais.copy()
    if "nr_zona" not in locais.columns:
        locais["nr_zona"] = ""
    locais["local_key"] = locais["nr_zona"].fillna("").astype(str) + "-" + locais["nr_local"].astype(str)
    info_lookup = locais.set_index("local_key").to_dict("index") if not locais.empty else {}
    name_by_local = {k: v.get("nm_local", "") for k, v in info_lookup.items()}
    rows = []

    for start_year, end_year in all_candidate_pairs(candidacy):
        pair = f"{start_year}-{end_year}"
        churn = local_churn_rows(roster, start_year, end_year, name_by_local)
        local_ids = set(churn)
        for lookup in vote_lookup.values():
            for year, local_key in lookup:
                if year in (start_year, end_year):
                    local_ids.add(local_key)

        for local_key in sorted(local_ids):
            info = info_lookup.get(local_key, {})
            nr_zona, nr_local_only = local_key.split("-", 1) if "-" in local_key else ("", local_key)
            row = {
                "pair": pair,
                "ano_inicio": start_year,
                "ano_fim": end_year,
                "nr_zona": nr_zona,
                "nr_local": nr_local_only,
                "nm_local": info.get("nm_local"),
                "bairro": info.get("bairro"),
                "lat": info.get("lat"),
                "lon": info.get("lon"),
                **{k: v for k, v in churn.get(local_key, {"local_status": "vote_data_only"}).items() if k not in ("nr_zona", "nr_local")},
            }

            def get_votes(key: str, year: int, lk=local_key) -> int:
                return vote_lookup[key].get((year, lk), 0)

            add_delta_fields(row, get_votes, candidacy)
            rows.append(row)

    return pd.DataFrame(rows)


def section_parts(section_id: str) -> tuple[str, str]:
    if "-" not in section_id:
        return section_id, ""
    return tuple(section_id.split("-", 1))


def build_section_delta_frame(
    votes_by_secao: dict[str, pd.DataFrame],
    roster: pd.DataFrame,
    locais: pd.DataFrame,
    candidacy: dict,
) -> pd.DataFrame:
    vote_lookup = aggregate_section_votes(votes_by_secao)
    locais = locais.copy()
    if "nr_zona" not in locais.columns:
        locais["nr_zona"] = ""
    locais["local_key"] = locais["nr_zona"].fillna("").astype(str) + "-" + locais["nr_local"].astype(str)
    info_lookup = locais.set_index("local_key").to_dict("index") if not locais.empty else {}
    # Use composite roster lookup; falls back to blank for missing sections.
    roster_by_year = {
        year: section_local_lookup_composite(roster, year)
        for year in sorted(int(y) for y in ALL_YEARS)
    }
    rows = []

    for start_year, end_year in all_candidate_pairs(candidacy):
        pair = f"{start_year}-{end_year}"
        start_sections = set(roster_by_year.get(start_year, {}))
        end_sections = set(roster_by_year.get(end_year, {}))
        section_ids = start_sections.union(end_sections)
        for lookup in vote_lookup.values():
            for year, section_id in lookup:
                if year in (start_year, end_year):
                    section_ids.add(section_id)

        for section_id in sorted(section_ids):
            zona, secao = section_parts(section_id)
            start_local = roster_by_year.get(start_year, {}).get(section_id, "")
            end_local = roster_by_year.get(end_year, {}).get(section_id, "")
            geom_local = end_local or start_local
            info = info_lookup.get(geom_local, {})

            if start_local and end_local:
                status = "both"
            elif start_local:
                status = "start_only"
            elif end_local:
                status = "end_only"
            else:
                status = "vote_data_only"

            row = {
                "pair": pair,
                "ano_inicio": start_year,
                "ano_fim": end_year,
                "NR_ZONA": zona,
                "NR_SECAO": secao,
                "section_id": section_id,
                "nr_local_inicio": start_local,
                "nr_local_fim": end_local,
                "nr_local": geom_local,
                "secao_status": status,
                "secao_moved": bool(start_local and end_local and start_local != end_local),
                "nm_local": info.get("nm_local"),
                "bairro": info.get("bairro"),
                "lat": info.get("lat"),
                "lon": info.get("lon"),
            }

            def get_votes(key: str, year: int) -> int:
                return vote_lookup[key].get((year, section_id), 0)

            add_delta_fields(row, get_votes, candidacy)
            rows.append(row)

    return pd.DataFrame(rows)


def write_geojson(df: pd.DataFrame, layer_name: str, path: Path) -> None:
    geojson = to_geojson(df, layer_name)
    path.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Saved {path.name}: {len(geojson['features']):,} features")




def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    DATA_GEO.mkdir(parents=True, exist_ok=True)

    print("Loading vote datasets ...")
    votes_by_secao = load_votes_by_secao()

    print("\nLoading polling-place coordinates ...")
    locais = load_local_info(DATA_GEO)

    print("\nBuilding section/local roster from raw vote files ...")
    roster = load_section_roster(votes_by_secao, ALL_YEARS, DATA_RAW, MUNICIPIO)

    print("\nLoading candidacy matrix ...")
    matrix = load_candidacy_matrix()
    candidacy = candidacy_lookup(matrix)
    if not candidacy:
        print("  [warn] candidacy_matrix.csv missing or empty — run scripts/08_candidacy_matrix.py first. All deltas will be gated to null.")

    print("\nComputing local deltas ...")
    local_deltas = build_local_delta_frame(votes_by_secao, roster, locais, candidacy)
    local_csv = DATA_PROCESSED / "vote_deltas_by_local.csv"
    local_deltas.to_csv(local_csv, index=False)
    print(f"  Saved {local_csv.name}: {len(local_deltas):,} rows")
    write_geojson(local_deltas, "vote_deltas", DATA_GEO / "vote_deltas.geojson")

    print("\nComputing section deltas ...")
    section_deltas = build_section_delta_frame(votes_by_secao, roster, locais, candidacy)
    section_csv = DATA_PROCESSED / "vote_deltas_by_secao.csv"
    section_deltas.to_csv(section_csv, index=False)
    print(f"  Saved {section_csv.name}: {len(section_deltas):,} rows")
    write_geojson(section_deltas, "vote_deltas_secao", DATA_GEO / "vote_deltas_secao.geojson")

    print("\nUpdating app bundle ...")
    _rebuild_data_js(DATA_GEO, DATA_GEO.parent.parent / "app")
    print("Done.")


if __name__ == "__main__":
    main()
