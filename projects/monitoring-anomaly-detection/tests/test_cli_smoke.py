from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from monitoring_anomaly_detection.pipeline import main


def test_main_writes_anomaly_report_and_registry(tmp_path: Path) -> None:
    with patch(
        "sys.argv",
        [
            "monitoring-anomaly",
            "--output-dir",
            str(tmp_path),
            "--warmup-window",
            "3",
        ],
    ):
        main()

    assert (tmp_path / "anomaly_report.json").exists()
    assert (tmp_path / "run_registry.json").exists()
