from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


def _site_rows(comparison_report: dict[str, Any]) -> str:
    rows = []
    for site in comparison_report.get("sites", []):
        rows.append(
            """
            <tr>
              <td>{site_name}</td>
              <td>{site_code}</td>
              <td>{volatility:.4f}</td>
              <td>{raw_pmse:.4f}</td>
              <td>{denoised_pmse:.4f}</td>
              <td>{benefit:.4f}</td>
              <td>{winner}</td>
            </tr>
            """.format(
                site_name=escape(str(site["siteName"])),
                site_code=escape(str(site["siteCode"])),
                volatility=float(site["hourToHourVolatility"]),
                raw_pmse=float(site["rawPmse"]),
                denoised_pmse=float(site["denoisedPmse"]),
                benefit=float(site["waveletPmseBenefit"]),
                winner=escape(str(site["winningSignal"])),
            )
        )
    return "\n".join(rows)


def render_review_summary(
    output_dir: Path,
    report: dict[str, Any],
    comparison_report: dict[str, Any] | None = None,
) -> str:
    summary = report["summary"]
    source = report["sourceContext"]
    artifacts = report.get("artifacts", {})
    chart_files = artifacts.get("chartFiles", [])
    comparison_chart = artifacts.get("comparisonChartFile")
    comparison_file = artifacts.get("comparisonReportFile")
    output_path = output_dir / "review-summary.html"

    comparison_section = ""
    if comparison_report is not None:
        comparison_summary = comparison_report["summary"]
        comparison_section = f"""
        <section class=\"panel full\">
          <h2>Cross-Site Comparison</h2>
          <p>Noisiest site: <strong>{escape(str(comparison_summary['noisiestSiteCode']))}</strong>. Largest denoising benefit: <strong>{escape(str(comparison_summary['largestDenoisingBenefitSiteCode']))}</strong>.</p>
          <p>{escape(str(comparison_summary['interpretation']))}</p>
          <div class=\"chart-grid single\">
            <figure><img src=\"{escape(str(comparison_chart or ''))}\" alt=\"Cross-site wavelet benefit chart\"></figure>
          </div>
          <table>
            <thead>
              <tr>
                <th>Site</th>
                <th>Code</th>
                <th>Volatility</th>
                <th>Raw PMSE</th>
                <th>Denoised PMSE</th>
                <th>Benefit</th>
                <th>Winner</th>
              </tr>
            </thead>
            <tbody>
              {_site_rows(comparison_report)}
            </tbody>
          </table>
          <p class=\"meta\">Comparison report: {escape(str(comparison_file or ''))}</p>
        </section>
        """

    chart_gallery = "\n".join(
        f'<figure><img src="{escape(str(chart_file))}" alt="{escape(Path(chart_file).stem)}"><figcaption>{escape(Path(chart_file).stem.replace("-", " ").title())}</figcaption></figure>'
        for chart_file in chart_files
    )

    html = f"""
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
      <meta charset=\"utf-8\">
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
      <title>{escape(report['reportName'])} Review Summary</title>
      <style>
        :root {{
          color-scheme: light;
          --bg: #eef1ea;
          --panel: #f9f7ef;
          --ink: #173330;
          --accent: #1e6f5c;
          --muted: #5d6d7e;
          --warn: #b04a2d;
          --edge: #d8d3c2;
        }}
        body {{ margin: 0; font-family: Georgia, serif; background: linear-gradient(180deg, #f4f2ea 0%, var(--bg) 100%); color: var(--ink); }}
        main {{ max-width: 1240px; margin: 0 auto; padding: 32px 24px 64px; }}
        .hero {{ background: #183a37; color: #f8f6ee; border-radius: 24px; padding: 28px 32px; box-shadow: 0 16px 40px rgba(24, 58, 55, 0.16); }}
        .hero h1 {{ margin: 0 0 12px; font-size: 2.2rem; }}
        .hero p {{ margin: 0; max-width: 900px; line-height: 1.5; font-family: Arial, sans-serif; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin-top: 22px; }}
        .stat {{ background: rgba(255,255,255,0.08); padding: 14px 16px; border-radius: 16px; }}
        .stat strong {{ display: block; font-size: 1.3rem; margin-bottom: 4px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 18px; margin-top: 22px; }}
        .panel {{ background: var(--panel); border: 1px solid var(--edge); border-radius: 22px; padding: 22px; box-shadow: 0 10px 22px rgba(29, 40, 38, 0.06); }}
        .panel.full {{ grid-column: 1 / -1; }}
        .panel h2 {{ margin-top: 0; margin-bottom: 12px; }}
        .meta {{ color: var(--muted); font-family: Arial, sans-serif; font-size: 0.94rem; }}
        .chart-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }}
        .chart-grid.single {{ grid-template-columns: 1fr; }}
        figure {{ margin: 0; }}
        img {{ width: 100%; border-radius: 14px; border: 1px solid var(--edge); background: white; }}
        figcaption {{ margin-top: 8px; color: var(--muted); font-family: Arial, sans-serif; font-size: 0.9rem; }}
        table {{ width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; }}
        th, td {{ padding: 10px 12px; border-bottom: 1px solid var(--edge); text-align: left; }}
        th {{ color: var(--muted); font-size: 0.86rem; text-transform: uppercase; letter-spacing: 0.04em; }}
        code {{ font-family: Consolas, monospace; }}
      </style>
    </head>
    <body>
      <main>
        <section class=\"hero\">
          <h1>{escape(report['reportName'])}</h1>
          <p>{escape(source['publicModelingNote'])}</p>
          <div class=\"stats\">
            <div class=\"stat\"><strong>{escape(str(summary['sourceSiteCode']))}</strong>Primary site code</div>
            <div class=\"stat\"><strong>{escape(str(summary['selectedSeries']))}</strong>Winning signal branch</div>
            <div class=\"stat\"><strong>{escape(str(summary['selectedOrder']))}</strong>Selected AR order</div>
            <div class=\"stat\"><strong>{float(summary['rawPmse']):.4f}</strong>Raw PMSE</div>
            <div class=\"stat\"><strong>{float(summary['denoisedPmse']):.4f}</strong>Denoised PMSE</div>
            <div class=\"stat\"><strong>{float(summary['reviewThresholdFt']):.2f}</strong>Review threshold (ft)</div>
          </div>
        </section>

        <section class=\"grid\">
          <section class=\"panel\">
            <h2>Primary Source</h2>
            <p><strong>{escape(str(source['siteName']))}</strong> ({escape(str(source['siteCode']))})</p>
            <p class=\"meta\">{escape(str(source['dataSource']))}</p>
            <p class=\"meta\">{escape(str(source['sourceUrl']))}</p>
          </section>
          <section class=\"panel\">
            <h2>Interpretation</h2>
            <p>Raw-versus-denoised comparison is driven by holdout PMSE rather than by assuming wavelet preprocessing always wins.</p>
            <p>Monte Carlo scenario bands translate residual uncertainty into a reviewer-friendly risk view instead of a single deterministic trace.</p>
          </section>
          <section class=\"panel full\">
            <h2>Chart Pack</h2>
            <div class=\"chart-grid\">{chart_gallery}</div>
          </section>
          {comparison_section}
        </section>
      </main>
    </body>
    </html>
    """
    output_path.write_text(html, encoding="utf-8")
    return output_path.name


