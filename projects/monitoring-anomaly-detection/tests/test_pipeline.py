from pathlib import Path

from monitoring_anomaly_detection.pipeline import build_anomaly_report, export_anomaly_report, load_observations


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_load_observations() -> None:
    observations = load_observations(PROJECT_ROOT / "data" / "station_observations.csv")

    assert len(observations) == 18
    assert observations[0]["stationId"] == "station-west-air-001"


def test_build_anomaly_report() -> None:
    report = build_anomaly_report(PROJECT_ROOT / "data" / "station_observations.csv")

    assert report["summary"]["stationCount"] == 3
    assert report["summary"]["anomalyCount"] == 4
    assert report["anomalies"][0]["stationId"] == "station-east-temp-203"
    assert report["anomalies"][0]["deviationScore"] >= report["anomalies"][1]["deviationScore"]


def test_export_anomaly_report(tmp_path: Path) -> None:
    output_path = export_anomaly_report(tmp_path, report_name="Telemetry Watch")

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "Telemetry Watch" in content
    assert "anomaly_report.json" in str(output_path)