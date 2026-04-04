"""Item 47: Plot smoke tests in headless CI."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import matplotlib
matplotlib.use("Agg")

from geoprompt import GeoPromptFrame
from geoprompt.demo import build_demo_report, export_pressure_plot, STYLE_PRESETS
from geoprompt.io import read_features
from geoprompt.types import DemoReport


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_pressure_plot_creates_png(tmp_path: Path) -> None:
    """Verify chart file is created successfully."""
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
    pressure = frame.neighborhood_pressure(weight_column="demand_index", scale=0.14, power=1.6)
    enriched = frame.assign(neighborhood_pressure=pressure)
    chart_path = export_pressure_plot(enriched.to_records(), tmp_path / "test_chart.png")
    assert chart_path.exists()
    assert chart_path.stat().st_size > 1000


def test_pressure_plot_svg_export(tmp_path: Path) -> None:
    """Item 85: Verify SVG export works."""
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
    pressure = frame.neighborhood_pressure(weight_column="demand_index", scale=0.14, power=1.6)
    enriched = frame.assign(neighborhood_pressure=pressure)
    export_pressure_plot(
        enriched.to_records(),
        tmp_path / "test_chart.png",
        export_formats=["png", "svg"],
    )
    assert (tmp_path / "test_chart.svg").exists()


def test_pressure_plot_colorblind_preset(tmp_path: Path) -> None:
    """Item 81: Verify colorblind-safe preset works."""
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
    pressure = frame.neighborhood_pressure(weight_column="demand_index", scale=0.14, power=1.6)
    enriched = frame.assign(neighborhood_pressure=pressure)
    chart_path = export_pressure_plot(
        enriched.to_records(),
        tmp_path / "colorblind.png",
        colormap="colorblind_safe",
    )
    assert chart_path.exists()


def test_pressure_plot_style_presets(tmp_path: Path) -> None:
    """Item 86: Verify all style presets render without error."""
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
    pressure = frame.neighborhood_pressure(weight_column="demand_index", scale=0.14, power=1.6)
    enriched = frame.assign(neighborhood_pressure=pressure)
    for preset_name in STYLE_PRESETS:
        chart_path = export_pressure_plot(
            enriched.to_records(),
            tmp_path / f"chart_{preset_name}.png",
            style_preset=preset_name,
        )
        assert chart_path.exists()


def test_pressure_plot_custom_title(tmp_path: Path) -> None:
    """Item 82: Verify custom title/subtitle."""
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
    pressure = frame.neighborhood_pressure(weight_column="demand_index", scale=0.14, power=1.6)
    enriched = frame.assign(neighborhood_pressure=pressure)
    chart_path = export_pressure_plot(
        enriched.to_records(),
        tmp_path / "titled.png",
        title="Custom Title",
        subtitle="Custom Subtitle",
    )
    assert chart_path.exists()


def test_no_plot_mode(tmp_path: Path) -> None:
    """Item 23: Verify no-plot mode skips chart."""
    report = cast(
        DemoReport,
        build_demo_report(
            input_path=PROJECT_ROOT / "data" / "sample_features.json",
            output_dir=tmp_path,
            no_plot=True,
        ),
    )
    assert report["outputs"]["chart"] == ""
    assert not (tmp_path / "charts").exists()
