from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from station_forecasting_workbench.workbench import main


def test_main_writes_forecast_report_and_registry(tmp_path: Path) -> None:
    with patch(
        "sys.argv",
        [
            "station-forecast",
            "--output-dir",
            str(tmp_path),
            "--projection-horizon",
            "4",
        ],
    ):
        main()

    assert (tmp_path / "station_forecast_report.json").exists()
    assert (tmp_path / "run_registry.json").exists()
