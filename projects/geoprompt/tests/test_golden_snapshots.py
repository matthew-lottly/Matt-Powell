from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from geoprompt.demo import build_demo_report
from geoprompt.io import read_features


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


def _load_golden(name: str) -> dict[str, Any]:
    return json.loads((GOLDEN_DIR / name).read_text(encoding="utf-8"))


def test_sample_reference_snapshot() -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
    bounds = frame.bounds()

    current = {
        "feature_count": len(frame),
        "bounds": {
            "min_x": bounds.min_x,
            "min_y": bounds.min_y,
            "max_x": bounds.max_x,
            "max_y": bounds.max_y,
        },
        "geometry_types": sorted(set(frame.geometry_types())),
        "nearest_neighbors": [
            [row["origin"], row["neighbor"]]
            for row in frame.nearest_neighbors(k=1)
        ],
    }

    assert current == _load_golden("sample_reference_snapshot.json")


def test_report_summary_snapshot(tmp_path: Path) -> None:
    report = build_demo_report(
        input_path=PROJECT_ROOT / "data" / "sample_features.json",
        output_dir=tmp_path,
        top_n=5,
        no_plot=True,
    )
    summary = cast(dict[str, Any], report["summary"])

    current = {
        "feature_count": summary["feature_count"],
        "crs": summary["crs"],
        "bounds": summary["bounds"],
        "geometry_types": summary["geometry_types"],
        "valley_window_feature_count": summary["valley_window_feature_count"],
    }

    assert current == _load_golden("report_summary_snapshot.json")
