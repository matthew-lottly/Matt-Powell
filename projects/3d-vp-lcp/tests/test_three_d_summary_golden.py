from __future__ import annotations

from pathlib import Path

from vp_lcp.scripts.summarize_3d_runs import summarize_root, write_outputs


def test_three_d_summary_matches_golden_files(tmp_path: Path) -> None:
    tests_root = Path(__file__).parent
    input_root = tests_root / "golden" / "three_d_summary_input"
    expected_root = tests_root / "golden" / "three_d_summary_expected"

    rows = summarize_root(
        input_root,
        min_path_voxels=2,
        min_z_std=0.05,
        min_unique_xy_columns=2,
    )

    out_csv = tmp_path / "three_d_summary.csv"
    out_md = tmp_path / "three_d_summary.md"
    out_json = tmp_path / "three_d_summary.json"
    write_outputs(rows, out_csv, out_md, out_json)

    assert out_csv.read_text(encoding="utf-8") == (expected_root / "three_d_summary.csv").read_text(encoding="utf-8")
    assert out_md.read_text(encoding="utf-8") == (expected_root / "three_d_summary.md").read_text(encoding="utf-8")
    assert out_json.read_text(encoding="utf-8") == (expected_root / "three_d_summary.json").read_text(encoding="utf-8")


def test_three_d_summary_golden_semantics() -> None:
    tests_root = Path(__file__).parent
    input_root = tests_root / "golden" / "three_d_summary_input"
    rows = summarize_root(
        input_root,
        min_path_voxels=2,
        min_z_std=0.05,
        min_unique_xy_columns=2,
    )

    assert len(rows) == 2
    assert rows[0].run_name == "run_degenerate"
    assert rows[1].run_name == "run_informative"
    assert rows[0].informative_3d is False
    assert rows[1].informative_3d is True
    assert rows[0].gate_reason == "path_voxel_count<2;z_std<0.05;unique_xy_columns<2"
    assert rows[1].gate_reason == "ok"
