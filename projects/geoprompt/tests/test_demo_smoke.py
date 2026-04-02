from __future__ import annotations

from pathlib import Path

from geoprompt.demo import build_demo_report


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_build_demo_report_writes_chart_output(tmp_path: Path) -> None:
    report = build_demo_report(PROJECT_ROOT / "data" / "sample_features.json", tmp_path)

    assert report["summary"]["feature_count"] > 0
    assert Path(report["outputs"]["chart"]).exists()
    assert report["summary"]["crs"] == "EPSG:4326"
