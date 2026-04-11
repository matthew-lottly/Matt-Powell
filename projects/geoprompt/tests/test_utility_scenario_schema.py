"""Schema contract tests for utility-scenario output.

Validates that the utility-scenario JSON output conforms to an expected
structure and data types, catching unintended breaking changes early.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest


def _validate_scenario_snapshot(snapshot: dict[str, Any], scenario_name: str) -> None:
    """Validate structure of a single scenario snapshot (baseline/outage/restoration)."""
    required_keys = {
        "supplied_count",
        "deenergized_count",
        "critical_impacted_count",
        "deenergized_nodes",
        "critical_impacted_nodes",
    }
    missing = required_keys - set(snapshot.keys())
    assert not missing, f"{scenario_name} snapshot missing keys: {missing}"

    # Type checks
    assert isinstance(snapshot["supplied_count"], int), f"{scenario_name}.supplied_count must be int"
    assert isinstance(snapshot["deenergized_count"], int), f"{scenario_name}.deenergized_count must be int"
    assert isinstance(snapshot["critical_impacted_count"], int), f"{scenario_name}.critical_impacted_count must be int"
    assert isinstance(snapshot["deenergized_nodes"], list), f"{scenario_name}.deenergized_nodes must be list"
    assert isinstance(snapshot["critical_impacted_nodes"], list), f"{scenario_name}.critical_impacted_nodes must be list"

    # All node lists should contain strings
    for node in snapshot["deenergized_nodes"]:
        assert isinstance(node, str), f"{scenario_name}.deenergized_nodes must contain strings"
    for node in snapshot["critical_impacted_nodes"]:
        assert isinstance(node, str), f"{scenario_name}.critical_impacted_nodes must contain strings"

    # Counts should be non-negative
    assert snapshot["supplied_count"] >= 0, f"{scenario_name}.supplied_count must be >= 0"
    assert snapshot["deenergized_count"] >= 0, f"{scenario_name}.deenergized_count must be >= 0"
    assert snapshot["critical_impacted_count"] >= 0, f"{scenario_name}.critical_impacted_count must be >= 0"


def _validate_scenario_delta(delta: dict[str, Any], delta_name: str) -> None:
    """Validate structure of a delta snapshot (differences between scenarios)."""
    required_keys = {"supplied_count", "deenergized_count", "critical_impacted_count"}
    missing = required_keys - set(delta.keys())
    assert not missing, f"{delta_name} missing keys: {missing}"

    # Type checks
    assert isinstance(delta["supplied_count"], int), f"{delta_name}.supplied_count must be int"
    assert isinstance(delta["deenergized_count"], int), f"{delta_name}.deenergized_count must be int"
    assert isinstance(delta["critical_impacted_count"], int), f"{delta_name}.critical_impacted_count must be int"


def test_utility_scenario_output_schema_with_sample_network() -> None:
    """Test utility-scenario JSON output schema with built-in sample network."""
    from geoprompt.demo import _run_utility_scenario
    from geoprompt.validation import SCHEMA_VERSION
    import argparse

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Create minimal args for utility-scenario command
        args = argparse.Namespace(
            command="utility-scenario",
            output_dir=output_dir,
            output_format="json",
            scenario_file=None,
            network_json=None,
            source_nodes=None,
            critical_nodes=None,
            outage_edges=None,
            restoration_edges=None,
            candidate_edges=None,
            static_blocked_edges=None,
            directed=False,
            device_type_field="device_type",
            state_field="state",
            unknown_state_policy="passable",
        )

        # Run the utility scenario
        _run_utility_scenario(args)

        # Load the output JSON
        output_file = output_dir / "geoprompt_utility_scenario.json"
        assert output_file.exists(), f"Output file not created at {output_file}"

        with open(output_file, "r", encoding="utf-8") as fh:
            payload = json.load(fh)

        # Validate top-level structure
        required_keys = {
            "schema_version",
            "command",
            "inputs",
            "baseline",
            "outage",
            "restoration",
            "delta_outage_vs_baseline",
            "delta_restoration_vs_outage",
        }
        missing = required_keys - set(payload.keys())
        assert not missing, f"Output missing required keys: {missing}"

        # Validate schema version
        assert payload["schema_version"] == SCHEMA_VERSION

        # Validate command
        assert payload["command"] == "utility-scenario"

        # Validate inputs structure
        inputs = payload["inputs"]
        assert isinstance(inputs, dict)
        input_keys = {
            "source_nodes",
            "critical_nodes",
            "outage_edges",
            "restoration_edges",
            "static_blocked_edges",
            "candidate_critical_edges",
            "device_type_field",
            "state_field",
            "unknown_state_policy",
        }
        missing_input = input_keys - set(inputs.keys())
        assert not missing_input, f"inputs missing keys: {missing_input}"

        # All node/edge lists should be lists
        assert isinstance(inputs["source_nodes"], list)
        assert isinstance(inputs["critical_nodes"], list)
        assert isinstance(inputs["outage_edges"], list)
        assert isinstance(inputs["restoration_edges"], list)
        assert isinstance(inputs["static_blocked_edges"], list)

        # Validate snapshots
        _validate_scenario_snapshot(payload["baseline"], "baseline")
        _validate_scenario_snapshot(payload["outage"], "outage")
        _validate_scenario_snapshot(payload["restoration"], "restoration")

        # Validate deltas
        _validate_scenario_delta(payload["delta_outage_vs_baseline"], "delta_outage_vs_baseline")
        _validate_scenario_delta(payload["delta_restoration_vs_outage"], "delta_restoration_vs_outage")

        # Sanity checks: outage should have more deenergized nodes than baseline
        assert payload["outage"]["deenergized_count"] >= payload["baseline"]["deenergized_count"]

        # Restoration should recover some or all nodes
        assert payload["restoration"]["deenergized_count"] <= payload["outage"]["deenergized_count"]


def test_utility_scenario_output_csv_format() -> None:
    """Test utility-scenario CSV output format and schema."""
    from geoprompt.demo import _run_utility_scenario
    import argparse
    import csv

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        args = argparse.Namespace(
            command="utility-scenario",
            output_dir=output_dir,
            output_format="csv",
            scenario_file=None,
            network_json=None,
            source_nodes=None,
            critical_nodes=None,
            outage_edges=None,
            restoration_edges=None,
            candidate_edges=None,
            static_blocked_edges=None,
            directed=False,
            device_type_field="device_type",
            state_field="state",
            unknown_state_policy="passable",
        )

        _run_utility_scenario(args)

        output_file = output_dir / "geoprompt_utility_scenario.csv"
        assert output_file.exists()

        with open(output_file, "r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        # Should have exactly 3 rows (baseline, outage, restoration)
        assert len(rows) == 3

        # Each row should have required columns
        required_cols = {
            "scenario",
            "supplied_count",
            "deenergized_count",
            "critical_impacted_count",
            "deenergized_nodes",
            "critical_impacted_nodes",
        }

        for row in rows:
            missing = required_cols - set(row.keys())
            assert not missing, f"CSV row missing columns: {missing}"

            # scenario should be one of the three
            assert row["scenario"] in {"baseline", "outage", "restoration"}

            # Counts should be parseable as integers
            assert int(row["supplied_count"]) >= 0
            assert int(row["deenergized_count"]) >= 0
            assert int(row["critical_impacted_count"]) >= 0

        # Verify scenario order
        scenarios = [row["scenario"] for row in rows]
        assert scenarios == ["baseline", "outage", "restoration"]


def test_utility_scenario_output_consistency() -> None:
    """Test that utility-scenario output is deterministic for same inputs."""
    from geoprompt.demo import _run_utility_scenario
    import argparse

    def run_scenario() -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            args = argparse.Namespace(
                command="utility-scenario",
                output_dir=output_dir,
                output_format="json",
                scenario_file=None,
                network_json=None,
                source_nodes=None,
                critical_nodes=None,
                outage_edges=None,
                restoration_edges=None,
                candidate_edges=None,
                static_blocked_edges=None,
                directed=False,
                device_type_field="device_type",
                state_field="state",
                unknown_state_policy="passable",
            )
            _run_utility_scenario(args)

            with open(output_dir / "geoprompt_utility_scenario.json", "r", encoding="utf-8") as fh:
                return json.load(fh)

    run1 = run_scenario()
    run2 = run_scenario()

    # The core scenario results should be identical
    assert run1["baseline"] == run2["baseline"], "Baseline results differ between runs"
    assert run1["outage"] == run2["outage"], "Outage results differ between runs"
    assert run1["restoration"] == run2["restoration"], "Restoration results differ between runs"
    assert run1["delta_outage_vs_baseline"] == run2["delta_outage_vs_baseline"]
    assert run1["delta_restoration_vs_outage"] == run2["delta_restoration_vs_outage"]


def test_utility_scenario_number_constraints() -> None:
    """Test numeric relationships and constraints in utility scenario output."""
    from geoprompt.demo import _run_utility_scenario
    import argparse

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        args = argparse.Namespace(
            command="utility-scenario",
            output_dir=output_dir,
            output_format="json",
            scenario_file=None,
            network_json=None,
            source_nodes=None,
            critical_nodes=None,
            outage_edges=None,
            restoration_edges=None,
            candidate_edges=None,
            static_blocked_edges=None,
            directed=False,
            device_type_field="device_type",
            state_field="state",
            unknown_state_policy="passable",
        )

        _run_utility_scenario(args)

        with open(output_dir / "geoprompt_utility_scenario.json", "r", encoding="utf-8") as fh:
            payload = json.load(fh)

        b = payload["baseline"]
        o = payload["outage"]
        r = payload["restoration"]

        # Length of deenergized_nodes should match deenergized_count
        assert len(b["deenergized_nodes"]) == b["deenergized_count"]
        assert len(o["deenergized_nodes"]) == o["deenergized_count"]
        assert len(r["deenergized_nodes"]) == r["deenergized_count"]

        # Same for critical impacted
        assert len(b["critical_impacted_nodes"]) == b["critical_impacted_count"]
        assert len(o["critical_impacted_nodes"]) == o["critical_impacted_count"]
        assert len(r["critical_impacted_nodes"]) == r["critical_impacted_count"]

        # Deltas should reflect differences
        d_out = payload["delta_outage_vs_baseline"]
        d_res = payload["delta_restoration_vs_outage"]

        assert d_out["supplied_count"] == o["supplied_count"] - b["supplied_count"]
        assert d_out["deenergized_count"] == o["deenergized_count"] - b["deenergized_count"]
        assert d_out["critical_impacted_count"] == o["critical_impacted_count"] - b["critical_impacted_count"]

        assert d_res["supplied_count"] == r["supplied_count"] - o["supplied_count"]
        assert d_res["deenergized_count"] == r["deenergized_count"] - o["deenergized_count"]
        assert d_res["critical_impacted_count"] == r["critical_impacted_count"] - o["critical_impacted_count"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
