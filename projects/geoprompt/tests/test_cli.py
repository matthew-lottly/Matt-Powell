"""Item 48: CLI integration tests for all flags."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_demo(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "geoprompt.demo", *args],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=120,
    )


def test_cli_dry_run() -> None:
    """Item 29: Verify dry-run mode validates without writing."""
    result = _run_demo("--dry-run", "--verbose")
    assert result.returncode == 0


def test_cli_no_plot(tmp_path: Path) -> None:
    """Item 23: Verify --no-plot flag."""
    result = _run_demo("--no-plot", "--no-asset-copy", "--output-dir", str(tmp_path))
    assert result.returncode == 0


def test_cli_skip_expensive(tmp_path: Path) -> None:
    """Item 27: Verify --skip-expensive flag."""
    result = _run_demo("--skip-expensive", "--no-asset-copy", "--output-dir", str(tmp_path))
    assert result.returncode == 0


def test_cli_csv_format(tmp_path: Path) -> None:
    """Item 22: Verify --format csv."""
    result = _run_demo("--format", "csv", "--no-asset-copy", "--output-dir", str(tmp_path))
    assert result.returncode == 0


def test_cli_verbose_flag(tmp_path: Path) -> None:
    """Item 18: Verify --verbose flag."""
    result = _run_demo("--verbose", "--dry-run")
    assert result.returncode == 0


def test_cli_help() -> None:
    """Verify --help works."""
    result = _run_demo("--help")
    assert result.returncode == 0
    assert "GeoPrompt" in result.stdout


def test_cli_accessibility_command(tmp_path: Path) -> None:
    result = _run_demo(
        "accessibility",
        "--format",
        "csv",
        "--output-dir",
        str(tmp_path),
        "--no-asset-copy",
    )
    assert result.returncode == 0


def test_cli_gravity_flow_command(tmp_path: Path) -> None:
    result = _run_demo(
        "gravity-flow",
        "--format",
        "json",
        "--output-dir",
        str(tmp_path),
        "--no-asset-copy",
    )
    assert result.returncode == 0


def test_cli_suitability_command(tmp_path: Path) -> None:
    result = _run_demo(
        "suitability",
        "--format",
        "json",
        "--output-dir",
        str(tmp_path),
        "--no-asset-copy",
        "--criteria-columns",
        "demand_index",
        "capacity_index",
        "priority_index",
    )
    assert result.returncode == 0


@pytest.mark.parametrize(
    "tool",
    [
        "accessibility",
        "gravity-flow",
        "suitability",
        "catchment-competition",
        "hotspot-scan",
        "equity-gap",
        "network-reliability",
        "transit-service-gap",
        "congestion-hotspots",
        "walkability-audit",
        "gentrification-scan",
        "land-value-surface",
        "pollution-surface",
        "habitat-fragmentation-map",
        "climate-vulnerability-map",
        "migration-pull-map",
        "mortality-risk-map",
        "market-power-map",
        "trade-corridor-map",
        "community-cohesion-map",
        "cultural-similarity-matrix",
        "noise-impact-map",
        "visual-prominence-map",
    ],
)
def test_cli_analyze_command_all_tools(tool: str, tmp_path: Path) -> None:
    """Unified analyze command works for every registered tool with default columns."""
    result = _run_demo(
        "analyze",
        "--tool",
        tool,
        "--format",
        "json",
        "--output-dir",
        str(tmp_path),
    )
    assert result.returncode == 0, result.stderr


def test_cli_analyze_command_no_tool_exits_nonzero() -> None:
    """analyze command without --tool should exit with non-zero code."""
    result = _run_demo("analyze")
    assert result.returncode != 0


def test_cli_analyze_command_custom_columns(tmp_path: Path) -> None:
    """analyze command accepts --columns to override defaults."""
    result = _run_demo(
        "analyze",
        "--tool",
        "hotspot-scan",
        "--columns",
        "capacity_index",
        "--format",
        "csv",
        "--output-dir",
        str(tmp_path),
    )
    assert result.returncode == 0
