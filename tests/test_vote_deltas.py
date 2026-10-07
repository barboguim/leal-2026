from conftest import load_script

vd = load_script("_vote_deltas", "06_build_vote_deltas.py")

MIGRATION_FIELDS = {
    "hugo_perda", "felipe_ganho", "psd_ganho",
    "mig_hugo_felipe_votos", "mig_hugo_psd_votos",
    "mig_hugo_felipe_score", "mig_hugo_psd_score",
    "mig_alvo", "mig_score", "mig_votos_correspondentes", "mig_signal",
}


def make_matrix_lookup(rows):
    # rows: list of (candidate_key, ano, tipo_eleicao) or (candidate_key, ano, tipo_eleicao, cargo)
    lookup = {}
    for row in rows:
        if len(row) == 4:
            key, ano, tipo, cargo = row
        else:
            key, ano, tipo = row
            cargo = "CARGO"
        lookup[(key, ano)] = {"tipo_eleicao": tipo, "cargo": cargo}
    return lookup


def test_add_delta_fields_no_longer_writes_migration_fields():
    lookup = make_matrix_lookup([
        ("hugo", 2010, "Geral"), ("hugo", 2014, "Geral"),
        ("felipe", 2010, "Geral"), ("felipe", 2014, "Geral"),
        ("psd", 2010, "Geral"), ("psd", 2014, "Geral"),
    ])
    row = {"ano_inicio": 2010, "ano_fim": 2014}
    votes = {
        ("hugo", 2010): 100, ("hugo", 2014): 60,
        ("felipe", 2010): 20, ("felipe", 2014): 55,
        ("psd", 2010): 30, ("psd", 2014): 30,
    }

    def get_votes(key, year):
        return votes.get((key, year), 0)

    vd.add_delta_fields(row, get_votes, lookup)

    assert MIGRATION_FIELDS.isdisjoint(row.keys())
    assert not hasattr(vd, "migration_score")
    assert not hasattr(vd, "MIN_SIGNAL_VOTES")


def test_add_delta_fields_keeps_deltas_and_map_fields_when_gated():
    # 2010 and 2014 are both Geral-type years (unlike the original
    # fixture's 2012/2014, which is Municipal->Geral and can never be
    # gated under the new same-type rule) — this test now specifically
    # exercises the "both sides present, same type" path.
    lookup = make_matrix_lookup([("hugo", 2010, "Geral"), ("hugo", 2014, "Geral")])
    row = {"ano_inicio": 2010, "ano_fim": 2014}
    votes = {("hugo", 2010): 100, ("hugo", 2014): 60}

    def get_votes(key, year):
        return votes.get((key, year), 0)

    vd.add_delta_fields(row, get_votes, lookup)

    assert row["votos_hugo_inicio"] == 100
    assert row["votos_hugo_fim"] == 60
    assert row["delta_hugo"] == -40
    assert row["pct_delta_hugo"] == -40.0
    assert row["candidacy_status_hugo"] == "concorreu"
    assert row["map_delta"] == -40
    assert row["map_abs_delta"] == 40
    assert row["tipo_par"] == "Geral -> Geral"


def test_candidate_pairs_from_matrix_finds_nearest_matching_cycle_within_type():
    lookup = make_matrix_lookup([
        ("felipe", 2010, "Geral"),
        ("felipe", 2012, "Municipal"),
        ("felipe", 2016, "Municipal"),
        ("felipe", 2018, "Geral"),
        ("felipe", 2020, "Municipal"),
        ("felipe", 2022, "Geral"),
    ])
    pairs = vd.candidate_pairs_from_matrix(lookup, "felipe")
    assert (2010, 2018) in pairs
    assert (2018, 2022) in pairs
    assert (2012, 2016) in pairs
    assert (2016, 2020) in pairs
    # never crosses type buckets
    assert (2010, 2012) not in pairs
    assert (2016, 2018) not in pairs


def test_candidate_pairs_from_matrix_empty_for_unknown_candidate():
    lookup = make_matrix_lookup([("felipe", 2010, "Geral")])
    assert vd.candidate_pairs_from_matrix(lookup, "hugo") == []


def test_candidate_pairs_from_matrix_single_candidacy_produces_no_pairs():
    lookup = make_matrix_lookup([("psd", 2012, "Municipal")])
    assert vd.candidate_pairs_from_matrix(lookup, "psd") == []


def test_all_candidate_pairs_unions_across_candidates():
    lookup = make_matrix_lookup([
        ("hugo", 2010, "Geral"), ("hugo", 2014, "Geral"),
        ("felipe", 2012, "Municipal"), ("felipe", 2016, "Municipal"),
    ])
    pairs = vd.all_candidate_pairs(lookup)
    assert (2010, 2014) in pairs
    assert (2012, 2016) in pairs
    assert len(pairs) == 2


