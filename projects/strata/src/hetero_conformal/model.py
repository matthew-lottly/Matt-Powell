"""Heterogeneous GNN with typed message passing layers."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class HeteroMessagePassingLayer(nn.Module):
    """Single message-passing layer with per-edge-type weight matrices.

    For each edge type (src_type, rel, dst_type), learns a separate
    linear transformation W_{rel} applied to source features, then
    aggregates (mean) into destination nodes.
    """

    def __init__(
        self,
        in_dims: Dict[str, int],
        out_dim: int,
        edge_types: List[Tuple[str, str, str]],
    ):
        super().__init__()
        self.out_dim = out_dim
        self.edge_types = edge_types

        # Per-edge-type linear transforms
        self.edge_linears = nn.ModuleDict()
        for src_type, rel, dst_type in edge_types:
            key = f"{src_type}__{rel}__{dst_type}"
            self.edge_linears[key] = nn.Linear(in_dims[src_type], out_dim, bias=False)

        # Per-node-type self-loop + bias
        self.self_linears = nn.ModuleDict()
        for ntype, d in in_dims.items():
            self.self_linears[ntype] = nn.Linear(d, out_dim)

    def forward(
        self,
        x: Dict[str, torch.Tensor],
        edge_index: Dict[Tuple[str, str, str], torch.Tensor],
        num_nodes: Dict[str, int],
    ) -> Dict[str, torch.Tensor]:
        # Start with self-loop contribution
        out = {}
        for ntype in x:
            out[ntype] = self.self_linears[ntype](x[ntype])

        # Accumulate messages from each edge type
        for src_type, rel, dst_type in self.edge_types:
            key = f"{src_type}__{rel}__{dst_type}"
            et = (src_type, rel, dst_type)
            if et not in edge_index or edge_index[et].shape[1] == 0:
                continue

            ei = edge_index[et]  # (2, E)
            src_idx, dst_idx = ei[0], ei[1]
            src_feats = x[src_type][src_idx]  # (E, D_src)
            messages = self.edge_linears[key](src_feats)  # (E, out_dim)

            # Mean aggregation into destination nodes
            n_dst = num_nodes[dst_type]
            agg = torch.zeros(n_dst, self.out_dim, device=messages.device)
            count = torch.zeros(n_dst, 1, device=messages.device)
            agg.scatter_add_(0, dst_idx.unsqueeze(1).expand_as(messages), messages)
            count.scatter_add_(0, dst_idx.unsqueeze(1), torch.ones_like(dst_idx.unsqueeze(1).float()))
            count = count.clamp(min=1.0)
            out[dst_type] = out[dst_type] + agg / count

        return out


class HeteroGNN(nn.Module):
    """Heterogeneous GNN for node-level risk regression.

    Stacks multiple HeteroMessagePassingLayer blocks with ReLU
    activations and optional residual connections, then produces
    a scalar risk prediction per node.
    """

    def __init__(
        self,
        in_dims: Dict[str, int],
        hidden_dim: int,
        num_layers: int,
        edge_types: List[Tuple[str, str, str]],
        dropout: float = 0.1,
    ):
        super().__init__()
        self.num_layers = num_layers

        # Input projection per node type
        self.input_proj = nn.ModuleDict()
        for ntype, d in in_dims.items():
            self.input_proj[ntype] = nn.Linear(d, hidden_dim)

        # Message passing layers
        hidden_dims = {ntype: hidden_dim for ntype in in_dims}
        self.mp_layers = nn.ModuleList()
        for _ in range(num_layers):
            self.mp_layers.append(
                HeteroMessagePassingLayer(hidden_dims, hidden_dim, edge_types)
            )

        # Output heads per node type
        self.output_heads = nn.ModuleDict()
        for ntype in in_dims:
            self.output_heads[ntype] = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.ReLU(),
                nn.Linear(hidden_dim // 2, 1),
            )

        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        x: Dict[str, torch.Tensor],
        edge_index: Dict[Tuple[str, str, str], torch.Tensor],
        num_nodes: Dict[str, int],
    ) -> Dict[str, torch.Tensor]:
        # Project inputs to hidden dim
        h = {}
        for ntype in x:
            h[ntype] = F.relu(self.input_proj[ntype](x[ntype]))

        # Message passing layers with residual connections
        for layer in self.mp_layers:
            h_new = layer(h, edge_index, num_nodes)
            for ntype in h:
                h_new[ntype] = F.relu(h_new[ntype])
                h_new[ntype] = self.dropout(h_new[ntype])
                # Residual
                h_new[ntype] = h_new[ntype] + h[ntype]
            h = h_new

        # Per-node predictions
        predictions = {}
        for ntype in h:
            predictions[ntype] = self.output_heads[ntype](h[ntype]).squeeze(-1)

        return predictions
