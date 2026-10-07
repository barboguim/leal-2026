import pandas as pd

from conftest import load_script

vp = load_script("_voter_profile_geojson", "09_voter_profile_geojson.py")


def make_profile_row(ano, zona, secao, **overrides):
    row = {
        "ano": ano, "NR_ZONA": zona, "NR_SECAO": secao, "total_eleitores": 100,
        "gen__feminino": 55, "gen__masculino": 44, "gen__nao informado": 1,
        "fai__16 anos": 2, "fai__17 anos": 2, "fai__18 anos": 2, "fai__19 anos": 2,
        "fai__20 anos": 2, "fai__21 a 24 anos": 5,
        "fai__25 a 29 anos": 5, "fai__30 a 34 anos": 5, "fai__35 a 39 anos": 5,
        "fai__40 a 44 anos": 5, "fai__45 a 49 anos": 5, "fai__50 a 54 anos": 5, "fai__55 a 59 anos": 5,
        "fai__60 a 64 anos": 5, "fai__65 a 69 anos": 5, "fai__70 a 74 anos": 5,
        "fai__75 a 79 anos": 5, "fai__80 a 84 anos": 5, "fai__85 a 89 anos": 5,
        "fai__90 a 94 anos": 5, "fai__95 a 99 anos": 5, "fai__100 anos ou mais": 4,
        "fai__invalido": 0, "fai__invalida": 0,
        "gra__analfabeto": 5, "gra__le e escreve": 5,
        "gra__ensino fundamental completo": 10, "gra__ensino fundamental incompleto": 10,
        "gra__ensino medio completo": 30, "gra__ensino medio incompleto": 10,
        "gra__superior completo": 20, "gra__superior incompleto": 9,
        "gra__nao informado": 1,
    }
    row.update(overrides)
    return row


def make_roster_row(ano, zona, secao, nr_local):
    return {"ano": ano, "NR_ZONA": zona, "NR_SECAO": secao, "section_id": f"{zona}-{secao}", "nr_local": nr_local}


def test_aggregate_profile_to_local_sums_raw_counts_across_secoes():
    profile = pd.DataFrame([
        make_profile_row(2022, "113", "1"),
        make_profile_row(2022, "113", "2"),
    ])
    roster = pd.DataFrame([
        make_roster_row(2022, "113", "1", "1015"),
        make_roster_row(2022, "113", "2", "1015"),
    ])
    result = vp.aggregate_profile_to_local(profile, roster)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["ano"] == 2022
    assert row["nr_local"] == "1015"
    assert row["total_eleitores"] == 200
    assert row["gen__feminino"] == 110


def test_aggregate_profile_to_local_keeps_different_locais_separate():
    profile = pd.DataFrame([
        make_profile_row(2022, "113", "1"),
        make_profile_row(2022, "114", "5"),
    ])
    roster = pd.DataFrame([
        make_roster_row(2022, "113", "1", "1015"),
        make_roster_row(2022, "114", "5", "1099"),
    ])
    result = vp.aggregate_profile_to_local(profile, roster)
    assert sorted(result["nr_local"]) == ["1015", "1099"]


def test_aggregate_profile_to_local_handles_int_zona_secao_against_str_roster():
    # Regression: pd.read_csv infers NR_ZONA/NR_SECAO as int64 from the real
    # voter_profile_by_secao.csv, but the roster (via clean_id_series) always
    # carries them as str. main() casts profile's columns to str before
    # calling this function, but the function itself should tolerate mixed
    # int/str inputs on the merge keys rather than raising a pandas dtype
    # ValueError, since a future caller might forget the cast.
    profile = pd.DataFrame([make_profile_row(2022, 113, 1)])
    roster = pd.DataFrame([make_roster_row(2022, "113", "1", "1015")])
    result = vp.aggregate_profile_to_local(profile, roster)
    assert len(result) == 1
    assert result.iloc[0]["nr_local"] == "1015"


def test_aggregate_profile_to_local_empty_inputs_return_empty_frame():
    result = vp.aggregate_profile_to_local(pd.DataFrame(), pd.DataFrame())
    assert result.empty
    assert "total_eleitores" in result.columns


