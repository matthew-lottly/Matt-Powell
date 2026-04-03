"""3-D graph construction and least-cost-path routing."""

from __future__ import annotations

import math

import networkx as nx
import numpy as np


def build_graph(
    resistance: dict[tuple[int, int, int], float],
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
    source_nodes: list[tuple[int, int, int]],
    target_nodes: list[tuple[int, int, int]],
) -> list[tuple[int, int, int]]:
    """Multi-source / multi-target Dijkstra via super-nodes.

    Returns the voxel-key sequence of the least-cost path (excluding the
    dummy super-nodes).
    """
    super_s = ("__super_source__",)
    super_t = ("__super_target__",)
    g_copy = g.copy()
    g_copy.add_node(super_s)
    g_copy.add_node(super_t)
    for s in source_nodes:
        if s in g_copy:
            g_copy.add_edge(super_s, s, weight=0.0)
    for t in target_nodes:
        if t in g_copy:
            g_copy.add_edge(super_t, t, weight=0.0)

    path = nx.shortest_path(g_copy, super_s, super_t, weight="weight")
    return [n for n in path if n not in (super_s, super_t)]
