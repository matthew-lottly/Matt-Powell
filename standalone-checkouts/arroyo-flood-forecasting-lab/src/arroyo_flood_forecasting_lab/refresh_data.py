from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "data" / "arroyo_stage_series.json"
DEFAULT_SITE_CODE = "08211500"
DEFAULT_PARAMETER_CODE = "00065"
DEFAULT_PERIOD = "P7D"
DEFAULT_SAMPLE_EVERY = 4
DEFAULT_POINT_COUNT = 168


def _build_series_payload(
    water_services_payload: dict[str, Any],
    source_url: str,
    sample_every: int = DEFAULT_SAMPLE_EVERY,
    point_count: int = DEFAULT_POINT_COUNT,
) -> dict[str, Any]:
    series = water_services_payload["value"]["timeSeries"][0]
    values = series["values"][0]["value"]
    sampled_values = [item for index, item in enumerate(values) if index % sample_every == 0]
    trimmed_values = sampled_values[-point_count:]
    stage_values = [round(float(item["value"]), 2) for item in trimmed_values]
    geolocation = series["sourceInfo"]["geoLocation"]["geogLocation"]
    threshold_index = min(len(stage_values) - 1, int(len(stage_values) * 0.9))
    return {
        "seriesName": "South Texas hourly stage series for Arroyo-style flood forecasting review",
        "dataSource": "USGS NWIS Instantaneous Values",
        "sourceUrl": source_url,
        "siteName": series["sourceInfo"]["siteName"],
        "siteCode": series["sourceInfo"]["siteCode"][0]["value"],
        "parameterCode": DEFAULT_PARAMETER_CODE,
        "parameterName": series["variable"]["variableName"],
        "latitude": geolocation["latitude"],
        "longitude": geolocation["longitude"],
        "startTimestamp": trimmed_values[0]["dateTime"],
        "frequencyHours": 1,
        "reviewThresholdFt": round(sorted(stage_values)[threshold_index], 2),
        "lastRefreshedAt": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "stageFt": stage_values,
    }


def refresh_public_series(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    site_code: str = DEFAULT_SITE_CODE,
    parameter_code: str = DEFAULT_PARAMETER_CODE,
    period: str = DEFAULT_PERIOD,
    sample_every: int = DEFAULT_SAMPLE_EVERY,
    point_count: int = DEFAULT_POINT_COUNT,
) -> Path:
    source_url = (
        "https://waterservices.usgs.gov/nwis/iv/"
        f"?sites={site_code}&parameterCd={parameter_code}&siteStatus=all&format=json&period={period}"
    )
    with urlopen(source_url) as response:
        payload = json.load(response)
    series_payload = _build_series_payload(payload, source_url, sample_every=sample_every, point_count=point_count)
    output_path.write_text(json.dumps(series_payload, indent=2), encoding="utf-8")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh the public USGS-backed series used by the flood forecasting lab.")
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH, help="JSON file to overwrite with the refreshed stage series.")
    parser.add_argument("--site-code", default=DEFAULT_SITE_CODE, help="USGS site code used for the public analog gauge.")
    parser.add_argument("--parameter-code", default=DEFAULT_PARAMETER_CODE, help="USGS parameter code to request.")
    parser.add_argument("--period", default=DEFAULT_PERIOD, help="USGS ISO period string, such as P7D.")
    parser.add_argument("--sample-every", type=int, default=DEFAULT_SAMPLE_EVERY, help="Keep every Nth observation when downsampling to hourly cadence.")
    parser.add_argument("--point-count", type=int, default=DEFAULT_POINT_COUNT, help="Maximum number of sampled points to keep in the output file.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = refresh_public_series(
        output_path=args.output_path,
        site_code=args.site_code,
        parameter_code=args.parameter_code,
        period=args.period,
        sample_every=args.sample_every,
        point_count=args.point_count,
    )
    print(f"Refreshed public stage series at {output_path}")


if __name__ == "__main__":
    main()