def test_compute_shares_gender_sums_to_100():
    grouped = pd.DataFrame([{
        "ano": 2022, "nr_local": "1015", "total_eleitores": 100,
        "gen__feminino": 55, "gen__masculino": 44, "gen__nao informado": 1,
        "fai__16 anos": 0, "fai__17 anos": 0, "fai__18 anos": 0, "fai__19 anos": 0,
        "fai__20 anos": 0, "fai__21 a 24 anos": 0, "fai__25 a 29 anos": 0, "fai__30 a 34 anos": 0,
        "fai__35 a 39 anos": 0, "fai__40 a 44 anos": 0, "fai__45 a 49 anos": 0, "fai__50 a 54 anos": 0,
        "fai__55 a 59 anos": 0, "fai__60 a 64 anos": 0, "fai__65 a 69 anos": 0, "fai__70 a 74 anos": 0,
        "fai__75 a 79 anos": 0, "fai__80 a 84 anos": 0, "fai__85 a 89 anos": 0, "fai__90 a 94 anos": 0,
        "fai__95 a 99 anos": 0, "fai__100 anos ou mais": 0, "fai__invalido": 0, "fai__invalida": 0,
        "gra__analfabeto": 0, "gra__le e escreve": 0, "gra__ensino fundamental completo": 0,
        "gra__ensino fundamental incompleto": 0, "gra__ensino medio completo": 0,
        "gra__ensino medio incompleto": 0, "gra__superior completo": 0, "gra__superior incompleto": 0,
        "gra__nao informado": 0,
    }])
    result = vp.compute_shares(grouped)
    assert result.iloc[0]["pct_mulheres"] == 55.0
    assert result.iloc[0]["pct_homens"] == 44.0
    assert result.iloc[0]["pct_genero_nao_informado"] == 1.0


def test_compute_shares_age_bands_collapse_correctly():
    profile = pd.DataFrame([make_profile_row(2022, "113", "1")])
    roster = pd.DataFrame([make_roster_row(2022, "113", "1", "1015")])
    grouped = vp.aggregate_profile_to_local(profile, roster)
    result = vp.compute_shares(grouped)
    row = result.iloc[0]
    # jovens: 2+2+2+2+2+5 = 15; adultos: 5*7 = 35; 60+: 5*8+4 = 44; total 100 -> 15%, 35%, 44%
    assert row["pct_jovens_16_24"] == 15.0
    assert row["pct_adultos_25_59"] == 35.0
    assert row["pct_60_mais"] == 44.0
    assert row["pct_idade_nao_informado"] == 0.0


def test_compute_shares_education_bands_include_le_e_escreve_in_ate_fundamental():
    profile = pd.DataFrame([make_profile_row(2022, "113", "1")])
    roster = pd.DataFrame([make_roster_row(2022, "113", "1", "1015")])
    grouped = vp.aggregate_profile_to_local(profile, roster)
    result = vp.compute_shares(grouped)
    row = result.iloc[0]
    # ate_fundamental: 5(analfabeto)+5(le_e_escreve)+10+10 = 30
    assert row["pct_ate_fundamental"] == 30.0
    assert row["pct_ensino_medio"] == 40.0
    assert row["pct_ensino_superior"] == 29.0
    assert row["pct_escolaridade_nao_informado"] == 1.0


def test_compute_shares_zero_total_eleitores_does_not_divide_by_zero():
    grouped = pd.DataFrame([{
        "ano": 2022, "nr_local": "1015", "total_eleitores": 0,
        "gen__feminino": 0, "gen__masculino": 0, "gen__nao informado": 0,
    }])
    result = vp.compute_shares(grouped)
    assert pd.isna(result.iloc[0]["pct_mulheres"])


def test_no_race_fields_anywhere_in_metric_columns():
    all_cols = [c for cols in vp.ALL_METRIC_COLS.values() for c in cols]
    assert not any(c.startswith("rac__") for c in all_cols)


def test_select_published_columns_drops_raw_intermediate_count_columns():
    # merged = shares (raw fai__/gen__/gra__ counts + pct_* shares) joined
    # with locais (nm_local, bairro, lat, lon) — same shape main() builds
    # right before calling to_geojson() for the standalone geojson.
    profile = pd.DataFrame([make_profile_row(2022, "113", "1")])
    roster = pd.DataFrame([make_roster_row(2022, "113", "1", "1015")])
    grouped = vp.aggregate_profile_to_local(profile, roster)
    shares = vp.compute_shares(grouped)
    shares["nm_local"] = "Escola Teste"
    shares["bairro"] = "Icarai"
    shares["lat"] = -22.9
    shares["lon"] = -43.1

    result = vp.select_published_columns(shares)

    expected = {"ano", "nr_local", "nm_local", "bairro", "lat", "lon", "total_eleitores"} | set(
        vp.ALL_METRIC_COLS.keys()
    )
    assert set(result.columns) == expected
    raw_cols = [c for cols in vp.ALL_METRIC_COLS.values() for c in cols]
    assert not any(c in result.columns for c in raw_cols)
