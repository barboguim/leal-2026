"""Shared TSE CSV reading helpers used by the LEAL data pipeline scripts."""

import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm
from unidecode import unidecode

ENCODINGS = ["latin-1", "utf-8", "cp1252"]
CHUNKSIZE = 200_000


def normalize(value: str) -> str:
    return unidecode(str(value)).upper().strip()


def election_type(year: int) -> str:
    return "Municipal" if year % 4 == 0 else "Geral"


def clean_id(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().strip('"')
    if text.endswith(".0"):
        text = text[:-2]
    return text


def clean_id_series(series: pd.Series) -> pd.Series:
    return series.map(clean_id)


def find_csv(folder: Path) -> Path | None:
    for pattern in ("*.csv", "*.txt"):
        files = sorted(folder.glob(pattern))
        if files:
            return files[0]
    return None


def read_csv_safe(path: Path, **kwargs) -> pd.DataFrame:
    for enc in ENCODINGS:
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    raise ValueError(f"Cannot read {path} with any configured encoding")


def read_tse_csv_safe(path: Path, **kwargs) -> pd.DataFrame:
    return read_csv_safe(path, sep=";", dtype=str, **kwargs)


def read_tse_chunks_safe(path: Path, **kwargs):
    last_error = None
    for enc in ENCODINGS:
        try:
            reader = pd.read_csv(
                path,
                sep=";",
                encoding=enc,
                dtype=str,
                chunksize=CHUNKSIZE,
                **kwargs,
            )
            for chunk in reader:
                yield chunk
            return
        except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as exc:
            last_error = exc
            continue
    raise ValueError(f"Cannot read {path} in chunks") from last_error


APP_GEOJSON_LAYERS = ["hugo_leal", "hugo_leal_secao", "felipe_peixoto", "psd", "vote_deltas", "voter_profile"]


def rebuild_data_js(data_geo: Path, app_dir: Path, layers: list[str] = APP_GEOJSON_LAYERS) -> None:
    all_data = {}
    for name in layers:
        path = data_geo / f"{name}.geojson"
        if path.exists():
            all_data[name] = json.loads(path.read_text(encoding="utf-8"))

    app_dir.mkdir(exist_ok=True)
    data_js = app_dir / "data.js"
    data_js.write_text(
        "const DATA = " + json.dumps(all_data, ensure_ascii=False, separators=(",", ":")) + ";",
        encoding="utf-8",
    )
    print("  Rebuilt app/data.js")


DOWNLOAD_TIMEOUT = 120
DOWNLOAD_CHUNK = 8192


def download_and_extract(url: str, dest: Path, label: str) -> bool:
    if any(dest.glob("*.csv")) or any(dest.glob("*.txt")):
        print(f"  [skip] {label} — already extracted")
        return True

    dest.mkdir(parents=True, exist_ok=True)
    print(f"  [GET]  {label}")
    print(f"         {url}")

    try:
        resp = requests.get(url, timeout=DOWNLOAD_TIMEOUT, stream=True)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [FAIL] {e}")
        return False

    total = int(resp.headers.get("content-length", 0))
    buf = io.BytesIO()
    with tqdm(total=total, unit="B", unit_scale=True, desc=label, leave=False) as bar:
        for chunk in resp.iter_content(DOWNLOAD_CHUNK):
            buf.write(chunk)
            bar.update(len(chunk))

    buf.seek(0)
    try:
        with zipfile.ZipFile(buf) as zf:
            zf.extractall(dest)
        print(f"  [OK]   {len(list(dest.iterdir()))} files")
    except zipfile.BadZipFile:
        print(f"  [FAIL] bad zip")
        return False
    return True


def load_local_info(data_geo: Path) -> pd.DataFrame:
    path = data_geo / "locais_votacao_niteroi.csv"
    if not path.exists():
        print("  [warn] locais_votacao_niteroi.csv not found; GeoJSON will be empty")
        return pd.DataFrame(columns=["nr_local", "nm_local", "bairro", "lat", "lon"])

    locais = pd.read_csv(path, dtype=str)
    locais["nr_local"] = clean_id_series(locais["nr_local"])
    if "nr_zona" in locais.columns:
        locais["nr_zona"] = clean_id_series(locais["nr_zona"])
    for col in ("lat", "lon"):
        locais[col] = pd.to_numeric(locais[col], errors="coerce")

    keep = [c for c in ("nr_zona", "nr_local", "nm_local", "bairro", "lat", "lon") if c in locais.columns]
    dedup_cols = ["nr_zona", "nr_local"] if "nr_zona" in locais.columns else ["nr_local"]
    locais = locais[keep].drop_duplicates(subset=dedup_cols).reset_index(drop=True)
    print(f"  Loaded locais_votacao_niteroi.csv: {len(locais):,} locais")
    return locais


def build_section_id(df: pd.DataFrame) -> pd.Series:
    return clean_id_series(df["NR_ZONA"]) + "-" + clean_id_series(df["NR_SECAO"])


def load_section_roster_from_raw(year: int, data_raw: Path, municipio: str) -> pd.DataFrame:
    folder = data_raw / f"votacao_secao_{year}"
    csv_file = find_csv(folder)
    if csv_file is None:
        return pd.DataFrame()

    header = read_tse_csv_safe(csv_file, nrows=0)
    required = ["NM_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO"]
    if any(col not in header.columns for col in required):
        return pd.DataFrame()

    pieces = []
    for chunk in read_tse_chunks_safe(csv_file, usecols=required):
        mask = chunk["NM_MUNICIPIO"].apply(lambda x: normalize(x) == normalize(municipio))
        nit = chunk.loc[mask, ["NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO"]].copy()
        if nit.empty:
            continue
        nit["ano"] = year
        nit["NR_ZONA"] = clean_id_series(nit["NR_ZONA"])
        nit["NR_SECAO"] = clean_id_series(nit["NR_SECAO"])
        nit["nr_local"] = clean_id_series(nit["NR_LOCAL_VOTACAO"])
        nit["section_id"] = build_section_id(nit)
        pieces.append(nit[["ano", "NR_ZONA", "NR_SECAO", "section_id", "nr_local"]].drop_duplicates())

    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, ignore_index=True).drop_duplicates()


