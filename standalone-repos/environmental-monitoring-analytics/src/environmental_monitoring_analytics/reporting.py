import argparse
import csv
import json
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, timedelta
from html import escape
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "station_observations.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
CSV_COLUMNS = [
    "station_id",
    "station_name",
    "category",
    "region",
    "observed_at",
    "status",
    "alert_score",
    "reading_value",
]
STATUS_ALERT_SCORES = {
    "alert": 1.0,
    "normal": 0.25,
    "offline": 0.05,
}


def _data_path(data_path: Path | None = None, csv_path: Path | None = None) -> Path:
    return data_path or csv_path or DATA_PATH


def _coalesce(*values: object) -> object | None:
    for value in values:
        if value is not None:
            return value
    return None


def _extract_feature_lookup(payload: object) -> dict[str, dict[str, str]]:
    if not isinstance(payload, dict):
        return {}

    raw_features = payload.get("features", [])
    if isinstance(raw_features, dict):
        raw_features = raw_features.get("features", [])
    if not isinstance(raw_features, list):
        return {}

    feature_lookup: dict[str, dict[str, str]] = {}
    for feature in raw_features:
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties", feature)
        if not isinstance(properties, dict):
            continue
        feature_id = _coalesce(
            properties.get("featureId"),
            properties.get("feature_id"),
            properties.get("stationId"),
            properties.get("station_id"),
        )
        if feature_id is None:
            continue
        feature_lookup[str(feature_id)] = {
            "station_name": str(_coalesce(properties.get("name"), properties.get("stationName"), "")),
            "category": str(_coalesce(properties.get("category"), "")),
            "region": str(_coalesce(properties.get("region"), "")),
        }
    return feature_lookup


