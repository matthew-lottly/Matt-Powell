from pathlib import Path

from monitoring_data_warehouse.builder import build_warehouse


def test_build_warehouse(tmp_path: Path) -> None:
    artifact_path = tmp_path / "warehouse-build-summary.json"
    summary = build_warehouse(tmp_path / "warehouse.duckdb", artifact_path=artifact_path)

    assert summary["counts"]["dim_station"] == 5
    assert summary["counts"]["dim_station_attribute_history"] == 6
    assert summary["counts"]["dim_region"] == 4
    assert summary["counts"]["dim_category"] == 3
    assert summary["counts"]["fact_observation"] == 7
    assert summary["counts"]["mart_alert_station_daily"] == 3
    assert summary["counts"]["mart_region_status_daily"] == 6
    assert summary["quality"]["null_station_keys"] == 0
    assert summary["quality"]["null_region_keys"] == 0
    assert summary["quality"]["alert_records"] == 4
    assert summary["quality"]["distinct_observation_dates"] == 2
    assert summary["quality"]["current_station_attribute_rows"] == 5
    assert summary["quality"]["open_ended_history_rows"] == 5
    assert summary["quality"]["contract_failures"] == 0
    assert summary["quality"]["sla_failures"] == 0
    assert summary["metadata"]["source_count"] == 2
    assert summary["metadata"]["model_count"] == 7
    assert "fact_observation" in summary["metadata"]["documented_models"]
    assert summary["contracts"]["failed_checks"] == []
    assert any(check["name"] == "non_null_dimension_keys" for check in summary["contracts"]["checks"])
    assert summary["sla"]["failed_checks"] == []
    assert any(check["name"] == "freshness_lag_hours" for check in summary["sla"]["checks"])
    assert artifact_path.exists()
    assert '"sla_failures": 0' in artifact_path.read_text(encoding="utf-8")