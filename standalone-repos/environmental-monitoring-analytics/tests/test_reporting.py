from environmental_monitoring_analytics.reporting import build_html_report, build_markdown_report, compute_summary, export_reports


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


def test_html_report() -> None:
    report = build_html_report()
    assert "<title>Monitoring Operations Brief</title>" in report
    assert "Regional Alert Load" in report
    assert "Sierra Air Quality Node" in report


def test_export_reports(tmp_path) -> None:
    outputs = export_reports(tmp_path)
    assert outputs["markdown"].exists()
    assert outputs["html"].exists()
    assert "Monitoring Operations Brief" in outputs["html"].read_text(encoding="utf-8")