def load_section_roster_from_votes(year: int, votes_by_secao: dict[str, pd.DataFrame]) -> pd.DataFrame:
    pieces = []
    for df in votes_by_secao.values():
        if df.empty:
            continue
        sub = df[df["ano"] == year]
        if sub.empty:
            continue
        pieces.append(sub[["ano", "NR_ZONA", "NR_SECAO", "section_id", "nr_local"]].drop_duplicates())
    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, ignore_index=True).drop_duplicates()


def load_section_roster(
    votes_by_secao: dict[str, pd.DataFrame], all_years, data_raw: Path, municipio: str
) -> pd.DataFrame:
    all_rows = []
    for year in sorted(all_years):
        print(f"  Reading section roster {year} ...")
        roster = load_section_roster_from_raw(year, data_raw, municipio)
        if roster.empty:
            print(f"    [fallback] using processed vote rows for {year}")
            roster = load_section_roster_from_votes(year, votes_by_secao)
        print(f"    {len(roster):,} section/local rows")
        if not roster.empty:
            all_rows.append(roster)
    if not all_rows:
        return pd.DataFrame(columns=["ano", "NR_ZONA", "NR_SECAO", "section_id", "nr_local"])
    return pd.concat(all_rows, ignore_index=True).drop_duplicates()


def section_local_lookup(roster: pd.DataFrame, year: int) -> dict[str, str]:
    sub = roster[roster["ano"] == year]
    deduped = sub.drop_duplicates(subset=["section_id"])
    return dict(zip(deduped["section_id"], deduped["nr_local"]))


def json_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return round(value, 6)
    if isinstance(value, int):
        return value
    return value


def to_geojson(df: pd.DataFrame, layer_name: str) -> dict:
    features = []
    if df.empty:
        return {"type": "FeatureCollection", "name": layer_name, "features": features}

    for _, row in df.dropna(subset=["lat", "lon"]).iterrows():
        props = {
            key: json_value(value)
            for key, value in row.items()
            if key not in ("lat", "lon")
        }
        features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row["lon"]), float(row["lat"])],
                },
            }
        )
    return {"type": "FeatureCollection", "name": layer_name, "features": features}
