from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from environmental_time_series_lab.lab import main


def test_main_writes_review_artifacts(tmp_path: Path) -> None:
    with patch(
        "sys.argv",
        [
            "time-series-lab",
            "--output-dir",
            str(tmp_path),
            "--review-window",
            "2",
            "--season-length",
            "3",
        ],
    ):
        main()

    assert (tmp_path / "time_series_report.json").exists()
    assert (tmp_path / "run_registry.json").exists()
