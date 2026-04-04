from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from geoprompt.demo import build_demo_report


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_demo(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "geoprompt.demo", *args],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        timeout=120,
    )


def test_top_interactions_deterministic_tie_break(tmp_path: Path) -> None:
    report = build_demo_report(
        input_path=PROJECT_ROOT / "data" / "sample_features.json",
        output_dir=tmp_path,
        top_n=5,
        no_plot=True,
    )
    top_interactions = cast(list[dict[str, Any]], report["top_interactions"])

    assert top_interactions == sorted(
        top_interactions,
        key=lambda item: (
            -float(item["interaction"]),
            str(item.get("origin", "")),
            str(item.get("destination", "")),
        ),
    )


def test_top_area_similarity_deterministic_tie_break(tmp_path: Path) -> None:
    report = build_demo_report(
        input_path=PROJECT_ROOT / "data" / "sample_features.json",
        output_dir=tmp_path,
        top_n=5,
        no_plot=True,
    )
    top_area_similarity = cast(list[dict[str, Any]], report["top_area_similarity"])

    assert top_area_similarity == sorted(
        top_area_similarity,
        key=lambda item: (
            -float(item["area_similarity"]),
            str(item.get("origin", "")),
            str(item.get("destination", "")),
        ),
    )


def test_manifest_includes_run_fingerprint_and_input_hash(tmp_path: Path) -> None:
    result = _run_demo(
        "report",
        "--no-plot",
        "--no-asset-copy",
        "--output-dir",
        str(tmp_path),
    )
    assert result.returncode == 0, result.stderr

    manifest_path = tmp_path / "manifests" / "geoprompt_report_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert payload["input"]["sha256"]
    assert payload["run_fingerprint"]
    assert payload["python_version"]
    assert payload["platform"]
    assert isinstance(payload["arguments"], dict)
