import importlib
from pathlib import Path
import sys
from typing import Any, cast

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

lab_module = cast(Any, importlib.import_module("environmental_time_series_lab.lab"))
TimeSeriesLab = lab_module.TimeSeriesLab
build_time_series_report = lab_module.build_time_series_report
export_time_series_report = lab_module.export_time_series_report
load_histories = lab_module.load_histories


def test_load_histories() -> None:
    histories = load_histories(PROJECT_ROOT / "data" / "station_histories.json")

    assert len(histories) == 3
    assert histories[0]["stationId"] == "station-west-air-001"


def test_build_time_series_report() -> None:
    report = build_time_series_report(PROJECT_ROOT / "data" / "station_histories.json")

    assert report["experiment"]["runLabel"] == "temporal-diagnostics-review"
    assert report["experiment"]["registryFile"] == "run_registry.json"
    assert report["experiment"]["candidateBaselineCount"] == 5
    assert report["experiment"]["seasonLength"] == 3
    assert report["summary"]["seriesCount"] == 3
    assert report["summary"]["reviewWindow"] == 2
    assert report["summary"]["averageSelectedReviewMae"] >= 0.0
    assert report["summary"]["averageSeasonalRange"] >= 0.0
    assert report["summary"]["trendLabels"] == {"downward": 1, "upward": 2}
    assert sum(report["summary"]["baselineWins"].values()) == 3
    assert report["seriesDiagnostics"][0]["trendLabel"] == "upward"
    assert report["seriesDiagnostics"][0]["selectedBaseline"] in {
        "drift",
        "last_value",
        "seasonal_naive",
        "trailing_mean_2",
        "trailing_mean_3",
    }
    assert report["seriesDiagnostics"][0]["selectedReviewMae"] >= 0.0
    assert len(report["seriesDiagnostics"][0]["rollingMeanShort"]) == 5
    assert len(report["seriesDiagnostics"][0]["rollingMeanLong"]) == 3
    assert len(report["seriesDiagnostics"][0]["baselineLeaderboard"]) == 5
    assert report["seriesDiagnostics"][0]["seasonalityProfile"]["seasonLength"] == 3
    assert report["seriesDiagnostics"][0]["changePointCandidate"]["direction"] in {"upward", "downward", "stable"}


def test_time_series_lab_class() -> None:
    lab = TimeSeriesLab(data_path=PROJECT_ROOT / "data" / "station_histories.json")

    report = lab.build_report()

    assert report["reportName"] == "Environmental Time Series Lab"
    assert report["summary"]["seriesCount"] == 3
    assert report["summary"]["seasonLength"] == 3
    assert "seasonalityProfile" in report["seriesDiagnostics"][0]


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
