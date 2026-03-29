from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from arroyo_flood_forecasting_lab.lab import ArroyoFloodForecastLab, _denoise_series, build_site_comparison, load_series
from arroyo_flood_forecasting_lab.refresh_data import _build_series_payload


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "arroyo_stage_series.json"
SECONDARY_DATA_PATH = PROJECT_ROOT / "data" / "oso_creek_stage_series.json"


def test_load_series_reads_expected_metadata() -> None:
    series_data = load_series(DATA_PATH)

    assert series_data.series_name.startswith("South Texas hourly stage series")
    assert series_data.site_code == "08211500"
    assert series_data.stage_values.size == 168
    assert series_data.timestamps[0] == "2026-03-12T17:30:00Z"
    assert series_data.review_threshold_ft == 3.72


def test_wavelet_denoising_preserves_length() -> None:
    series_data = load_series(DATA_PATH)
    denoised, level_used, threshold = _denoise_series(series_data.stage_values, "db4", 2)

    assert denoised.shape == series_data.stage_values.shape
    assert level_used >= 1
    assert threshold >= 0.0
    assert float(np.std(series_data.stage_values - denoised)) > 0.0


def test_report_contains_raw_and_denoised_candidates() -> None:
    report = ArroyoFloodForecastLab().build_report()

    assert report["summary"]["selectedSeries"] in {"raw", "denoised"}
    assert report["summary"]["sourceSiteCode"] == "08211500"
    assert report["candidateModels"]["raw"]["bestOrder"] >= 1
    assert report["candidateModels"]["denoised"]["bestOrder"] >= 1
    assert len(report["candidateModels"]["raw"]["candidates"]) == 6
    assert len(report["monteCarlo"]["medianForecast"]) == 12


def test_export_report_writes_json_and_registry(tmp_path: Path) -> None:
    output_path = ArroyoFloodForecastLab().export_report(tmp_path)
    report = json.loads(output_path.read_text(encoding="utf-8"))
    registry = json.loads((tmp_path / "run_registry.json").read_text(encoding="utf-8"))

    assert output_path.name == "arroyo_flood_forecast_report.json"
    assert report["summary"]["observationCount"] == 168
    assert len(report["artifacts"]["chartFiles"]) == 5
    assert (tmp_path / "charts" / "hydrograph-overview.png").exists()
    assert (tmp_path / "charts" / "lag-diagnostics.png").exists()
    assert (tmp_path / "charts" / "wavelet-benefit-comparison.png").exists()
    assert (tmp_path / "review-summary.html").exists()
    assert (tmp_path / "cross-site-comparison.html").exists()
    assert (tmp_path / "multi_site_comparison.json").exists()
    assert registry["runs"][0]["selectedSeries"] == report["summary"]["selectedSeries"]


def test_build_site_comparison_uses_two_public_gauges() -> None:
    comparison = build_site_comparison([DATA_PATH, SECONDARY_DATA_PATH], forecast_horizon=12, max_order=6, wavelet_name="db4", wavelet_level=2)

    assert comparison["summary"]["siteCount"] == 2
    assert {site["siteCode"] for site in comparison["sites"]} == {"08211500", "08211520"}
    assert "interpretation" in comparison["summary"]


def test_build_series_payload_transforms_usgs_shape() -> None:
    payload = {
        "value": {
            "timeSeries": [
                {
                    "sourceInfo": {
                        "siteName": "Example Gauge",
                        "siteCode": [{"value": "12345678"}],
                        "geoLocation": {"geogLocation": {"latitude": 1.5, "longitude": -2.5}},
                    },
                    "variable": {"variableName": "Gage height, ft"},
                    "values": [
                        {
                            "value": [
                                {"dateTime": "2026-01-01T00:00:00.000-05:00", "value": "3.10"},
                                {"dateTime": "2026-01-01T00:15:00.000-05:00", "value": "3.11"},
                                {"dateTime": "2026-01-01T00:30:00.000-05:00", "value": "3.12"},
                                {"dateTime": "2026-01-01T00:45:00.000-05:00", "value": "3.13"},
                                {"dateTime": "2026-01-01T01:00:00.000-05:00", "value": "3.14"},
                                {"dateTime": "2026-01-01T01:15:00.000-05:00", "value": "3.15"},
                                {"dateTime": "2026-01-01T01:30:00.000-05:00", "value": "3.16"},
                                {"dateTime": "2026-01-01T01:45:00.000-05:00", "value": "3.17"}
                            ]
                        }
                    ],
                }
            ]
        }
    }

    result = _build_series_payload(payload, "https://example.test", sample_every=4, point_count=2)

    assert result["siteName"] == "Example Gauge"
    assert result["siteCode"] == "12345678"
    assert result["stageFt"] == [3.1, 3.14]
    assert result["reviewThresholdFt"] == 3.14