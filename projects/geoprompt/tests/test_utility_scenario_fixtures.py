"""Deterministic scenario fixtures for behavior drift detection.

Provides small, well-understood test networks with pre-computed expected
scenario outcomes. These fixtures enable early detection of unintended
changes to scenario runner logic.

Fixture Scenarios:
1. simple_linear_3node: 3-node linear chain (A->B->C)
   - Single source at A, tests basic path blocking
   - Outage of B blocks all downstream nodes

2. simple_branching_5node: 5-node tree (A with B,C children; B with D,E)
   - Single source at A, tests differential impact of edge failure
   - Outage of B-D affects D only; outage of A-B affects subtree

3. simple_mesh_4node: 4-node with redundancy (A-B, A-C, B-D, C-D)
   - Single source at A, tests redundancy preservation
   - Outage of any single edge doesn't block all downstream

4. simple_critical_node_scenario: Network with designated critical nodes
   - Tests critical node impact tracking and ranking
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from geoprompt.network import NetworkEdge, build_network_graph, run_utility_scenarios


@dataclass
class FixtureScenarioExpectation:
    """Expected outcomes for a deterministic scenario fixture."""

    # Scenario metadata
    name: str
    description: str

    # Network structure
    edges: list[NetworkEdge]
    source_nodes: list[str]
    critical_nodes: list[str]
    outage_edges: list[str]
    restoration_edges: list[str]

    # Expected results for each phase
    baseline: dict[str, Any]  # supplied_count, deenergized_count, critical_impacted_count
    outage: dict[str, Any]
    restoration: dict[str, Any]


# Fixture 1: Simple 3-node linear chain
FIXTURE_LINEAR_3NODE = FixtureScenarioExpectation(
    name="simple_linear_3node",
    description="3-node linear chain (A->B->C) with single source at A",
    edges=[
        {"edge_id": "A-B", "from_node": "A", "to_node": "B", "capacity": 100.0, "cost": 1.0},
        {"edge_id": "B-C", "from_node": "B", "to_node": "C", "capacity": 100.0, "cost": 1.0},
    ],
    source_nodes=["A"],
    critical_nodes=["C"],
    outage_edges=["B-C"],  # Block B-C edge
    restoration_edges=["B-C"],  # Restore it
    baseline={
        "supplied_count": 3,  # All nodes supplied
        "deenergized_count": 0,
        "critical_impacted_count": 0,
    },
    outage={
        "supplied_count": 2,  # A and B supplied, C deenergized
        "deenergized_count": 1,
        "critical_impacted_count": 1,  # C is critical and impacted
    },
    restoration={
        "supplied_count": 3,  # All nodes restored
        "deenergized_count": 0,
        "critical_impacted_count": 0,
    },
)


# Fixture 2: 5-node branching tree
FIXTURE_BRANCHING_5NODE = FixtureScenarioExpectation(
    name="simple_branching_5node",
    description="5-node tree: A with children B,C; B with children D,E",
    edges=[
        {"edge_id": "A-B", "from_node": "A", "to_node": "B", "capacity": 100.0, "cost": 1.0},
        {"edge_id": "A-C", "from_node": "A", "to_node": "C", "capacity": 100.0, "cost": 1.0},
        {"edge_id": "B-D", "from_node": "B", "to_node": "D", "capacity": 100.0, "cost": 1.0},
        {"edge_id": "B-E", "from_node": "B", "to_node": "E", "capacity": 100.0, "cost": 1.0},
    ],
    source_nodes=["A"],
    critical_nodes=["D", "E"],
    outage_edges=["A-B"],  # Cut off B subtree
    restoration_edges=["A-B"],
    baseline={
        "supplied_count": 5,
        "deenergized_count": 0,
        "critical_impacted_count": 0,
    },
    outage={
        "supplied_count": 2,  # Only A and C supplied
        "deenergized_count": 3,  # B, D, E deenergized
        "critical_impacted_count": 2,  # D and E are critical
    },
    restoration={
        "supplied_count": 5,
        "deenergized_count": 0,
        "critical_impacted_count": 0,
    },
)


# Fixture 3: 4-node mesh with redundancy
FIXTURE_MESH_4NODE = FixtureScenarioExpectation(
    name="simple_mesh_4node",
    description="4-node mesh: A connects to B,C; both B,C connect to D (redundant paths)",
    edges=[
        {"edge_id": "A-B", "from_node": "A", "to_node": "B", "capacity": 100.0, "cost": 1.0},
        {"edge_id": "A-C", "from_node": "A", "to_node": "C", "capacity": 100.0, "cost": 1.0},
        {"edge_id": "B-D", "from_node": "B", "to_node": "D", "capacity": 100.0, "cost": 1.0},
        {"edge_id": "C-D", "from_node": "C", "to_node": "D", "capacity": 100.0, "cost": 1.0},
    ],
    source_nodes=["A"],
    critical_nodes=["D"],
    outage_edges=["B-D"],  # Fail B-D, but C-D still provides path
    restoration_edges=["B-D"],
    baseline={
        "supplied_count": 4,
        "deenergized_count": 0,
        "critical_impacted_count": 0,
    },
    outage={
        "supplied_count": 4,  # D still reachable via C
        "deenergized_count": 0,
        "critical_impacted_count": 0,
    },
    restoration={
        "supplied_count": 4,
        "deenergized_count": 0,
        "critical_impacted_count": 0,
    },
)


# Fixture 4: Network with clearly identified critical nodes
FIXTURE_CRITICAL_NODE_SCENARIO = FixtureScenarioExpectation(
    name="critical_node_scenario",
    description="Network where specific nodes are marked critical for impact tracking",
    edges=[
        {"edge_id": "HUB-N1", "from_node": "HUB", "to_node": "N1", "capacity": 100.0, "cost": 1.0},
        {"edge_id": "HUB-N2", "from_node": "HUB", "to_node": "N2", "capacity": 100.0, "cost": 1.0},
        {"edge_id": "N1-D1", "from_node": "N1", "to_node": "D1", "capacity": 100.0, "cost": 1.0},
        {"edge_id": "N2-D2", "from_node": "N2", "to_node": "D2", "capacity": 100.0, "cost": 1.0},
    ],
    source_nodes=["HUB"],
    critical_nodes=["D1", "D2"],
    outage_edges=["N1-D1"],
    restoration_edges=["N1-D1"],
    baseline={
        "supplied_count": 5,
        "deenergized_count": 0,
        "critical_impacted_count": 0,
    },
    outage={
        "supplied_count": 4,
        "deenergized_count": 1,  # D1 deenergized
        "critical_impacted_count": 1,  # D1 is critical
    },
    restoration={
        "supplied_count": 5,
        "deenergized_count": 0,
        "critical_impacted_count": 0,
    },
)


# All fixtures for parametrized tests
ALL_FIXTURES = [
    FIXTURE_LINEAR_3NODE,
    FIXTURE_BRANCHING_5NODE,
    FIXTURE_MESH_4NODE,
    FIXTURE_CRITICAL_NODE_SCENARIO,
]


@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=[f.name for f in ALL_FIXTURES])
def test_deterministic_scenario_fixture(fixture: FixtureScenarioExpectation) -> None:
    """Test that scenario runner produces expected results for deterministic fixtures.

    This test detects unintended behavior drift in the scenario runner logic.
    """
    graph = build_network_graph(fixture.edges, directed=True)

    result = run_utility_scenarios(
        graph,
        source_nodes=fixture.source_nodes,
        critical_nodes=fixture.critical_nodes,
        outage_edges=fixture.outage_edges,
        restoration_edges=fixture.restoration_edges,
    )

    # Validate baseline
    assert result["baseline"]["supplied_count"] == fixture.baseline["supplied_count"], (
        f"{fixture.name}: baseline supplied_count mismatch. "
        f"Expected {fixture.baseline['supplied_count']}, got {result['baseline']['supplied_count']}"
    )
    assert result["baseline"]["deenergized_count"] == fixture.baseline["deenergized_count"], (
        f"{fixture.name}: baseline deenergized_count mismatch"
    )
    assert result["baseline"]["critical_impacted_count"] == fixture.baseline["critical_impacted_count"], (
        f"{fixture.name}: baseline critical_impacted_count mismatch"
    )

    # Validate outage
    assert result["outage"]["supplied_count"] == fixture.outage["supplied_count"], (
        f"{fixture.name}: outage supplied_count mismatch. "
        f"Expected {fixture.outage['supplied_count']}, got {result['outage']['supplied_count']}"
    )
    assert result["outage"]["deenergized_count"] == fixture.outage["deenergized_count"], (
        f"{fixture.name}: outage deenergized_count mismatch. "
        f"Expected {fixture.outage['deenergized_count']}, got {result['outage']['deenergized_count']}"
    )
    assert result["outage"]["critical_impacted_count"] == fixture.outage["critical_impacted_count"], (
        f"{fixture.name}: outage critical_impacted_count mismatch"
    )

    # Validate restoration
    assert result["restoration"]["supplied_count"] == fixture.restoration["supplied_count"], (
        f"{fixture.name}: restoration supplied_count mismatch"
    )
    assert result["restoration"]["deenergized_count"] == fixture.restoration["deenergized_count"], (
        f"{fixture.name}: restoration deenergized_count mismatch"
    )
    assert result["restoration"]["critical_impacted_count"] == fixture.restoration["critical_impacted_count"], (
        f"{fixture.name}: restoration critical_impacted_count mismatch"
    )


def test_fixture_linear_3node_expects_downstream_impact() -> None:
    """Specific test: linear chain demonstrates downstream impact of edge failure."""
    fixture = FIXTURE_LINEAR_3NODE
    graph = build_network_graph(fixture.edges, directed=True)

    result = run_utility_scenarios(
        graph,
        source_nodes=fixture.source_nodes,
        critical_nodes=fixture.critical_nodes,
        outage_edges=fixture.outage_edges,
    )

    # When B-C is blocked, C should be in deenergized_nodes
    assert "C" in result["outage"]["deenergized_nodes"]
    assert len(result["outage"]["deenergized_nodes"]) == 1


def test_fixture_branching_5node_subtree_isolation() -> None:
    """Specific test: branching network shows subtree isolation on parent edge failure."""
    fixture = FIXTURE_BRANCHING_5NODE
    graph = build_network_graph(fixture.edges, directed=True)

    result = run_utility_scenarios(
        graph,
        source_nodes=fixture.source_nodes,
        critical_nodes=fixture.critical_nodes,
        outage_edges=fixture.outage_edges,
    )

    # When A-B is blocked, entire B subtree should be deenergized
    deenergized = set(result["outage"]["deenergized_nodes"])
    assert deenergized == {"B", "D", "E"}


def test_fixture_mesh_4node_redundancy_preservation() -> None:
    """Specific test: redundant mesh preserves connectivity despite single edge failure."""
    fixture = FIXTURE_MESH_4NODE
    graph = build_network_graph(fixture.edges, directed=True)

    result = run_utility_scenarios(
        graph,
        source_nodes=fixture.source_nodes,
        critical_nodes=fixture.critical_nodes,
        outage_edges=fixture.outage_edges,
    )

    # D should remain supplied via alternative path C-D
    assert "D" not in result["outage"]["deenergized_nodes"]
    assert result["outage"]["supplied_count"] == 4  # All nodes remain supplied


def test_all_fixtures_restoration_equals_baseline() -> None:
    """Test that restoration phase always returns to baseline state."""
    for fixture in ALL_FIXTURES:
        graph = build_network_graph(fixture.edges, directed=True)

        result = run_utility_scenarios(
            graph,
            source_nodes=fixture.source_nodes,
            critical_nodes=fixture.critical_nodes,
            outage_edges=fixture.outage_edges,
            restoration_edges=fixture.restoration_edges,
        )

        # Restoration should match baseline
        assert result["restoration"]["supplied_count"] == result["baseline"]["supplied_count"], (
            f"{fixture.name}: restoration doesn't match baseline in supplied_count"
        )
        assert result["restoration"]["deenergized_count"] == result["baseline"]["deenergized_count"], (
            f"{fixture.name}: restoration doesn't match baseline in deenergized_count"
        )
        assert result["restoration"]["critical_impacted_count"] == result["baseline"]["critical_impacted_count"], (
            f"{fixture.name}: restoration doesn't match baseline in critical_impacted_count"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