def render_comparison_summary(
    output_dir: Path,
    report: dict[str, Any],
    comparison_report: dict[str, Any],
) -> str:
    output_path = output_dir / "cross-site-comparison.html"
    comparison_summary = comparison_report["summary"]
    comparison_chart = report.get("artifacts", {}).get("comparisonChartFile", "")
    primary_summary_page = report.get("artifacts", {}).get("summaryPage", "review-summary.html")
    comparison_file = report.get("artifacts", {}).get("comparisonReportFile", "multi_site_comparison.json")

    site_cards = "\n".join(
        f"""
        <article class=\"site-card\">
          <h3>{escape(str(site['siteName']))}</h3>
          <p class=\"meta\">USGS {escape(str(site['siteCode']))}</p>
          <ul>
            <li>Hour-to-hour volatility: <strong>{float(site['hourToHourVolatility']):.4f}</strong></li>
            <li>Raw PMSE: <strong>{float(site['rawPmse']):.4f}</strong></li>
            <li>Denoised PMSE: <strong>{float(site['denoisedPmse']):.4f}</strong></li>
            <li>Wavelet benefit: <strong>{float(site['waveletPmseBenefit']):.4f}</strong></li>
            <li>Winning branch: <strong>{escape(str(site['winningSignal']))}</strong></li>
          </ul>
        </article>
        """
        for site in comparison_report.get("sites", [])
    )

    html = f"""
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
      <meta charset=\"utf-8\">
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
      <title>Cross-Site Wavelet Comparison</title>
      <style>
        :root {{
          --bg: #f3efe6;
          --panel: #fffaf0;
          --ink: #1e312d;
          --muted: #60716d;
          --accent: #1e6f5c;
          --warn: #b04a2d;
          --edge: #d8d3c2;
        }}
        body {{ margin: 0; font-family: Georgia, serif; background: radial-gradient(circle at top, #f8f4ea 0%, var(--bg) 58%, #ebe8de 100%); color: var(--ink); }}
        main {{ max-width: 1180px; margin: 0 auto; padding: 34px 24px 64px; }}
        .hero {{ background: linear-gradient(135deg, #183a37 0%, #204d48 100%); color: #f8f6ee; border-radius: 26px; padding: 30px 34px; box-shadow: 0 18px 42px rgba(24, 58, 55, 0.16); }}
        .hero h1 {{ margin: 0 0 12px; font-size: 2.3rem; }}
        .hero p {{ margin: 0; font-family: Arial, sans-serif; line-height: 1.55; max-width: 920px; }}
        .hero-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-top: 22px; }}
        .hero-stat {{ background: rgba(255,255,255,0.09); border-radius: 16px; padding: 14px 16px; }}
        .hero-stat strong {{ display: block; font-size: 1.35rem; margin-bottom: 6px; }}
        .layout {{ display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 18px; margin-top: 22px; }}
        .panel {{ background: var(--panel); border: 1px solid var(--edge); border-radius: 22px; padding: 22px; box-shadow: 0 10px 24px rgba(31, 45, 41, 0.06); }}
        .panel h2, .panel h3 {{ margin-top: 0; }}
        .meta {{ color: var(--muted); font-family: Arial, sans-serif; font-size: 0.94rem; }}
        .chart {{ width: 100%; border-radius: 16px; border: 1px solid var(--edge); background: white; }}
        .site-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-top: 18px; }}
        .site-card {{ background: #fffdf7; border: 1px solid var(--edge); border-radius: 18px; padding: 18px; }}
        .site-card ul {{ margin: 12px 0 0; padding-left: 20px; font-family: Arial, sans-serif; line-height: 1.6; }}
        .callout {{ border-left: 5px solid var(--accent); padding-left: 14px; font-family: Arial, sans-serif; line-height: 1.6; }}
        .links a {{ color: var(--accent); text-decoration: none; font-family: Arial, sans-serif; }}
        .links a:hover {{ text-decoration: underline; }}
        @media (max-width: 900px) {{ .layout {{ grid-template-columns: 1fr; }} }}
      </style>
    </head>
    <body>
      <main>
        <section class=\"hero\">
          <h1>Cross-Site Wavelet Comparison</h1>
          <p>This page isolates the question behind the extra gauge: does wavelet denoising help more once the stage signal becomes noisier? The answer in this sample is yes.</p>
          <div class=\"hero-grid\">
            <div class=\"hero-stat\"><strong>{escape(str(comparison_summary['noisiestSiteCode']))}</strong>Noisiest site</div>
            <div class=\"hero-stat\"><strong>{escape(str(comparison_summary['largestDenoisingBenefitSiteCode']))}</strong>Largest denoising benefit</div>
            <div class=\"hero-stat\"><strong>{escape(str(comparison_summary['denoisingHelpsMoreOnNoisySeries']))}</strong>Benefit tracks noise</div>
          </div>
        </section>

        <section class=\"layout\">
          <section class=\"panel\">
            <h2>Comparison Chart</h2>
            <img class=\"chart\" src=\"{escape(str(comparison_chart))}\" alt=\"Wavelet benefit comparison chart\">
            <p class=\"meta\">Comparison data: {escape(str(comparison_file))}</p>
          </section>
          <section class=\"panel\">
            <h2>What It Means</h2>
            <p class=\"callout\">{escape(str(comparison_summary['interpretation']))}</p>
            <p class=\"meta\">The Nueces River series is smoother, and the raw branch still wins there. Oso Creek is noisier, and denoising improves holdout PMSE.</p>
            <div class=\"links\">
              <p><a href=\"{escape(str(primary_summary_page))}\">Open the full review summary</a></p>
              <p><a href=\"{escape(str(comparison_file))}\">Open the JSON comparison payload</a></p>
            </div>
          </section>
        </section>

        <section class=\"panel\" style=\"margin-top: 18px;\">
          <h2>Site Narratives</h2>
          <div class=\"site-grid\">{site_cards}</div>
        </section>
      </main>
    </body>
    </html>
    """
    output_path.write_text(html, encoding="utf-8")
    return output_path.name