def test_add_delta_fields_gates_ungated_pair_to_null_with_status():
    lookup = make_matrix_lookup([("hugo", 2010, "Geral"), ("hugo", 2014, "Geral")])
    row = {"ano_inicio": 2010, "ano_fim": 2014}
    votes = {("hugo", 2010): 100, ("hugo", 2014): 60, ("felipe", 2010): 20, ("felipe", 2014): 55, ("psd", 2010): 0, ("psd", 2014): 30}

    def get_votes(key, year):
        return votes.get((key, year), 0)

    vd.add_delta_fields(row, get_votes, lookup)

    # hugo is gated (both years present, same type) -> real numbers
    assert row["votos_hugo_inicio"] == 100
    assert row["delta_hugo"] == -40
    assert row["candidacy_status_hugo"] == "concorreu"

    # felipe has no matrix rows at all for either year -> null, not a fake delta
    assert row["votos_felipe_inicio"] is None
    assert row["votos_felipe_fim"] is None
    assert row["delta_felipe"] is None
    assert row["pct_delta_felipe"] is None
    assert row["candidacy_status_felipe"] == "nao_concorreu"

    # psd has no matrix rows either (2010 predates PSD's founding) -> null,
    # and the status must say the party didn't exist yet, not "didn't run"
    assert row["delta_psd"] is None
    assert row["candidacy_status_psd"] == "partido_inexistente"


def test_add_delta_fields_null_when_only_one_side_gated():
    lookup = make_matrix_lookup([("felipe", 2018, "Geral")])
    row = {"ano_inicio": 2018, "ano_fim": 2022}
    votes = {("felipe", 2018): 40}

    def get_votes(key, year):
        return votes.get((key, year), 0)

    vd.add_delta_fields(row, get_votes, lookup)
    assert row["delta_felipe"] is None
    assert row["candidacy_status_felipe"] == "nao_concorreu_fim"


def test_add_delta_fields_null_when_types_mismatch_despite_both_present():
    lookup = make_matrix_lookup([("felipe", 2018, "Geral"), ("felipe", 2020, "Municipal")])
    row = {"ano_inicio": 2018, "ano_fim": 2020}
    votes = {("felipe", 2018): 40, ("felipe", 2020): 300}

    def get_votes(key, year):
        return votes.get((key, year), 0)

    vd.add_delta_fields(row, get_votes, lookup)
    assert row["delta_felipe"] is None
    assert row["candidacy_status_felipe"] == "tipo_incompativel"


def test_add_delta_fields_map_fields_are_null_when_hugo_ungated():
    lookup = make_matrix_lookup([("hugo", 2012, "Municipal"), ("hugo", 2014, "Geral")])
    # deliberately NOT gated for hugo (types differ) to prove map_delta handles null
    row = {"ano_inicio": 2012, "ano_fim": 2014}

    def get_votes(key, year):
        return 0

    vd.add_delta_fields(row, get_votes, lookup)
    assert row["map_delta"] is None
    assert row["map_abs_delta"] is None


def test_add_delta_fields_psd_pre_founding_year_is_partido_inexistente_not_nao_concorreu():
    # PSD has a real matrix row for 2012 (Municipal) but none for 2010,
    # because PSD (founded 2011) didn't exist yet in 2010 — this must be
    # distinguished from "PSD existed but chose not to run".
    lookup = make_matrix_lookup([("psd", 2012, "Municipal")])
    row = {"ano_inicio": 2010, "ano_fim": 2012}
    votes = {("psd", 2012): 30}

    def get_votes(key, year):
        return votes.get((key, year), 0)

    vd.add_delta_fields(row, get_votes, lookup)
    assert row["delta_psd"] is None
    assert row["candidacy_status_psd"] == "partido_inexistente"


def test_add_delta_fields_flags_cargo_diferente_when_gated_and_cargo_changes():
    # Mirrors the real Felipe 2018->2022 case: both Geral (gated), but
    # Deputado Estadual -> Deputado Federal is not the same office.
    lookup = make_matrix_lookup([
        ("felipe", 2018, "Geral", "DEPUTADO ESTADUAL"),
        ("felipe", 2022, "Geral", "DEPUTADO FEDERAL"),
    ])
    row = {"ano_inicio": 2018, "ano_fim": 2022}
    votes = {("felipe", 2018): 40, ("felipe", 2022): 55}

    def get_votes(key, year):
        return votes.get((key, year), 0)

    vd.add_delta_fields(row, get_votes, lookup)
    assert row["candidacy_status_felipe"] == "concorreu"
    assert row["cargo_diferente_felipe"] is True


def test_add_delta_fields_cargo_diferente_false_when_cargo_unchanged():
    lookup = make_matrix_lookup([
        ("hugo", 2018, "Geral", "DEPUTADO FEDERAL"),
        ("hugo", 2022, "Geral", "DEPUTADO FEDERAL"),
    ])
    row = {"ano_inicio": 2018, "ano_fim": 2022}
    votes = {("hugo", 2018): 40, ("hugo", 2022): 55}

    def get_votes(key, year):
        return votes.get((key, year), 0)

    vd.add_delta_fields(row, get_votes, lookup)
    assert row["cargo_diferente_hugo"] is False


def test_add_delta_fields_cargo_diferente_null_when_ungated():
    lookup = make_matrix_lookup([("hugo", 2018, "Geral", "DEPUTADO FEDERAL")])
    row = {"ano_inicio": 2018, "ano_fim": 2022}

    def get_votes(key, year):
        return 0

    vd.add_delta_fields(row, get_votes, lookup)
    assert row["candidacy_status_hugo"] == "nao_concorreu_fim"
    assert row["cargo_diferente_hugo"] is None
