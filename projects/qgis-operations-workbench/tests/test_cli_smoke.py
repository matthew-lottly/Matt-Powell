from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from qgis_operations_workbench.workbench import main


def test_main_writes_pack_and_geopackage(tmp_path: Path) -> None:
    geopackage_path = tmp_path / "review_bundle.gpkg"

    with patch(
        "sys.argv",
        [
            "qgis-workbench",
            "--output-dir",
            str(tmp_path),
            "--export-geopackage",
            "--geopackage-path",
            str(geopackage_path),
        ],
    ):
        main()

    assert (tmp_path / "qgis_workbench_pack.json").exists()
    assert geopackage_path.exists()
