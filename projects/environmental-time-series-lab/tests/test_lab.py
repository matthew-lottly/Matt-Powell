from pathlib import Path

from environmental_time_series_lab.lab import build_time_series_report, export_time_series_report, load_histories


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_load_histories() -> None:
    histories = load_histories(PROJECT_ROOT / "data" / "station_histories.json")

    assert len(histories) == 3
    assert histories[0]["stationId"] == "station-west-air-001"


def test_build_time_series_report() -> None:
    report = build_time_series_report(PROJECT_ROOT / "data" / "station_histories.json")

    assert report["experiment"]["runLabel"] == "temporal-diagnostics-review"
    assert report["experiment"]["registryFile"] == "run_registry.json"
    assert report["summary"]["seriesCount"] == 3
    assert report["summary"]["reviewWindow"] == 2
    assert report["summary"]["averageSelectedReviewMae"] == 0.41
    assert report["summary"]["trendLabels"] == {"downward": 1, "upward": 2}
    assert report["summary"]["baselineWins"] == {"drift": 1, "last_value": 1, "trailing_mean_3": 1}
    assert report["seriesDiagnostics"][0]["trendLabel"] == "upward"
    assert report["seriesDiagnostics"][0]["selectedBaseline"] == "drift"
    assert report["seriesDiagnostics"][0]["selectedReviewMae"] == 0.05
    assert len(report["seriesDiagnostics"][0]["rollingMeanShort"]) == 5
    assert len(report["seriesDiagnostics"][0]["rollingMeanLong"]) == 3
    assert len(report["seriesDiagnostics"][0]["baselineLeaderboard"]) == 4


def test_export_time_series_report(tmp_path: Path) -> None:
    output_path = export_time_series_report(tmp_path, report_name="Temporal Review")

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "Temporal Review" in content
    assert "temporal-diagnostics-review" in content
    registry_path = tmp_path / "run_registry.json"
    assert registry_path.exists()
    registry = registry_path.read_text(encoding="utf-8")
    assert "Temporal Review" in registry
    assert "time_series_report.json" in registry
