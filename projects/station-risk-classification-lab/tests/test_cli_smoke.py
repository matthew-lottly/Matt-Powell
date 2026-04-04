from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from station_risk_classification_lab.lab import main


def test_main_writes_risk_report_and_registry(tmp_path: Path) -> None:
    with patch(
        "sys.argv",
        [
            "station-risk-lab",
            "--output-dir",
            str(tmp_path),
            "--test-size",
            "3",
        ],
    ):
        main()

    assert (tmp_path / "station_risk_report.json").exists()
    assert (tmp_path / "run_registry.json").exists()
