from pathlib import Path

import pytest

from environmental_monitoring_analytics.reporting import build_html_report, build_markdown_report, compute_summary, export_reports


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_SNAPSHOT_PATH = PROJECT_ROOT / "data" / "api_observation_snapshot.json"


def test_compute_summary() -> None:
    summary = compute_summary()
    assert summary["total_observations"] == 7
    assert summary["alert_observations"] == 4
    assert summary["alert_rate"] == 0.5714
    assert summary["regional_alerts"][0][0] == "West"
    assert summary["regional_alerts"][0][1] == 2
    assert summary["time_window_trends"]["window_hours"] == 2
    assert summary["time_window_trends"]["recent"]["alert_observations"] == 3
    assert summary["time_window_trends"]["previous"]["alert_observations"] == 1
    assert summary["time_window_trends"]["direction"] == "improving"
    assert summary["category_breakdown"][0]["category"] == "air_quality"
    assert summary["category_breakdown"][0]["recent_alerts"][0][0] == "Sierra Air Quality Node"


def test_compute_summary_with_date_window() -> None:
    summary = compute_summary(start_date="2026-03-18", end_date="2026-03-18")
    assert summary["total_observations"] == 6
    assert summary["alert_observations"] == 4
    assert summary["report_period"] == {
        "start_date": "2026-03-18",
        "end_date": "2026-03-18",
        "comparison_start_date": "2026-03-17",
        "comparison_end_date": "2026-03-17",
    }
    assert summary["time_window_trends"]["window_hours"] is None
    assert summary["time_window_trends"]["recent"]["total_observations"] == 6
    assert summary["time_window_trends"]["previous"]["total_observations"] == 1
    assert summary["time_window_trends"]["direction"] == "worsening"


def test_markdown_report() -> None:
    report = build_markdown_report()
    assert "# Monitoring Operations Brief" in report
    assert "Alert observations: 4" in report
    assert "## Trend Window" in report
    assert "## Category Alert Breakdown" in report
    assert "Alert-rate direction: improving" in report
    assert "Sierra Air Quality Node" in report


def test_markdown_report_with_date_window() -> None:
    report = build_markdown_report(start_date="2026-03-18", end_date="2026-03-18")
    assert "## Report Period" in report
    assert "Window A: 2026-03-18 to 2026-03-18" in report
    assert "Window B: 2026-03-17 to 2026-03-17" in report
    assert "air_quality: 2 alerts out of 2 observations" in report


def test_html_report() -> None:
    report = build_html_report()
    assert "<title>Monitoring Operations Brief</title>" in report
    assert "Regional Alert Load" in report
    assert "Regional Trend Shift" in report
    assert "Custom date-range comparison" not in report
    assert "trend-badge" in report
    assert "Sierra Air Quality Node" in report


def test_html_report_with_date_window() -> None:
    report = build_html_report(start_date="2026-03-18", end_date="2026-03-18")
    assert "Custom date-range comparison" in report
    assert "Window A:</strong> 2026-03-18 to 2026-03-18" in report
    assert "Top Alerts" in report


def test_export_reports(tmp_path) -> None:
    outputs = export_reports(tmp_path)
    assert outputs["markdown"].exists()
    assert outputs["html"].exists()
    assert "Monitoring Operations Brief" in outputs["html"].read_text(encoding="utf-8")


def test_invalid_date_window_raises() -> None:
    with pytest.raises(ValueError, match="Both --start-date and --end-date"):
        compute_summary(start_date="2026-03-18")

    with pytest.raises(ValueError, match="on or after"):
        compute_summary(start_date="2026-03-18", end_date="2026-03-17")


def test_compute_summary_from_api_snapshot() -> None:
    summary = compute_summary(API_SNAPSHOT_PATH)
    assert summary["total_observations"] == 6
    assert summary["alert_observations"] == 2
    assert summary["alert_rate"] == 0.3333
    assert summary["regional_alerts"] == [("West", 2)]
    assert summary["time_window_trends"]["direction"] == "worsening"
    assert summary["category_breakdown"][0]["category"] == "air_quality"


def test_report_generation_from_api_snapshot(tmp_path) -> None:
    report = build_markdown_report(API_SNAPSHOT_PATH)
    assert "Sierra Air Quality Node" in report
    assert "Alert observations: 2" in report
    assert "## Category Alert Breakdown" in report

    outputs = export_reports(output_dir=tmp_path, data_path=API_SNAPSHOT_PATH)
    assert outputs["markdown"].exists()
    assert outputs["html"].exists()
    assert "Sierra Air Quality Node" in outputs["html"].read_text(encoding="utf-8")