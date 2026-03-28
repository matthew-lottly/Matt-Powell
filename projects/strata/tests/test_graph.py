"""Tests for heterogeneous infrastructure graph generation."""

import numpy as np
import pytest

from hetero_conformal.graph import (
    HeteroInfraGraph,
    generate_synthetic_infrastructure,
    NODE_TYPES,
)


class TestHeteroInfraGraph:
    def test_default_generation(self):
        g = generate_synthetic_infrastructure()
        assert isinstance(g, HeteroInfraGraph)
        for ntype in NODE_TYPES:
            assert ntype in g.node_features
            assert ntype in g.node_positions
            assert ntype in g.node_labels
            assert ntype in g.node_masks

    def test_node_counts(self):
        g = generate_synthetic_infrastructure(n_power=50, n_water=40, n_telecom=30)
        assert g.num_nodes["power"] == 50
        assert g.num_nodes["water"] == 40
        assert g.num_nodes["telecom"] == 30

    def test_feature_dimensions(self):
        dim = 12
        g = generate_synthetic_infrastructure(feature_dim=dim, n_power=20, n_water=15, n_telecom=10)
        for ntype in NODE_TYPES:
            assert g.node_features[ntype].shape[1] == dim

    def test_positions_in_bounds(self):
        bounds = (-95.5, 29.6, -95.2, 29.9)
        g = generate_synthetic_infrastructure(bounds=bounds, n_power=50)
        for ntype in g.node_positions:
            pos = g.node_positions[ntype]
            assert np.all(pos[:, 0] >= bounds[0])
            assert np.all(pos[:, 0] <= bounds[2])
            assert np.all(pos[:, 1] >= bounds[1])
            assert np.all(pos[:, 1] <= bounds[3])

    def test_labels_range(self):
        g = generate_synthetic_infrastructure()
        for ntype in g.node_labels:
            assert np.all(g.node_labels[ntype] >= 0.0)
            assert np.all(g.node_labels[ntype] <= 1.0)

    def test_masks_partition(self):
        g = generate_synthetic_infrastructure(n_power=100, n_water=80, n_telecom=60)
        for ntype in NODE_TYPES:
            masks = g.node_masks[ntype]
            total = masks["train"].sum() + masks["cal"].sum() + masks["test"].sum()
            assert total == g.num_nodes[ntype]
            # No overlap
            assert not np.any(masks["train"] & masks["cal"])
            assert not np.any(masks["train"] & masks["test"])
            assert not np.any(masks["cal"] & masks["test"])

    def test_edge_indices_valid(self):
        g = generate_synthetic_infrastructure(n_power=30, n_water=25, n_telecom=20)
        for etype, ei in g.edge_index.items():
            src_type, _, dst_type = etype
            if ei.shape[1] == 0:
                continue
            assert np.all(ei[0] >= 0)
            assert np.all(ei[1] >= 0)
            assert np.all(ei[0] < g.num_nodes[src_type])
            assert np.all(ei[1] < g.num_nodes[dst_type])

    def test_intra_edges_exist(self):
        g = generate_synthetic_infrastructure(n_power=30, n_water=25, n_telecom=20)
        assert g.num_edges[("power", "feeds", "power")] > 0
        assert g.num_edges[("water", "pipes", "water")] > 0
        assert g.num_edges[("telecom", "connects", "telecom")] > 0

    def test_reproducibility(self):
        g1 = generate_synthetic_infrastructure(seed=99)
        g2 = generate_synthetic_infrastructure(seed=99)
        for ntype in NODE_TYPES:
            np.testing.assert_array_equal(g1.node_features[ntype], g2.node_features[ntype])
            np.testing.assert_array_equal(g1.node_labels[ntype], g2.node_labels[ntype])

    def test_summary_string(self):
        g = generate_synthetic_infrastructure(n_power=10, n_water=8, n_telecom=5)
        s = g.summary()
        assert "HeteroInfraGraph" in s
        assert "power" in s
        assert "water" in s
        assert "telecom" in s
