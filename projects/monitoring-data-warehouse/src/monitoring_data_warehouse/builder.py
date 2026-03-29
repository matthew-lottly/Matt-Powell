import json
from pathlib import Path

import duckdb
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "station_readings.csv"
ATTRIBUTE_HISTORY_PATH = PROJECT_ROOT / "data" / "station_attribute_history.csv"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"
TRANSFORM_PATH = PROJECT_ROOT / "sql" / "transforms.sql"
METADATA_PATH = PROJECT_ROOT / "metadata" / "warehouse_models.yml"
WAREHOUSE_PATH = PROJECT_ROOT / "monitoring_warehouse.duckdb"
ARTIFACT_PATH = PROJECT_ROOT / "artifacts" / "warehouse-build-summary.json"


def _scalar(connection: duckdb.DuckDBPyConnection, query: str) -> int:
    row = connection.execute(query).fetchone()
    if row is None:
        raise RuntimeError(f"Query returned no rows: {query}")
    return int(row[0])


def _load_metadata(metadata_path: Path = METADATA_PATH) -> dict:
    return yaml.safe_load(metadata_path.read_text(encoding="utf-8"))


def _run_sla_checks(connection: duckdb.DuckDBPyConnection, metadata: dict) -> dict:
    freshness_rows: list[dict[str, object]] = []
    completeness_rows: list[dict[str, object]] = []

    for source in metadata.get("sources", []):
        sla = source.get("sla", {})
        freshness = sla.get("freshness")
        if freshness and freshness.get("query"):
            freshest_value = connection.execute(freshness["query"]).fetchone()[0]
            freshness_rows.append(
                {
                    "source": source["name"],
                    "freshest_at": freshest_value,
                    "max_lag_hours": int(freshness.get("max_lag_hours_from_freshest", 0)),
                }
            )

        completeness = sla.get("completeness", {})
        for field in completeness.get("required_fields", []):
            missing_rows = _scalar(
                connection,
                f"SELECT COUNT(*) FROM {source['name']} WHERE {field} IS NULL OR TRIM(CAST({field} AS VARCHAR)) = ''",
            )
            completeness_rows.append(
                {
                    "source": source["name"],
                    "name": f"required_{field}",
                    "expected": 0,
                    "actual": missing_rows,
                    "passed": missing_rows == 0,
                }
            )

    freshest_reference = max((row["freshest_at"] for row in freshness_rows if row["freshest_at"] is not None), default=None)
    freshness_checks = []
    for row in freshness_rows:
        freshest_at = row["freshest_at"]
        lag_hours = 0.0
        if freshest_reference is not None and freshest_at is not None:
            lag_hours = round((freshest_reference - freshest_at).total_seconds() / 3600, 2)
        freshness_checks.append(
            {
                "source": row["source"],
                "name": "freshness_lag_hours",
                "expected": row["max_lag_hours"],
                "actual": lag_hours,
                "freshest_at": freshest_at.isoformat() if freshest_at is not None else None,
                "passed": lag_hours <= row["max_lag_hours"],
            }
        )

    checks = freshness_checks + completeness_rows
    failed_checks = [check for check in checks if not check["passed"]]
    return {"checks": checks, "failed_checks": failed_checks}


def _write_artifact(summary: dict, artifact_path: Path) -> None:
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")


def _run_contract_checks(connection: duckdb.DuckDBPyConnection, metadata: dict) -> dict:
    checks: list[dict[str, object]] = []
    for model in metadata.get("models", []):
        contract = model.get("contract", {})
        for check in contract.get("checks", []):
            actual = _scalar(connection, check["query"])
            expected = int(check.get("expected", 0))
            checks.append(
                {
                    "model": model["name"],
                    "name": check["name"],
                    "expected": expected,
                    "actual": actual,
                    "passed": actual == expected,
                }
            )

    failed_checks = [check for check in checks if not check["passed"]]
    return {"checks": checks, "failed_checks": failed_checks}