def _extract_observations(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        raise ValueError("Unsupported input payload; expected a list or object.")

    raw_observations = payload.get("observations", [])
    if isinstance(raw_observations, dict):
        raw_observations = raw_observations.get("observations", [])
    if not isinstance(raw_observations, list):
        raise ValueError("Input payload does not contain an observations list.")
    return [item for item in raw_observations if isinstance(item, dict)]


def _fallback_alert_score(status: str) -> float:
    return STATUS_ALERT_SCORES.get(status.lower(), 0.0)


def _normalize_snapshot_rows(data_path: Path) -> list[dict[str, object]]:
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    feature_lookup = _extract_feature_lookup(payload)
    observations = _extract_observations(payload)

    rows: list[dict[str, object]] = []
    for observation in observations:
        station_id = _coalesce(
            observation.get("station_id"),
            observation.get("stationId"),
            observation.get("feature_id"),
            observation.get("featureId"),
        )
        observed_at = _coalesce(observation.get("observed_at"), observation.get("observedAt"))
        status = _coalesce(observation.get("status"), "normal")
        reading_value = _coalesce(
            observation.get("reading_value"),
            observation.get("readingValue"),
            observation.get("value"),
        )
        alert_score = _coalesce(observation.get("alert_score"), observation.get("alertScore"))
        feature_details = feature_lookup.get(str(station_id), {})

        row = {
            "station_id": station_id,
            "station_name": _coalesce(
                observation.get("station_name"),
                observation.get("stationName"),
                feature_details.get("station_name"),
            ),
            "category": _coalesce(observation.get("category"), feature_details.get("category")),
            "region": _coalesce(observation.get("region"), feature_details.get("region")),
            "observed_at": observed_at,
            "status": status,
            "alert_score": alert_score if alert_score is not None else _fallback_alert_score(str(status)),
            "reading_value": reading_value,
        }

        missing_fields = [column for column, value in row.items() if value is None]
        if missing_fields:
            raise ValueError(
                f"Input snapshot {data_path.name} is missing required fields: {', '.join(missing_fields)}"
            )
        rows.append(row)

    if not rows:
        raise ValueError(f"Input snapshot {data_path.name} does not contain any observations.")
    return rows


@contextmanager
def _normalized_csv_path(data_path: Path | None = None, csv_path: Path | None = None) -> Iterator[Path]:
    resolved_path = _data_path(data_path=data_path, csv_path=csv_path)
    if resolved_path.suffix.lower() == ".csv":
        yield resolved_path
        return

    rows = _normalize_snapshot_rows(resolved_path)
    with tempfile.TemporaryDirectory() as temp_dir:
        normalized_path = Path(temp_dir) / "normalized_observations.csv"
        with normalized_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        yield normalized_path


def _trend_direction(delta: float, tolerance: float = 1e-9) -> str:
    if delta > tolerance:
        return "worsening"
    if delta < -tolerance:
        return "improving"
    return "steady"


def _format_timestamp(value: str | None) -> str:
    return value or "n/a"


def _parse_report_window(start_date: str | None, end_date: str | None) -> dict[str, str] | None:
    if start_date is None and end_date is None:
        return None
    if start_date is None or end_date is None:
        raise ValueError("Both --start-date and --end-date must be provided together.")

    start_value = date.fromisoformat(start_date)
    end_value = date.fromisoformat(end_date)
    if end_value < start_value:
        raise ValueError("--end-date must be on or after --start-date.")

    window_days = (end_value - start_value).days + 1
    previous_end = start_value - timedelta(days=1)
    previous_start = previous_end - timedelta(days=window_days - 1)

    return {
        "start_date": start_value.isoformat(),
        "end_date": end_value.isoformat(),
        "comparison_start_date": previous_start.isoformat(),
        "comparison_end_date": previous_end.isoformat(),
    }


def _window_summary(connection: duckdb.DuckDBPyConnection, clause: str) -> dict[str, object]:
    total_observations, alert_observations, average_alert_score, earliest_observed_at, latest_observed_at = connection.execute(
        f"""
        SELECT
            COUNT(*) AS total_observations,
            SUM(CASE WHEN status = 'alert' THEN 1 ELSE 0 END) AS alert_observations,
            ROUND(AVG(alert_score), 2) AS average_alert_score,
            MIN(observed_at) AS earliest_observed_at,
            MAX(observed_at) AS latest_observed_at
        FROM observations
        WHERE {clause}
        """
    ).fetchone()
    return {
        "total_observations": total_observations,
        "alert_observations": alert_observations or 0,
        "alert_rate": round((alert_observations or 0) / total_observations, 4) if total_observations else 0.0,
        "average_alert_score": average_alert_score,
        "earliest_observed_at": earliest_observed_at,
        "latest_observed_at": latest_observed_at,
    }


def _regional_changes(
    connection: duckdb.DuckDBPyConnection,
    recent_clause: str,
    previous_clause: str,
) -> list[tuple[str, int, int, int]]:
    return connection.execute(
        f"""
        WITH recent AS (
          SELECT region, COUNT(*) AS alerts
          FROM observations
          WHERE status = 'alert' AND {recent_clause}
          GROUP BY region
        ),
        previous AS (
          SELECT region, COUNT(*) AS alerts
          FROM observations
          WHERE status = 'alert' AND {previous_clause}
          GROUP BY region
        )
        SELECT
          COALESCE(recent.region, previous.region) AS region,
          COALESCE(recent.alerts, 0) AS recent_alerts,
          COALESCE(previous.alerts, 0) AS previous_alerts,
          COALESCE(recent.alerts, 0) - COALESCE(previous.alerts, 0) AS alert_delta
        FROM recent
        FULL OUTER JOIN previous ON recent.region = previous.region
        ORDER BY alert_delta DESC, region ASC
        """
    ).fetchall()


def _category_breakdown(connection: duckdb.DuckDBPyConnection, clause: str) -> list[dict[str, object]]:
    rows = connection.execute(
        f"""
        SELECT
            category,
            COUNT(*) AS total_observations,
            SUM(CASE WHEN status = 'alert' THEN 1 ELSE 0 END) AS alert_observations,
            SUM(CASE WHEN status = 'normal' THEN 1 ELSE 0 END) AS normal_observations,
            SUM(CASE WHEN status = 'offline' THEN 1 ELSE 0 END) AS offline_observations,
            ROUND(AVG(alert_score), 2) AS average_alert_score
        FROM observations
        WHERE {clause}
        GROUP BY category
        ORDER BY alert_observations DESC, category ASC
        """
    ).fetchall()

    categories: list[dict[str, object]] = []
    for category, total_observations, alert_observations, normal_observations, offline_observations, average_alert_score in rows:
        top_alerts = connection.execute(
            f"""
            SELECT station_name, region, observed_at, alert_score
            FROM observations
            WHERE {clause}
              AND category = ?
              AND status = 'alert'
            ORDER BY observed_ts DESC
            LIMIT 3
            """,
            [category],
        ).fetchall()
        categories.append(
            {
                "category": category,
                "total_observations": total_observations,
                "alert_observations": alert_observations or 0,
                "alert_rate": round((alert_observations or 0) / total_observations, 4) if total_observations else 0.0,
                "status_breakdown": {
                    "alert": alert_observations or 0,
                    "normal": normal_observations or 0,
                    "offline": offline_observations or 0,
                },
                "average_alert_score": average_alert_score,
                "recent_alerts": top_alerts,
            }
        )
    return categories


def compute_summary(
    data_path: Path | None = None,
    csv_path: Path | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    report_period = _parse_report_window(start_date, end_date)

    with _normalized_csv_path(data_path=data_path, csv_path=csv_path) as path:
        csv_literal = str(path).replace("\\", "/").replace("'", "''")
        connection = duckdb.connect(database=":memory:")
        connection.execute(
            f"""
            CREATE VIEW observations AS
            SELECT *, strptime(observed_at, '%Y-%m-%dT%H:%M:%SZ') AS observed_ts
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

        if report_period is None:
            report_clause = "TRUE"
            latest_timestamp = connection.execute("SELECT MAX(observed_ts) FROM observations").fetchone()[0]
            recent_end = latest_timestamp
            recent_start = latest_timestamp - timedelta(hours=2) if latest_timestamp is not None else None
            previous_start = latest_timestamp - timedelta(hours=4) if latest_timestamp is not None else None
            recent_clause = (
                f"observed_ts > TIMESTAMP '{recent_start.strftime('%Y-%m-%d %H:%M:%S')}' "
                f"AND observed_ts <= TIMESTAMP '{recent_end.strftime('%Y-%m-%d %H:%M:%S')}'"
                if latest_timestamp is not None
                else "FALSE"
            )
            previous_clause = (
                f"observed_ts > TIMESTAMP '{previous_start.strftime('%Y-%m-%d %H:%M:%S')}' "
                f"AND observed_ts <= TIMESTAMP '{recent_start.strftime('%Y-%m-%d %H:%M:%S')}'"
                if latest_timestamp is not None and recent_start is not None and previous_start is not None
                else "FALSE"
            )
            trend_metadata = {
                "window_hours": 2,
                "latest_timestamp": str(latest_timestamp) if latest_timestamp is not None else None,
            }
        else:
            report_clause = (
                f"CAST(observed_ts AS DATE) BETWEEN DATE '{report_period['start_date']}' "
                f"AND DATE '{report_period['end_date']}'"
            )
            recent_clause = report_clause
            previous_clause = (
                f"CAST(observed_ts AS DATE) BETWEEN DATE '{report_period['comparison_start_date']}' "
                f"AND DATE '{report_period['comparison_end_date']}'"
            )
            trend_metadata = {
                "window_hours": None,
                "latest_timestamp": None,
                "report_period": report_period,
            }

        total_observations = connection.execute(
            f"SELECT COUNT(*) FROM observations WHERE {report_clause}"
        ).fetchone()[0]
        alert_observations = connection.execute(
            f"SELECT COUNT(*) FROM observations WHERE {report_clause} AND status = 'alert'"
        ).fetchone()[0]
        average_alert_score = connection.execute(
            f"SELECT ROUND(AVG(alert_score), 2) FROM observations WHERE {report_clause}"
        ).fetchone()[0]

        regional_alerts = connection.execute(
            f"""
            SELECT region, COUNT(*) AS alerts
            FROM observations
            WHERE {report_clause} AND status = 'alert'
            GROUP BY region
            ORDER BY alerts DESC, region ASC
            """
        ).fetchall()

        latest_alerts = connection.execute(
            f"""
            SELECT station_name, region, category, observed_at, alert_score
            FROM observations
            WHERE {report_clause} AND status = 'alert'
            ORDER BY observed_ts DESC
            LIMIT 3
            """
        ).fetchall()

        recent_window = _window_summary(connection, recent_clause)
        previous_window = _window_summary(connection, previous_clause)
        regional_trends = _regional_changes(connection, recent_clause, previous_clause)
        category_breakdown = _category_breakdown(connection, report_clause)
        connection.close()

        average_delta = round(
            (recent_window["average_alert_score"] or 0.0) - (previous_window["average_alert_score"] or 0.0),
            2,
        )
        alert_rate_delta = round(recent_window["alert_rate"] - previous_window["alert_rate"], 4)

        return {
            "total_observations": total_observations,
            "alert_observations": alert_observations,
            "alert_rate": round(alert_observations / total_observations, 4) if total_observations else 0.0,
            "average_alert_score": average_alert_score,
            "regional_alerts": regional_alerts,
            "latest_alerts": latest_alerts,
            "report_period": report_period,
            "category_breakdown": category_breakdown,
            "time_window_trends": {
                **trend_metadata,
                "recent": recent_window,
                "previous": previous_window,
                "alert_rate_delta": alert_rate_delta,
                "average_alert_score_delta": average_delta,
                "direction": _trend_direction(alert_rate_delta),
                "regional_changes": regional_trends,
            },
        }


def build_markdown_report(
    data_path: Path | None = None,
    csv_path: Path | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    summary = compute_summary(data_path=data_path, csv_path=csv_path, start_date=start_date, end_date=end_date)
    trends = summary["time_window_trends"]
    report_period = summary["report_period"]

    regional_lines = "\n".join(
        f"- {region}: {alerts} alert observations" for region, alerts in summary["regional_alerts"]
    ) or "- No alert observations in the selected report period"
    latest_lines = "\n".join(
        f"- {station} ({region}, {category}) at {observed_at} with alert score {alert_score}"
        for station, region, category, observed_at, alert_score in summary["latest_alerts"]
    ) or "- No alert observations in the selected report period"
    regional_trend_lines = "\n".join(
        f"- {region}: {recent_alerts} alerts in Window A vs {previous_alerts} in Window B ({alert_delta:+d})"
        for region, recent_alerts, previous_alerts, alert_delta in trends["regional_changes"]
    ) or "- No regional alert movement across the comparison windows"
    category_lines = "\n".join(
        (
            f"- {entry['category']}: {entry['alert_observations']} alerts out of {entry['total_observations']} observations "
            f"({entry['alert_rate']:.2%}), status mix alert {entry['status_breakdown']['alert']} / "
            f"normal {entry['status_breakdown']['normal']} / offline {entry['status_breakdown']['offline']}"
        )
        for entry in summary["category_breakdown"]
    ) or "- No category observations in the selected report period"
    report_period_lines = (
        "\n".join(
            [
                "## Report Period",
                "",
                f"- Window A: {report_period['start_date']} to {report_period['end_date']}",
                f"- Window B: {report_period['comparison_start_date']} to {report_period['comparison_end_date']}",
                "",
            ]
        )
        if report_period is not None
        else ""
    )

    window_size_line = (
        f"- Window size: {trends['window_hours']} hours"
        if trends["window_hours"] is not None
        else f"- Window size: date range {report_period['start_date']} to {report_period['end_date']}"
    )

    return f"""# Monitoring Operations Brief

{report_period_lines}## Summary

- Total observations: {summary['total_observations']}
- Alert observations: {summary['alert_observations']}
- Alert rate: {summary['alert_rate']:.2%}
- Average alert score: {summary['average_alert_score']}

## Regional Alert Load

{regional_lines}

## Trend Window

{window_size_line}
- Window A: {_format_timestamp(trends['recent']['earliest_observed_at'])} to {_format_timestamp(trends['recent']['latest_observed_at'])}
- Window B: {_format_timestamp(trends['previous']['earliest_observed_at'])} to {_format_timestamp(trends['previous']['latest_observed_at'])}
- Alert Rate (Window A): {trends['recent']['alert_rate']:.2%} ({trends['recent']['alert_observations']} of {trends['recent']['total_observations']})
- Alert Rate (Window B): {trends['previous']['alert_rate']:.2%} ({trends['previous']['alert_observations']} of {trends['previous']['total_observations']})
- Alert-rate direction: {trends['direction']} ({trends['alert_rate_delta']:+.2%})
- Average alert-score delta: {trends['average_alert_score_delta']:+.2f}

## Category Alert Breakdown

{category_lines}

## Regional Trend Shift

{regional_trend_lines}

## Latest Alert Stations

{latest_lines}
"""


def build_html_report(
    data_path: Path | None = None,
    csv_path: Path | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    summary = compute_summary(data_path=data_path, csv_path=csv_path, start_date=start_date, end_date=end_date)
    trends = summary["time_window_trends"]
    report_period = summary["report_period"]
    max_alerts = max((alerts for _, alerts in summary["regional_alerts"]), default=1)

    def bar_width(alerts: int) -> int:
        return max(12, round((alerts / max_alerts) * 100)) if max_alerts else 12

    regional_cards = "\n".join(
        f"""
        <div class="bar-group bar-width-{bar_width(alerts)}">
          <div class="bar-label"><span>{escape(region)}</span><strong>{alerts}</strong></div>
          <div class="bar-track"><div class="bar-fill"></div></div>
        </div>
        """.strip()
        for region, alerts in summary["regional_alerts"]
    ) or "<p>No alert observations in the selected report period.</p>"
    latest_cards = "\n".join(
        f"<li>{escape(station)} ({escape(region)}, {escape(category)}) at {escape(observed_at)} with alert score {alert_score}</li>"
        for station, region, category, observed_at, alert_score in summary["latest_alerts"]
    ) or "<li>No alert observations in the selected report period.</li>"
    trend_cards = "\n".join(
        f"<li><strong>{escape(region)}</strong>: {recent_alerts} alerts in Window A vs {previous_alerts} in Window B ({alert_delta:+d})</li>"
        for region, recent_alerts, previous_alerts, alert_delta in trends["regional_changes"]
    ) or "<li>No regional alert movement across the comparison windows.</li>"
    category_cards = "\n".join(
        f"""
        <article class="card category-card">
          <p class="eyebrow">{escape(entry['category'].replace('_', ' '))}</p>
          <div class="metric">{entry['alert_rate']:.2%}</div>
          <p><strong>{entry['alert_observations']}</strong> alerts out of {entry['total_observations']} observations.</p>
          <table>
            <thead><tr><th>Status</th><th>Count</th></tr></thead>
            <tbody>
              <tr><td>alert</td><td>{entry['status_breakdown']['alert']}</td></tr>
              <tr><td>normal</td><td>{entry['status_breakdown']['normal']}</td></tr>
              <tr><td>offline</td><td>{entry['status_breakdown']['offline']}</td></tr>
            </tbody>
          </table>
          <p class="eyebrow">Top Alerts</p>
          <ul class="alerts">{"".join(f"<li>{escape(alert_station)} ({escape(alert_region)}) at {escape(alert_time)} with score {alert_score}</li>" for alert_station, alert_region, alert_time, alert_score in entry['recent_alerts']) or '<li>No alert observations in this category.</li>'}</ul>
        </article>
        """.strip()
        for entry in summary["category_breakdown"]
    )

    report_period_block = ""
    if report_period is not None:
        report_period_block = (
            f"<p><strong>Window A:</strong> {escape(report_period['start_date'])} to {escape(report_period['end_date'])}</p>"
            f"<p><strong>Window B:</strong> {escape(report_period['comparison_start_date'])} to {escape(report_period['comparison_end_date'])}</p>"
        )

    window_label = (
        f"{trends['window_hours']} hour comparison"
        if trends['window_hours'] is not None
        else "Custom date-range comparison"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Monitoring Operations Brief</title>
    <style>
      body {{ font-family: Georgia, "Times New Roman", serif; margin: 0; background: #f6f2e8; color: #1f2a25; }}
      main {{ max-width: 1080px; margin: 0 auto; padding: 32px 20px 48px; }}
      .hero, .card {{ background: rgba(255,255,255,0.82); border: 1px solid rgba(31,42,37,0.08); border-radius: 22px; padding: 24px; box-shadow: 0 18px 40px rgba(47,56,50,0.08); }}
      .hero {{ margin-bottom: 18px; }}
      .eyebrow {{ text-transform: uppercase; letter-spacing: 0.18em; font-size: 0.76rem; color: #5f6d66; margin: 0 0 10px; }}
      .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 18px; }}
      .metric {{ font-size: 2rem; margin: 8px 0; }}
      .bars, .alerts {{ display: grid; gap: 12px; }}
      .trend-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin: 18px 0; }}
      .category-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-top: 18px; }}
      .bar-label {{ display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 0.95rem; }}
      .bar-track {{ height: 12px; border-radius: 999px; background: rgba(73,97,109,0.12); overflow: hidden; }}
      .bar-fill {{ height: 100%; background: linear-gradient(90deg, #49616d, #d4a85f); }}
      .bar-width-12 .bar-fill {{ width: 12%; }}
      .bar-width-50 .bar-fill {{ width: 50%; }}
      .bar-width-100 .bar-fill {{ width: 100%; }}
      .two-col {{ display: grid; grid-template-columns: 1.2fr 1fr; gap: 16px; }}
      .trend-badge {{ display: inline-flex; padding: 6px 10px; border-radius: 999px; background: rgba(212,168,95,0.16); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em; }}
      table {{ width: 100%; border-collapse: collapse; margin: 12px 0 16px; }}
      th, td {{ text-align: left; padding: 6px 0; border-bottom: 1px solid rgba(31,42,37,0.08); }}
      ul {{ margin: 0; padding-left: 18px; }}
      li {{ margin-bottom: 10px; }}
      @media (max-width: 800px) {{ .grid, .two-col, .trend-grid, .category-grid {{ grid-template-columns: 1fr; }} }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <p class="eyebrow">Generated Report</p>
        <h1>Monitoring Operations Brief</h1>
        <p>Operational HTML summary for alert load, category pressure, latest priority stations, and regional monitoring shifts.</p>
        {report_period_block}
      </section>
      <section class="grid">
        <article class="card"><p class="eyebrow">Observations</p><div class="metric">{summary['total_observations']}</div><p>Total observations processed in the report period.</p></article>
        <article class="card"><p class="eyebrow">Alert Rate</p><div class="metric">{summary['alert_rate']:.2%}</div><p>Observations currently flagged as alerts.</p></article>
        <article class="card"><p class="eyebrow">Avg Alert Score</p><div class="metric">{summary['average_alert_score']}</div><p>Average alert score across the selected observations.</p></article>
      </section>
      <section class="trend-grid">
        <article class="card">
          <p class="eyebrow">Trend Window</p>
          <p class="trend-badge">{escape(trends['direction'])}</p>
          <p><strong>Window Type:</strong> {escape(window_label)}</p>
          <p><strong>Window A:</strong> {_format_timestamp(trends['recent']['earliest_observed_at'])} to {_format_timestamp(trends['recent']['latest_observed_at'])}</p>
          <p><strong>Window B:</strong> {_format_timestamp(trends['previous']['earliest_observed_at'])} to {_format_timestamp(trends['previous']['latest_observed_at'])}</p>
          <p><strong>Alert Rate (Window A):</strong> {trends['recent']['alert_rate']:.2%}</p>
          <p><strong>Alert Rate (Window B):</strong> {trends['previous']['alert_rate']:.2%}</p>
          <p><strong>Alert-rate delta:</strong> {trends['alert_rate_delta']:+.2%}</p>
          <p><strong>Avg alert-score delta:</strong> {trends['average_alert_score_delta']:+.2f}</p>
        </article>
        <article class="card">
          <p class="eyebrow">Regional Trend Shift</p>
          <ul class="alerts">{trend_cards}</ul>
        </article>
      </section>
      <section class="two-col">
        <article class="card">
          <p class="eyebrow">Regional Alert Load</p>
          <div class="bars">{regional_cards}</div>
        </article>
        <article class="card">
          <p class="eyebrow">Latest Alert Stations</p>
          <ul class="alerts">{latest_cards}</ul>
        </article>
      </section>
      <section class="category-grid">
        {category_cards}
      </section>
    </main>
  </body>
</html>
"""


def export_reports(
    output_dir: Path | None = None,
    data_path: Path | None = None,
    csv_path: Path | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Path]:
    target_dir = output_dir or OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = target_dir / "monitoring-operations-brief.md"
    html_path = target_dir / "monitoring-operations-brief.html"
    markdown_path.write_text(
        build_markdown_report(data_path=data_path, csv_path=csv_path, start_date=start_date, end_date=end_date),
        encoding="utf-8",
    )
    html_path.write_text(
        build_html_report(data_path=data_path, csv_path=csv_path, start_date=start_date, end_date=end_date),
        encoding="utf-8",
    )
    return {"markdown": markdown_path, "html": html_path}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate monitoring operations reports from CSV or API snapshot input.")
    parser.add_argument("--input", type=Path, default=None, help="Optional path to a CSV dataset or API-derived JSON snapshot.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Optional output directory for generated markdown and HTML reports.")
    parser.add_argument("--start-date", type=str, default=None, help="Optional inclusive report start date in YYYY-MM-DD format.")
    parser.add_argument("--end-date", type=str, default=None, help="Optional inclusive report end date in YYYY-MM-DD format.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    print(build_markdown_report(data_path=args.input, start_date=args.start_date, end_date=args.end_date))
    output_paths = export_reports(
        output_dir=args.output_dir,
        data_path=args.input,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    print(f"\nWrote {output_paths['markdown']} and {output_paths['html']}")


if __name__ == "__main__":
    main()