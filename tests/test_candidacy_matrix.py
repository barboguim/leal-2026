import pandas as pd

from conftest import load_script

cm = load_script("_candidacy_matrix", "08_candidacy_matrix.py")


def make_consulta_df(rows):
    return pd.DataFrame(rows)


def test_match_candidate_finds_exact_name_match():
    df = make_consulta_df([
        {"NM_CANDIDATO": "HUGO LEAL DA SILVA", "NM_URNA_CANDIDATO": "HUGO LEAL", "DS_CARGO": "DEPUTADO FEDERAL", "SG_PARTIDO": "PSD", "DS_SITUACAO_CANDIDATURA": "DEFERIDO"},
        {"NM_CANDIDATO": "OUTRO CANDIDATO", "NM_URNA_CANDIDATO": "OUTRO", "DS_CARGO": "PREFEITO", "SG_PARTIDO": "PSD", "DS_SITUACAO_CANDIDATURA": "DEFERIDO"},
    ])
    result = cm.match_candidate(df, "HUGO LEAL")
    assert len(result) == 1
    assert result.iloc[0]["DS_CARGO"] == "DEPUTADO FEDERAL"


def test_match_candidate_excludes_urna_name_only_collision():
    df = make_consulta_df([
        {"NM_CANDIDATO": "HUGO VIEIRA LEAL", "NM_URNA_CANDIDATO": "HUGO LEAL", "DS_CARGO": "VEREADOR", "SG_PARTIDO": "AVANTE", "DS_SITUACAO_CANDIDATURA": "APTO"},
    ])
    result = cm.match_candidate(df, "HUGO LEAL")
    assert result.empty


def test_match_candidate_returns_empty_when_no_match():
    df = make_consulta_df([
        {"NM_CANDIDATO": "OUTRO CANDIDATO", "NM_URNA_CANDIDATO": "OUTRO", "DS_CARGO": "PREFEITO", "SG_PARTIDO": "PSD", "DS_SITUACAO_CANDIDATURA": "DEFERIDO"},
    ])
    result = cm.match_candidate(df, "HUGO LEAL")
    assert result.empty


