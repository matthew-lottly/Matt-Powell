"""Item 48: CLI integration tests for all flags."""

from __future__ import annotations

import json
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


def _read_output_records(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["records"]


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
        "drought-stress-map",
        "heat-island-map",
        "school-access-map",
        "healthcare-access-map",
        "food-desert-map",
        "digital-divide-map",
        "wildfire-risk-map",
        "emergency-response-map",
        "infrastructure-lifecycle-map",
        "adaptive-capacity-map",
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


def test_cli_analyze_command_with_chunk_size(tmp_path: Path) -> None:
    result = _run_demo(
        "analyze",
        "--tool",
        "hotspot-scan",
        "--chunk-size",
        "2",
        "--format",
        "json",
        "--output-dir",
        str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    output_path = tmp_path / "geoprompt_analyze_hotspot_scan.json"
    assert len(_read_output_records(output_path)) == 6


def test_cli_analyze_command_with_sample(tmp_path: Path) -> None:
    result = _run_demo(
        "analyze",
        "--tool",
        "hotspot-scan",
        "--sample",
        "0.5",
        "--format",
        "json",
        "--output-dir",
        str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    output_path = tmp_path / "geoprompt_analyze_hotspot_scan.json"
    assert len(_read_output_records(output_path)) == 3


def test_cli_analyze_command_invalid_sample_exits_nonzero(tmp_path: Path) -> None:
    result = _run_demo(
        "analyze",
        "--tool",
        "hotspot-scan",
        "--sample",
        "0",
        "--format",
        "json",
        "--output-dir",
        str(tmp_path),
    )
    assert result.returncode != 0
    assert "--sample must be between 0 and 1" in result.stderr


def test_cli_analyze_command_with_max_results(tmp_path: Path) -> None:
    result = _run_demo(
        "analyze",
        "--tool",
        "gravity-flow",
        "--max-results",
        "2",
        "--format",
        "json",
        "--output-dir",
        str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    output_path = tmp_path / "geoprompt_analyze_gravity_flow.json"
    assert len(_read_output_records(output_path)) == 2


def test_cli_analyze_command_with_max_distance(tmp_path: Path) -> None:
    result = _run_demo(
        "analyze",
        "--tool",
        "gravity-flow",
        "--max-distance",
        "0",
        "--format",
        "json",
        "--output-dir",
        str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    output_path = tmp_path / "geoprompt_analyze_gravity_flow.json"
    assert _read_output_records(output_path) == []


def test_cli_report_writes_manifest(tmp_path: Path) -> None:
    result = _run_demo(
        "report",
        "--no-plot",
        "--no-asset-copy",
        "--output-dir",
        str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    manifest = tmp_path / "manifests" / "geoprompt_report_manifest.json"
    assert manifest.exists()


def test_cli_analyze_writes_manifest(tmp_path: Path) -> None:
    result = _run_demo(
        "analyze",
        "--tool",
        "hotspot-scan",
        "--output-dir",
        str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    manifest = tmp_path / "manifests" / "geoprompt_analyze_hotspot_scan_manifest.json"
    assert manifest.exists()


def test_cli_pipeline_runs_steps_and_writes_checkpoint(tmp_path: Path) -> None:
        pipeline_file = tmp_path / "pipeline.json"
        pipeline_file.write_text(
                """
{
    "steps": [
        {"name": "scan", "command": "analyze", "tool": "hotspot-scan", "format": "json"},
        {"name": "report", "command": "report", "no_plot": true, "no_asset_copy": true}
    ]
}
                """.strip(),
                encoding="utf-8",
        )

        result = _run_demo(
                "pipeline",
                "--pipeline-file",
                str(pipeline_file),
                "--output-dir",
                str(tmp_path),
        )
        assert result.returncode == 0, result.stderr

        checkpoint = tmp_path / "checkpoints" / "geoprompt_pipeline_state.json"
        assert checkpoint.exists()
        pipeline_manifest = tmp_path / "manifests" / "geoprompt_pipeline_manifest.json"
        assert pipeline_manifest.exists()


def test_cli_pipeline_resume_skips_completed_steps(tmp_path: Path) -> None:
        pipeline_file = tmp_path / "pipeline_resume.json"
        pipeline_file.write_text(
                """
{
    "steps": [
        {"name": "scan", "command": "analyze", "tool": "hotspot-scan", "format": "json"},
        {"name": "flow", "command": "analyze", "tool": "gravity-flow", "format": "json", "max_results": 2}
    ]
}
                """.strip(),
                encoding="utf-8",
        )

        first = _run_demo(
                "pipeline",
                "--pipeline-file",
                str(pipeline_file),
                "--output-dir",
                str(tmp_path),
        )
        assert first.returncode == 0, first.stderr

        second = _run_demo(
                "pipeline",
                "--pipeline-file",
                str(pipeline_file),
                "--output-dir",
                str(tmp_path),
                "--resume",
        )
        assert second.returncode == 0, second.stderr


def test_cli_pipeline_continue_on_error_with_retries(tmp_path: Path) -> None:
    pipeline_file = tmp_path / "pipeline_continue.json"
    pipeline_file.write_text(
        """
{
    "steps": [
        {
            "name": "bad-step",
            "command": "analyze",
            "tool": "not-a-tool",
            "retries": 2,
            "continue_on_error": true
        },
        {
            "name": "good-step",
            "command": "analyze",
            "tool": "hotspot-scan",
            "format": "json"
        }
    ]
}
        """.strip(),
        encoding="utf-8",
    )

    result = _run_demo(
        "pipeline",
        "--pipeline-file",
        str(pipeline_file),
        "--output-dir",
        str(tmp_path),
    )
    assert result.returncode == 0, result.stderr

    checkpoint_payload = json.loads((tmp_path / "checkpoints" / "geoprompt_pipeline_state.json").read_text(encoding="utf-8"))
    assert checkpoint_payload["failed_steps"] == ["bad-step"]
    assert checkpoint_payload["completed_steps"] == ["good-step"]

    manifest_payload = json.loads((tmp_path / "manifests" / "geoprompt_pipeline_manifest.json").read_text(encoding="utf-8"))
    failed = [item for item in manifest_payload["extra"]["step_results"] if item["name"] == "bad-step"]
    completed = [item for item in manifest_payload["extra"]["step_results"] if item["name"] == "good-step"]
    assert failed[0]["attempts"] == 3
    assert failed[0]["status"] == "failed"
    assert completed[0]["status"] == "completed"


def test_cli_pipeline_batch_mode(tmp_path: Path) -> None:
    batch_dir = tmp_path / "inputs"
    batch_dir.mkdir(parents=True, exist_ok=True)
    source = PROJECT_ROOT / "data" / "sample_features.json"
    (batch_dir / "a.json").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (batch_dir / "b.json").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    pipeline_file = tmp_path / "pipeline_batch.json"
    pipeline_file.write_text(
        """
{
    "steps": [
        {"name": "scan", "command": "analyze", "tool": "hotspot-scan", "format": "json"},
        {"name": "report", "command": "report", "no_plot": true, "no_asset_copy": true}
    ]
}
        """.strip(),
        encoding="utf-8",
    )

    result = _run_demo(
        "pipeline",
        "--pipeline-file",
        str(pipeline_file),
        "--batch-input-dir",
        str(batch_dir),
        "--batch-pattern",
        "*.json",
        "--output-dir",
        str(tmp_path / "batch_outputs"),
    )
    assert result.returncode == 0, result.stderr

    base = tmp_path / "batch_outputs" / "batches"
    assert (base / "a" / "manifests" / "geoprompt_pipeline_manifest.json").exists()
    assert (base / "b" / "manifests" / "geoprompt_pipeline_manifest.json").exists()
    summary = tmp_path / "batch_outputs" / "geoprompt_pipeline_batch_summary.json"
    assert summary.exists()
