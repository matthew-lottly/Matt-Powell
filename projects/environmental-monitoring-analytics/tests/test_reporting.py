from environmental_monitoring_analytics.reporting import build_markdown_report, compute_summary


def test_compute_summary() -> None:
    summary = compute_summary()
    assert summary["total_observations"] == 7
    assert summary["alert_observations"] == 4
    assert summary["alert_rate"] == 0.5714
    assert summary["regional_alerts"][0][0] == "West"
    assert summary["regional_alerts"][0][1] == 2


def test_markdown_report() -> None:
    report = build_markdown_report()
    assert "# Monitoring Operations Brief" in report
    assert "Alert observations: 4" in report
    assert "Sierra Air Quality Node" in report