import json

import pandas as pd

from conftest import load_script

pu = load_script("_pipeline_utils", "_pipeline_utils.py")


def test_normalize_strips_accents_and_uppercases():
    assert pu.normalize("hugo leal") == "HUGO LEAL"
    assert pu.normalize("Niterói") == "NITEROI"


def test_clean_id_strips_trailing_float_suffix():
    assert pu.clean_id("1058.0") == "1058"
    assert pu.clean_id("1058") == "1058"
    assert pu.clean_id(None) == ""


def test_rebuild_data_js_writes_only_existing_layers(tmp_path):
    data_geo = tmp_path / "geo"
    data_geo.mkdir()
    app_dir = tmp_path / "app"
    (data_geo / "hugo_leal.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": []}), encoding="utf-8"
    )

    pu.rebuild_data_js(data_geo, app_dir, layers=["hugo_leal", "felipe_peixoto"])

    data_js = (app_dir / "data.js").read_text(encoding="utf-8")
    assert data_js.startswith("const DATA = ")
    assert '"hugo_leal"' in data_js
    assert "felipe_peixoto" not in data_js


def test_election_type_classifies_municipal_and_geral_years():
    assert pu.election_type(2012) == "Municipal"
    assert pu.election_type(2022) == "Geral"


def test_download_and_extract_skips_when_already_extracted(tmp_path):
    dest = tmp_path / "already_here"
    dest.mkdir()
    (dest / "existing.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    # No network call should happen — if it tried, this would fail on the
    # fake URL. skip path returns True without touching the network.
    assert pu.download_and_extract("http://example.invalid/x.zip", dest, "test") is True


def test_load_local_info_reads_and_cleans_locais_csv(tmp_path):
    geo = tmp_path / "geo"
    geo.mkdir()
    (geo / "locais_votacao_niteroi.csv").write_text(
        "nr_local,nm_local,bairro,lat,lon\n"
        "1015.0,Escola Teste,Icarai,-22.9,-43.1\n",
        encoding="utf-8",
    )
    result = pu.load_local_info(geo)
    assert list(result["nr_local"]) == ["1015"]
    assert result.iloc[0]["lat"] == -22.9


def test_load_local_info_missing_file_returns_empty_frame(tmp_path):
    result = pu.load_local_info(tmp_path / "nope")
    assert result.empty
    assert list(result.columns) == ["nr_local", "nm_local", "bairro", "lat", "lon"]


def test_build_section_id_concatenates_zona_and_secao():
    df = pd.DataFrame({"NR_ZONA": ["113", "114"], "NR_SECAO": ["1", "22"]})
    result = pu.build_section_id(df)
    assert list(result) == ["113-1", "114-22"]


def test_section_local_lookup_dedupes_by_section_id():
    roster = pd.DataFrame({
        "ano": [2022, 2022, 2020],
        "section_id": ["113-1", "113-1", "113-1"],
        "nr_local": ["1015", "1015", "1099"],
    })
    result = pu.section_local_lookup(roster, 2022)
    assert result == {"113-1": "1015"}


def test_json_value_handles_nan_bool_float_int():
    assert pu.json_value(float("nan")) is None
    assert pu.json_value(True) is True
    assert pu.json_value(3.0) == 3
    assert pu.json_value(3.5) == 3.5
    assert pu.json_value(7) == 7


def test_to_geojson_drops_rows_missing_coordinates():
    df = pd.DataFrame([
        {"nr_local": "1", "lat": -22.9, "lon": -43.1, "total": 5},
        {"nr_local": "2", "lat": None, "lon": -43.1, "total": 9},
    ])
    result = pu.to_geojson(df, "test_layer")
    assert len(result["features"]) == 1
    assert result["features"][0]["properties"]["nr_local"] == "1"
    assert "lat" not in result["features"][0]["properties"]
