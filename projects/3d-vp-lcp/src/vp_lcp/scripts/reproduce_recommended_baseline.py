"""Reproduce the recommended strict-gate baseline in one command."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import json

from vp_lcp.config import PipelineConfig
from vp_lcp.scripts.benchmark_cross_site import (
    aggregate_cross_site,
    load_site_rows,
    write_cross_site,
)
from vp_lcp.scripts.benchmark_real_tile import run_real_tile_benchmark, write_rows
from vp_lcp.scripts.fetch_public_tile import fetch_public_tile
from vp_lcp.scripts.summarize_3d_runs import summarize_root, write_outputs


@dataclass(slots=True)
class BaselineSite:
    name: str
    manifest: str


def parse_site_specs(specs: list[str] | None) -> list[BaselineSite]:
    if not specs:
        return [
            BaselineSite(
                name="ia",
                manifest="data/public_lidar_tile.ia_eastern_1_2019_ept_node.json",
            ),
            BaselineSite(
                name="ca",
                manifest="data/public_lidar_tile.ca_alamedaco_1_2021_ept_node.json",
            ),
            BaselineSite(
                name="al",
                manifest="data/public_lidar_tile.al_northal_ept_node.json",
            ),
        ]

    parsed: list[BaselineSite] = []
    for spec in specs:
        if "=" not in spec:
            raise ValueError("Each --site value must be name=path/to/manifest.json")
        name, manifest = spec.split("=", 1)
        name = name.strip()
        manifest = manifest.strip()
        if not name or not manifest:
            raise ValueError("Each --site value must include a non-empty name and manifest")
        parsed.append(BaselineSite(name=name, manifest=manifest))
    return parsed


def reproduce_recommended_baseline(
    config_path: str | Path,
    data_dir: str | Path,
    output_root: str | Path,
    sites: list[BaselineSite],
    force_download: bool,
    min_path_voxels_gate: int,
    min_z_std_gate: float,
    min_unique_xy_columns_gate: int,
    allow_non_informative_cross_site: bool,
) -> dict:
    cfg = PipelineConfig.from_json(config_path)
    data_dir = Path(data_dir)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    site_csv_specs: list[tuple[str, Path]] = []
    site_summaries: list[dict] = []

    for site in sites:
        tile_path = fetch_public_tile(site.manifest, data_dir, force=force_download)
        site_root = output_root / site.name

        rows = run_real_tile_benchmark(
            tile_path=tile_path,
            output_root=site_root,
            voxel_sizes=[cfg.input.voxel_size],
            neighbours_list=[cfg.routing.neighbours],
            algorithms=[cfg.routing.algorithm],
            normalize_options=[cfg.resistance.normalize],
            min_height=cfg.input.min_height,
            species_h_min=cfg.species.h_min,
            species_h_max=cfg.species.h_max,
            vegetation_classes=cfg.input.vegetation_classes,
            min_path_voxels_gate=min_path_voxels_gate,
            min_z_std_gate=min_z_std_gate,
            min_unique_xy_columns_gate=min_unique_xy_columns_gate,
            stratum_weights=cfg.species.stratum_weights,
        )

        benchmark_csv = site_root / "benchmark_results.csv"
        benchmark_json = site_root / "benchmark_results.json"
        write_rows(rows, benchmark_csv, benchmark_json)

        summary_rows = summarize_root(
            site_root,
            min_path_voxels=min_path_voxels_gate,
            min_z_std=min_z_std_gate,
            min_unique_xy_columns=min_unique_xy_columns_gate,
        )
        write_outputs(
            summary_rows,
            site_root / "three_d_summary.csv",
            site_root / "three_d_summary.md",
            site_root / "three_d_summary.json",
        )

        ok_count = sum(1 for row in rows if row.status == "ok")
        informative_count = sum(1 for row in rows if row.status == "ok" and row.informative_3d)
        site_summaries.append(
            {
                "site": site.name,
                "manifest": site.manifest,
                "tile": str(tile_path),
                "benchmark_csv": str(benchmark_csv),
                "benchmark_json": str(benchmark_json),
                "three_d_summary_json": str(site_root / "three_d_summary.json"),
                "ok_count": ok_count,
                "informative_count": informative_count,
            }
        )
        site_csv_specs.append((site.name, benchmark_csv))

    cross_site_rows = []
    for site_name, csv_path in site_csv_specs:
        cross_site_rows.extend(
            load_site_rows(
                site_name,
                csv_path,
                require_informative=not allow_non_informative_cross_site,
            )
        )

    aggregated = aggregate_cross_site(cross_site_rows)
    cross_site_root = output_root / "cross-site"
    write_cross_site(
        aggregated,
        cross_site_root / "cross_site_summary.csv",
        cross_site_root / "cross_site_summary.json",
        expected_site_count=len(sites),
    )

    report = {
        "config": str(config_path),
        "data_dir": str(data_dir),
        "output_root": str(output_root),
        "sites": site_summaries,
        "cross_site_summary": str(cross_site_root / "cross_site_summary.json"),
        "gate": {
            "min_path_voxels": min_path_voxels_gate,
            "min_z_std": min_z_std_gate,
            "min_unique_xy_columns": min_unique_xy_columns_gate,
        },
        "allow_non_informative_cross_site": allow_non_informative_cross_site,
    }
    report_path = output_root / "baseline_reproduction_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Fetch preferred baseline sites, run the recommended config, and summarize outputs.",
    )
    parser.add_argument(
        "--config",
        default="configs/robust_default_candidate.json",
        help="Path to the recommended baseline config JSON.",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory used to store fetched LAS/LAZ tiles.",
    )
    parser.add_argument(
        "--output-root",
        default="outputs/recommended-baseline-repro",
        help="Root directory for benchmark and summary artifacts.",
    )
    parser.add_argument(
        "--site",
        action="append",
        default=None,
        help="Optional site spec as name=path/to/manifest.json. Repeat for each site.",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download tiles even if local files already exist.",
    )
    parser.add_argument(
        "--min-path-voxels-gate",
        type=int,
        default=2,
        help="Minimum path voxel count for informative 3D rows.",
    )
    parser.add_argument(
        "--min-z-std-gate",
        type=float,
        default=0.05,
        help="Minimum z standard deviation for informative 3D rows.",
    )
    parser.add_argument(
        "--min-unique-xy-columns-gate",
        type=int,
        default=2,
        help="Minimum unique XY columns for informative 3D rows.",
    )
    parser.add_argument(
        "--allow-non-informative-cross-site",
        action="store_true",
        help="Include non-informative rows in cross-site ranking.",
    )
    args = parser.parse_args(argv)

    sites = parse_site_specs(args.site)
    report = reproduce_recommended_baseline(
        config_path=args.config,
        data_dir=args.data_dir,
        output_root=args.output_root,
        sites=sites,
        force_download=args.force_download,
        min_path_voxels_gate=args.min_path_voxels_gate,
        min_z_std_gate=args.min_z_std_gate,
        min_unique_xy_columns_gate=args.min_unique_xy_columns_gate,
        allow_non_informative_cross_site=args.allow_non_informative_cross_site,
    )

    print("Baseline reproduction complete.")
    print(f"Report: {report['report_path']}")
    print(f"Cross-site summary: {report['cross_site_summary']}")


if __name__ == "__main__":
    main()