"""Summarize corridor outputs with explicit 3D structure metrics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import argparse
import csv
import json

import numpy as np


@dataclass(slots=True)
class ThreeDSummaryRow:
    run_name: str
    runtime_seconds: float
    path_voxel_count: int
    graph_nodes: int
    graph_edges: int
    mean_corridor_height: float | None
    z_min: float | None
    z_max: float | None
    z_q25: float | None
    z_q50: float | None
    z_q75: float | None
    z_std: float | None
    unique_xy_columns: int
    x_span: float | None
    y_span: float | None
    hband_0_2m: int
    hband_2_5m: int
    hband_5_10m: int
    hband_10m_plus: int
    informative_3d: bool
    gate_reason: str


def _gate_reason(
    path_voxel_count: int,
    z_std: float | None,
    unique_xy_columns: int,
    min_path_voxels: int,
    min_z_std: float,
    min_unique_xy_columns: int,
) -> str:
    reasons: list[str] = []
    if path_voxel_count < min_path_voxels:
        reasons.append(f"path_voxel_count<{min_path_voxels}")
    if z_std is None or z_std < min_z_std:
        reasons.append(f"z_std<{min_z_std}")
    if unique_xy_columns < min_unique_xy_columns:
        reasons.append(f"unique_xy_columns<{min_unique_xy_columns}")
    return "ok" if not reasons else ";".join(reasons)


def _read_corridor_z(csv_path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            xs.append(float(row["x"]))
            ys.append(float(row["y"]))
            zs.append(float(row["z"]))
    return np.asarray(xs), np.asarray(ys), np.asarray(zs)


def _height_bands(zs: np.ndarray) -> tuple[int, int, int, int]:
    if zs.size == 0:
        return (0, 0, 0, 0)
    b0 = int(np.sum(zs < 2.0))
    b1 = int(np.sum((zs >= 2.0) & (zs < 5.0)))
    b2 = int(np.sum((zs >= 5.0) & (zs < 10.0)))
    b3 = int(np.sum(zs >= 10.0))
    return (b0, b1, b2, b3)


def summarize_run(
    run_dir: Path,
    min_path_voxels: int,
    min_z_std: float,
    min_unique_xy_columns: int,
) -> ThreeDSummaryRow | None:
    report_path = run_dir / "run_report.json"
    corridor_path = run_dir / "corridor.csv"
    if not report_path.exists() or not corridor_path.exists():
        return None

    report = json.loads(report_path.read_text(encoding="utf-8"))
    xs, ys, zs = _read_corridor_z(corridor_path)

    if zs.size == 0:
        z_stats = (None, None, None, None, None, None)
        spans = (None, None)
        unique_xy = 0
        bands = (0, 0, 0, 0)
    else:
        z_stats = (
            float(np.min(zs)),
            float(np.max(zs)),
            float(np.quantile(zs, 0.25)),
            float(np.quantile(zs, 0.50)),
            float(np.quantile(zs, 0.75)),
            float(np.std(zs)),
        )
        spans = (float(np.max(xs) - np.min(xs)), float(np.max(ys) - np.min(ys)))
        unique_xy = int(len({(float(x), float(y)) for x, y in zip(xs, ys, strict=False)}))
        bands = _height_bands(zs)

    reason = _gate_reason(
        path_voxel_count=int(report.get("path_voxel_count", 0)),
        z_std=z_stats[5],
        unique_xy_columns=unique_xy,
        min_path_voxels=min_path_voxels,
        min_z_std=min_z_std,
        min_unique_xy_columns=min_unique_xy_columns,
    )

    return ThreeDSummaryRow(
        run_name=run_dir.name,
        runtime_seconds=float(report.get("runtime_seconds", 0.0)),
        path_voxel_count=int(report.get("path_voxel_count", 0)),
        graph_nodes=int(report.get("graph_nodes", 0)),
        graph_edges=int(report.get("graph_edges", 0)),
        mean_corridor_height=(
            float(report["mean_corridor_height"])
            if report.get("mean_corridor_height") is not None
            else None
        ),
        z_min=z_stats[0],
        z_max=z_stats[1],
        z_q25=z_stats[2],
        z_q50=z_stats[3],
        z_q75=z_stats[4],
        z_std=z_stats[5],
        unique_xy_columns=unique_xy,
        x_span=spans[0],
        y_span=spans[1],
        hband_0_2m=bands[0],
        hband_2_5m=bands[1],
        hband_5_10m=bands[2],
        hband_10m_plus=bands[3],
        informative_3d=(reason == "ok"),
        gate_reason=reason,
    )


def summarize_root(
    root_dir: str | Path,
    min_path_voxels: int,
    min_z_std: float,
    min_unique_xy_columns: int,
) -> list[ThreeDSummaryRow]:
    root = Path(root_dir)
    rows: list[ThreeDSummaryRow] = []
    for child in sorted(p for p in root.iterdir() if p.is_dir()):
        row = summarize_run(
            child,
            min_path_voxels=min_path_voxels,
            min_z_std=min_z_std,
            min_unique_xy_columns=min_unique_xy_columns,
        )
        if row is not None:
            rows.append(row)
    rows.sort(key=lambda r: (r.runtime_seconds, -r.path_voxel_count))
    return rows


def write_outputs(rows: list[ThreeDSummaryRow], output_csv: Path, output_md: Path, output_json: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(rows[0]).keys()) if rows else list(asdict(ThreeDSummaryRow(
        run_name="",
        runtime_seconds=0.0,
        path_voxel_count=0,
        graph_nodes=0,
        graph_edges=0,
        mean_corridor_height=None,
        z_min=None,
        z_max=None,
        z_q25=None,
        z_q50=None,
        z_q75=None,
        z_std=None,
        unique_xy_columns=0,
        x_span=None,
        y_span=None,
        hband_0_2m=0,
        hband_2_5m=0,
        hband_5_10m=0,
        hband_10m_plus=0,
        informative_3d=False,
        gate_reason="",
    )).keys())

    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))

    lines = [
        "# 3D Connectivity Summary",
        "",
        "This table summarizes vertical structure and corridor geometry for each run.",
        "Runs marked as non-informative should not be used for ecological connectivity conclusions.",
        "",
        "| Run | Informative 3D | Runtime (s) | Path Voxels | Mean Z (m) | Z Min | Z Max | Z Std | XY Columns | X Span (m) | Y Span (m) | Gate Reason |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r.run_name} | {'yes' if r.informative_3d else 'no'} | {r.runtime_seconds:.3f} | {r.path_voxel_count} | "
            f"{(f'{r.mean_corridor_height:.3f}' if r.mean_corridor_height is not None else 'NA')} | "
            f"{(f'{r.z_min:.3f}' if r.z_min is not None else 'NA')} | "
            f"{(f'{r.z_max:.3f}' if r.z_max is not None else 'NA')} | "
            f"{(f'{r.z_std:.3f}' if r.z_std is not None else 'NA')} | "
            f"{r.unique_xy_columns} | "
            f"{(f'{r.x_span:.3f}' if r.x_span is not None else 'NA')} | "
            f"{(f'{r.y_span:.3f}' if r.y_span is not None else 'NA')} | {r.gate_reason} |"
        )

    lines.extend([
        "",
        "## Height-Band Counts",
        "",
        "| Run | 0-2m | 2-5m | 5-10m | 10m+ |",
        "|---|---:|---:|---:|---:|",
    ])
    for r in rows:
        lines.append(
            f"| {r.run_name} | {r.hband_0_2m} | {r.hband_2_5m} | {r.hband_5_10m} | {r.hband_10m_plus} |"
        )

    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    informative_runs = [asdict(r) for r in rows if r.informative_3d]
    non_informative_runs = [asdict(r) for r in rows if not r.informative_3d]
    payload = {
        "run_count": len(rows),
        "informative_count": len(informative_runs),
        "non_informative_count": len(non_informative_runs),
        "informative_runs": informative_runs,
        "non_informative_runs": non_informative_runs,
    }
    output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Summarize run outputs with 3D corridor metrics.")
    parser.add_argument("--root", required=True, help="Root directory containing one subdirectory per run.")
    parser.add_argument("--output-csv", default=None, help="Optional output CSV path.")
    parser.add_argument("--output-md", default=None, help="Optional output Markdown path.")
    parser.add_argument("--output-json", default=None, help="Optional output JSON path.")
    parser.add_argument("--min-path-voxels", type=int, default=2, help="Minimum path voxel count for an informative 3D run.")
    parser.add_argument("--min-z-std", type=float, default=0.05, help="Minimum corridor z standard deviation for an informative 3D run.")
    parser.add_argument("--min-unique-xy-columns", type=int, default=2, help="Minimum unique XY footprint columns for an informative 3D run.")
    args = parser.parse_args(argv)

    root = Path(args.root)
    rows = summarize_root(
        root,
        min_path_voxels=args.min_path_voxels,
        min_z_std=args.min_z_std,
        min_unique_xy_columns=args.min_unique_xy_columns,
    )

    output_csv = Path(args.output_csv) if args.output_csv else root / "three_d_summary.csv"
    output_md = Path(args.output_md) if args.output_md else root / "three_d_summary.md"
    output_json = Path(args.output_json) if args.output_json else root / "three_d_summary.json"
    write_outputs(rows, output_csv, output_md, output_json)

    print(f"Wrote {output_csv}")
    print(f"Wrote {output_md}")
    print(f"Wrote {output_json}")
    print(f"Runs summarized: {len(rows)}")
    print(f"Informative runs: {sum(1 for r in rows if r.informative_3d)}")


if __name__ == "__main__":
    main()
