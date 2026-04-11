from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .config import load_scenario, write_default_scenario
from .prepare import prepare_raster_stack
from .preview import render_preview_png
from .workflow import evaluate_cumulative_cost, run_demo_workflow, run_multipatch_workflow, run_real_workflow


def _parse_cell(value: str) -> tuple[int, int]:
    if "," not in value:
        raise argparse.ArgumentTypeError("Cell must be in 'row,col' format")
    row_text, col_text = value.split(",", maxsplit=1)
    try:
        row = int(row_text)
        col = int(col_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Cell coordinates must be integers") from exc
    if row < 0 or col < 0:
        raise argparse.ArgumentTypeError("Cell coordinates must be >= 0")
    return row, col


def _run_from_manifest_payload(
    *,
    scenario_path: str,
    manifest_path: str,
    mode: str,
    source: tuple[int, int] | None,
    target: tuple[int, int] | None,
    max_pairs: int | None,
    output_dir: str,
) -> dict[str, float | int]:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))

    required_manifest_keys = {
        "land_cover",
        "water_distance",
        "slope",
        "human_footprint",
        "road_mask",
        "urban_mask",
        "ag_mask",
    }
    missing = required_manifest_keys - set(manifest)
    if missing:
        raise ValueError(f"Manifest missing required keys: {sorted(missing)}")

    layer_paths = {
        "land_cover": manifest["land_cover"],
        "water_distance": manifest["water_distance"],
        "slope": manifest["slope"],
        "human_footprint": manifest["human_footprint"],
    }
    if "prey" in manifest:
        layer_paths["prey"] = manifest["prey"]

    barrier_paths = {
        "road": manifest["road_mask"],
        "urban": manifest["urban_mask"],
        "agriculture": manifest["ag_mask"],
    }

    scenario = load_scenario(scenario_path)

    active_mode = mode
    if active_mode == "auto":
        active_mode = "multipatch" if "patches" in manifest else "single"

    if active_mode == "multipatch":
        if "patches" not in manifest:
            raise ValueError("Manifest does not include 'patches'; rerun prep-raster-stack with --patches")
        return run_multipatch_workflow(
            scenario=scenario,
            output_dir=output_dir,
            layer_paths=layer_paths,
            barrier_paths=barrier_paths,
            patch_raster_path=manifest["patches"],
            max_pairs=max_pairs,
        )

    if source is None or target is None:
        raise ValueError("Single mode requires both --source and --target")

    return run_real_workflow(
        scenario=scenario,
        output_dir=output_dir,
        layer_paths=layer_paths,
        barrier_paths=barrier_paths,
        source=source,
        target=target,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bobcat-corridor",
        description="Bobcat-focused habitat suitability and corridor analysis toolkit.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_p = subparsers.add_parser("init-config", help="Write a default scenario JSON config")
    init_p.add_argument("--output", default="configs/default_scenario.json", help="Output JSON config path")

    run_p = subparsers.add_parser("run-demo", help="Run synthetic end-to-end corridor workflow")
    run_p.add_argument("--config", default="configs/default_scenario.json", help="Scenario JSON config path")
    run_p.add_argument("--output-dir", default="outputs/latest-run", help="Directory for workflow outputs")

    real_p = subparsers.add_parser("run-real", help="Run workflow using prepared real raster/mask inputs")
    real_p.add_argument("--config", default="configs/default_scenario.json", help="Scenario JSON config path")
    real_p.add_argument("--land-cover", required=True, help="Raster path for land cover suitability")
    real_p.add_argument("--water-distance", required=True, help="Raster path for water distance suitability")
    real_p.add_argument("--slope", required=True, help="Raster path for slope suitability")
    real_p.add_argument("--human-footprint", required=True, help="Raster path for human footprint suitability")
    real_p.add_argument("--prey", help="Optional raster path for prey suitability")
    real_p.add_argument("--road-mask", required=True, help="Barrier mask raster path for roads")
    real_p.add_argument("--urban-mask", required=True, help="Barrier mask raster path for urban areas")
    real_p.add_argument("--ag-mask", required=True, help="Barrier mask raster path for agriculture")
    real_p.add_argument("--source", required=True, type=_parse_cell, help="Source habitat cell as row,col")
    real_p.add_argument("--target", required=True, type=_parse_cell, help="Target habitat cell as row,col")
    real_p.add_argument("--output-dir", default="outputs/latest-real-run", help="Directory for workflow outputs")

    prep_p = subparsers.add_parser("prep-raster-stack", help="Align GeoTIFF layers to one reference and export .npy")
    prep_p.add_argument("--reference", required=True, help="Reference GeoTIFF for CRS, extent, and resolution")
    prep_p.add_argument("--land-cover", required=True, help="Land cover suitability GeoTIFF")
    prep_p.add_argument("--water-distance", required=True, help="Water distance suitability GeoTIFF")
    prep_p.add_argument("--slope", required=True, help="Slope suitability GeoTIFF")
    prep_p.add_argument("--human-footprint", required=True, help="Human footprint suitability GeoTIFF")
    prep_p.add_argument("--prey", help="Optional prey suitability GeoTIFF")
    prep_p.add_argument("--road-mask", required=True, help="Road mask GeoTIFF")
    prep_p.add_argument("--urban-mask", required=True, help="Urban mask GeoTIFF")
    prep_p.add_argument("--ag-mask", required=True, help="Agriculture mask GeoTIFF")
    prep_p.add_argument("--patches", help="Optional patch ID GeoTIFF for multipatch mode")
    prep_p.add_argument("--resampling", default="bilinear", choices=["nearest", "bilinear", "cubic"])
    prep_p.add_argument("--output-dir", default="data/processed/stack", help="Output directory for .npy layers")

    multi_p = subparsers.add_parser("run-multipatch", help="Run pairwise corridors across patch IDs")
    multi_p.add_argument("--config", default="configs/default_scenario.json", help="Scenario JSON config path")
    multi_p.add_argument("--land-cover", required=True, help="Raster path for land cover suitability")
    multi_p.add_argument("--water-distance", required=True, help="Raster path for water distance suitability")
    multi_p.add_argument("--slope", required=True, help="Raster path for slope suitability")
    multi_p.add_argument("--human-footprint", required=True, help="Raster path for human footprint suitability")
    multi_p.add_argument("--prey", help="Optional raster path for prey suitability")
    multi_p.add_argument("--road-mask", required=True, help="Barrier mask raster path for roads")
    multi_p.add_argument("--urban-mask", required=True, help="Barrier mask raster path for urban areas")
    multi_p.add_argument("--ag-mask", required=True, help="Barrier mask raster path for agriculture")
    multi_p.add_argument("--patch-raster", required=True, help="Raster of patch IDs, with IDs > 0 as habitat patches")
    multi_p.add_argument("--max-pairs", type=int, help="Optional maximum pair count for quicker runs")
    multi_p.add_argument("--output-dir", default="outputs/latest-multipatch-run", help="Directory for multipatch outputs")

    preview_p = subparsers.add_parser("render-preview", help="Render quick corridor preview PNG")
    preview_p.add_argument("--suitability", required=True, help="Path to suitability .npy")
    preview_p.add_argument("--corridor-mask", required=True, help="Path to corridor_mask .npy")
    preview_p.add_argument("--path-csv", required=True, help="Path to least_cost_path.csv")
    preview_p.add_argument("--output-png", default="outputs/latest-run/preview.png", help="Output PNG path")
    preview_p.add_argument("--title", default="Bobcat Corridor Preview", help="Plot title")

    manifest_p = subparsers.add_parser(
        "run-from-manifest",
        help="Run corridor analysis using stack_manifest.json from prep-raster-stack",
    )
    manifest_p.add_argument("--config", default="configs/default_scenario.json", help="Scenario JSON config path")
    manifest_p.add_argument("--manifest", required=True, help="Path to stack_manifest.json")
    manifest_p.add_argument(
        "--mode",
        choices=["auto", "single", "multipatch"],
        default="auto",
        help="Execution mode: auto uses multipatch when patches are present",
    )
    manifest_p.add_argument("--source", type=_parse_cell, help="Required for single mode: source cell row,col")
    manifest_p.add_argument("--target", type=_parse_cell, help="Required for single mode: target cell row,col")
    manifest_p.add_argument("--max-pairs", type=int, help="Optional max pairs for multipatch mode")
    manifest_p.add_argument("--output-dir", default="outputs/latest-manifest-run", help="Output directory")

    pipe_p = subparsers.add_parser(
        "run-pipeline",
        help="One-shot run: prep GeoTIFF stack, run analysis from manifest, optionally render preview",
    )
    pipe_p.add_argument("--config", default="configs/default_scenario.json", help="Scenario JSON config path")
    pipe_p.add_argument("--reference", required=True, help="Reference GeoTIFF for CRS, extent, and resolution")
    pipe_p.add_argument("--land-cover", required=True, help="Land cover suitability GeoTIFF")
    pipe_p.add_argument("--water-distance", required=True, help="Water distance suitability GeoTIFF")
    pipe_p.add_argument("--slope", required=True, help="Slope suitability GeoTIFF")
    pipe_p.add_argument("--human-footprint", required=True, help="Human footprint suitability GeoTIFF")
    pipe_p.add_argument("--prey", help="Optional prey suitability GeoTIFF")
    pipe_p.add_argument("--road-mask", required=True, help="Road mask GeoTIFF")
    pipe_p.add_argument("--urban-mask", required=True, help="Urban mask GeoTIFF")
    pipe_p.add_argument("--ag-mask", required=True, help="Agriculture mask GeoTIFF")
    pipe_p.add_argument("--patches", help="Optional patch ID GeoTIFF for multipatch mode")
    pipe_p.add_argument(
        "--mode",
        choices=["auto", "single", "multipatch"],
        default="auto",
        help="Execution mode after stack prep",
    )
    pipe_p.add_argument("--source", type=_parse_cell, help="Required for single mode: source cell row,col")
    pipe_p.add_argument("--target", type=_parse_cell, help="Required for single mode: target cell row,col")
    pipe_p.add_argument("--max-pairs", type=int, help="Optional max pairs for multipatch mode")
    pipe_p.add_argument("--resampling", default="bilinear", choices=["nearest", "bilinear", "cubic"])
    pipe_p.add_argument("--stack-dir", default="data/processed/stack", help="Intermediate stack output directory")
    pipe_p.add_argument("--output-dir", default="outputs/latest-pipeline-run", help="Analysis output directory")
    pipe_p.add_argument("--render-preview", action="store_true", help="Render PNG preview for single mode output")
    pipe_p.add_argument("--preview-png", default="preview.png", help="Preview PNG name or path")
    pipe_p.add_argument("--preview-title", default="Bobcat Corridor Preview", help="Preview plot title")

    eval_p = subparsers.add_parser("evaluate", help="Evaluate an existing cumulative cost raster (.npy)")
    eval_p.add_argument("--cost-raster", required=True, help="Path to cumulative_cost.npy")
    eval_p.add_argument("--quantile", type=float, default=0.10, help="Corridor quantile threshold")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "init-config":
        out = write_default_scenario(args.output)
        print(f"Wrote default scenario: {out}")
        return 0

    if args.command == "run-demo":
        scenario = load_scenario(args.config)
        summary = run_demo_workflow(scenario, output_dir=args.output_dir)
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "run-real":
        scenario = load_scenario(args.config)
        layer_paths = {
            "land_cover": args.land_cover,
            "water_distance": args.water_distance,
            "slope": args.slope,
            "human_footprint": args.human_footprint,
        }
        if args.prey:
            layer_paths["prey"] = args.prey

        barrier_paths = {
            "road": args.road_mask,
            "urban": args.urban_mask,
            "agriculture": args.ag_mask,
        }

        summary = run_real_workflow(
            scenario=scenario,
            output_dir=args.output_dir,
            layer_paths=layer_paths,
            barrier_paths=barrier_paths,
            source=args.source,
            target=args.target,
        )
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "prep-raster-stack":
        layers = {
            "land_cover": args.land_cover,
            "water_distance": args.water_distance,
            "slope": args.slope,
            "human_footprint": args.human_footprint,
            "road_mask": args.road_mask,
            "urban_mask": args.urban_mask,
            "ag_mask": args.ag_mask,
        }
        if args.prey:
            layers["prey"] = args.prey
        if args.patches:
            layers["patches"] = args.patches

        manifest = prepare_raster_stack(
            reference_raster=args.reference,
            layers=layers,
            output_dir=args.output_dir,
            resampling=args.resampling,
        )
        print(json.dumps(manifest, indent=2))
        return 0

    if args.command == "run-multipatch":
        scenario = load_scenario(args.config)
        layer_paths = {
            "land_cover": args.land_cover,
            "water_distance": args.water_distance,
            "slope": args.slope,
            "human_footprint": args.human_footprint,
        }
        if args.prey:
            layer_paths["prey"] = args.prey

        barrier_paths = {
            "road": args.road_mask,
            "urban": args.urban_mask,
            "agriculture": args.ag_mask,
        }

        summary = run_multipatch_workflow(
            scenario=scenario,
            output_dir=args.output_dir,
            layer_paths=layer_paths,
            barrier_paths=barrier_paths,
            patch_raster_path=args.patch_raster,
            max_pairs=args.max_pairs,
        )
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "render-preview":
        out_path = render_preview_png(
            suitability_path=args.suitability,
            corridor_mask_path=args.corridor_mask,
            path_csv=args.path_csv,
            output_png=args.output_png,
            title=args.title,
        )
        print(f"Wrote preview: {out_path}")
        return 0

    if args.command == "run-from-manifest":
        summary = _run_from_manifest_payload(
            scenario_path=args.config,
            manifest_path=args.manifest,
            mode=args.mode,
            source=args.source,
            target=args.target,
            max_pairs=args.max_pairs,
            output_dir=args.output_dir,
        )
        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "run-pipeline":
        layers = {
            "land_cover": args.land_cover,
            "water_distance": args.water_distance,
            "slope": args.slope,
            "human_footprint": args.human_footprint,
            "road_mask": args.road_mask,
            "urban_mask": args.urban_mask,
            "ag_mask": args.ag_mask,
        }
        if args.prey:
            layers["prey"] = args.prey
        if args.patches:
            layers["patches"] = args.patches

        prepare_raster_stack(
            reference_raster=args.reference,
            layers=layers,
            output_dir=args.stack_dir,
            resampling=args.resampling,
        )

        manifest_path = str(Path(args.stack_dir) / "stack_manifest.json")
        summary = _run_from_manifest_payload(
            scenario_path=args.config,
            manifest_path=manifest_path,
            mode=args.mode,
            source=args.source,
            target=args.target,
            max_pairs=args.max_pairs,
            output_dir=args.output_dir,
        )

        if args.render_preview:
            if summary.get("mode") == "multipatch":
                raise ValueError("--render-preview is only supported for single mode outputs")
            preview_path = Path(args.preview_png)
            if not preview_path.is_absolute():
                preview_path = Path(args.output_dir) / preview_path
            render_preview_png(
                suitability_path=Path(args.output_dir) / "suitability.npy",
                corridor_mask_path=Path(args.output_dir) / "corridor_mask.npy",
                path_csv=Path(args.output_dir) / "least_cost_path.csv",
                output_png=preview_path,
                title=args.preview_title,
            )

        print(json.dumps(summary, indent=2))
        return 0

    if args.command == "evaluate":
        cumulative = np.load(Path(args.cost_raster))
        result = evaluate_cumulative_cost(cumulative, quantile=args.quantile)
        print(json.dumps(result, indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
