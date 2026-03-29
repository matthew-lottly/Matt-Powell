from pathlib import Path

from monitoring_anomaly_detection.pipeline import AnomalyDetectionWorkflow, build_anomaly_report, export_anomaly_report, load_observations


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_load_observations() -> None:
    observations = load_observations(PROJECT_ROOT / "data" / "station_observations.csv")

    assert len(observations) == 18
    assert observations[0]["stationId"] == "station-central-flow-010"
    assert observations[-1]["stationId"] == "station-west-air-001"
    assert sum(observation["isKnownEvent"] for observation in observations) == 4


def test_build_anomaly_report() -> None:
    report = build_anomaly_report(PROJECT_ROOT / "data" / "station_observations.csv")

    assert report["experiment"]["runLabel"] == "detector-comparison-pass"
    assert report["experiment"]["registryFile"] == "run_registry.json"
    assert report["summary"]["stationCount"] == 3
    assert report["summary"]["knownEventCount"] == 4
    assert report["summary"]["selectedAlertCount"] >= 3
    assert report["summary"]["selectedDetector"] in {"global_zscore", "rolling_zscore", "mad_score", "delta_zscore"}
    assert len(report["detectorLeaderboard"]) == 4
    assert report["detectorLeaderboard"][0]["f1Score"] >= report["detectorLeaderboard"][1]["f1Score"]
    assert report["rankedEvents"][0]["scores"][report["summary"]["selectedDetector"]] >= report["rankedEvents"][1]["scores"][report["summary"]["selectedDetector"]]
    assert report["selectedAlerts"][0]["selectedDetector"] == report["summary"]["selectedDetector"]


def test_export_anomaly_report(tmp_path: Path) -> None:
    output_path = export_anomaly_report(tmp_path, report_name="Telemetry Watch")

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "Telemetry Watch" in content
    assert "detector-comparison-pass" in content
    assert "anomaly_report.json" in str(output_path)
    registry_path = tmp_path / "run_registry.json"
    assert registry_path.exists()
    registry = registry_path.read_text(encoding="utf-8")
    assert "Telemetry Watch" in registry
    assert "anomaly_report.json" in registry


def test_anomaly_detection_workflow_class() -> None:
    workflow = AnomalyDetectionWorkflow(data_path=PROJECT_ROOT / "data" / "station_observations.csv")

    report = workflow.build_report()

    assert report["reportName"] == "Monitoring Anomaly Detection"
    assert report["summary"]["stationCount"] == 3
    assert report["summary"]["selectedDetector"] in {"global_zscore", "rolling_zscore", "mad_score", "delta_zscore"}