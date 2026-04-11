from __future__ import annotations

from pathlib import Path

import duckdb

from monitoring_data_warehouse.builder import build_warehouse


def test_built_database_supports_mart_queries(tmp_path: Path) -> None:
    database_path = tmp_path / "warehouse.duckdb"
    artifact_path = tmp_path / "warehouse-build-summary.json"

    build_warehouse(database_path, artifact_path=artifact_path)

    with duckdb.connect(str(database_path)) as connection:
        region_rows = connection.execute("SELECT COUNT(*) FROM mart_region_status_daily").fetchone()[0]
        alert_rows = connection.execute("SELECT COUNT(*) FROM mart_alert_station_daily").fetchone()[0]

    assert artifact_path.exists()
    assert region_rows == 6
    assert alert_rows == 3
