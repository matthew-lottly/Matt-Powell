from __future__ import annotations

from pathlib import Path
import json

from vp_lcp.scripts.benchmark_real_tile import (
    BenchmarkRow,
    parse_float_list,
    parse_int_list,
    write_rows,
)


def test_parse_float_list() -> None:
    assert parse_float_list("1.0, 2,3.5") == [1.0, 2.0, 3.5]


def test_parse_int_list() -> None:
    assert parse_int_list("6, 18,26") == [6, 18, 26]


def test_write_rows_outputs_csv_and_json(tmp_path: Path) -> None:
    rows = [
        BenchmarkRow(
            status="ok",
            voxel_size=1.0,
            neighbours=18,
            algorithm="astar",
            normalize_resistance=True,
            runtime_seconds=2.0,
            path_voxel_count=100,
            path_cost=25.0,
            graph_nodes=500,
            graph_edges=1200,
            mean_corridor_height=4.0,
            connectivity_efficiency=4.0,
            runtime_penalized_score=2.0,
            output_dir="outputs/example",
            informative_3d=True,
            gate_reason="ok",
            z_std=0.5,
            unique_xy_columns=20,
            error=None,
        )
    ]

    csv_path = tmp_path / "bench.csv"
    json_path = tmp_path / "bench.json"
    write_rows(rows, csv_path, json_path)

    assert csv_path.exists()
    assert json_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["best_by_runtime_penalized_score"]["algorithm"] == "astar"
