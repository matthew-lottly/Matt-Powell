"""Geoprompt integration for spatial data preparation.

Uses the geoprompt package (GeoPromptFrame API) to generate spatially-aware
infrastructure layouts, build network topologies, compute spatial weights,
and produce risk surfaces via conformal kriging.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

from .graph import HeteroInfraGraph


def _frame_for_type(graph: HeteroInfraGraph, ntype: str) -> Any:
    """Build a GeoPromptFrame for a single node type."""
    from geoprompt import GeoPromptFrame

    pos = graph.node_positions[ntype]
    labels = graph.node_labels.get(ntype, np.zeros(len(pos)))
    records = []
    for i in range(len(pos)):
        records.append({
            "geometry": {
                "type": "Point",
                "coordinates": [float(pos[i, 0]), float(pos[i, 1])],
            },
            "site_id": f"{ntype}_{i}",
            "node_type": ntype,
            "risk_score": float(labels[i]),
        })
    return GeoPromptFrame.from_records(records, geometry="geometry", crs="EPSG:4326")


def build_spatial_layout(
    graph: HeteroInfraGraph,
) -> Dict[str, Any]:
    """Convert node positions to GeoPromptFrames per node type.

    Returns
    -------
    dict mapping node type -> GeoPromptFrame.
    """
    return {ntype: _frame_for_type(graph, ntype) for ntype in graph.node_positions}


def compute_spatial_weights(
    graph: HeteroInfraGraph,
    ntype: str,
    k: int = 6,
) -> dict:
    """Compute a spatial weights matrix for a given node type using geoprompt.

    Parameters
    ----------
    graph : HeteroInfraGraph
    ntype : str
        Node type to compute weights for.
    k : int
        Number of neighbors for knn.

    Returns
    -------
    dict with weight information from GeoPromptFrame.spatial_weights_matrix.
    """
    frame = _frame_for_type(graph, ntype)
    return frame.spatial_weights_matrix(
        id_column="site_id",
        mode="k_nearest",
        k=k,
    )


def build_network_topology(
    graph: HeteroInfraGraph,
    ntype: str,
) -> Any:
    """Build a network graph from edge geometry using geoprompt.

    Constructs LineString features from the intra-utility edges and
    passes them through GeoPromptFrame.network_build.

    Parameters
    ----------
    graph : HeteroInfraGraph
    ntype : str

    Returns
    -------
    GeoPromptFrame with network topology.
    """
    from geoprompt import GeoPromptFrame

    edge_type_map = {
        "power": ("power", "feeds", "power"),
        "water": ("water", "pipes", "water"),
        "telecom": ("telecom", "connects", "telecom"),
    }
    et = edge_type_map.get(ntype)
    if et is None or et not in graph.edge_index:
        return GeoPromptFrame.from_records([], geometry="geometry")

    ei = graph.edge_index[et]
    pos = graph.node_positions[ntype]
    records = []
    seen: set[tuple[int, int]] = set()
    for e in range(ei.shape[1]):
        s, d = int(ei[0, e]), int(ei[1, e])
        edge_key = (min(s, d), max(s, d))
        if edge_key in seen:
            continue
        seen.add(edge_key)
        records.append({
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [float(pos[s, 0]), float(pos[s, 1])],
                    [float(pos[d, 0]), float(pos[d, 1])],
                ],
            },
            "site_id": f"edge_{s}_{d}",
        })

    frame = GeoPromptFrame.from_records(records, geometry="geometry", crs="EPSG:4326")
    return frame.network_build(id_column="site_id")


def generate_risk_surface(
    graph: HeteroInfraGraph,
    ntype: str,
    grid_resolution: int = 50,
    alpha: float = 0.1,
) -> Any:
    """Generate a conformally-calibrated risk surface via conformal_kriging.

    Parameters
    ----------
    graph : HeteroInfraGraph
    ntype : str
    grid_resolution : int
        Number of grid points per axis.
    alpha : float
        Significance level for conformal intervals.

    Returns
    -------
    GeoPromptFrame with kriging predictions, lower, and upper bounds.
    """
    frame = _frame_for_type(graph, ntype)
    return frame.conformal_kriging(
        value_column="risk_score",
        grid_resolution=grid_resolution,
        alpha=alpha,
    )


def compute_hotspots(
    graph: HeteroInfraGraph,
    ntype: str,
) -> Any:
    """Identify infrastructure risk hotspots using Getis-Ord Gi*.

    Parameters
    ----------
    graph : HeteroInfraGraph
    ntype : str

    Returns
    -------
    GeoPromptFrame with z-scores and p-values from hotspot_getis_ord.
    """
    frame = _frame_for_type(graph, ntype)
    return frame.hotspot_getis_ord(
        value_column="risk_score",
        id_column="site_id",
    )
