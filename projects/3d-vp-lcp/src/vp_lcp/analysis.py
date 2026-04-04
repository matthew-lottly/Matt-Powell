"""Ensemble, sensitivity sweep, bottleneck, and circuit-theory utilities."""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import numpy as np

from .config import PipelineConfig, ResistanceConfig
from .graph3d import VoxelKey
from .pipeline import PipelineResult, run_pipeline


def run_ensemble(
    lidar_path: str | Path,
    configs: list[PipelineConfig],
) -> list[PipelineResult]:
    """Run the pipeline for multiple configurations and return all results.

    Parameters
    ----------
    lidar_path:
        Path to the input LAS/LAZ file.
    configs:
        List of ``PipelineConfig`` instances to run in sequence.

    Returns
    -------
    list[PipelineResult]
        One result per config, in the same order as *configs*.
    """
    return [run_pipeline(lidar_path, cfg) for cfg in configs]


_RESISTANCE_PARAMS = {"alpha", "beta", "gamma", "delta"}


def sensitivity_sweep(
    lidar_path: str | Path,
    base_config: PipelineConfig,
    param: str,
    values: list[float],
) -> list[dict[str, Any]]:
    """Vary a single resistance weight and record path metrics for each value.

    Parameters
    ----------
    lidar_path:
        Path to the input LAS/LAZ file.
    base_config:
        Configuration used as baseline (unchanged across calls).
    param:
        Resistance weight to vary: ``"alpha"``, ``"beta"``, ``"gamma"``, or
        ``"delta"``.
    values:
        Sequence of values to try for *param*.

    Returns
    -------
    list[dict]
        One record per value with keys ``param``, ``param_value``,
        ``path_voxel_count``, ``path_cost``, ``filtered_voxels``,
        ``runtime_seconds``.
    """
    if param not in _RESISTANCE_PARAMS:
        raise ValueError(
            f"param must be one of {sorted(_RESISTANCE_PARAMS)}; got {param!r}"
        )

    results: list[dict[str, Any]] = []
    for val in values:
        new_resistance = dataclasses.replace(base_config.resistance, **{param: val})
        new_config = dataclasses.replace(base_config, resistance=new_resistance)
        result = run_pipeline(lidar_path, new_config)
        results.append(
            {
                "param": param,
                "param_value": val,
                "path_voxel_count": result.path_voxel_count,
                "path_cost": result.path_cost,
                "filtered_voxels": result.filtered_voxel_count,
                "runtime_seconds": result.runtime_seconds,
            }
        )
    return results


def find_bottlenecks(
    path: list[VoxelKey],
    resistance: dict[VoxelKey, float],
    n: int = 5,
) -> list[tuple[VoxelKey, float]]:
    """Return the *n* highest-resistance voxels on a least-cost path.

    Parameters
    ----------
    path:
        Ordered list of voxel keys on the corridor.
    resistance:
        Per-voxel resistance dict (from :func:`~vp_lcp.resistance.compute_resistance`
        or after species filtering).
    n:
        Maximum number of bottleneck voxels to return.

    Returns
    -------
    list[tuple[VoxelKey, float]]
        Pairs of (voxel_key, resistance_value) sorted descending by resistance.
    """
    scored = [(key, resistance.get(key, 0.0)) for key in path]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:n]


def circuit_theory_current(
    g: "Any",
    source_nodes: list[VoxelKey],
    target_nodes: list[VoxelKey],
) -> dict[VoxelKey, float]:
    """Compute effective current flow through the resistance graph.

    Models the graph as an electrical circuit where edge conductance equals
    ``1 / edge_weight``.  Injects unit current at *source_nodes* and
    extracts it at *target_nodes*, then solves for the voltage distribution
    using a sparse Laplacian solver.  The resulting per-node current map
    highlights the most-used corridors and connectivity bottlenecks.

    Parameters
    ----------
    g:
        Weighted NetworkX graph from :func:`~vp_lcp.graph3d.build_graph`.
    source_nodes:
        Voxel keys at the source side of the corridor.
    target_nodes:
        Voxel keys at the target side of the corridor.

    Returns
    -------
    dict[VoxelKey, float]
        Per-voxel effective current.  Higher values mark nodes with more
        current flow, indicating corridor importance.

    Raises
    ------
    ImportError
        If ``scipy`` is not installed.
    """
    try:
        import scipy.sparse as sp
        import scipy.sparse.linalg as spla
    except ImportError:  # pragma: no cover
        raise ImportError(
            "Circuit theory mode requires scipy: pip install scipy"
        )

    voxel_nodes: list[VoxelKey] = [
        node  # type: ignore[assignment]
        for node in g.nodes
        if isinstance(node, tuple) and len(node) == 3 and all(isinstance(x, int) for x in node)
    ]
    if not voxel_nodes:
        return {}

    n = len(voxel_nodes)
    node_to_idx: dict[VoxelKey, int] = {node: i for i, node in enumerate(voxel_nodes)}

    # Build symmetric conductance matrix
    C = sp.lil_matrix((n, n), dtype=np.float64)
    for u, v_node, data in g.edges(data=True):
        if u not in node_to_idx or v_node not in node_to_idx:
            continue
        w = float(data.get("weight", 1.0))
        conductance = 1.0 / max(w, 1e-12)
        i_idx = node_to_idx[u]  # type: ignore[index]
        j_idx = node_to_idx[v_node]  # type: ignore[index]
        C[i_idx, j_idx] += conductance
        C[j_idx, i_idx] += conductance

    C_csr = C.tocsr()
    degree = np.asarray(C_csr.sum(axis=1)).ravel()
    L = sp.diags(degree, format="csr") - C_csr

    # Build current injection vector (+1 at sources, -1 at targets)
    b = np.zeros(n)
    valid_sources = [node_to_idx[s] for s in source_nodes if s in node_to_idx]
    valid_targets = [node_to_idx[t] for t in target_nodes if t in node_to_idx]
    if not valid_sources or not valid_targets:
        return {node: 0.0 for node in voxel_nodes}

    for si in valid_sources:
        b[si] += 1.0 / len(valid_sources)
    for ti in valid_targets:
        b[ti] -= 1.0 / len(valid_targets)

    # Fix ground node (one target) to remove Laplacian singularity
    ground_idx = valid_targets[0]
    L_mod = L.tolil()
    L_mod[ground_idx, :] = 0
    L_mod[ground_idx, ground_idx] = 1.0
    b[ground_idx] = 0.0
    L_mod = L_mod.tocsr()

    try:
        v = spla.spsolve(L_mod, b)
    except Exception:  # pragma: no cover
        return {node: 0.0 for node in voxel_nodes}

    # Compute per-node effective current (sum of edge currents halved)
    result: dict[VoxelKey, float] = {}
    for node, i_idx in node_to_idx.items():
        row = C_csr[i_idx].tocsr()
        js = row.indices
        cs = row.data
        current = float(sum(cs[k] * abs(v[i_idx] - v[int(js[k])]) for k in range(len(js))))
        result[node] = current / 2.0

    return result
