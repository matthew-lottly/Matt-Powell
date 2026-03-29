from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

from raster_monitoring_pipeline.pipeline import build_change_report, export_change_report, load_grid


def test_load_grid() -> None:
    grid = load_grid(PROJECT_ROOT / "data" / "baseline_grid.json")

    assert grid["rasterName"] == "baseline_heat_index"
    assert len(grid["grid"]) == 4


def test_build_change_report() -> None:
    report = build_change_report(
        baseline_path=PROJECT_ROOT / "data" / "baseline_grid.json",
        latest_path=PROJECT_ROOT / "data" / "latest_grid.json",
    )

    assert report["pipelineName"] == "Raster Monitoring Pipeline"
    assert report["summary"]["cellCount"] == 16
    assert report["summary"]["hotspotCount"] == 3
    assert report["topChanges"][0]["delta"] == 6
    assert report["tileManifest"][0]["tileId"] == "tile-northwest"


def test_export_change_report(tmp_path: Path) -> None:
    output_path = export_change_report(tmp_path, pipeline_name="Heat Watch Pipeline")

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "Heat Watch Pipeline" in content
    assert "raster_change_report.json" in str(output_path)
