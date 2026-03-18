from pathlib import Path

import duckdb


DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "station_observations.csv"


def _csv_path(csv_path: Path | None = None) -> Path:
    return csv_path or DATA_PATH


def compute_summary(csv_path: Path | None = None) -> dict:
    path = _csv_path(csv_path)
    csv_literal = str(path).replace("\\", "/").replace("'", "''")
    connection = duckdb.connect(database=":memory:")
    connection.execute(
        f"""
        CREATE VIEW observations AS
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

    total_observations = connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
    alert_observations = connection.execute(
        "SELECT COUNT(*) FROM observations WHERE status = 'alert'"
    ).fetchone()[0]
    average_alert_score = connection.execute(
        "SELECT ROUND(AVG(alert_score), 2) FROM observations"
    ).fetchone()[0]

    regional_alerts = connection.execute(
        """
        SELECT region, COUNT(*) AS alerts
        FROM observations
        WHERE status = 'alert'
        GROUP BY region
        ORDER BY alerts DESC, region ASC
        """
    ).fetchall()

    latest_alerts = connection.execute(
        """
        SELECT station_name, region, category, observed_at, alert_score
        FROM observations
        WHERE status = 'alert'
        ORDER BY observed_at DESC
        LIMIT 3
        """
    ).fetchall()
    connection.close()

    return {
        "total_observations": total_observations,
        "alert_observations": alert_observations,
        "alert_rate": round(alert_observations / total_observations, 4),
        "average_alert_score": average_alert_score,
        "regional_alerts": regional_alerts,
        "latest_alerts": latest_alerts,
    }


def build_markdown_report(csv_path: Path | None = None) -> str:
    summary = compute_summary(csv_path)

    regional_lines = "\n".join(
        f"- {region}: {alerts} alert observations" for region, alerts in summary["regional_alerts"]
    )
    latest_lines = "\n".join(
        f"- {station} ({region}, {category}) at {observed_at} with alert score {alert_score}"
        for station, region, category, observed_at, alert_score in summary["latest_alerts"]
    )

    return f"""# Monitoring Operations Brief

## Summary

- Total observations: {summary['total_observations']}
- Alert observations: {summary['alert_observations']}
- Alert rate: {summary['alert_rate']:.2%}
- Average alert score: {summary['average_alert_score']}

## Regional Alert Load

{regional_lines}

## Latest Alert Stations

{latest_lines}
"""


def main() -> None:
    print(build_markdown_report())


if __name__ == "__main__":
    main()