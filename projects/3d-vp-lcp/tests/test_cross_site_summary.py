from __future__ import annotations

import importlib

cross_site = importlib.import_module("vp_lcp.scripts.benchmark_cross_site")


def test_aggregate_cross_site_prefers_lower_mean_rank() -> None:
    rows = [
        cross_site.SiteRow("a", 1.0, 18, "dijkstra", False, 1.0, 100.0, True),
        cross_site.SiteRow("a", 2.0, 26, "dijkstra", False, 1.0, 50.0, True),
        cross_site.SiteRow("b", 1.0, 18, "dijkstra", False, 1.0, 80.0, True),
        cross_site.SiteRow("b", 2.0, 26, "dijkstra", False, 1.0, 40.0, True),
    ]

    out = cross_site.aggregate_cross_site(rows)
    assert out
    top = out[0]
    assert top.voxel_size == 1.0
    assert top.neighbours == 18
    assert top.mean_site_rank == 1.0


def test_load_site_rows_filters_non_informative(tmp_path) -> None:
    csv_path = tmp_path / "rows.csv"
    csv_path.write_text(
        "status,voxel_size,neighbours,algorithm,normalize_resistance,runtime_seconds,runtime_penalized_score,informative_3d\n"
        "ok,1.0,26,dijkstra,true,1.0,10.0,true\n"
        "ok,2.0,26,dijkstra,true,1.0,20.0,false\n",
        encoding="utf-8",
    )
    rows = cross_site.load_site_rows("x", csv_path, require_informative=True)
    assert len(rows) == 1
    assert rows[0].voxel_size == 1.0
