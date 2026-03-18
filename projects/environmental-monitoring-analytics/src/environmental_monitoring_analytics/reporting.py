from html import escape
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "station_observations.csv"
OUTPUT_DIR = PROJECT_ROOT / "outputs"


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


def build_html_report(csv_path: Path | None = None) -> str:
    summary = compute_summary(csv_path)
    max_alerts = max((alerts for _, alerts in summary["regional_alerts"]), default=1)
    regional_cards = "\n".join(
        f"""
        <div>
          <div class="bar-label"><span>{escape(region)}</span><strong>{alerts}</strong></div>
          <div class="bar-track"><div class="bar-fill" style="width: {max(12, round((alerts / max_alerts) * 100))}%"></div></div>
        </div>
        """.strip()
        for region, alerts in summary["regional_alerts"]
    )
    latest_cards = "\n".join(
        f"<li>{escape(station)} ({escape(region)}, {escape(category)}) at {escape(observed_at)} with alert score {alert_score}</li>"
        for station, region, category, observed_at, alert_score in summary["latest_alerts"]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Monitoring Operations Brief</title>
    <style>
      body {{ font-family: Georgia, "Times New Roman", serif; margin: 0; background: #f6f2e8; color: #1f2a25; }}
      main {{ max-width: 960px; margin: 0 auto; padding: 32px 20px 48px; }}
      .hero, .card {{ background: rgba(255,255,255,0.82); border: 1px solid rgba(31,42,37,0.08); border-radius: 22px; padding: 24px; box-shadow: 0 18px 40px rgba(47,56,50,0.08); }}
      .hero {{ margin-bottom: 18px; }}
      .eyebrow {{ text-transform: uppercase; letter-spacing: 0.18em; font-size: 0.76rem; color: #5f6d66; margin: 0 0 10px; }}
      .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 18px; }}
      .metric {{ font-size: 2rem; margin: 8px 0; }}
      .bars, .alerts {{ display: grid; gap: 12px; }}
      .bar-label {{ display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 0.95rem; }}
      .bar-track {{ height: 12px; border-radius: 999px; background: rgba(73,97,109,0.12); overflow: hidden; }}
      .bar-fill {{ height: 100%; background: linear-gradient(90deg, #49616d, #d4a85f); }}
      .two-col {{ display: grid; grid-template-columns: 1.2fr 1fr; gap: 16px; }}
      ul {{ margin: 0; padding-left: 18px; }}
      li {{ margin-bottom: 10px; }}
      @media (max-width: 800px) {{ .grid, .two-col {{ grid-template-columns: 1fr; }} }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <p class="eyebrow">Generated Report</p>
        <h1>Monitoring Operations Brief</h1>
        <p>Operational HTML summary for alert load, latest priority stations, and regional monitoring pressure.</p>
      </section>
      <section class="grid">
        <article class="card"><p class="eyebrow">Observations</p><div class="metric">{summary['total_observations']}</div><p>Total observations processed.</p></article>
        <article class="card"><p class="eyebrow">Alert Rate</p><div class="metric">{summary['alert_rate']:.2%}</div><p>Observations currently flagged as alerts.</p></article>
        <article class="card"><p class="eyebrow">Avg Alert Score</p><div class="metric">{summary['average_alert_score']}</div><p>Average alert score across the dataset.</p></article>
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
    </main>
  </body>
</html>
"""


def export_reports(output_dir: Path | None = None, csv_path: Path | None = None) -> dict[str, Path]:
    target_dir = output_dir or OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = target_dir / "monitoring-operations-brief.md"
    html_path = target_dir / "monitoring-operations-brief.html"
    markdown_path.write_text(build_markdown_report(csv_path), encoding="utf-8")
    html_path.write_text(build_html_report(csv_path), encoding="utf-8")
    return {"markdown": markdown_path, "html": html_path}


def main() -> None:
    print(build_markdown_report())
    output_paths = export_reports()
    print(f"\nWrote {output_paths['markdown']} and {output_paths['html']}")


if __name__ == "__main__":
    main()