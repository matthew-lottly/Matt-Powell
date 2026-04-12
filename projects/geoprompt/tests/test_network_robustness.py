from __future__ import annotations

import math

import pytest

from geoprompt.network import (
    build_network_graph,
    constrained_flow_assignment,
    od_cost_matrix,
    shortest_path,
    utility_bottlenecks,
)


def test_disconnected_graph_reports_unreachable() -> None:
    graph = build_network_graph(
        [
            {"edge_id": "a", "from_node": "A", "to_node": "B", "cost": 1.0},
            {"edge_id": "c", "from_node": "C", "to_node": "D", "cost": 1.0},
        ],
        directed=False,
    )

    result = shortest_path(graph, "A", "D")
    assert result["reachable"] is False
    assert math.isinf(result["total_cost"])


def test_negative_cost_rejected() -> None:
    with pytest.raises(ValueError):
        build_network_graph(
            [{"edge_id": "bad", "from_node": "A", "to_node": "B", "cost": -1.0}],
            directed=False,
        )


def test_nan_capacity_rejected() -> None:
    with pytest.raises(ValueError):
        build_network_graph(
            [{"edge_id": "bad", "from_node": "A", "to_node": "B", "cost": 1.0, "capacity": float("nan")}],
            directed=False,
        )


def test_od_matrix_skips_missing_origins() -> None:
    graph = build_network_graph(
        [{"edge_id": "e1", "from_node": "A", "to_node": "B", "cost": 1.0}],
        directed=False,
    )

    rows = od_cost_matrix(graph, origins=["A", "Z"], destinations=["B"])
    assert len(rows) == 1
    assert rows[0]["origin"] == "A"


def test_bottlenecks_with_zero_demand_remains_zero() -> None:
    graph = build_network_graph(
        [{"edge_id": "e1", "from_node": "A", "to_node": "B", "cost": 1.0, "capacity": 10.0}],
        directed=False,
    )

    rows = utility_bottlenecks(graph, [("A", "B", 0.0)])
    assert rows[0]["flow_load"] == 0.0


def test_constrained_flow_handles_unreachable_destinations() -> None:
    graph = build_network_graph(
        [{"edge_id": "e1", "from_node": "A", "to_node": "B", "cost": 1.0, "capacity": 10.0}],
        directed=True,
    )

    result = constrained_flow_assignment(graph, [("B", "A", 5.0)], max_iterations=2)
    assert result["unmet_demand"] >= 5.0
