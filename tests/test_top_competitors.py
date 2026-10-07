import pandas as pd

from conftest import load_script

tc = load_script("_top_competitors", "07_top_competitors.py")


def make_df(rows):
    return pd.DataFrame(rows)


def test_is_real_candidate_excludes_blank_and_null():
    assert tc.is_real_candidate("95", "DEPUTADO FEDERAL") is False
    assert tc.is_real_candidate("96", "PREFEITO") is False


def test_is_real_candidate_excludes_legenda_for_proportional_cargo():
    assert tc.is_real_candidate("55", "DEPUTADO FEDERAL") is False


def test_is_real_candidate_keeps_two_digit_number_for_majoritarian_cargo():
    assert tc.is_real_candidate("55", "PREFEITO") is True


def test_is_real_candidate_keeps_full_candidate_number():
    assert tc.is_real_candidate("5512", "DEPUTADO FEDERAL") is True
    assert tc.is_real_candidate("10008", "DEPUTADO ESTADUAL") is True


def test_build_party_lookup_reads_legenda_rows_only():
    df = make_df([
        {"NR_VOTAVEL": "55", "NM_VOTAVEL": "Partido Social Democratico", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "5512", "NM_VOTAVEL": "FELIPE DOS SANTOS PEIXOTO", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "96", "NM_VOTAVEL": "VOTO NULO", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "12", "NM_VOTAVEL": "AXEL GRAEL", "cargo_norm": "PREFEITO"},
    ])
    lookup = tc.build_party_lookup(df)
    assert lookup == {"55": "Partido Social Democratico"}


def test_build_party_lookup_includes_vereador_legenda_rows():
    df = make_df([
        {"NR_VOTAVEL": "55", "NM_VOTAVEL": "Partido Social Democratico", "cargo_norm": "VEREADOR"},
        {"NR_VOTAVEL": "12", "NM_VOTAVEL": "AXEL GRAEL", "cargo_norm": "PREFEITO"},
    ])
    lookup = tc.build_party_lookup(df)
    assert lookup == {"55": "Partido Social Democratico"}


def test_build_party_lookup_excludes_placeholder_names_starting_with_hash():
    df = make_df([
        {"NR_VOTAVEL": "55", "NM_VOTAVEL": "#NULO#", "cargo_norm": "VEREADOR"},
        {"NR_VOTAVEL": "13", "NM_VOTAVEL": "Partido dos Trabalhadores", "cargo_norm": "DEPUTADO FEDERAL"},
    ])
    lookup = tc.build_party_lookup(df)
    assert lookup == {"13": "Partido dos Trabalhadores"}


def test_party_for_falls_back_to_number_when_unknown():
    assert tc.party_for("9012", {}) == "90"
    assert tc.party_for("5512", {"55": "PSD"}) == "PSD"


