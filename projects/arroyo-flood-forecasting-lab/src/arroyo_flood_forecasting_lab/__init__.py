from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from arroyo_flood_forecasting_lab.lab import ArroyoFloodForecastLab, build_site_comparison

__all__ = ["ArroyoFloodForecastLab", "build_flood_report", "export_flood_report", "build_site_comparison"]


def __getattr__(name: str) -> Any:
    if name == "ArroyoFloodForecastLab":
        from arroyo_flood_forecasting_lab.lab import ArroyoFloodForecastLab

        return ArroyoFloodForecastLab
    if name == "build_flood_report":
        from arroyo_flood_forecasting_lab.lab import build_flood_report

        return build_flood_report
    if name == "export_flood_report":
        from arroyo_flood_forecasting_lab.lab import export_flood_report

        return export_flood_report
    if name == "build_site_comparison":
        from arroyo_flood_forecasting_lab.lab import build_site_comparison

        return build_site_comparison
    raise AttributeError(f"module 'arroyo_flood_forecasting_lab' has no attribute {name!r}")