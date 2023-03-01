"Test functions for clustering renewable sites"

from pathlib import Path

import pandas as pd

from powergenome.cluster.renewables import (
    assign_site_cluster,
    value_bin,
    agg_cluster_other,
    agg_cluster_profile,
    agglomerative_cluster_binned,
    agglomerative_cluster_no_bin,
)

import hypothesis
from hypothesis import given, strategies as st
from hypothesis.extra.pandas import data_frames, column, range_indexes, series
from hypothesis.extra.numpy import arrays

CWD = Path.cwd()
DATA_FOLDER = CWD / "tests" / "data" / "cpa_cluster_data"

cluster_data = data_frames(
    columns=[
        column(
            name="profile",
            elements=arrays(
                float, (10,), elements=st.floats(min_value=0, max_value=100)
            ),
        ),
        column(
            name="lcoe",
            elements=st.floats(min_value=0, max_value=100, allow_infinity=False),
        ),
        column(name="state", elements=st.sampled_from(["a", "b"])),
    ]
)


@given(
    bins=st.one_of(
        st.integers(min_value=1, max_value=20),
        st.lists(
            st.floats(min_value=0.001, max_value=100),
            min_size=2,
            max_size=5,
            unique=True,
        ),
    ),
    q=st.one_of(
        st.none(),
        st.integers(min_value=1, max_value=20),
        st.lists(
            st.floats(min_value=0, max_value=1), min_size=2, max_size=5, unique=True
        ),
    ),
    data=st.data(),
)
def test_fuzz_value_bins(bins, q, data):
    strategy = series(
        elements=st.floats(min_value=0, max_value=100),
        index=range_indexes(min_size=10, max_size=10),
    )
    s = data.draw(strategy)
    # pandas binning breaks with very small values. Allow 0 but nothing smaller than 0.01
    s.loc[(s > 0) & (s < 0.01)] = 0.01

    # Run separately with and without weights. Tried st.one_of but it causes an error:
    # elif (weights == 0).all():
    # AttributeError: 'bool' object has no attribute 'all'
    value_bin(s=s, bins=bins, q=q)
    w = data.draw(strategy)
    value_bin(s=s, bins=bins, q=q, weights=w)


@given(
    s=series(
        elements=arrays(float, (10,), elements=st.floats(min_value=0, max_value=100))
    ),
    n_clusters=st.integers(),
)
def test_fuzz_agg_cluster_profile(s, n_clusters):
    agg_cluster_profile(s=s, n_clusters=n_clusters)


@given(s=st.builds(pd.Series), n_clusters=st.integers())
def test_fuzz_agg_cluster_other(s, n_clusters):
    agg_cluster_other(s=s, n_clusters=n_clusters)


@given(
    data=cluster_data,
    feature=st.sampled_from(["profile", "lcoe"]),
    n_clusters=st.integers(),
)
def test_fuzz_agglomerative_cluster_no_bin(data, feature, n_clusters):
    agglomerative_cluster_no_bin(data=data, feature=feature, n_clusters=n_clusters)


@given(
    data=cluster_data,
    by=st.just(["state"]),
    feature=st.sampled_from(["profile", "lcoe"]),
    n_clusters=st.integers(),
)
def test_fuzz_agglomerative_cluster_binned(data, feature, by, n_clusters):
    agglomerative_cluster_binned(
        data=data, by=by, feature=feature, n_clusters=n_clusters
    )


def test_assign_site_cluster():
    renew_data = pd.read_csv(DATA_FOLDER / "cpa_data.csv")
    profile_path = DATA_FOLDER / "cpa_profiles.csv"
    regions = ["A", "B"]
    cluster = {
        "min_capacity": 2000,
        "filter": [
            {
                "feature": "lcoe",
                "max": 49,
            }
        ],
        "bin": [{"feature": "interconnect_annuity", "bins": 2}],
        "group": ["county"],
        "cluster": [
            {"feature": "lcoe", "method": "agg", "n_clusters": 2},
        ],
    }

    data = assign_site_cluster(
        renew_data=renew_data, profile_path=profile_path, regions=regions, **cluster
    )
    assert data.notna().all().all()
    assert "cluster" in data.columns

    cluster = {
        "cluster": [
            {"feature": "profile", "method": "hierarchical", "n_clusters": 3},
        ],
    }
    data = assign_site_cluster(
        renew_data=renew_data, profile_path=profile_path, regions=regions, **cluster
    )
    assert data.notna().all().all()
    assert "cluster" in data.columns

    cluster = {
        "bin": [{"feature": "interconnect_annuity", "mw_per_bin": 200}],
    }
    data = assign_site_cluster(
        renew_data=renew_data, profile_path=profile_path, regions=regions, **cluster
    )
    assert data.notna().all().all()
    assert "cluster" in data.columns

    cluster = {
        "bin": [{"feature": "interconnect_annuity", "mw_per_q": 200}],
    }
    data = assign_site_cluster(
        renew_data=renew_data, profile_path=profile_path, regions=regions, **cluster
    )
    assert data.notna().all().all()
    assert "cluster" in data.columns

    cluster = {
        "cluster": [
            {"feature": "profile", "method": "agglomerative", "mw_per_cluster": 200},
        ],
    }
    data = assign_site_cluster(
        renew_data=renew_data, profile_path=profile_path, regions=regions, **cluster
    )
    assert data.notna().all().all()
    assert "cluster" in data.columns
    assert len(data) == len(renew_data)
