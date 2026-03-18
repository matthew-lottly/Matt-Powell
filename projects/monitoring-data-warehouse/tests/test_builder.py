from pathlib import Path

from monitoring_data_warehouse.builder import build_warehouse


def test_build_warehouse(tmp_path: Path) -> None:
    summary = build_warehouse(tmp_path / "warehouse.duckdb")

    assert summary["counts"]["dim_station"] == 5
    assert summary["counts"]["dim_region"] == 4
    assert summary["counts"]["dim_category"] == 3
    assert summary["counts"]["fact_observation"] == 7
    assert summary["counts"]["mart_alert_station_daily"] == 3
    assert summary["counts"]["mart_region_status_daily"] == 6
    assert summary["quality"]["null_station_keys"] == 0
    assert summary["quality"]["null_region_keys"] == 0
    assert summary["quality"]["alert_records"] == 4
    assert summary["quality"]["distinct_observation_dates"] == 2