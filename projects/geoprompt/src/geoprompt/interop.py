from __future__ import annotations

import importlib
from typing import Any

from .frame import GeoPromptFrame
from .overlay import geometry_to_shapely


def geopandas_available() -> bool:
    """Return True when GeoPandas is importable in the current environment."""
    try:
        importlib.import_module("geopandas")
    except ImportError:
        return False
    return True


def _load_geopandas() -> Any:
    try:
        return importlib.import_module("geopandas")
    except ImportError as exc:  # pragma: no cover - exercised by error path tests
        raise RuntimeError("Install GeoPandas support with 'pip install -e .[io]' or 'pip install geoprompt[all]'.") from exc


def to_geopandas(frame: GeoPromptFrame) -> Any:
    """Convert a GeoPromptFrame to a GeoPandas GeoDataFrame."""
    geopandas = _load_geopandas()
    rows = frame.to_records()
    geometry_values = [geometry_to_shapely(row[frame.geometry_column]) for row in rows]
    records = []
    for row in rows:
        copied = dict(row)
        copied.pop(frame.geometry_column, None)
        records.append(copied)
    return geopandas.GeoDataFrame(records, geometry=geometry_values, crs=frame.crs)


def from_geopandas(dataframe: Any, geometry_column: str | None = None) -> GeoPromptFrame:
    """Convert a GeoPandas GeoDataFrame into a GeoPromptFrame."""
    geometry_accessor = getattr(dataframe, "geometry", None)
    geometry_name = geometry_column or getattr(geometry_accessor, "name", None)
    if geometry_name is None:
        raise ValueError("geometry column could not be determined")

    rows: list[dict[str, object]] = []
    for _, row in dataframe.iterrows():
        record = dict(row)
        geometry = record[geometry_name]
        if hasattr(geometry, "geom_type"):
            if geometry.geom_type == "Point":
                record[geometry_name] = {"type": "Point", "coordinates": (float(geometry.x), float(geometry.y))}
            elif geometry.geom_type == "LineString":
                record[geometry_name] = {
                    "type": "LineString",
                    "coordinates": tuple((float(x), float(y)) for x, y in geometry.coords),
                }
            elif geometry.geom_type == "Polygon":
                record[geometry_name] = {
                    "type": "Polygon",
                    "coordinates": tuple((float(x), float(y)) for x, y in geometry.exterior.coords),
                }
            else:
                raise TypeError(f"unsupported geometry type: {geometry.geom_type}")
        rows.append(record)
    return GeoPromptFrame.from_records(rows, geometry=geometry_name, crs=getattr(dataframe, "crs", None))


__all__ = [
    "from_geopandas",
    "geopandas_available",
    "to_geopandas",
]
