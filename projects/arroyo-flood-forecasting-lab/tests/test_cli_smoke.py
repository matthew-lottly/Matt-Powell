from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from arroyo_flood_forecasting_lab.lab import main


def test_main_writes_expected_review_artifacts(tmp_path: Path) -> None:
    with patch(
        "sys.argv",
        [
            "arroyo-flood-lab",
            "--output-dir",
            str(tmp_path),
            "--forecast-horizon",
            "6",
            "--simulation-count",
            "12",
        ],
    ):
        main()

    assert (tmp_path / "arroyo_flood_forecast_report.json").exists()
    assert (tmp_path / "run_registry.json").exists()
    assert (tmp_path / "charts" / "hydrograph-overview.png").exists()
