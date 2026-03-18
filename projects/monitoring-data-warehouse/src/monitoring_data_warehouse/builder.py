from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "station_readings.csv"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"
TRANSFORM_PATH = PROJECT_ROOT / "sql" / "transforms.sql"
WAREHOUSE_PATH = PROJECT_ROOT / "monitoring_warehouse.duckdb"


def _scalar(connection: duckdb.DuckDBPyConnection, query: str) -> int:
    row = connection.execute(query).fetchone()
    if row is None:
        raise RuntimeError(f"Query returned no rows: {query}")
    return int(row[0])


def build_warehouse(database_path: Path | None = None) -> dict:
    db_path = database_path or WAREHOUSE_PATH
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
    connection.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
    connection.execute(TRANSFORM_PATH.read_text(encoding="utf-8"))

    counts = {
        "dim_station": _scalar(connection, "SELECT COUNT(*) FROM dim_station"),
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
    }
    connection.close()
    return {"counts": counts, "quality": quality, "warehouse_path": str(db_path)}


def main() -> None:
    summary = build_warehouse()
    print("Monitoring warehouse built")
    for section, values in summary.items():
        print(section, values)


if __name__ == "__main__":
    main()