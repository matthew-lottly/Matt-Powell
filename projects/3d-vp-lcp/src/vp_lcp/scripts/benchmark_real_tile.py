"""Run repeatable accuracy/performance benchmarks on a real LAS/LAZ tile."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import argparse
import csv
import json

import numpy as np

from vp_lcp.config import PipelineConfig
from vp_lcp.pipeline import PipelineResult, run_pipeline


@dataclass(slots=True)
class BenchmarkRow:
    status: str
    voxel_size: float
    neighbours: int
    algorithm: str
    normalize_resistance: bool
    runtime_seconds: float
    path_voxel_count: int
    path_cost: float
    graph_nodes: int
    graph_edges: int
    mean_corridor_height: float | None
    connectivity_efficiency: float
    runtime_penalized_score: float
    output_dir: str
    informative_3d: bool
    gate_reason: str
    z_std: float | None
    unique_xy_columns: int
    error: str | None = None


def _corridor_3d_metrics(output_dir: str | Path) -> tuple[float | None, int]:
    corridor_path = Path(output_dir) / "corridor.csv"
    if not corridor_path.exists():
        return (None, 0)
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    with corridor_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            xs.append(float(row["x"]))
            ys.append(float(row["y"]))
            zs.append(float(row["z"]))
    if not zs:
        return (None, 0)
    z_std = float(np.std(np.asarray(zs, dtype=np.float64)))
    unique_xy = len({(x, y) for x, y in zip(xs, ys, strict=False)})
    return (z_std, unique_xy)


def _gate_reason(
    path_voxel_count: int,
    z_std: float | None,
    unique_xy_columns: int,
    min_path_voxels_gate: int,
    min_z_std_gate: float,
    min_unique_xy_columns_gate: int,
) -> str:
    reasons: list[str] = []
    if path_voxel_count < min_path_voxels_gate:
        reasons.append(f"path_voxel_count<{min_path_voxels_gate}")
    if z_std is None or z_std < min_z_std_gate:
        reasons.append(f"z_std<{min_z_std_gate}")
    if unique_xy_columns < min_unique_xy_columns_gate:
        reasons.append(f"unique_xy_columns<{min_unique_xy_columns_gate}")
    return "ok" if not reasons else ";".join(reasons)


def parse_float_list(raw: str) -> list[float]:
    return [float(x.strip()) for x in raw.split(",") if x.strip()]


def parse_int_list(raw: str) -> list[int]:
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def build_row(
    result: PipelineResult,
    *,
    voxel_size: float,
    neighbours: int,
    algorithm: str,
    normalize_resistance: bool,
    min_path_voxels_gate: int,
    min_z_std_gate: float,
    min_unique_xy_columns_gate: int,
) -> BenchmarkRow:
    efficiency = float(result.path_voxel_count) / max(result.path_cost, 1e-9)
    runtime_penalized = efficiency / max(result.runtime_seconds, 1e-9)
    z_std, unique_xy_columns = _corridor_3d_metrics(result.output_dir)
    gate_reason = _gate_reason(
        path_voxel_count=result.path_voxel_count,
        z_std=z_std,
        unique_xy_columns=unique_xy_columns,
        min_path_voxels_gate=min_path_voxels_gate,
        min_z_std_gate=min_z_std_gate,
        min_unique_xy_columns_gate=min_unique_xy_columns_gate,
    )
    return BenchmarkRow(
        status="ok",
        voxel_size=voxel_size,
        neighbours=neighbours,
        algorithm=algorithm,
        normalize_resistance=normalize_resistance,
        runtime_seconds=result.runtime_seconds,
        path_voxel_count=result.path_voxel_count,
        path_cost=result.path_cost,
        graph_nodes=result.graph_nodes,
        graph_edges=result.graph_edges,
        mean_corridor_height=result.mean_corridor_height,
        connectivity_efficiency=efficiency,
        runtime_penalized_score=runtime_penalized,
        output_dir=result.output_dir,
        informative_3d=(gate_reason == "ok"),
        gate_reason=gate_reason,
        z_std=z_std,
        unique_xy_columns=unique_xy_columns,
    )


def write_rows(rows: list[BenchmarkRow], output_csv: str | Path, output_json: str | Path) -> None:
    output_csv = Path(output_csv)
    output_json = Path(output_json)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = list(asdict(rows[0]).keys()) if rows else [
        "status",
        "voxel_size",
        "neighbours",
        "algorithm",
        "normalize_resistance",
        "runtime_seconds",
        "path_voxel_count",
        "path_cost",
        "graph_nodes",
        "graph_edges",
        "mean_corridor_height",
        "connectivity_efficiency",
        "runtime_penalized_score",
        "output_dir",
        "informative_3d",
        "gate_reason",
        "z_std",
        "unique_xy_columns",
        "error",
    ]

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))

    ok_rows = [r for r in rows if r.status == "ok"]
    informative_rows = [r for r in ok_rows if r.informative_3d]
    payload = {
        "rows": [asdict(r) for r in rows],
        "best_by_runtime_penalized_score": (
            asdict(max(informative_rows, key=lambda r: r.runtime_penalized_score))
            if informative_rows
            else (asdict(max(ok_rows, key=lambda r: r.runtime_penalized_score)) if ok_rows else None)
        ),
        "summary": {
            "run_count": len(rows),
            "ok_count": len(ok_rows),
            "error_count": len(rows) - len(ok_rows),
            "informative_count": len(informative_rows),
        },
    }
    output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_real_tile_benchmark(
    tile_path: str | Path,
    output_root: str | Path,
    voxel_sizes: list[float],
    neighbours_list: list[int],
    algorithms: list[str],
    normalize_options: list[bool],
    min_height: float,
    species_h_min: float,
    species_h_max: float,
    vegetation_classes: tuple[int, ...],
    min_path_voxels_gate: int,
    min_z_std_gate: float,
    min_unique_xy_columns_gate: int,
    stratum_weights: dict[str, float] | None,
) -> list[BenchmarkRow]:
    tile_path = str(tile_path)
    output_root = Path(output_root)
    rows: list[BenchmarkRow] = []

    for voxel_size in voxel_sizes:
        for neighbours in neighbours_list:
            for algorithm in algorithms:
                for normalize in normalize_options:
                    cfg = PipelineConfig()
                    cfg.input.voxel_size = voxel_size
                    cfg.input.min_height = min_height
                    cfg.input.vegetation_classes = vegetation_classes
                    cfg.species.h_min = species_h_min
                    cfg.species.h_max = species_h_max
                    cfg.species.stratum_weights = stratum_weights
                    cfg.routing.neighbours = neighbours
                    cfg.routing.algorithm = algorithm
                    cfg.resistance.normalize = normalize
                    tag = f"vs{voxel_size:g}-n{neighbours}-{algorithm}-norm{int(normalize)}"
                    cfg.output.output_dir = str(output_root / tag)
                    cfg.output.export_surface = False
                    cfg.output.export_occupancy = True
                    cfg.output.export_vgf = True
                    cfg.output.export_cost_volume = True

                    try:
                        res = run_pipeline(tile_path, cfg)
                        rows.append(
                            build_row(
                                res,
                                voxel_size=voxel_size,
                                neighbours=neighbours,
                                algorithm=algorithm,
                                normalize_resistance=normalize,
                                min_path_voxels_gate=min_path_voxels_gate,
                                min_z_std_gate=min_z_std_gate,
                                min_unique_xy_columns_gate=min_unique_xy_columns_gate,
                            )
                        )
                    except Exception as exc:
                        rows.append(
                            BenchmarkRow(
                                status="error",
                                voxel_size=voxel_size,
                                neighbours=neighbours,
                                algorithm=algorithm,
                                normalize_resistance=normalize,
                                runtime_seconds=0.0,
                                path_voxel_count=0,
                                path_cost=0.0,
                                graph_nodes=0,
                                graph_edges=0,
                                mean_corridor_height=None,
                                connectivity_efficiency=0.0,
                                runtime_penalized_score=0.0,
                                output_dir=str(output_root / tag),
                                informative_3d=False,
                                gate_reason="pipeline_error",
                                z_std=None,
                                unique_xy_columns=0,
                                error=str(exc),
                            )
                        )

    rows.sort(key=lambda r: r.runtime_penalized_score, reverse=True)
    return rows


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark 3D-VP-LCP on a real LAS/LAZ tile for quality/performance tradeoffs.",
    )
    parser.add_argument("--tile", required=True, help="Path to a LAS/LAZ tile to benchmark.")
    parser.add_argument(
        "--output-root",
        default="outputs/real-data-benchmark",
        help="Directory where run outputs and benchmark tables are written.",
    )
    parser.add_argument("--voxel-sizes", default="1.0,2.0", help="Comma-separated voxel sizes.")
    parser.add_argument("--neighbours", default="6,18,26", help="Comma-separated neighbour counts.")
    parser.add_argument(
        "--algorithms",
        default="dijkstra,astar",
        help="Comma-separated routing algorithms.",
    )
    parser.add_argument(
        "--normalize-options",
        default="false,true",
        help="Comma-separated resistance normalization flags (false,true).",
    )
    parser.add_argument(
        "--min-height",
        type=float,
        default=0.0,
        help="Minimum normalized height threshold for retained points.",
    )
    parser.add_argument(
        "--species-h-min",
        type=float,
        default=0.0,
        help="Species minimum corridor height in meters.",
    )
    parser.add_argument(
        "--species-h-max",
        type=float,
        default=60.0,
        help="Species maximum corridor height in meters.",
    )
    parser.add_argument(
        "--vegetation-classes",
        default="2,3,4,5",
        help="Comma-separated LAS classes treated as vegetation for resistance occupancy.",
    )
    parser.add_argument("--min-path-voxels-gate", type=int, default=2, help="Minimum path voxel count for informative 3D benchmark rows.")
    parser.add_argument("--min-z-std-gate", type=float, default=0.05, help="Minimum corridor z standard deviation for informative 3D benchmark rows.")
    parser.add_argument("--min-unique-xy-columns-gate", type=int, default=2, help="Minimum unique XY columns for informative 3D benchmark rows.")
    parser.add_argument("--w-0-2m", type=float, default=None, help="Optional stratum weight for 0-2m band.")
    parser.add_argument("--w-2-5m", type=float, default=None, help="Optional stratum weight for 2-5m band.")
    parser.add_argument("--w-5-10m", type=float, default=None, help="Optional stratum weight for 5-10m band.")
    parser.add_argument("--w-10m-plus", type=float, default=None, help="Optional stratum weight for 10m+ band.")
    args = parser.parse_args(argv)

    normalize_options = [x.strip().lower() in {"1", "true", "yes", "y"} for x in args.normalize_options.split(",")]

    stratum_weights: dict[str, float] | None = None
    if any(v is not None for v in [args.w_0_2m, args.w_2_5m, args.w_5_10m, args.w_10m_plus]):
        stratum_weights = {
            "0-2m": 1.0 if args.w_0_2m is None else float(args.w_0_2m),
            "2-5m": 1.0 if args.w_2_5m is None else float(args.w_2_5m),
            "5-10m": 1.0 if args.w_5_10m is None else float(args.w_5_10m),
            "10m+": 1.0 if args.w_10m_plus is None else float(args.w_10m_plus),
        }

    rows = run_real_tile_benchmark(
        tile_path=args.tile,
        output_root=args.output_root,
        voxel_sizes=parse_float_list(args.voxel_sizes),
        neighbours_list=parse_int_list(args.neighbours),
        algorithms=[x.strip() for x in args.algorithms.split(",") if x.strip()],
        normalize_options=normalize_options,
        min_height=args.min_height,
        species_h_min=args.species_h_min,
        species_h_max=args.species_h_max,
        vegetation_classes=tuple(parse_int_list(args.vegetation_classes)),
        min_path_voxels_gate=args.min_path_voxels_gate,
        min_z_std_gate=args.min_z_std_gate,
        min_unique_xy_columns_gate=args.min_unique_xy_columns_gate,
        stratum_weights=stratum_weights,
    )

    out_root = Path(args.output_root)
    write_rows(rows, out_root / "benchmark_results.csv", out_root / "benchmark_results.json")

    ok_rows = [r for r in rows if r.status == "ok"]
    informative_rows = [r for r in ok_rows if r.informative_3d]
    if informative_rows:
        best = informative_rows[0]
        print(
            f"Best run: voxel={best.voxel_size:g}, neighbours={best.neighbours}, "
            f"algorithm={best.algorithm}, normalize={best.normalize_resistance}, "
            f"score={best.runtime_penalized_score:.6f}, runtime={best.runtime_seconds:.3f}s"
        )
        print(f"Successful runs: {len(ok_rows)}/{len(rows)}")
        print(f"Informative runs: {len(informative_rows)}/{len(ok_rows)}")
    elif ok_rows:
        best = ok_rows[0]
        print(
            f"Best non-informative run: voxel={best.voxel_size:g}, neighbours={best.neighbours}, "
            f"algorithm={best.algorithm}, normalize={best.normalize_resistance}, "
            f"score={best.runtime_penalized_score:.6f}, runtime={best.runtime_seconds:.3f}s"
        )
        print(f"Successful runs: {len(ok_rows)}/{len(rows)}")
        print("Informative runs: 0")
    else:
        print("No successful runs. Check benchmark_results.json for error details.")


if __name__ == "__main__":
    main()
