"""Heterogeneous infrastructure graph data structures and synthetic generators."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np

NODE_TYPES = ("power", "water", "telecom")

INTRA_EDGE_TYPES = (
    ("power", "feeds", "power"),
    ("water", "pipes", "water"),
    ("telecom", "connects", "telecom"),
)

CROSS_EDGE_TYPES = (
    ("power", "colocated", "water"),
    ("water", "colocated", "telecom"),
    ("power", "colocated", "telecom"),
)

ALL_EDGE_TYPES = INTRA_EDGE_TYPES + CROSS_EDGE_TYPES


@dataclass
class HeteroInfraGraph:
    """Heterogeneous infrastructure graph with typed nodes and edges.

    Attributes
    ----------
    node_features : dict mapping node type -> (N_t, D_t) float array
    node_positions : dict mapping node type -> (N_t, 2) float array (lon, lat)
    edge_index : dict mapping (src_type, rel, dst_type) -> (2, E) int array
    node_labels : dict mapping node type -> (N_t,) float array (risk scores)
    node_masks : dict mapping node type -> dict with 'train', 'cal', 'test' bool arrays
    """

    node_features: Dict[str, np.ndarray] = field(default_factory=dict)
    node_positions: Dict[str, np.ndarray] = field(default_factory=dict)
    edge_index: Dict[Tuple[str, str, str], np.ndarray] = field(default_factory=dict)
    node_labels: Dict[str, np.ndarray] = field(default_factory=dict)
    node_masks: Dict[str, Dict[str, np.ndarray]] = field(default_factory=dict)

    @property
    def num_nodes(self) -> Dict[str, int]:
        return {t: f.shape[0] for t, f in self.node_features.items()}

    @property
    def num_edges(self) -> Dict[Tuple[str, str, str], int]:
        return {t: e.shape[1] for t, e in self.edge_index.items()}

    def summary(self) -> str:
        lines = ["HeteroInfraGraph"]
        for t, n in self.num_nodes.items():
            lines.append(f"  {t}: {n} nodes, {self.node_features[t].shape[1]} features")
        for t, e in self.num_edges.items():
            lines.append(f"  {t[0]}--{t[1]}-->{t[2]}: {e} edges")
        return "\n".join(lines)


def _generate_tree_edges(n: int, rng: np.random.Generator) -> np.ndarray:
    """Generate a random tree on n nodes (power distribution topology)."""
    if n <= 1:
        return np.zeros((2, 0), dtype=np.int64)
    src, dst = [], []
    for i in range(1, n):
        parent = rng.integers(0, i)
        src.extend([parent, i])
        dst.extend([i, parent])
    return np.array([src, dst], dtype=np.int64)


def _generate_grid_mesh_edges(n: int, grid_w: int, rng: np.random.Generator) -> np.ndarray:
    """Generate a grid/mesh topology on n nodes (water pipe network)."""
    if n <= 1:
        return np.zeros((2, 0), dtype=np.int64)
    src, dst = [], []
    grid_h = math.ceil(n / grid_w)
    for i in range(n):
        row, col = divmod(i, grid_w)
        # right neighbor
        if col + 1 < grid_w and i + 1 < n:
            src.extend([i, i + 1])
            dst.extend([i + 1, i])
        # down neighbor
        down = i + grid_w
        if down < n:
            src.extend([i, down])
            dst.extend([down, i])
    return np.array([src, dst], dtype=np.int64)


def _generate_star_hub_edges(n: int, n_hubs: int, rng: np.random.Generator) -> np.ndarray:
    """Generate a star-hub topology on n nodes (telecom network)."""
    if n <= 1:
        return np.zeros((2, 0), dtype=np.int64)
    n_hubs = min(n_hubs, n)
    hubs = list(range(n_hubs))
    src, dst = [], []
    # connect hubs in a ring
    for i in range(n_hubs):
        j = (i + 1) % n_hubs
        src.extend([hubs[i], hubs[j]])
        dst.extend([hubs[j], hubs[i]])
    # assign leaves to nearest hub
    for i in range(n_hubs, n):
        hub = rng.integers(0, n_hubs)
        src.extend([i, hub])
        dst.extend([hub, i])
    return np.array([src, dst], dtype=np.int64)


def _generate_cross_edges(
    positions_a: np.ndarray,
    positions_b: np.ndarray,
    coupling_prob: float,
    coupling_radius: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Generate coupling edges between two sets of nodes based on proximity."""
    src, dst = [], []
    for i in range(len(positions_a)):
        dists = np.sqrt(np.sum((positions_b - positions_a[i]) ** 2, axis=1))
        within = np.where(dists < coupling_radius)[0]
        for j in within:
            if rng.random() < coupling_prob:
                src.append(i)
                dst.append(j)
    if not src:
        return np.zeros((2, 0), dtype=np.int64)
    return np.array([src, dst], dtype=np.int64)