def build_warehouse(database_path: Path | None = None, artifact_path: Path | None = None) -> dict:
    db_path = database_path or WAREHOUSE_PATH
    metadata = _load_metadata()
    connection = duckdb.connect(str(db_path))
    csv_literal = str(DATA_PATH).replace("\\", "/").replace("'", "''")
    connection.execute(
        f"""
        CREATE OR REPLACE VIEW staging_readings AS
        SELECT *
        FROM read_csv(
            '{csv_literal}',
            header=true,
            columns={{
                'station_id': 'VARCHAR',
                'station_name': 'VARCHAR',
                'category': 'VARCHAR',
                'region': 'VARCHAR',
                'observed_at': 'VARCHAR',
                'status': 'VARCHAR',
                'alert_score': 'DOUBLE',
                'reading_value': 'DOUBLE'
            }}
        )
        """
    )
    attribute_literal = str(ATTRIBUTE_HISTORY_PATH).replace("\\", "/").replace("'", "''")
    connection.execute(
        f"""
        CREATE OR REPLACE VIEW staging_station_attribute_history AS
        SELECT *
        FROM read_csv(
            '{attribute_literal}',
            header=true,
            columns={{
                'station_id': 'VARCHAR',
                'station_name': 'VARCHAR',
                'owner_team': 'VARCHAR',
                'response_tier': 'VARCHAR',
                'effective_from': 'VARCHAR',
                'effective_to': 'VARCHAR',
                'is_current': 'BOOLEAN'
            }}
        )
        """
    )
    connection.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.execute(TRANSFORM_PATH.read_text(encoding="utf-8"))

    counts = {
        "dim_station": _scalar(connection, "SELECT COUNT(*) FROM dim_station"),
        "dim_station_attribute_history": _scalar(connection, "SELECT COUNT(*) FROM dim_station_attribute_history"),
        "dim_region": _scalar(connection, "SELECT COUNT(*) FROM dim_region"),
        "dim_category": _scalar(connection, "SELECT COUNT(*) FROM dim_category"),
        "fact_observation": _scalar(connection, "SELECT COUNT(*) FROM fact_observation"),
        "mart_alert_station_daily": _scalar(connection, "SELECT COUNT(*) FROM mart_alert_station_daily"),
        "mart_region_status_daily": _scalar(connection, "SELECT COUNT(*) FROM mart_region_status_daily"),
    }

    quality = {
        "null_station_keys": _scalar(connection, "SELECT COUNT(*) FROM fact_observation WHERE station_key IS NULL"),
        "null_region_keys": _scalar(connection, "SELECT COUNT(*) FROM fact_observation WHERE region_key IS NULL"),
        "alert_records": _scalar(connection, "SELECT COUNT(*) FROM fact_observation WHERE status = 'alert'"),
        "distinct_observation_dates": _scalar(connection, "SELECT COUNT(DISTINCT observation_date) FROM mart_region_status_daily"),
        "current_station_attribute_rows": _scalar(
            connection,
            "SELECT COUNT(*) FROM dim_station_attribute_history WHERE is_current",
        ),
        "open_ended_history_rows": _scalar(
            connection,
            "SELECT COUNT(*) FROM dim_station_attribute_history WHERE effective_to IS NULL",
        ),
    }
    contracts = _run_contract_checks(connection, metadata)
    sla = _run_sla_checks(connection, metadata)
    quality["contract_failures"] = len(contracts["failed_checks"])
    quality["sla_failures"] = len(sla["failed_checks"])
    connection.close()
    summary = {
        "counts": counts,
        "quality": quality,
        "contracts": contracts,
        "sla": sla,
        "metadata": {
            "source_count": len(metadata.get("sources", [])),
            "model_count": len(metadata.get("models", [])),
            "documented_models": [model["name"] for model in metadata.get("models", [])],
        },
        "warehouse_path": str(db_path),
        "artifact_path": str(artifact_path or ARTIFACT_PATH),
    }
    _write_artifact(summary, artifact_path or ARTIFACT_PATH)
    return summary


def main() -> None:
    summary = build_warehouse()
    print("Monitoring warehouse built")
    for section, values in summary.items():
        print(section, values)


if __name__ == "__main__":
    main()