def test_rank_top3_by_local_excludes_named_people_and_sorts_by_votes():
    df = make_df([
        {"NR_VOTAVEL": "7733", "NM_VOTAVEL": "AUREO RIBEIRO", "QT_VOTOS": 30, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "5555", "NM_VOTAVEL": "HUGO LEAL", "QT_VOTOS": 100, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "1000", "NM_VOTAVEL": "MARCELO CRIVELLA", "QT_VOTOS": 20, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "1006", "NM_VOTAVEL": "ANTONIO RIBEIRO", "QT_VOTOS": 10, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "95", "NM_VOTAVEL": "VOTO BRANCO", "QT_VOTOS": 5, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
    ])
    result = tc.rank_top3_by_local(df, {"HUGO LEAL"}, {})
    assert list(result.keys()) == ["1015"]
    names = [c["nome"] for c in result["1015"]]
    assert names == ["AUREO RIBEIRO", "MARCELO CRIVELLA", "ANTONIO RIBEIRO"]
    assert "HUGO LEAL" not in names
    assert "VOTO BRANCO" not in names


def test_rank_top3_by_local_caps_at_three():
    rows = [
        {"NR_VOTAVEL": str(1000 + i), "NM_VOTAVEL": f"CAND {i}", "QT_VOTOS": 10 - i, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"}
        for i in range(5)
    ]
    result = tc.rank_top3_by_local(make_df(rows), set(), {})
    assert len(result["1015"]) == 3


def test_rank_top3_by_local_returns_empty_dict_when_no_candidates_survive():
    df = make_df([
        {"NR_VOTAVEL": "5555", "NM_VOTAVEL": "HUGO LEAL", "QT_VOTOS": 100, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
    ])
    assert tc.rank_top3_by_local(df, {"HUGO LEAL"}, {}) == {}


def test_top3_fields_pads_missing_slots_with_none():
    fields = tc.top3_fields([{"nome": "A", "partido": "PSD", "votos": 10}])
    assert fields["top1_nome"] == "A"
    assert fields["top1_partido"] == "PSD"
    assert fields["top1_votos"] == 10
    assert fields["top2_nome"] is None
    assert fields["top2_partido"] is None
    assert fields["top2_votos"] is None
    assert fields["top3_nome"] is None


def test_top3_fields_empty_list_is_all_none():
    fields = tc.top3_fields([])
    assert all(v is None for v in fields.values())
    assert set(fields.keys()) == {
        "top1_nome", "top1_partido", "top1_votos",
        "top2_nome", "top2_partido", "top2_votos",
        "top3_nome", "top3_partido", "top3_votos",
    }


def write_fixture_year(raw_dir, year, rows):
    header = "NM_MUNICIPIO;DS_CARGO;NR_VOTAVEL;NM_VOTAVEL;QT_VOTOS;NR_LOCAL_VOTACAO\n"
    folder = raw_dir / f"votacao_secao_{year}"
    folder.mkdir(parents=True)
    lines = [header] + [";".join(row) + "\n" for row in rows]
    (folder / f"votacao_secao_{year}_RJ.csv").write_text("".join(lines), encoding="utf-8")


def test_shared_cargo_year_produces_one_ranking_reused_by_both(tmp_path, monkeypatch):
    write_fixture_year(tmp_path, 2022, [
        ['"NITEROI"', '"Deputado Federal"', '"5555"', '"HUGO LEAL"', '"100"', '"1015"'],
        ['"NITEROI"', '"Deputado Federal"', '"5512"', '"FELIPE DOS SANTOS PEIXOTO"', '"80"', '"1015"'],
        ['"NITEROI"', '"Deputado Federal"', '"1000"', '"MARCELO CRIVELLA"', '"50"', '"1015"'],
        ['"NITEROI"', '"Deputado Federal"', '"95"', '"VOTO BRANCO"', '"5"', '"1015"'],
        ['"OUTRA CIDADE"', '"Deputado Federal"', '"1000"', '"MARCELO CRIVELLA"', '"999"', '"1015"'],
    ])
    monkeypatch.setattr(tc, "DATA_RAW", tmp_path)

    all_rankings, _ = tc.build_all_rankings()
    hugo_rankings = tc.rankings_for_person("hugo_leal", all_rankings)
    felipe_rankings = tc.rankings_for_person("felipe_peixoto", all_rankings)

    assert hugo_rankings[2022] == felipe_rankings[2022]
    assert hugo_rankings[2022]["1015"][0]["nome"] == "MARCELO CRIVELLA"
    assert hugo_rankings[2022]["1015"][0]["votos"] == 50


def test_load_niteroi_year_returns_empty_frame_when_folder_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(tc, "DATA_RAW", tmp_path)
    assert tc.load_niteroi_year(1999).empty


def test_merge_top_competitors_matches_on_year_and_local():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {"ano": 2022, "nr_local": "1015"}, "geometry": None},
            {"type": "Feature", "properties": {"ano": 2018, "nr_local": "1015"}, "geometry": None},
        ],
    }
    rankings_by_year = {
        2022: {"1015": [{"nome": "MARCELO CRIVELLA", "partido": "PRTB", "votos": 50}]},
    }

    tc.merge_top_competitors(geojson, rankings_by_year, {})

    assert geojson["features"][0]["properties"]["top1_nome"] == "MARCELO CRIVELLA"
    assert geojson["features"][0]["properties"]["top1_votos"] == 50
    assert geojson["features"][1]["properties"]["top1_nome"] is None


def test_total_valid_votes_by_local_includes_all_real_candidates():
    df = make_df([
        {"NR_VOTAVEL": "5555", "NM_VOTAVEL": "HUGO LEAL", "QT_VOTOS": 100, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "7733", "NM_VOTAVEL": "AUREO RIBEIRO", "QT_VOTOS": 30, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "95", "NM_VOTAVEL": "VOTO BRANCO", "QT_VOTOS": 5, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
    ])
    result = tc.total_valid_votes_by_local(df)
    # Hugo's own votes count toward the total (unlike rank_top3_by_local, which excludes him)
    assert result["1015"] == 130
    # voto branco is excluded (not a real candidate)


def test_total_valid_votes_by_local_empty_for_empty_input():
    assert tc.total_valid_votes_by_local(make_df([])) == {}


def test_total_valid_votes_by_local_includes_legenda_votes():
    df = make_df([
        {"NR_VOTAVEL": "5555", "NM_VOTAVEL": "HUGO LEAL", "QT_VOTOS": 100, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
        # bare 2-digit party number on a proportional cargo = voto de legenda;
        # a valid vote under TSE's convention, just not a candidate row
        {"NR_VOTAVEL": "55", "NM_VOTAVEL": "PARTIDO SOCIAL DEMOCRATICO", "QT_VOTOS": 20, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "95", "NM_VOTAVEL": "VOTO BRANCO", "QT_VOTOS": 5, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
        {"NR_VOTAVEL": "96", "NM_VOTAVEL": "VOTO NULO", "QT_VOTOS": 3, "nr_local": "1015", "cargo_norm": "DEPUTADO FEDERAL"},
    ])
    result = tc.total_valid_votes_by_local(df)
    # legenda's 20 votes count toward the total; blank (95) and null (96) don't
    assert result["1015"] == 120