def _simulate_cascade_labels(
    graph: HeteroInfraGraph,
    shock_center: np.ndarray,
    shock_radius: float,
    propagation_decay: float,
    noise_std: float,
    rng: np.random.Generator,
) -> Dict[str, np.ndarray]:
    """Simulate cascading failure risk from an external shock (e.g., storm)."""
    labels = {}
    for ntype in graph.node_features:
        pos = graph.node_positions[ntype]
        dist_to_shock = np.sqrt(np.sum((pos - shock_center) ** 2, axis=1))
        base_risk = np.exp(-propagation_decay * dist_to_shock / shock_radius)
        noise = rng.normal(0, noise_std, size=len(pos))
        risk = np.clip(base_risk + noise, 0.0, 1.0)
        labels[ntype] = risk.astype(np.float32)
    return labels


def _split_masks(
    n: int, train_frac: float, cal_frac: float, rng: np.random.Generator
) -> Dict[str, np.ndarray]:
    """Create train/calibration/test boolean masks."""
    indices = rng.permutation(n)
    n_train = int(n * train_frac)
    n_cal = int(n * cal_frac)
    train_mask = np.zeros(n, dtype=bool)
    cal_mask = np.zeros(n, dtype=bool)
    test_mask = np.zeros(n, dtype=bool)
    train_mask[indices[:n_train]] = True
    cal_mask[indices[n_train : n_train + n_cal]] = True
    test_mask[indices[n_train + n_cal :]] = True
    return {"train": train_mask, "cal": cal_mask, "test": test_mask}


def generate_synthetic_infrastructure(
    n_power: int = 200,
    n_water: int = 150,
    n_telecom: int = 100,
    feature_dim: int = 8,
    coupling_prob: float = 0.3,
    coupling_radius: float = 0.15,
    train_frac: float = 0.5,
    cal_frac: float = 0.25,
    seed: int = 42,
    bounds: Tuple[float, float, float, float] = (-95.5, 29.6, -95.2, 29.9),
) -> HeteroInfraGraph:
    """Generate a synthetic heterogeneous infrastructure graph.

    Parameters
    ----------
    n_power, n_water, n_telecom : int
        Number of nodes per utility type.
    feature_dim : int
        Dimensionality of node features.
    coupling_prob : float
        Probability of creating a cross-utility edge for nearby nodes.
    coupling_radius : float
        Max distance (in coordinate units) for coupling eligibility.
    train_frac, cal_frac : float
        Fraction of nodes for training and calibration (rest goes to test).
    seed : int
        Random seed for reproducibility.
    bounds : tuple
        (min_lon, min_lat, max_lon, max_lat) for spatial layout.

    Returns
    -------
    HeteroInfraGraph
    """
    rng = np.random.default_rng(seed)
    min_lon, min_lat, max_lon, max_lat = bounds

    graph = HeteroInfraGraph()
    counts = {"power": n_power, "water": n_water, "telecom": n_telecom}

    # Generate positions
    for ntype, n in counts.items():
        lons = rng.uniform(min_lon, max_lon, size=n)
        lats = rng.uniform(min_lat, max_lat, size=n)
        graph.node_positions[ntype] = np.column_stack([lons, lats]).astype(np.float32)

    # Generate node features: [capacity, age, condition, elevation_proxy, 4 random]
    for ntype, n in counts.items():
        feats = np.column_stack([
            rng.uniform(0.1, 1.0, size=n),           # capacity
            rng.uniform(0.0, 40.0, size=n),           # age (years)
            rng.uniform(0.0, 1.0, size=n),            # condition score
            rng.uniform(0.0, 50.0, size=n),           # elevation proxy
            rng.standard_normal(size=(n, feature_dim - 4)),  # auxiliary features
        ]).astype(np.float32)
        graph.node_features[ntype] = feats

    # Generate intra-utility edges
    grid_w = max(1, int(math.sqrt(n_water)))
    graph.edge_index[("power", "feeds", "power")] = _generate_tree_edges(n_power, rng)
    graph.edge_index[("water", "pipes", "water")] = _generate_grid_mesh_edges(n_water, grid_w, rng)
    graph.edge_index[("telecom", "connects", "telecom")] = _generate_star_hub_edges(
        n_telecom, max(1, n_telecom // 10), rng
    )

    # Generate cross-utility coupling edges
    type_pairs = [
        (("power", "colocated", "water"), "power", "water"),
        (("water", "colocated", "telecom"), "water", "telecom"),
        (("power", "colocated", "telecom"), "power", "telecom"),
    ]
    for edge_type, src_type, dst_type in type_pairs:
        graph.edge_index[edge_type] = _generate_cross_edges(
            graph.node_positions[src_type],
            graph.node_positions[dst_type],
            coupling_prob,
            coupling_radius,
            rng,
        )

    # Simulate failure risk labels from a storm shock
    shock_center = np.array(
        [(min_lon + max_lon) / 2, (min_lat + max_lat) / 2], dtype=np.float32
    )
    graph.node_labels = _simulate_cascade_labels(
        graph,
        shock_center=shock_center,
        shock_radius=0.2,
        propagation_decay=2.0,
        noise_std=0.1,
        rng=rng,
    )

    # Create train/cal/test splits
    for ntype, n in counts.items():
        graph.node_masks[ntype] = _split_masks(n, train_frac, cal_frac, rng)

    return graph