def test_build_psd_matrix_rows_derives_existence_from_psd_by_secao(tmp_path, monkeypatch):
    psd_csv = tmp_path / "psd_by_secao.csv"
    psd_csv.write_text(
        "ano,NR_ZONA,NR_SECAO,QT_VOTOS\n"
        "2012,1,1,100\n"
        "2016,1,1,50\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cm, "DATA_PROCESSED", tmp_path)

    rows = cm.build_psd_matrix_rows()
    years = {r["ano"] for r in rows}
    assert years == {2012, 2016}
    assert all(r["candidate_key"] == "psd" for r in rows)
    row_2012 = next(r for r in rows if r["ano"] == 2012)
    assert row_2012["tipo_eleicao"] == "Municipal"


def test_build_psd_matrix_rows_returns_empty_when_no_data(tmp_path, monkeypatch):
    monkeypatch.setattr(cm, "DATA_PROCESSED", tmp_path)
    assert cm.build_psd_matrix_rows() == []


def test_build_candidacy_matrix_combines_people_and_psd(monkeypatch):
    monkeypatch.setattr(cm, "build_person_matrix_rows", lambda key, person: [
        {"candidate_key": key, "ano": 2022, "cargo": "DEPUTADO FEDERAL", "tipo_eleicao": "Federal", "partido": "PSD", "situacao_candidatura": "DEFERIDO"},
    ])
    monkeypatch.setattr(cm, "build_psd_matrix_rows", lambda: [
        {"candidate_key": "psd", "ano": 2012, "cargo": "AGREGADO", "tipo_eleicao": "Municipal", "partido": "PSD", "situacao_candidatura": "PARTIDO_ATIVO"},
    ])

    matrix = cm.build_candidacy_matrix()

    assert set(matrix["candidate_key"]) == {"hugo", "felipe", "psd"}
    assert len(matrix[matrix["candidate_key"] == "hugo"]) == 1
    assert len(matrix[matrix["candidate_key"] == "felipe"]) == 1
    assert len(matrix[matrix["candidate_key"] == "psd"]) == 1


def write_psd_fixture_year(raw_dir, year, rows):
    header = "NM_MUNICIPIO;DS_CARGO;NR_VOTAVEL;NM_VOTAVEL;SG_PARTIDO;QT_VOTOS;NR_LOCAL_VOTACAO\n"
    folder = raw_dir / f"votacao_secao_{year}"
    folder.mkdir(parents=True)
    lines = [header] + [";".join(row) + "\n" for row in rows]
    (folder / f"votacao_secao_{year}_RJ.csv").write_text("".join(lines), encoding="utf-8")


def test_rank_psd_breakdown_ranks_across_cargos_by_votes():
    df = pd.DataFrame([
        {"NR_VOTAVEL": "5501", "NM_VOTAVEL": "CANDIDATO VEREADOR", "SG_PARTIDO": "PSD", "QT_VOTOS": 200, "nr_local": "1015", "cargo_norm": "VEREADOR"},
        {"NR_VOTAVEL": "55", "NM_VOTAVEL": "CANDIDATO PREFEITO", "SG_PARTIDO": "PSD", "QT_VOTOS": 900, "nr_local": "1015", "cargo_norm": "PREFEITO"},
        {"NR_VOTAVEL": "5502", "NM_VOTAVEL": "OUTRO VEREADOR", "SG_PARTIDO": "PSD", "QT_VOTOS": 50, "nr_local": "1015", "cargo_norm": "VEREADOR"},
    ])
    result = cm.rank_psd_breakdown_by_local(df)
    assert "1015" in result
    top = result["1015"]["top3"]
    assert top[0]["nome"] == "CANDIDATO PREFEITO"
    assert top[0]["cargo"] == "PREFEITO"
    assert result["1015"]["candidate_count"] == 3
    assert result["1015"]["total_por_cargo"] == {"PREFEITO": 900, "VEREADOR": 250}


def test_rank_psd_breakdown_returns_empty_dict_for_empty_input():
    assert cm.rank_psd_breakdown_by_local(pd.DataFrame()) == {}


def test_psd_breakdown_fields_shapes_output_for_merge():
    breakdown = {
        "top3": [
            {"nome": "CANDIDATO PREFEITO", "cargo": "PREFEITO", "votos": 900, "share": 45.0},
        ],
        "candidate_count": 3,
        "total_por_cargo": {"PREFEITO": 900, "VEREADOR": 250},
    }
    fields = cm.psd_breakdown_fields(breakdown)
    assert fields["psd_candidate_count"] == 3
    assert fields["psd_top1_nome"] == "CANDIDATO PREFEITO"
    assert fields["psd_top1_cargo"] == "PREFEITO"
    assert fields["psd_top1_votos"] == 900
    assert fields["psd_top1_share"] == 45.0
    assert fields["psd_top2_nome"] is None
    assert fields["psd_total_por_cargo"] == '{"PREFEITO": 900, "VEREADOR": 250}'


def test_load_niteroi_psd_year_excludes_proportional_legenda_but_keeps_majoritarian_bare_number(tmp_path, monkeypatch):
    # NM_MUNICIPIO is written without the accent (vs. config.MUNICIPIO="NITERÓI")
    # because the fixture file is UTF-8 but read_tse_chunks_safe always tries
    # latin-1 first (which never raises, so it never falls through) — same as
    # real TSE files, which are latin-1-encoded. normalize() strips accents
    # either way, so the unaccented spelling still matches.
    write_psd_fixture_year(tmp_path, 2012, [
        # Proportional cargos: bare party number is a voto de legenda -> excluded.
        ("NITEROI", "VEREADOR", "55", "PARTIDO SOCIAL DEMOCRATICO", "PSD", "100", "1015"),
        ("NITEROI", "VEREADOR", "55107", "CANDIDATO REAL", "PSD", "50", "1015"),
        ("NITEROI", "DEPUTADO FEDERAL", "55", "PARTIDO SOCIAL DEMOCRATICO", "PSD", "200", "1015"),
        # Majoritarian cargos: bare party number IS the real candidate -> kept.
        ("NITEROI", "PREFEITO", "55", "SERGIO ZVEITER", "PSD", "900", "1015"),
        ("NITEROI", "GOVERNADOR", "55", "ANTONIO PEDRO INDIO DA COSTA", "PSD", "625", "1015"),
    ])
    monkeypatch.setattr(cm, "DATA_RAW", tmp_path)

    df = cm.load_niteroi_psd_year(2012)

    assert "PARTIDO SOCIAL DEMOCRATICO" not in df["NM_VOTAVEL"].values
    assert "CANDIDATO REAL" in df["NM_VOTAVEL"].values
    deputado = df[df["cargo_norm"] == "DEPUTADO FEDERAL"]
    assert deputado.empty

    prefeito = df[df["cargo_norm"] == "PREFEITO"]
    assert list(prefeito["NR_VOTAVEL"]) == ["55"]
    assert list(prefeito["NM_VOTAVEL"]) == ["SERGIO ZVEITER"]

    governador = df[df["cargo_norm"] == "GOVERNADOR"]
    assert list(governador["NR_VOTAVEL"]) == ["55"]
    assert list(governador["NM_VOTAVEL"]) == ["ANTONIO PEDRO INDIO DA COSTA"]
