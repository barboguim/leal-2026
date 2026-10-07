import pandas as pd

from conftest import load_script

bg = load_script("_build_geojson", "05_build_geojson.py")


def test_add_cargo_column_maps_from_config_by_year():
    by_local = pd.DataFrame([
        {"ano": 2022, "nr_local": "1", "QT_VOTOS": 50},
        {"ano": 2014, "nr_local": "1", "QT_VOTOS": 30},
    ])
    result = bg.add_cargo_column(by_local, "hugo_leal")
    assert list(result["cargo"]) == ["DEPUTADO FEDERAL", "DEPUTADO FEDERAL"]


def test_add_cargo_column_handles_felipes_varying_cargo():
    by_local = pd.DataFrame([
        {"ano": 2012, "nr_local": "1", "QT_VOTOS": 50},
        {"ano": 2022, "nr_local": "1", "QT_VOTOS": 30},
    ])
    result = bg.add_cargo_column(by_local, "felipe_peixoto")
    assert list(result["cargo"]) == ["PREFEITO", "DEPUTADO FEDERAL"]


def test_add_cargo_column_is_noop_for_psd():
    by_local = pd.DataFrame([{"ano": 2022, "nr_local": "1", "QT_VOTOS": 500}])
    result = bg.add_cargo_column(by_local, "psd")
    assert "cargo" not in result.columns
