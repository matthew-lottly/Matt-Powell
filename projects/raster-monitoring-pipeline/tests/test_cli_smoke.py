from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from raster_monitoring_pipeline.pipeline import main


def test_main_writes_raster_change_report(tmp_path: Path) -> None:
    with patch(
        "sys.argv",
        [
            "raster-pipeline",
            "--output-dir",
            str(tmp_path),
            "--pipeline-name",
            "Smoke Raster Pipeline",
        ],
    ):
        main()

    assert (tmp_path / "raster_change_report.json").exists()
