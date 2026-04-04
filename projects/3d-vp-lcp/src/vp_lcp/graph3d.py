"""3-D graph construction and least-cost-path routing."""

from __future__ import annotations

import math
from typing import Any, TypeAlias, cast

import networkx as nx


VoxelKey: TypeAlias = tuple[int, int, int]
SuperKey: TypeAlias = tuple[str]


def build_graph(
    resistance: dict[VoxelKey, float],
    voxel_size: float,
    neighbours: int = 6,
) -> nx.Graph:
    """Build a weighted graph over passable voxels.

    Parameters
    ----------
    resistance:
        Per-voxel resistance from :func:`compute_resistance` or after species
        filtering.
    voxel_size:
        Edge length of each cubic voxel in metres.
    neighbours:
        Adjacency type: 6 (face), 18 (face + edge), or 26 (face + edge + corner).
    """
    offsets_6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
    offsets_18 = offsets_6 + [
        (1, 1, 0), (1, -1, 0), (-1, 1, 0), (-1, -1, 0),
        (1, 0, 1), (1, 0, -1), (-1, 0, 1), (-1, 0, -1),
        (0, 1, 1), (0, 1, -1), (0, -1, 1), (0, -1, -1),
    ]
    offsets_26 = offsets_18 + [
        (1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1),
        (-1, 1, 1), (-1, 1, -1), (-1, -1, 1), (-1, -1, -1),
    ]

    if neighbours == 26:
        offsets = offsets_26
    elif neighbours == 18:
        offsets = offsets_18
    else:
        offsets = offsets_6

    g = nx.Graph()
    keys = set(resistance)

    for key in keys:
        g.add_node(key, resistance=resistance[key])

    for key in keys:
        i, j, k = key
        r1 = resistance[key]
        for di, dj, dk in offsets:
            nid = (i + di, j + dj, k + dk)
            if nid in keys and not g.has_edge(key, nid):
                r2 = resistance[nid]
                dist = voxel_size * math.sqrt(di * di + dj * dj + dk * dk)
                weight = (r1 + r2) / 2.0 * dist
                g.add_edge(key, nid, weight=weight)

    return g


def least_cost_path(
    g: nx.Graph,
    source_nodes: list[VoxelKey],
    target_nodes: list[VoxelKey],
    algorithm: str = "dijkstra",
) -> list[VoxelKey]:
    """Multi-source / multi-target shortest path via super-nodes.

    Supported algorithms are ``dijkstra`` and ``astar``.  A* uses a zero
    heuristic for the super-node routing setup, which preserves correctness
    while allowing a consistent algorithm switch from the CLI and config.
    """
    super_s: SuperKey = ("__super_source__",)
    super_t: SuperKey = ("__super_target__",)
    g_copy = g.copy()
    g_copy.add_node(super_s)
    g_copy.add_node(super_t)
    for s in source_nodes:
        if s in g_copy:
            g_copy.add_edge(super_s, s, weight=0.0)
    for t in target_nodes:
        if t in g_copy:
            g_copy.add_edge(super_t, t, weight=0.0)

    if algorithm == "astar":
        raw_path = nx.astar_path(
            g_copy, super_s, super_t, heuristic=lambda _u, _v: 0.0, weight="weight"
        )
    else:
        raw_path = nx.shortest_path(g_copy, super_s, super_t, weight="weight")

    path = cast(list[Any], raw_path)
    voxel_path: list[VoxelKey] = []
    for node in path:
        if isinstance(node, tuple) and len(node) == 3 and all(isinstance(part, int) for part in node):
            voxel_path.append(cast(VoxelKey, node))
    return voxel_path


def accumulated_cost_volume(
    g: nx.Graph,
    source_nodes: list[VoxelKey],
) -> dict[VoxelKey, float]:
    """Compute the minimum travel cost from any source to every reachable voxel."""
    cost_src: SuperKey = ("__cost_source__",)
    g_copy = g.copy()
    g_copy.add_node(cost_src)
    for s in source_nodes:
        if s in g_copy:
            g_copy.add_edge(cost_src, s, weight=0.0)
    raw_costs = nx.single_source_dijkstra_path_length(g_copy, cost_src, weight="weight")
    result: dict[VoxelKey, float] = {}
    for node, cost in raw_costs.items():
        if isinstance(node, tuple) and len(node) == 3:
            vk = cast(VoxelKey, node)
            i, j, k = vk
            if isinstance(i, int) and isinstance(j, int) and isinstance(k, int):
                result[vk] = cost
    return result
