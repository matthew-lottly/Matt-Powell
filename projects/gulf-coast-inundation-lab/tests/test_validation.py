from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from gulf_coast_inundation_lab.validation import GulfCoastValidationWorkflow, _coefficient_of_determination, build_validation_report, main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = PROJECT_ROOT / "data" / "gauge_validation_sample.csv"
MANIFEST_PATH = PROJECT_ROOT / "data" / "gauge_validation_manifest.geojson"


def test_coefficient_of_determination_detects_strong_relation() -> None:
    r_squared, slope, intercept = _coefficient_of_determination([1.0, 2.0, 3.0, 4.0], [2.0, 4.0, 6.0, 8.0])

    assert r_squared == 1.0
    assert slope == 2.0
    assert intercept == 0.0


def test_build_validation_report_ranks_gauges() -> None:
    report = build_validation_report(SAMPLE_PATH)

    assert report["summary"]["gaugeCount"] == 3
    assert report["summary"]["adequateGaugeCount"] >= 1
    assert report["gauges"][0]["gaugeId"] == "07374000"
    assert report["gauges"][-1]["gaugeId"] == "02375500"


def test_export_report_writes_summary_and_registry(tmp_path: Path) -> None:
    output_path = GulfCoastValidationWorkflow(input_path=SAMPLE_PATH).export_report(tmp_path)
    report = json.loads(output_path.read_text(encoding="utf-8"))
    registry = json.loads((tmp_path / "run_registry.json").read_text(encoding="utf-8"))

    assert output_path.name == "gulf_coast_validation_summary.json"
    assert report["summary"]["gaugeCount"] == 3
    assert registry["runs"][0]["reportFile"] == output_path.name


def test_main_writes_report_from_cli_arguments(tmp_path: Path) -> None:
    with patch(
        "sys.argv",
        [
            "gulf-coast-validation",
            "--input-path",
            str(SAMPLE_PATH),
            "--output-dir",
            str(tmp_path),
        ],
    ):
        main()

    assert (tmp_path / "gulf_coast_validation_summary.json").exists()
    assert (tmp_path / "run_registry.json").exists()


def test_manifest_contains_ten_public_gauges() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["type"] == "FeatureCollection"
    assert len(manifest["features"]) == 10
    assert manifest["features"][0]["properties"]["gaugeId"] == "02358000"