from pathlib import Path

from station_forecasting_workbench.workbench import ForecastWorkbench, build_forecast_report, export_forecast_report, load_histories


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_load_histories() -> None:
    histories = load_histories(PROJECT_ROOT / "data" / "forecast_histories.json")

    assert len(histories) == 3
    assert histories[1]["stationId"] == "station-central-flow-010"


def test_build_forecast_report() -> None:
    report = build_forecast_report(PROJECT_ROOT / "data" / "forecast_histories.json")

    assert report["experiment"]["runLabel"] == "baseline-model-review"
    assert report["experiment"]["registryFile"] == "run_registry.json"
    assert report["summary"]["seriesCount"] == 3
    assert report["summary"]["validationHorizon"] == 1
    assert report["summary"]["testHorizon"] == 1
    assert report["summary"]["projectionHorizon"] == 3
    assert report["summary"]["averageValidationMae"] <= report["summary"]["averageTestMae"]
    assert report["forecasts"][0]["trainingWindow"] == 6
    assert report["forecasts"][0]["featureProfile"]["trailingMean3"] == 13.03
    assert report["forecasts"][0]["validationWindow"] == 1
    assert report["forecasts"][0]["testWindow"] == 1
    assert report["forecasts"][0]["selectedModel"] in {"drift", "linear_regression", "last_value", "trailing_average_3"}
    assert len(report["forecasts"][0]["modelLeaderboard"]) == 4
    assert report["forecasts"][0]["modelLeaderboard"][0]["validationMae"] <= report["forecasts"][0]["modelLeaderboard"][1]["validationMae"]
    assert report["forecasts"][0]["selectedFeatureSet"] in {"recent_level", "trend_profile"}
    assert len(report["forecasts"][0]["datasetSplit"]["validation"]) == 1
    assert len(report["forecasts"][0]["testPrediction"]) == 1
    assert len(report["forecasts"][0]["projection"]) == 3


def test_export_forecast_report(tmp_path: Path) -> None:
    output_path = export_forecast_report(tmp_path, report_name="Forecast Review")

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "Forecast Review" in content
    assert "baseline-model-review" in content
    registry_path = tmp_path / "run_registry.json"
    assert registry_path.exists()
    registry = registry_path.read_text(encoding="utf-8")
    assert "Forecast Review" in registry
    assert "station_forecast_report.json" in registry


def test_forecast_workbench_class() -> None:
    workbench = ForecastWorkbench(data_path=PROJECT_ROOT / "data" / "forecast_histories.json")

    report = workbench.build_report()

    assert report["reportName"] == "Station Forecasting Workbench"
    assert report["summary"]["seriesCount"] == 3
    assert report["forecasts"][0]["selectedModel"] in {"drift", "linear_regression", "last_value", "trailing_average_3"}