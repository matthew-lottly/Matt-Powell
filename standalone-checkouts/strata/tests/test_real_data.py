"""Tests for the real-world ACTIVSg200 dataset loader."""

import numpy as np
import pytest

from hetero_conformal.real_data import (
    _parse_matrix,
    _parse_cell_array,
    _geocode_bus,
    load_activsg200,
    load_ieee118,
)


# ---------------------------------------------------------------------------
# Unit tests for parsing helpers
# ---------------------------------------------------------------------------

SAMPLE_MATPOWER = """
mpc.bus = [
    1  1  10.0  3.0  0  0  1  1.02  -5.0  115  2  1.1  0.9;
    2  2  0     0    0  0  1  1.04   0.0   13.8 2  1.1  0.9;
];

mpc.branch = [
    1  2  0.01  0.05  0  100  0  0  0  0  1  0  0;
];

mpc.bus_name = {
    'PEORIA 1 0';
    'SPRINGFIELD 2 1';
};
"""


def test_parse_matrix():
    bus = _parse_matrix(SAMPLE_MATPOWER, "bus")
    assert bus.shape == (2, 13)
    assert bus[0, 0] == 1
    assert bus[1, 9] == pytest.approx(13.8)


def test_parse_matrix_missing_raises():
    with pytest.raises(ValueError, match="Could not find mpc.gen"):
        _parse_matrix(SAMPLE_MATPOWER, "gen")


def test_parse_cell_array():
    names = _parse_cell_array(SAMPLE_MATPOWER, "bus_name")
    assert len(names) == 2
    assert names[0] == "PEORIA 1 0"
    assert names[1] == "SPRINGFIELD 2 1"


def test_parse_cell_array_missing():
    names = _parse_cell_array(SAMPLE_MATPOWER, "nonexistent")
    assert names == []


def test_geocode_known_city():
    rng = np.random.default_rng(0)
    lat, lon = _geocode_bus("PEORIA 1 0", rng)
    assert 40.5 < lat < 40.9  # near Peoria IL
    assert -89.8 < lon < -89.4


def test_geocode_unknown_city():
    rng = np.random.default_rng(0)
    lat, lon = _geocode_bus("NONEXISTENT 0", rng)
    assert 39.5 < lat < 41.0  # fallback Central Illinois region
    assert -90.0 < lon < -88.0


# ---------------------------------------------------------------------------
# Integration test: full dataset load
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_graph():
    return load_activsg200(seed=99)


class TestACTIVSg200Graph:
    def test_three_node_types(self, real_graph):
        assert set(real_graph.node_features.keys()) == {"power", "water", "telecom"}

    def test_power_nodes_count(self, real_graph):
        assert real_graph.node_features["power"].shape[0] == 200

    def test_water_nodes_derived_from_load(self, real_graph):
        n_water = real_graph.node_features["water"].shape[0]
        assert 50 < n_water < 200  # subset of buses with non-zero load

    def test_telecom_nodes_limited(self, real_graph):
        n_telecom = real_graph.node_features["telecom"].shape[0]
        assert n_telecom <= 100

    def test_feature_dim_8(self, real_graph):
        for ntype in real_graph.node_features:
            assert real_graph.node_features[ntype].shape[1] == 8

    def test_has_real_power_edges(self, real_graph):
        power_edges = real_graph.edge_index[("power", "feeds", "power")]
        assert power_edges.shape[1] > 200  # should have more edges than nodes

    def test_has_cross_utility_edges(self, real_graph):
        for etype in [
            ("power", "colocated", "water"),
            ("water", "colocated", "telecom"),
            ("power", "colocated", "telecom"),
        ]:
            assert etype in real_graph.edge_index
            assert real_graph.edge_index[etype].shape[1] > 0

    def test_labels_in_valid_range(self, real_graph):
        for ntype in real_graph.node_labels:
            labels = real_graph.node_labels[ntype]
            assert labels.min() >= 0.0
            assert labels.max() <= 1.0

    def test_masks_cover_all_nodes(self, real_graph):
        for ntype in real_graph.node_masks:
            masks = real_graph.node_masks[ntype]
            n = real_graph.node_features[ntype].shape[0]
            total = masks["train"].sum() + masks["cal"].sum() + masks["test"].sum()
            assert total == n

    def test_positions_in_illinois(self, real_graph):
        for ntype in real_graph.node_positions:
            pos = real_graph.node_positions[ntype]
            # lon should be roughly -90 to -87
            assert pos[:, 0].min() > -91
            assert pos[:, 0].max() < -87
            # lat should be roughly 39 to 41
            assert pos[:, 1].min() > 38
            assert pos[:, 1].max() < 42

    def test_different_seeds_produce_different_splits(self):
        g1 = load_activsg200(seed=1)
        g2 = load_activsg200(seed=2)
        # Masks should differ
        m1 = g1.node_masks["power"]["train"]
        m2 = g2.node_masks["power"]["train"]
        assert not np.array_equal(m1, m2)


def test_load_ieee118_smoke():
    graph = load_ieee118(seed=7)
    assert set(graph.node_features.keys()) == {"power", "water", "telecom"}
    assert graph.node_features["power"].shape[0] == 118
    assert graph.edge_index[("power", "feeds", "power")].shape[1] > 118
    assert graph.node_labels["power"].min() >= 0.0
    assert graph.node_labels["power"].max() <= 1.0

