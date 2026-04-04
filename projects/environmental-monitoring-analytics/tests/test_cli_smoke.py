from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from environmental_monitoring_analytics.reporting import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_SNAPSHOT_PATH = PROJECT_ROOT / "data" / "api_observation_snapshot.json"


def test_main_writes_markdown_and_html_reports(tmp_path: Path) -> None:
    with patch(
        "sys.argv",
        [
            "environmental-monitoring-analytics",
            "--input",
            str(API_SNAPSHOT_PATH),
            "--output-dir",
            str(tmp_path),
            "--start-date",
            "2026-03-18",
            "--end-date",
            "2026-03-18",
        ],
    ):
        main()

    assert (tmp_path / "monitoring-operations-brief.md").exists()
    assert (tmp_path / "monitoring-operations-brief.html").exists()
