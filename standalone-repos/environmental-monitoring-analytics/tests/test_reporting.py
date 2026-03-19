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
    assert summary["anomalies"][0]["station_name"] == "Mississippi River Gauge"
    assert "status shifted" in summary["anomalies"][0]["reason"]


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
    assert "## Anomaly Watch" in report
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
    assert "Anomaly Watch" in report
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
    assert summary["alert_observations"] == 1
    assert summary["alert_rate"] == 0.1667
    assert summary["regional_alerts"] == [("West", 1)]
    assert summary["time_window_trends"]["direction"] == "worsening"
    assert summary["category_breakdown"][0]["category"] == "air_quality"
    assert summary["category_breakdown"][0]["alert_observations"] == 1


def test_report_generation_from_api_snapshot(tmp_path) -> None:
    report = build_markdown_report(API_SNAPSHOT_PATH)
    assert "Sierra Air Quality Node" in report
    assert "Alert observations: 1" in report
    assert "## Category Alert Breakdown" in report

    outputs = export_reports(output_dir=tmp_path, data_path=API_SNAPSHOT_PATH)
    assert outputs["markdown"].exists()
    assert outputs["html"].exists()
    assert "Sierra Air Quality Node" in outputs["html"].read_text(encoding="utf-8")


def test_snapshot_threshold_metadata_changes_classification(tmp_path: Path) -> None:
        snapshot_path = tmp_path / "snapshot.json"
        snapshot_path.write_text(
                """
                {
                    "features": {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "properties": {
                                    "featureId": "station-900",
                                    "name": "Threshold Demo",
                                    "category": "air_quality",
                                    "region": "West",
                                    "status": "alert",
                                    "lastObservationAt": "2026-03-18T14:00:00Z"
                                },
                                "geometry": {
                                    "type": "Point",
                                    "coordinates": [-121.0, 38.0]
                                }
                            }
                        ]
                    },
                    "thresholds": [
                        {
                            "featureId": "station-900",
                            "metricName": "pm25",
                            "maxValue": 35.0
                        }
                    ],
                    "observations": {
                        "observations": [
                            {
                                "observationId": "obs-1",
                                "featureId": "station-900",
                                "observedAt": "2026-03-18T13:00:00Z",
                                "metricName": "pm25",
                                "value": 33.0,
                                "unit": "ug/m3",
                                "status": "alert"
                            },
                            {
                                "observationId": "obs-2",
                                "featureId": "station-900",
                                "observedAt": "2026-03-18T14:00:00Z",
                                "metricName": "pm25",
                                "value": 41.0,
                                "unit": "ug/m3",
                                "status": "normal"
                            }
                        ]
                    }
                }
                """.strip(),
                encoding="utf-8",
        )

        summary = compute_summary(snapshot_path)

        assert summary["alert_observations"] == 1
        assert summary["anomalies"][0]["station_name"] == "Threshold Demo"
        assert "status shifted from normal to alert" in summary["anomalies"][0]["reason"]