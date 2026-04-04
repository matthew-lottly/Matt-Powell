"""GeoPrompt demo report and review plot generation.

Generates enriched spatial analytics reports with neighborhood pressure,
anchor influence, corridor accessibility, interaction tables, and
presentation-quality review charts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import platform
import random as _random
import subprocess
import sys
from heapq import nlargest
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

import matplotlib.pyplot as plt

from .config import GeoPromptConfig, load_config
from .geometry import geometry_centroid, geometry_type, geometry_vertices
from .io import read_features, read_features_chunked, write_geojson, write_json
from .logging_ import configure_logging, log_timing, log_trace
from .validation import SCHEMA_VERSION, add_schema_version, validate_non_empty_features


logger = logging.getLogger("geoprompt.demo")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_PATH = PROJECT_ROOT / "data" / "sample_features.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_ASSET_PATH = PROJECT_ROOT / "assets" / "neighborhood-pressure-review-live.png"

# Item 81: Colorblind-safe colormap presets
COLORMAP_PRESETS: dict[str, str] = {
    "default": "YlOrRd",
    "colorblind_safe": "cividis",
    "viridis": "viridis",
    "plasma": "plasma",
    "cool_warm": "coolwarm",
}

# Item 86: Thematic style presets for publication outputs
STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "default": {
        "bg_color": "#f4f2eb",
        "grid_color": "#d6cec2",
        "text_color": "#23343b",
        "line_color": "#557a95",
        "fill_color": "#bdd7c6",
        "edge_color": "#557a65",
    },
    "dark": {
        "bg_color": "#1e1e2e",
        "grid_color": "#45475a",
        "text_color": "#cdd6f4",
        "line_color": "#89b4fa",
        "fill_color": "#313244",
        "edge_color": "#a6e3a1",
    },
    "publication": {
        "bg_color": "#ffffff",
        "grid_color": "#cccccc",
        "text_color": "#000000",
        "line_color": "#333333",
        "fill_color": "#e0e0e0",
        "edge_color": "#666666",
    },
}

# Item 89: Marker shapes by geometry type
GEOMETRY_MARKERS: dict[str, str] = {
    "Point": "o",
    "LineString": "s",
    "Polygon": "D",
    "MultiPoint": "^",
    "MultiLineString": "v",
    "MultiPolygon": "p",
}

# All available analysis tools for the unified analyze command
ANALYZE_TOOLS: list[str] = [
    "accessibility",
    "gravity-flow",
    "suitability",
    "catchment-competition",
    "hotspot-scan",
    "equity-gap",
    "network-reliability",
    "transit-service-gap",
    "congestion-hotspots",
    "walkability-audit",
    "gentrification-scan",
    "land-value-surface",
    "pollution-surface",
    "habitat-fragmentation-map",
    "climate-vulnerability-map",
    "migration-pull-map",
    "mortality-risk-map",
    "market-power-map",
    "trade-corridor-map",
    "community-cohesion-map",
    "cultural-similarity-matrix",
    "noise-impact-map",
    "visual-prominence-map",
    "drought-stress-map",
    "heat-island-map",
    "school-access-map",
    "healthcare-access-map",
    "food-desert-map",
    "digital-divide-map",
    "wildfire-risk-map",
    "emergency-response-map",
    "infrastructure-lifecycle-map",
    "adaptive-capacity-map",
]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _current_git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _write_run_manifest(
    *,
    output_dir: Path,
    command: str,
    input_path: Path,
    output_paths: list[Path],
    args: argparse.Namespace,
    extra: dict[str, Any] | None = None,
) -> Path:
    manifest_dir = output_dir / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"geoprompt_{command.replace('-', '_')}_manifest.json"

    config_hash: str | None = None
    config_path = getattr(args, "config", None)
    if isinstance(config_path, Path) and config_path.exists():
        config_hash = _sha256_file(config_path)

    arguments = {
        key: (str(value) if isinstance(value, Path) else value)
        for key, value in vars(args).items()
    }

    fingerprint_payload = {
        "command": command,
        "input_sha256": _sha256_file(input_path),
        "arguments": arguments,
        "git_commit": _current_git_commit(),
        "config_hash": config_hash,
    }
    run_fingerprint = hashlib.sha256(json.dumps(fingerprint_payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "package": "geoprompt",
        "command": command,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "cwd": str(Path.cwd()),
        "git_commit": _current_git_commit(),
        "run_fingerprint": run_fingerprint,
        "input": {
            "path": str(input_path),
            "sha256": _sha256_file(input_path),
        },
        "config": {
            "path": str(config_path) if isinstance(config_path, Path) else None,
            "sha256": config_hash,
        },
        "arguments": arguments,
        "outputs": [str(path) for path in output_paths],
    }
    if extra:
        payload["extra"] = extra

    return write_json(manifest_path, payload)


def _run_pipeline(args: argparse.Namespace) -> None:
    pipeline_file = getattr(args, "pipeline_file", None)
    if not isinstance(pipeline_file, Path):
        print("error: --pipeline-file is required for the pipeline command.", file=sys.stderr)
        raise SystemExit(2)
    if not pipeline_file.exists():
        print(f"error: pipeline file not found: {pipeline_file}", file=sys.stderr)
        raise SystemExit(2)

    payload = json.loads(pipeline_file.read_text(encoding="utf-8"))
    steps = payload.get("steps")
    if not isinstance(steps, list) or not steps:
        print("error: pipeline file must contain a non-empty 'steps' list.", file=sys.stderr)
        raise SystemExit(2)

    def _resolve_inputs() -> list[Path]:
        batch_input_dir = getattr(args, "batch_input_dir", None)
        if not isinstance(batch_input_dir, Path):
            return [args.input_path]
        if not batch_input_dir.exists() or not batch_input_dir.is_dir():
            print(f"error: --batch-input-dir must be an existing directory: {batch_input_dir}", file=sys.stderr)
            raise SystemExit(2)
        pattern = str(getattr(args, "batch_pattern", "*.json") or "*.json")
        files = sorted(path for path in batch_input_dir.glob(pattern) if path.is_file())
        if not files:
            print(
                f"error: no input files matched pattern '{pattern}' in {batch_input_dir}",
                file=sys.stderr,
            )
            raise SystemExit(2)
        return files

    def _run_for_input(input_path: Path, output_dir: Path) -> dict[str, Any]:
        checkpoint_dir = output_dir / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = checkpoint_dir / "geoprompt_pipeline_state.json"

        completed_steps: list[str] = []
        failed_steps: list[str] = []
        if args.resume and checkpoint_path.exists():
            checkpoint_payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            completed_steps = list(checkpoint_payload.get("completed_steps", []))
            failed_steps = list(checkpoint_payload.get("failed_steps", []))

        run_results: list[dict[str, Any]] = []
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                print(f"error: step {index} is not an object", file=sys.stderr)
                raise SystemExit(2)

            step_name = str(step.get("name") or f"step_{index}")
            if args.resume and step_name in completed_steps:
                logger.info("Skipping completed pipeline step: %s", step_name)
                run_results.append({"name": step_name, "status": "skipped"})
                continue

            step_command = str(step.get("command", "analyze"))
            if step_command == "pipeline":
                print("error: nested 'pipeline' command is not allowed in pipeline steps.", file=sys.stderr)
                raise SystemExit(2)

            retries = int(step.get("retries", 0))
            if retries < 0:
                print(f"error: step '{step_name}' has invalid retries={retries}; expected >= 0", file=sys.stderr)
                raise SystemExit(2)
            continue_on_error = bool(step.get("continue_on_error", False))

            attempt = 0
            result: subprocess.CompletedProcess[str] | None = None
            while attempt <= retries:
                cli = [
                    sys.executable,
                    "-m",
                    "geoprompt.demo",
                    step_command,
                    "--input-path",
                    str(input_path),
                    "--output-dir",
                    str(output_dir),
                ]

                for key, value in step.items():
                    if key in {"name", "command", "retries", "continue_on_error"}:
                        continue
                    flag = f"--{key.replace('_', '-')}"
                    if isinstance(value, bool):
                        if value:
                            cli.append(flag)
                    elif isinstance(value, list):
                        cli.append(flag)
                        cli.extend(str(item) for item in value)
                    elif value is not None:
                        cli.extend([flag, str(value)])

                result = subprocess.run(
                    cli,
                    capture_output=True,
                    text=True,
                    cwd=str(PROJECT_ROOT),
                    check=False,
                )

                if result.returncode == 0:
                    break
                attempt += 1
                if attempt <= retries:
                    logger.warning(
                        "Retrying pipeline step '%s' (%d/%d)",
                        step_name,
                        attempt,
                        retries,
                    )

            assert result is not None
            if result.returncode != 0:
                if continue_on_error:
                    if step_name not in failed_steps:
                        failed_steps.append(step_name)
                    checkpoint_payload = {
                        "completed_steps": completed_steps,
                        "failed_steps": failed_steps,
                        "last_failed_step": step_name,
                        "total_steps": len(steps),
                    }
                    write_json(checkpoint_path, checkpoint_payload)
                    run_results.append(
                        {
                            "name": step_name,
                            "status": "failed",
                            "command": step_command,
                            "attempts": retries + 1,
                            "exit_code": result.returncode,
                        }
                    )
                    logger.error(
                        "Pipeline step '%s' failed with exit code %d; continuing",
                        step_name,
                        result.returncode,
                    )
                    continue

                print(result.stderr, file=sys.stderr)
                print(f"error: pipeline step '{step_name}' failed with exit code {result.returncode}", file=sys.stderr)
                raise SystemExit(result.returncode)

            completed_steps.append(step_name)
            checkpoint_payload = {
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "last_completed_step": step_name,
                "total_steps": len(steps),
            }
            write_json(checkpoint_path, checkpoint_payload)
            run_results.append(
                {
                    "name": step_name,
                    "status": "completed",
                    "command": step_command,
                    "attempts": attempt + 1,
                }
            )

        _write_run_manifest(
            output_dir=output_dir,
            command="pipeline",
            input_path=input_path,
            output_paths=[checkpoint_path],
            args=args,
            extra={
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
                "step_results": run_results,
            },
        )
        logger.info("Pipeline complete for %s: %d/%d steps complete", input_path.name, len(completed_steps), len(steps))
        return {
            "input_path": str(input_path),
            "output_dir": str(output_dir),
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "step_results": run_results,
        }

    input_paths = _resolve_inputs()
    if len(input_paths) == 1 and getattr(args, "batch_input_dir", None) is None:
        _run_for_input(input_paths[0], args.output_dir)
        return

    batch_results: list[dict[str, Any]] = []
    for input_path in input_paths:
        batch_output_dir = args.output_dir / "batches" / input_path.stem
        batch_results.append(_run_for_input(input_path, batch_output_dir))

    summary_path = write_json(
        args.output_dir / "geoprompt_pipeline_batch_summary.json",
        {
            "schema_version": SCHEMA_VERSION,
            "command": "pipeline",
            "pipeline_file": str(pipeline_file),
            "batch_input_dir": str(args.batch_input_dir),
            "batch_pattern": args.batch_pattern,
            "results": batch_results,
        },
    )
    _write_run_manifest(
        output_dir=args.output_dir,
        command="pipeline_batch",
        input_path=pipeline_file,
        output_paths=[summary_path],
        args=args,
        extra={"inputs_processed": len(input_paths)},
    )
    logger.info("Batch pipeline complete for %d input files", len(input_paths))


def export_pressure_plot(
    records: list[dict[str, object]],
    output_path: Path,
    *,
    colormap: str = "YlOrRd",
    style_preset: str = "default",
    title: str | None = None,
    subtitle: str | None = None,
    export_formats: list[str] | None = None,
    extent_padding: float = 0.02,
    run_params: dict[str, Any] | None = None,
) -> Path:
    """Export a neighborhood pressure review plot.

    Args:
        records: Enriched feature records with neighborhood_pressure.
        output_path: Output file path for the chart.
        colormap: Matplotlib colormap name or preset key (item 81).
        style_preset: Thematic style preset name (item 86).
        title: Custom chart title (item 82).
        subtitle: Custom chart subtitle (item 82).
        export_formats: Additional export formats like 'svg', 'pdf' (item 85).
        extent_padding: Map extent padding in coordinate units (item 87).
        run_params: Parameters dict for chart metadata footer (item 90).

    Returns:
        Path to the saved chart.
    """
    with log_timing("export_pressure_plot", records=len(records)):
        output_path.parent.mkdir(parents=True, exist_ok=True)

        resolved_cmap = COLORMAP_PRESETS.get(colormap, colormap)
        style = STYLE_PRESETS.get(style_preset, STYLE_PRESETS["default"])

        figure, axis = plt.subplots(figsize=(10, 6))
        figure.patch.set_facecolor(style["bg_color"])
        axis.set_facecolor(style["bg_color"])

        # Item 31: Cache centroids instead of recomputing
        centroid_cache: dict[int, tuple[float, float]] = {}
        for i, record in enumerate(records):
            centroid_cache[i] = geometry_centroid(record["geometry"])

        xs = [centroid_cache[i][0] for i in range(len(records))]
        ys = [centroid_cache[i][1] for i in range(len(records))]
        pressures = [float(record["neighborhood_pressure"]) for record in records]
        sizes = [200 + pressure * 220 for pressure in pressures]

        for record in records:
            geometry = record["geometry"]
            vertices = geometry_vertices(geometry)
            if geometry_type(geometry) == "LineString":
                axis.plot(
                    [coord[0] for coord in vertices],
                    [coord[1] for coord in vertices],
                    color=style["line_color"],
                    linewidth=2.0,
                    alpha=0.8,
                )
            elif geometry_type(geometry) == "Polygon":
                axis.fill(
                    [coord[0] for coord in vertices],
                    [coord[1] for coord in vertices],
                    color=style["fill_color"],
                    alpha=0.45,
                    edgecolor=style["edge_color"],
                    linewidth=1.5,
                )

        # Item 89: Marker shape encoding by geometry type
        geom_types = [geometry_type(record["geometry"]) for record in records]
        markers_used = set(geom_types)
        if len(markers_used) > 1:
            for geom_t in markers_used:
                idxs = [i for i, gt in enumerate(geom_types) if gt == geom_t]
                marker = GEOMETRY_MARKERS.get(geom_t, "o")
                axis.scatter(
                    [xs[i] for i in idxs],
                    [ys[i] for i in idxs],
                    s=[sizes[i] for i in idxs],
                    c=[pressures[i] for i in idxs],
                    cmap=resolved_cmap,
                    edgecolors=style["text_color"],
                    linewidths=0.8,
                    marker=marker,
                    label=geom_t,
                    vmin=min(pressures),
                    vmax=max(pressures),
                )
            axis.legend(fontsize=7, loc="lower right")
            # Create invisible scatter for colorbar
            scatter = axis.scatter([], [], c=[], cmap=resolved_cmap, vmin=min(pressures), vmax=max(pressures))
        else:
            scatter = axis.scatter(
                xs,
                ys,
                s=sizes,
                c=pressures,
                cmap=resolved_cmap,
                edgecolors=style["text_color"],
                linewidths=0.8,
            )

        # Item 83: Better label collision handling
        label_positions: list[tuple[float, float]] = []
        for i, record in enumerate(records):
            centroid = centroid_cache[i]
            offset_x, offset_y = 6, 6
            for lx, ly in label_positions:
                if abs(centroid[0] - lx) < 0.005 and abs(centroid[1] - ly) < 0.005:
                    offset_y += 10
            label_positions.append(centroid)
            axis.annotate(
                record["name"],
                xy=centroid,
                xytext=(offset_x, offset_y),
                textcoords="offset points",
                fontsize=8,
                color=style["text_color"],
            )

        # Item 82: Chart title/subtitle customization
        chart_title = title or "GeoPrompt Neighborhood Pressure"
        axis.set_title(chart_title, fontsize=16, color=style["text_color"])
        if subtitle:
            axis.text(
                0.5, 1.02, subtitle,
                transform=axis.transAxes, fontsize=10,
                color=style["text_color"], ha="center", va="bottom",
            )

        axis.set_xlabel("Longitude")
        axis.set_ylabel("Latitude")
        axis.grid(color=style["grid_color"], linewidth=0.7, alpha=0.8)

        # Item 87: Map extent padding
        if xs and ys:
            axis.set_xlim(min(xs) - extent_padding, max(xs) + extent_padding)
            axis.set_ylim(min(ys) - extent_padding, max(ys) + extent_padding)

        # Item 84: Legend improvements and scale explanations
        colorbar = figure.colorbar(scatter, ax=axis)
        colorbar.set_label("Neighborhood pressure (weighted decay sum)")

        # Item 90: Chart metadata footer
        if run_params:
            footer = " | ".join(f"{k}={v}" for k, v in run_params.items())
            figure.text(0.5, 0.01, footer, fontsize=6, ha="center", color=style["text_color"], alpha=0.6)

        figure.tight_layout()
        figure.savefig(output_path, dpi=180, bbox_inches="tight")

        # Item 85: SVG and PDF export
        if export_formats:
            for fmt in export_formats:
                if fmt == "png":
                    continue
                alt_path = output_path.with_suffix(f".{fmt}")
                figure.savefig(alt_path, dpi=180, bbox_inches="tight", format=fmt)
                logger.info("Exported chart to %s", alt_path)

        plt.close(figure)
        return output_path


def build_demo_report(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    top_n: int = 5,
    no_plot: bool = False,
    skip_expensive: bool = False,
    colormap: str = "YlOrRd",
    style_preset: str = "default",
    chart_title: str | None = None,
    chart_subtitle: str | None = None,
    export_formats: list[str] | None = None,
) -> dict[str, object]:
    """Build the full GeoPrompt demo report.

    Args:
        input_path: Path to input JSON feature fixture.
        output_dir: Output directory for report and charts.
        top_n: Number of top results to include (item 26).
        no_plot: Skip chart generation for headless runs (item 23).
        skip_expensive: Skip expensive pairwise computations (item 27).
        colormap: Colormap for pressure plot (item 81).
        style_preset: Style preset for charts (item 86).
        chart_title: Override chart title (item 82).
        chart_subtitle: Override chart subtitle (item 82).
        export_formats: Additional chart export formats (item 85).

    Returns:
        Enriched demo report dictionary with schema version.
    """
    with log_timing("build_demo_report", input=str(input_path)):
        frame = read_features(input_path, crs="EPSG:4326")

        # Item 3: Clear error on zero features
        validate_non_empty_features(frame.to_records())

        log_trace("Loaded %d features from %s", len(frame), input_path)

        with log_timing("CRS projection"):
            projected_frame = frame.to_crs("EPSG:3857")

        valley_window = frame.query_bounds(min_x=-111.97, min_y=40.68, max_x=-111.84, max_y=40.79)

        with log_timing("neighborhood_pressure"):
            pressure = frame.neighborhood_pressure(weight_column="demand_index", scale=0.14, power=1.6)

        with log_timing("anchor_influence"):
            anchor = frame.anchor_influence(
                weight_column="priority_index",
                anchor="north-hub-point",
                scale=0.14,
                power=1.4,
            )

        with log_timing("corridor_accessibility"):
            corridor = frame.corridor_accessibility(
                weight_column="capacity_index",
                anchor="north-hub-point",
                scale=0.18,
                power=1.4,
            )

        enriched = frame.assign(
            neighborhood_pressure=pressure,
            anchor_influence=anchor,
            corridor_accessibility=corridor,
            geometry_type=frame.geometry_types(),
            geometry_length=frame.geometry_lengths(),
            geometry_area=frame.geometry_areas(),
        )

        log_trace("Enriched frame: %d features, %d columns", len(enriched), len(enriched.columns))

        if skip_expensive:
            top_interactions: list[dict[str, Any]] = []
            top_area_similarity: list[dict[str, Any]] = []
            logger.info("Skipped expensive pairwise computations (--skip-expensive)")
        else:
            with log_timing("interaction_table"):
                top_interactions = nlargest(
                    top_n,
                    enriched.interaction_table(
                        origin_weight="capacity_index",
                        destination_weight="demand_index",
                        scale=0.16,
                        power=1.5,
                        preferred_bearing=135.0,
                    ),
                    key=lambda item: float(item["interaction"]),
                )
                top_interactions = sorted(
                    top_interactions,
                    key=lambda item: (
                        -float(item["interaction"]),
                        str(item.get("origin", "")),
                        str(item.get("destination", "")),
                    ),
                )

            with log_timing("area_similarity_table"):
                top_area_similarity = nlargest(
                    top_n,
                    enriched.area_similarity_table(scale=0.2, power=1.2),
                    key=lambda item: float(item["area_similarity"]),
                )
                top_area_similarity = sorted(
                    top_area_similarity,
                    key=lambda item: (
                        -float(item["area_similarity"]),
                        str(item.get("origin", "")),
                        str(item.get("destination", "")),
                    ),
                )

        top_nearest_neighbors = enriched.nearest_neighbors(k=1)
        top_geographic_neighbors = enriched.nearest_neighbors(k=1, distance_method="haversine")

        chart_path_str = ""
        if not no_plot:
            chart_dir = output_dir / "charts"
            run_params = {"scale": 0.14, "power": 1.6, "crs": "EPSG:4326"}
            chart_path = export_pressure_plot(
                enriched.to_records(),
                chart_dir / "neighborhood-pressure-review.png",
                colormap=colormap,
                style_preset=style_preset,
                title=chart_title,
                subtitle=chart_subtitle,
                export_formats=export_formats,
                run_params=run_params,
            )
            chart_path_str = str(chart_path)

        # Item 4: Deterministic output ordering
        records = sorted(enriched.to_records(), key=lambda r: str(r.get("site_id", "")))

        # Item 10: Schema version
        report: dict[str, object] = add_schema_version({
            "package": "geoprompt",
            "equations": {
                "prompt_decay": "1 / (1 + distance / scale) ^ power",
                "prompt_influence": "weight * prompt_decay(distance, scale, power)",
                "prompt_interaction": "origin_weight * destination_weight * prompt_decay(distance, scale, power)",
                "corridor_strength": "weight * log(1 + corridor_length) * prompt_decay(distance, scale, power)",
                "area_similarity": "min(area_a, area_b) / max(area_a, area_b) * prompt_decay(distance, scale, power)",
            },
            "summary": {
                "feature_count": len(enriched),
                "crs": enriched.crs,
                "centroid": enriched.centroid(),
                "bounds": enriched.bounds().__dict__,
                "projected_bounds_3857": projected_frame.bounds().__dict__,
                "geometry_types": sorted(set(enriched.geometry_types())),
                "valley_window_feature_count": len(valley_window),
            },
            "top_interactions": top_interactions,
            "top_area_similarity": top_area_similarity,
            "top_nearest_neighbors": top_nearest_neighbors,
            "top_geographic_neighbors": top_geographic_neighbors,
            "records": records,
            "outputs": {
                "chart": chart_path_str,
            },
        })
        return report


def _write_csv(path: Path, records: list[dict[str, Any]]) -> Path:
    """Item 22: CSV output format support."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not records:
        path.write_text("", encoding="utf-8")
        return path
    fieldnames = list(records[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            flat = {}
            for k, v in record.items():
                flat[k] = json.dumps(v) if isinstance(v, (dict, list, tuple)) else v
            writer.writerow(flat)
    return path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments with full flag support (items 21-29)."""
    parser = argparse.ArgumentParser(
        description="Generate the GeoPrompt demo report and review plot.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Config: place geoprompt.toml in working directory for defaults.",
    )

    # Subcommand-style grouping (item 21)
    parser.add_argument(
        "command",
        nargs="?",
        default="report",
        choices=["report", "plot", "export", "accessibility", "gravity-flow", "suitability", "analyze", "pipeline"],
        help="Command to run: report (default), plot, export, accessibility, gravity-flow, suitability, analyze, or pipeline.",
    )

    # Path options
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH, help="Input JSON feature fixture.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory for report and charts.")
    parser.add_argument("--asset-path", type=Path, default=DEFAULT_ASSET_PATH, help="Committed asset path for the review plot.")
    parser.add_argument("--config", type=Path, default=None, help="Path to geoprompt.toml config file (item 30).")
    parser.add_argument("--pipeline-file", type=Path, default=None, help="Path to pipeline JSON file (pipeline command only).")
    parser.add_argument("--resume", action="store_true", help="Resume pipeline execution from checkpoint state.")
    parser.add_argument("--batch-input-dir", type=Path, default=None, help="Directory of input files for batch pipeline runs.")
    parser.add_argument("--batch-pattern", default="*.json", help="Glob pattern for files in --batch-input-dir.")

    # Output format (item 22)
    parser.add_argument("--format", dest="output_format", default="json", choices=["json", "csv", "geojson"],
                        help="Output format for the report.")

    # Behavior flags (items 23-29)
    parser.add_argument("--no-plot", action="store_true", help="Skip chart generation for headless runs (item 23).")
    parser.add_argument("--no-asset-copy", action="store_true", help="Skip copying chart to asset path (item 24).")
    parser.add_argument("--scale", type=float, default=0.14, help="Decay scale parameter (item 25).")
    parser.add_argument("--power", type=float, default=1.6, help="Decay power parameter (item 25).")
    parser.add_argument("--top-n", type=int, default=5, help="Number of top results to include (item 26).")
    parser.add_argument("--skip-expensive", action="store_true", help="Skip expensive pairwise computations (item 27).")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files (item 28).")
    parser.add_argument("--dry-run", action="store_true", help="Validate input without writing files (item 29).")

    # Analysis command options
    parser.add_argument("--id-column", default="site_id", help="Identifier column for analysis outputs.")
    parser.add_argument("--opportunities-column", default="demand_index", help="Opportunities column for accessibility command.")
    parser.add_argument("--origin-weight-column", default="capacity_index", help="Origin weight column for gravity-flow command.")
    parser.add_argument("--destination-weight-column", default="demand_index", help="Destination weight column for gravity-flow command.")
    parser.add_argument("--friction", type=float, default=1.0, help="Distance friction for accessibility command.")
    parser.add_argument("--beta", type=float, default=2.0, help="Gravity distance exponent for gravity-flow command.")
    parser.add_argument("--offset", type=float, default=1e-6, help="Gravity offset for gravity-flow command.")
    parser.add_argument("--distance-method", default="euclidean", choices=["euclidean", "haversine"], help="Distance method for analysis commands.")
    parser.add_argument("--include-self", action="store_true", help="Include origin-to-origin self links in analysis commands.")
    parser.add_argument("--criteria-columns", nargs="*", default=["demand_index", "capacity_index", "priority_index"], help="Criteria columns for suitability command.")
    parser.add_argument("--criteria-weights", nargs="*", type=float, default=None, help="Optional weights for suitability criteria.")

    # Large-data options
    parser.add_argument("--max-distance", type=float, default=None, help="Skip feature pairs beyond this distance (degrees or meters).")
    parser.add_argument("--max-results", type=int, default=None, help="Return at most this many results from pairwise tools.")
    parser.add_argument("--chunk-size", type=int, default=None, help="Process input in chunks of this many features.")
    parser.add_argument("--sample", type=float, default=None, help="Random sample fraction (0 < sample <= 1) of input features.")

    # Unified analyze command options
    parser.add_argument(
        "--tool",
        choices=ANALYZE_TOOLS,
        default=None,
        help="Analysis tool name for the analyze command (one of the 23 available tools).",
    )
    parser.add_argument(
        "--columns",
        nargs="*",
        default=[],
        help=(
            "Column names passed positionally to the selected analysis tool. "
            "Number and order of columns depends on the tool. "
            "Sensible defaults are applied when omitted."
        ),
    )

    # Logging (items 17-20)
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose DEBUG logging.")
    parser.add_argument("--trace", action="store_true", help="Enable trace-level output for intermediate summaries.")

    # Plotting options (items 81-90)
    parser.add_argument("--colormap", default="YlOrRd", help="Colormap name or preset (item 81).")
    parser.add_argument("--style-preset", default="default", choices=list(STYLE_PRESETS),
                        help="Thematic style preset for charts (item 86).")
    parser.add_argument("--chart-title", default=None, help="Override chart title (item 82).")
    parser.add_argument("--chart-subtitle", default=None, help="Chart subtitle text (item 82).")
    parser.add_argument("--export-formats", nargs="*", default=["png"], help="Chart export formats: png svg pdf (item 85).")

    return parser.parse_args()


def main() -> None:
    """Entry point for geoprompt-demo CLI."""
    args = parse_args()

    # Item 30: Config file support
    config = load_config(args.config)

    # Items 17-18: Structured logging
    configure_logging(verbose=args.verbose or config.verbose, trace=args.trace or config.trace)

    logger.info("GeoPrompt demo v%s (schema %s)", "0.1.8", SCHEMA_VERSION)

    if args.command == "pipeline":
        _run_pipeline(args)
        return

    # Item 29: Dry-run mode
    if args.dry_run:
        frame = read_features(args.input_path, crs="EPSG:4326")
        validate_non_empty_features(frame.to_records())
        logger.info("Dry run: validated %d features from %s", len(frame), args.input_path)
        return

    if args.command == "plot":
        frame = read_features(args.input_path, crs="EPSG:4326")
        pressure = frame.neighborhood_pressure(weight_column="demand_index", scale=args.scale, power=args.power)
        enriched = frame.assign(neighborhood_pressure=pressure)
        chart_path = export_pressure_plot(
            enriched.to_records(),
            args.output_dir / "charts" / "neighborhood-pressure-review.png",
            colormap=args.colormap,
            style_preset=args.style_preset,
            title=args.chart_title,
            subtitle=args.chart_subtitle,
            export_formats=args.export_formats,
        )
        _write_run_manifest(
            output_dir=args.output_dir,
            command="plot",
            input_path=args.input_path,
            output_paths=[chart_path],
            args=args,
        )
        logger.info("Wrote chart to %s", args.output_dir / "charts")
        return

    if args.command == "accessibility":
        frame = read_features(args.input_path, crs="EPSG:4326")
        rows = frame.accessibility_analysis(
            opportunities=args.opportunities_column,
            id_column=args.id_column,
            friction=args.friction,
            include_self=args.include_self,
            distance_method=args.distance_method,
        )

        if args.output_format == "csv":
            output_path = _write_csv(args.output_dir / "geoprompt_accessibility.csv", rows)
        elif args.output_format == "geojson":
            score_lookup = {row[args.id_column]: float(row["accessibility_score"]) for row in rows}
            enriched = frame.assign(
                accessibility_score=[float(score_lookup.get(record.get(args.id_column), 0.0)) for record in frame.to_records()]
            )
            output_path = write_geojson(args.output_dir / "geoprompt_accessibility.geojson", enriched, id_column=args.id_column)
        else:
            output_path = write_json(
                args.output_dir / "geoprompt_accessibility.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "command": "accessibility",
                    "records": rows,
                },
            )
        _write_run_manifest(
            output_dir=args.output_dir,
            command="accessibility",
            input_path=args.input_path,
            output_paths=[output_path],
            args=args,
        )
        logger.info("Wrote accessibility analysis to %s", output_path)
        return

    if args.command == "gravity-flow":
        frame = read_features(args.input_path, crs="EPSG:4326")
        rows = frame.gravity_flow_analysis(
            origin_weight=args.origin_weight_column,
            destination_weight=args.destination_weight_column,
            id_column=args.id_column,
            beta=args.beta,
            offset=args.offset,
            include_self=args.include_self,
            distance_method=args.distance_method,
        )

        if args.output_format == "csv":
            output_path = _write_csv(args.output_dir / "geoprompt_gravity_flow.csv", rows)
        else:
            output_path = write_json(
                args.output_dir / "geoprompt_gravity_flow.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "command": "gravity-flow",
                    "records": rows,
                },
            )
        _write_run_manifest(
            output_dir=args.output_dir,
            command="gravity-flow",
            input_path=args.input_path,
            output_paths=[output_path],
            args=args,
        )
        logger.info("Wrote gravity-flow analysis to %s", output_path)
        return

    if args.command == "suitability":
        frame = read_features(args.input_path, crs="EPSG:4326")
        rows = frame.suitability_analysis(
            criteria_columns=args.criteria_columns,
            id_column=args.id_column,
            criteria_weights=args.criteria_weights,
        )

        if args.output_format == "csv":
            output_path = _write_csv(args.output_dir / "geoprompt_suitability.csv", rows)
        elif args.output_format == "geojson":
            score_lookup = {row[args.id_column]: float(row["suitability_score"]) for row in rows}
            enriched = frame.assign(
                suitability_score=[float(score_lookup.get(record.get(args.id_column), 0.0)) for record in frame.to_records()]
            )
            output_path = write_geojson(args.output_dir / "geoprompt_suitability.geojson", enriched, id_column=args.id_column)
        else:
            output_path = write_json(
                args.output_dir / "geoprompt_suitability.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "command": "suitability",
                    "records": rows,
                },
            )
        _write_run_manifest(
            output_dir=args.output_dir,
            command="suitability",
            input_path=args.input_path,
            output_paths=[output_path],
            args=args,
        )
        logger.info("Wrote suitability analysis to %s", output_path)
        return

    if args.command == "analyze":
        if not args.tool:
            import sys as _sys
            print("error: --tool is required for the analyze command.", file=_sys.stderr)
            print(f"  Available tools: {', '.join(ANALYZE_TOOLS)}", file=_sys.stderr)
            raise SystemExit(2)

        _chunk_size: int | None = getattr(args, "chunk_size", None)
        _max_distance: float | None = getattr(args, "max_distance", None)
        _max_results: int | None = getattr(args, "max_results", None)
        _sample_frac: float | None = getattr(args, "sample", None)

        if _chunk_size is not None:
            _frames_to_process = list(read_features_chunked(args.input_path, chunk_size=_chunk_size, crs="EPSG:4326"))
        else:
            _raw_frame = read_features(args.input_path, crs="EPSG:4326")
            if _sample_frac is not None:
                if not (0.0 < _sample_frac <= 1.0):
                    import sys as _sys2
                    print("error: --sample must be between 0 and 1 (exclusive of 0).", file=_sys2.stderr)
                    raise SystemExit(2)
                _all_rows = _raw_frame.to_records()
                _k = max(1, int(len(_all_rows) * _sample_frac))
                from .frame import GeoPromptFrame as _GPF
                _raw_frame = _GPF.from_records(_random.sample(_all_rows, _k), crs=_raw_frame.crs)
            _frames_to_process = [_raw_frame]

        cols = list(args.columns or [])

        def _c(idx: int, default: str) -> str:
            return cols[idx] if idx < len(cols) else default

        id_col = args.id_column
        dm = args.distance_method
        tool = args.tool

        def _make_dispatch(frame_obj: Any) -> dict:
            _a = frame_obj.analysis
            return {
                "accessibility": lambda: _a.accessibility(
                    opportunities=_c(0, "demand_index"),
                    id_column=id_col,
                    friction=args.friction,
                    include_self=args.include_self,
                    distance_method=dm,
                    max_distance=_max_distance,
                ),
                "gravity-flow": lambda: _a.gravity_flow(
                    origin_weight=_c(0, "capacity_index"),
                    destination_weight=_c(1, "demand_index"),
                    id_column=id_col,
                    beta=args.beta,
                    offset=args.offset,
                    include_self=args.include_self,
                    distance_method=dm,
                    max_distance=_max_distance,
                    max_results=_max_results,
                ),
                "suitability": lambda: _a.suitability(
                    criteria_columns=cols if cols else args.criteria_columns,
                    id_column=id_col,
                    criteria_weights=args.criteria_weights,
                ),
                "catchment-competition": lambda: _a.catchment_competition(
                    demand_column=_c(0, "demand_index"),
                    supply_column=_c(1, "capacity_index"),
                    id_column=id_col,
                    distance_method=dm,
                    max_distance=_max_distance,
                ),
                "hotspot-scan": lambda: _a.hotspot_scan(
                    value_column=_c(0, "demand_index"),
                    id_column=id_col,
                ),
                "equity-gap": lambda: _a.equity_gap(
                    min_column=_c(0, "capacity_index"),
                    max_column=_c(1, "priority_index"),
                    id_column=id_col,
                ),
                "network-reliability": lambda: _a.network_reliability(
                    capacity_column=_c(0, "capacity_index"),
                    failure_proxy_column=_c(1, "demand_index"),
                    id_column=id_col,
                ),
                "transit-service-gap": lambda: _a.transit_service_gap(
                    service_frequency_column=_c(0, "capacity_index"),
                    coverage_column=_c(1, "demand_index"),
                    id_column=id_col,
                    distance_method=dm,
                ),
                "congestion-hotspots": lambda: _a.congestion_hotspots(
                    flow_column=_c(0, "demand_index"),
                    capacity_column=_c(1, "capacity_index"),
                    id_column=id_col,
                ),
                "walkability-audit": lambda: _a.walkability_audit(
                    connectivity_column=_c(0, "demand_index"),
                    density_column=_c(1, "capacity_index"),
                    amenities_column=_c(2, "priority_index"),
                    id_column=id_col,
                ),
                "gentrification-scan": lambda: _a.gentrification_scan(
                    appreciation_column=_c(0, "priority_index"),
                    income_column=_c(1, "capacity_index"),
                    displacement_column=_c(2, "demand_index"),
                    id_column=id_col,
                ),
                "land-value-surface": lambda: _a.land_value_surface(
                    base_value_column=_c(0, "priority_index"),
                    id_column=id_col,
                    distance_method=dm,
                ),
                "pollution-surface": lambda: _a.pollution_surface(
                    source_column=_c(0, "priority_index"),
                    id_column=id_col,
                    distance_method=dm,
                ),
                "habitat-fragmentation-map": lambda: _a.habitat_fragmentation_map(
                    patch_column=_c(0, "capacity_index"),
                    connectivity_column=_c(1, "demand_index"),
                    id_column=id_col,
                    distance_method=dm,
                ),
                "climate-vulnerability-map": lambda: _a.climate_vulnerability_map(
                    exposure_column=_c(0, "priority_index"),
                    sensitivity_column=_c(1, "demand_index"),
                    adaptive_column=_c(2, "capacity_index"),
                    id_column=id_col,
                ),
                "migration-pull-map": lambda: _a.migration_pull_map(
                    economic_column=_c(0, "demand_index"),
                    quality_column=_c(1, "capacity_index"),
                    cultural_column=_c(2, "priority_index"),
                    id_column=id_col,
                    distance_method=dm,
                ),
                "mortality-risk-map": lambda: _a.mortality_risk_map(
                    population_column=_c(0, "priority_index"),
                    disease_column=_c(1, "demand_index"),
                    healthcare_column=_c(2, "capacity_index"),
                    id_column=id_col,
                ),
                "market-power-map": lambda: _a.market_power_map(
                    largest_share_column=_c(0, "demand_index"),
                    concentration_column=_c(1, "capacity_index"),
                    id_column=id_col,
                ),
                "trade-corridor-map": lambda: _a.trade_corridor_map(
                    export_column=_c(0, "capacity_index"),
                    import_column=_c(1, "demand_index"),
                    id_column=id_col,
                    distance_method=dm,
                    max_distance=_max_distance,
                    max_results=_max_results,
                ),
                "community-cohesion-map": lambda: _a.community_cohesion_map(
                    internal_column=_c(0, "capacity_index"),
                    external_column=_c(1, "demand_index"),
                    identity_column=_c(2, "priority_index"),
                    id_column=id_col,
                ),
                "cultural-similarity-matrix": lambda: _a.cultural_similarity_matrix(
                    value_column=_c(0, "demand_index"),
                    language_column=_c(1, "capacity_index"),
                    tradition_column=_c(2, "priority_index"),
                    history_column=_c(3, "demand_index"),
                    id_column=id_col,
                    max_results=_max_results,
                ),
                "noise-impact-map": lambda: _a.noise_impact_map(
                    source_column=_c(0, "priority_index"),
                    barrier_column=_c(1, "capacity_index"),
                    id_column=id_col,
                    distance_method=dm,
                ),
                "visual-prominence-map": lambda: _a.visual_prominence_map(
                    vertical_column=_c(0, "priority_index"),
                    range_column=_c(1, "capacity_index"),
                    distinctiveness_column=_c(2, "demand_index"),
                    id_column=id_col,
                    distance_method=dm,
                ),
                "drought-stress-map": lambda: _a.drought_stress_map(
                    demand_column=_c(0, "demand_index"),
                    supply_column=_c(1, "capacity_index"),
                    reserve_column=_c(2, "priority_index"),
                    id_column=id_col,
                ),
                "heat-island-map": lambda: _a.heat_island_map(
                    impervious_column=_c(0, "demand_index"),
                    canopy_column=_c(1, "capacity_index"),
                    albedo_column=_c(2, "priority_index"),
                    id_column=id_col,
                ),
                "school-access-map": lambda: _a.school_access_map(
                    capacity_column=_c(0, "capacity_index"),
                    demand_column=_c(1, "demand_index"),
                    id_column=id_col,
                    distance_method=dm,
                ),
                "healthcare-access-map": lambda: _a.healthcare_access_map(
                    provider_column=_c(0, "capacity_index"),
                    population_column=_c(1, "demand_index"),
                    id_column=id_col,
                    distance_method=dm,
                ),
                "food-desert-map": lambda: _a.food_desert_map(
                    grocery_column=_c(0, "demand_index"),
                    vehicle_column=_c(1, "capacity_index"),
                    transit_column=_c(2, "priority_index"),
                    id_column=id_col,
                ),
                "digital-divide-map": lambda: _a.digital_divide_map(
                    broadband_column=_c(0, "demand_index"),
                    device_column=_c(1, "capacity_index"),
                    literacy_column=_c(2, "priority_index"),
                    id_column=id_col,
                ),
                "wildfire-risk-map": lambda: _a.wildfire_risk_map(
                    fuel_column=_c(0, "demand_index"),
                    dryness_column=_c(1, "capacity_index"),
                    wind_column=_c(2, "priority_index"),
                    suppression_column=_c(3, "capacity_index"),
                    id_column=id_col,
                ),
                "emergency-response-map": lambda: _a.emergency_response_map(
                    station_column=_c(0, "capacity_index"),
                    coverage_column=_c(1, "demand_index"),
                    id_column=id_col,
                    distance_method=dm,
                ),
                "infrastructure-lifecycle-map": lambda: _a.infrastructure_lifecycle_map(
                    age_column=_c(0, "demand_index"),
                    life_column=_c(1, "capacity_index"),
                    maintenance_column=_c(2, "priority_index"),
                    id_column=id_col,
                ),
                "adaptive-capacity-map": lambda: _a.adaptive_capacity_map(
                    income_column=_c(0, "demand_index"),
                    education_column=_c(1, "capacity_index"),
                    health_column=_c(2, "priority_index"),
                    governance_column=_c(3, "demand_index"),
                    id_column=id_col,
                ),
            }

        _all_output_rows: list[dict] = []
        for _chunk_f in _frames_to_process:
            _all_output_rows.extend(_make_dispatch(_chunk_f)[tool]())
        rows = _all_output_rows
        stem = tool.replace("-", "_")
        if args.output_format == "csv":
            output_path = _write_csv(args.output_dir / f"geoprompt_analyze_{stem}.csv", rows)
        else:
            output_path = write_json(
                args.output_dir / f"geoprompt_analyze_{stem}.json",
                {"schema_version": SCHEMA_VERSION, "tool": tool, "records": rows},
            )
        _write_run_manifest(
            output_dir=args.output_dir,
            command=f"analyze_{stem}",
            input_path=args.input_path,
            output_paths=[output_path],
            args=args,
            extra={"tool": tool, "row_count": len(rows)},
        )
        logger.info("Wrote analyze/%s to %s", tool, output_path)
        return

    report = build_demo_report(
        input_path=args.input_path,
        output_dir=args.output_dir,
        top_n=args.top_n,
        no_plot=args.no_plot,
        skip_expensive=args.skip_expensive,
        colormap=args.colormap,
        style_preset=args.style_preset,
        chart_title=args.chart_title,
        chart_subtitle=args.chart_subtitle,
        export_formats=args.export_formats,
    )

    # Item 22: Output format selection
    if args.output_format == "csv":
        report_path = _write_csv(args.output_dir / "geoprompt_demo_report.csv", report["records"])
    elif args.output_format == "geojson":
        enriched_frame = read_features(args.input_path, crs="EPSG:4326").assign(
            neighborhood_pressure=[record["neighborhood_pressure"] for record in report["records"]],
            anchor_influence=[record["anchor_influence"] for record in report["records"]],
            corridor_accessibility=[record["corridor_accessibility"] for record in report["records"]],
        )
        report_path = write_geojson(args.output_dir / "geoprompt_demo_report.geojson", enriched_frame)
    else:
        report_path = write_json(args.output_dir / "geoprompt_demo_report.json", report)

    # Item 33: Reuse report records instead of re-reading input
    enriched_frame = read_features(args.input_path, crs="EPSG:4326").assign(
        neighborhood_pressure=[record["neighborhood_pressure"] for record in report["records"]],
        anchor_influence=[record["anchor_influence"] for record in report["records"]],
        corridor_accessibility=[record["corridor_accessibility"] for record in report["records"]],
        geometry_type=[record["geometry_type"] for record in report["records"]],
        geometry_length=[record["geometry_length"] for record in report["records"]],
        geometry_area=[record["geometry_area"] for record in report["records"]],
    )
    geojson_path = write_geojson(args.output_dir / "geoprompt_demo_features.geojson", enriched_frame)

    # Item 24: No-asset-copy mode
    if not args.no_asset_copy and not args.no_plot:
        export_pressure_plot(report["records"], args.asset_path)
        logger.info("Wrote GeoPrompt asset to %s", args.asset_path)

    output_paths = [report_path, geojson_path]
    if report.get("outputs", {}).get("chart"):
        output_paths.append(Path(report["outputs"]["chart"]))
    _write_run_manifest(
        output_dir=args.output_dir,
        command="report",
        input_path=args.input_path,
        output_paths=output_paths,
        args=args,
    )

    logger.info("Wrote GeoPrompt report to %s", report_path)
    logger.info("Wrote GeoPrompt GeoJSON to %s", geojson_path)


__all__ = ["build_demo_report", "export_pressure_plot", "main"]


if __name__ == "__main__":
    main()
