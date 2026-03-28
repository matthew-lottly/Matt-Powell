"""Tests for the heterogeneous GNN model."""

import numpy as np
import pytest
import torch

from hetero_conformal.graph import generate_synthetic_infrastructure
from hetero_conformal.model import HeteroGNN, HeteroMessagePassingLayer


@pytest.fixture
def small_graph():
    return generate_synthetic_infrastructure(
        n_power=20, n_water=15, n_telecom=10, seed=42
    )


@pytest.fixture
def model_and_tensors(small_graph):
    g = small_graph
    in_dims = {ntype: f.shape[1] for ntype, f in g.node_features.items()}
    edge_types = list(g.edge_index.keys())

    model = HeteroGNN(
        in_dims=in_dims,
        hidden_dim=16,
        num_layers=2,
        edge_types=edge_types,
        dropout=0.0,
    )

    x = {ntype: torch.tensor(f, dtype=torch.float32) for ntype, f in g.node_features.items()}
    ei = {et: torch.tensor(e, dtype=torch.long) for et, e in g.edge_index.items()}
    num_nodes = g.num_nodes

    return model, x, ei, num_nodes


class TestHeteroMessagePassingLayer:
    def test_output_shape(self, small_graph):
        g = small_graph
        in_dims = {ntype: f.shape[1] for ntype, f in g.node_features.items()}
        edge_types = list(g.edge_index.keys())
        out_dim = 32

        layer = HeteroMessagePassingLayer(in_dims, out_dim, edge_types)
        x = {ntype: torch.tensor(f, dtype=torch.float32) for ntype, f in g.node_features.items()}
        ei = {et: torch.tensor(e, dtype=torch.long) for et, e in g.edge_index.items()}

        out = layer(x, ei, g.num_nodes)
        for ntype in out:
            assert out[ntype].shape == (g.num_nodes[ntype], out_dim)


class TestHeteroGNN:
    def test_forward_output_shape(self, model_and_tensors):
        model, x, ei, num_nodes = model_and_tensors
        preds = model(x, ei, num_nodes)
        for ntype in preds:
            assert preds[ntype].shape == (num_nodes[ntype],)

    def test_forward_produces_finite(self, model_and_tensors):
        model, x, ei, num_nodes = model_and_tensors
        preds = model(x, ei, num_nodes)
        for ntype in preds:
            assert torch.all(torch.isfinite(preds[ntype]))

    def test_gradient_flows(self, model_and_tensors):
        model, x, ei, num_nodes = model_and_tensors
        preds = model(x, ei, num_nodes)
        loss = torch.stack([p.mean() for p in preds.values()]).sum()
        loss.backward()
        for name, param in model.named_parameters():
            if param.requires_grad:
                assert param.grad is not None, f"No gradient for {name}"

    def test_different_seeds_different_outputs(self, small_graph):
        g = small_graph
        in_dims = {ntype: f.shape[1] for ntype, f in g.node_features.items()}
        edge_types = list(g.edge_index.keys())

        torch.manual_seed(1)
        m1 = HeteroGNN(in_dims, 16, 2, edge_types)
        torch.manual_seed(2)
        m2 = HeteroGNN(in_dims, 16, 2, edge_types)

        x = {ntype: torch.tensor(f, dtype=torch.float32) for ntype, f in g.node_features.items()}
        ei = {et: torch.tensor(e, dtype=torch.long) for et, e in g.edge_index.items()}

        p1 = m1(x, ei, g.num_nodes)
        p2 = m2(x, ei, g.num_nodes)
        for ntype in p1:
            assert not torch.allclose(p1[ntype], p2[ntype])
