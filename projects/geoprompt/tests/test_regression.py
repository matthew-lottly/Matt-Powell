"""Item 42: Regression snapshot tests for report output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from geoprompt.demo import build_demo_report
from geoprompt.types import DemoReport


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _build_report(tmp_path: Path) -> DemoReport:
    return cast(
        DemoReport,
        build_demo_report(
            input_path=PROJECT_ROOT / "data" / "sample_features.json",
            output_dir=tmp_path,
        ),
    )


def test_report_structure_regression(tmp_path: Path) -> None:
    """Verify the report structure has all expected top-level keys."""
    report = _build_report(tmp_path)
    expected_keys = {
        "package", "schema_version", "equations", "summary",
        "top_interactions", "top_area_similarity",
        "top_nearest_neighbors", "top_geographic_neighbors",
        "records", "outputs",
    }
    assert set(report.keys()) == expected_keys


def test_report_summary_regression(tmp_path: Path) -> None:
    """Verify summary fields are consistent."""
    report = _build_report(tmp_path)
    summary = report["summary"]
    assert summary["feature_count"] == 6
    assert summary["crs"] == "EPSG:4326"
    assert summary["geometry_types"] == ["LineString", "Point", "Polygon"]
    assert summary["valley_window_feature_count"] == 3


def test_report_record_count_regression(tmp_path: Path) -> None:
    """Verify record count is stable."""
    report = _build_report(tmp_path)
    assert len(report["records"]) == 6


def test_report_top_n_regression(tmp_path: Path) -> None:
    """Verify top-N lists have expected sizes."""
    report = _build_report(tmp_path)
    assert len(report["top_interactions"]) == 5
    assert len(report["top_area_similarity"]) == 5
    assert len(report["top_nearest_neighbors"]) == 6
    assert len(report["top_geographic_neighbors"]) == 6


def test_report_is_json_serializable(tmp_path: Path) -> None:
    """Verify the full report can be serialized to JSON without error."""
    report = _build_report(tmp_path)
    serialized = json.dumps(report, indent=2)
    assert len(serialized) > 100
    reloaded = json.loads(serialized)
    assert reloaded["package"] == "geoprompt"


def test_report_schema_version(tmp_path: Path) -> None:
    """Verify schema_version is present."""
    report = _build_report(tmp_path)
    assert "schema_version" in report
    assert report["schema_version"] == "1.0.0"


def test_report_deterministic_ordering(tmp_path: Path) -> None:
    """Item 4: Verify records are in deterministic sorted order."""
    report = _build_report(tmp_path)
    site_ids = [r["site_id"] for r in report["records"]]
    assert site_ids == sorted(site_ids)


# ---- Demo smoke test (merged from test_demo_smoke.py) ----


def test_build_demo_report_writes_chart_output(tmp_path: Path) -> None:
    """Smoke test: report runs end-to-end and produces chart output."""
    report = cast(DemoReport, build_demo_report(PROJECT_ROOT / "data" / "sample_features.json", tmp_path))
    assert report["summary"]["feature_count"] > 0
    assert Path(report["outputs"]["chart"]).exists()
    assert report["summary"]["crs"] == "EPSG:4326"
