from pathlib import Path

from station_risk_classification_lab.lab import RiskClassificationLab, build_risk_report, export_risk_report, load_samples


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_load_samples() -> None:
    samples = load_samples(PROJECT_ROOT / "data" / "station_risk_samples.json")

    assert len(samples) == 9
    assert samples[0]["stationId"] == "station-west-air-001"
    assert samples[-1]["riskLabel"] == "high"


def test_build_risk_report() -> None:
    report = build_risk_report(PROJECT_ROOT / "data" / "station_risk_samples.json")

    assert report["experiment"]["runLabel"] == "candidate-classifier-review"
    assert report["experiment"]["registryFile"] == "run_registry.json"
    assert report["summary"]["sampleCount"] == 9
    assert report["summary"]["trainCount"] == 6
    assert report["summary"]["testCount"] == 3
    assert report["summary"]["selectedModel"] in {"scorecard_classifier", "centroid_classifier", "profile_rules"}
    assert report["summary"]["selectedAccuracy"] >= 0.67
    assert report["summary"]["selectedF1"] >= 0.8
    assert len(report["modelLeaderboard"]) == 3
    assert report["modelLeaderboard"][0]["f1Score"] >= report["modelLeaderboard"][1]["f1Score"]
    assert len(report["testCases"]) == 3
    assert len(report["testCases"][0]["topRiskDrivers"]) == 3


def test_risk_classification_lab_class() -> None:
    lab = RiskClassificationLab(data_path=PROJECT_ROOT / "data" / "station_risk_samples.json")

    report = lab.build_report()

    assert report["reportName"] == "Station Risk Classification Lab"
    assert report["summary"]["classDistribution"] == {"high": 4, "low": 5}
    assert report["trainingProfile"]["sampleCount"] == 6


def test_export_risk_report(tmp_path: Path) -> None:
    output_path = export_risk_report(tmp_path, report_name="Risk Review")

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "Risk Review" in content
    assert "candidate-classifier-review" in content
    registry_path = tmp_path / "run_registry.json"
    assert registry_path.exists()
    registry = registry_path.read_text(encoding="utf-8")
    assert "Risk Review" in registry
    assert "station_risk_report.json" in registry