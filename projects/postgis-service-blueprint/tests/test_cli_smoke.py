from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from postgis_service_blueprint.blueprint import main


def test_main_writes_blueprint_and_seed_sql(tmp_path: Path) -> None:
    seed_path = tmp_path / "seed.sql"

    with patch(
        "sys.argv",
        [
            "postgis-blueprint",
            "--output-dir",
            str(tmp_path),
            "--export-seed-sql",
            "--seed-sql-path",
            str(seed_path),
        ],
    ):
        main()

    assert (tmp_path / "postgis_service_blueprint.json").exists()
    assert seed_path.exists()
