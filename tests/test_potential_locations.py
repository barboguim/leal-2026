import pandas as pd

from conftest import load_script

pl = load_script("_potential_locations", "10_potential_locations.py")


def make_local(nr_local, pct_share, **demographics):
    row = {
        "nr_local": nr_local, "nm_local": f"Local {nr_local}", "bairro": "Centro",
        "lat": -22.9, "lon": -43.1, "ano": 2022,
        "QT_VOTOS": 1, "total_votos_validos": 100,  # overridden by pct_share below
        "pct_mulheres": 50.0, "pct_jovens_16_24": 15.0, "pct_adultos_25_59": 55.0,
        "pct_60_mais": 30.0, "pct_ate_fundamental": 20.0, "pct_ensino_medio": 40.0,
        "pct_ensino_superior": 40.0,
    }
    row.update(demographics)
    row["pct_share"] = pct_share
    return row


def test_stronghold_centroid_uses_only_top_quartile_locais():
    # 4 locais, pct_share [10, 20, 30, 40] -> pandas' 75th-percentile threshold
    # is 32.5, so only the single highest local (40) clears it. The centroid
    # must equal that local's own vector, not an average pulled down by the
    # three lower-share locais.
    rows = [make_local(str(share), share, pct_mulheres=float(share)) for share in (10, 20, 30, 40)]
    df = pd.DataFrame(rows)
    centroid = pl.stronghold_centroid(df)
    assert centroid["pct_mulheres"] == 40.0


def test_candidate_pool_excludes_locais_at_or_above_median():
    rows = [make_local(str(i), share) for i, share in enumerate([10, 20, 30, 40, 50, 60], start=1)]
    df = pd.DataFrame(rows)
    pool = pl.candidate_pool(df)
    # median of [10,20,30,40,50,60] is 35 -> only 10, 20, 30 are below it
    assert sorted(pool["pct_share"].tolist()) == [10, 20, 30]


def test_rank_by_similarity_orders_nearest_first():
    centroid = pd.Series({
        "pct_mulheres": 50.0, "pct_jovens_16_24": 15.0, "pct_adultos_25_59": 55.0,
        "pct_60_mais": 30.0, "pct_ate_fundamental": 20.0, "pct_ensino_medio": 40.0,
        "pct_ensino_superior": 40.0,
    })
    close = make_local("close", 10, pct_mulheres=51.0)  # distance 1 from centroid
    far = make_local("far", 10, pct_mulheres=90.0)  # distance 40 from centroid
    pool = pd.DataFrame([far, close])  # deliberately out of order
    ranked = pl.rank_by_similarity(pool, centroid)
    assert ranked["nr_local"].tolist() == ["close", "far"]
    assert ranked["rank"].tolist() == [1, 2]


def test_rank_by_similarity_reports_the_most_aligned_fields_not_just_the_aggregate_distance():
    # pct_share alone barely distinguishes locais (this was the actual gap
    # reported: "hard to grasp why they're ranked at all" from pct_share
    # only) -- maior_semelhanca must name which fields are actually closest
    # to the centroid for each local, not restate the rank/score.
    centroid = pd.Series({
        "pct_mulheres": 50.0, "pct_jovens_16_24": 15.0, "pct_adultos_25_59": 55.0,
        "pct_60_mais": 30.0, "pct_ate_fundamental": 20.0, "pct_ensino_medio": 40.0,
        "pct_ensino_superior": 40.0,
    })
    # Exact match on pct_mulheres and pct_ensino_superior (gap 0); every
    # other field is off by 5+ -- those two must be the reported pair.
    local = make_local(
        "1", 10, pct_mulheres=50.0, pct_ensino_superior=40.0,
        pct_jovens_16_24=25.0, pct_adultos_25_59=45.0, pct_60_mais=40.0,
        pct_ate_fundamental=30.0, pct_ensino_medio=50.0,
    )
    ranked = pl.rank_by_similarity(pd.DataFrame([local]), centroid)
    assert ranked.iloc[0]["maior_semelhanca"] == "% Mulheres, % Ensino Superior"


def test_rank_by_similarity_caps_at_top_n():
    centroid = pd.Series({f: 50.0 for f in pl.DEMOGRAPHIC_FIELDS})
    rows = [make_local(str(i), 10, pct_mulheres=float(i)) for i in range(30)]
    pool = pd.DataFrame(rows)
    ranked = pl.rank_by_similarity(pool, centroid)
    assert len(ranked) == pl.TOP_N


def test_load_hugo_year_computes_pct_share_and_filters_to_the_given_year():
    geojson = {
        "features": [
            {"properties": {"ano": 2022, "nr_local": "1", "QT_VOTOS": 50, "total_votos_validos": 200}},
            {"properties": {"ano": 2018, "nr_local": "2", "QT_VOTOS": 10, "total_votos_validos": 100}},
        ]
    }
    df = pl.load_hugo_year(geojson, 2022)
    assert len(df) == 1
    assert df.iloc[0]["nr_local"] == "1"
    assert df.iloc[0]["pct_share"] == 25.0
