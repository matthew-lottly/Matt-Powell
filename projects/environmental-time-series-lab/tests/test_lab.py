from pathlib import Path

from environmental_time_series_lab.lab import build_time_series_report, export_time_series_report, load_histories


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_load_histories() -> None:
    histories = load_histories(PROJECT_ROOT / "data" / "station_histories.json")

    assert len(histories) == 3
    assert histories[0]["stationId"] == "station-west-air-001"


def test_build_time_series_report() -> None:
    report = build_time_series_report(PROJECT_ROOT / "data" / "station_histories.json")

    assert report["summary"]["seriesCount"] == 3
    assert report["summary"]["upwardTrends"] == 2
    assert report["seriesSummaries"][0]["trendLabel"] == "upward"
    assert len(report["seriesSummaries"][0]["rollingMean"]) == 5


def test_export_time_series_report(tmp_path: Path) -> None:
    output_path = export_time_series_report(tmp_path, report_name="Temporal Review")

    assert output_path.exists()
    assert "Temporal Review" in output_path.read_text(encoding="utf-8")
