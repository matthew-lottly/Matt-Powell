from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Any

from .geometry import Geometry, geometry_bounds, geometry_type


def _bounds_intersect(left: tuple[float, float, float, float], right: tuple[float, float, float, float]) -> bool:
    return not (
        left[2] < right[0]
        or left[0] > right[2]
        or left[3] < right[1]
        or left[1] > right[3]
    )


@lru_cache(maxsize=1)
def _load_shapely() -> tuple[Any, Any, Any, Any]:
    try:
        shapely_geometry = importlib.import_module("shapely.geometry")
        shapely_ops = importlib.import_module("shapely.ops")
        shapely_prepared = importlib.import_module("shapely.prepared")
    except ImportError as exc:
        raise RuntimeError("Install overlay support with 'pip install -e .[overlay]' before using clip or overlay operations.") from exc

    return shapely_geometry, shapely_geometry.shape, shapely_ops.unary_union, shapely_prepared.prep


def geometry_to_geojson(geometry: Geometry) -> dict[str, Any]:
    geometry_kind = geometry_type(geometry)
    coordinates = geometry["coordinates"]
    if geometry_kind == "Point":
        return {"type": "Point", "coordinates": list(coordinates)}
    if geometry_kind == "LineString":
        return {"type": "LineString", "coordinates": [list(coord) for coord in coordinates]}
    if geometry_kind == "Polygon":
        return {"type": "Polygon", "coordinates": [[list(coord) for coord in coordinates]]}
    raise TypeError(f"unsupported geometry type: {geometry_kind}")


def geometry_to_shapely(geometry: Geometry) -> Any:
    shapely_geometry, _, _, _ = _load_shapely()
    geometry_kind = geometry_type(geometry)
    coordinates = geometry["coordinates"]
    if geometry_kind == "Point":
        return shapely_geometry.Point(coordinates)
    if geometry_kind == "LineString":
        return shapely_geometry.LineString(coordinates)
    if geometry_kind == "Polygon":
        return shapely_geometry.Polygon(coordinates)
    raise TypeError(f"unsupported geometry type: {geometry_kind}")


def geometry_from_shapely(value: Any) -> list[Geometry]:
    if value.is_empty:
        return []

    geometry_kind = value.geom_type
    if geometry_kind == "Point":
        return [{"type": "Point", "coordinates": (float(value.x), float(value.y))}]
    if geometry_kind == "LineString":
        return [{"type": "LineString", "coordinates": tuple((float(x_value), float(y_value)) for x_value, y_value in value.coords)}]
    if geometry_kind == "Polygon":
        return [
            {
                "type": "Polygon",
                "coordinates": tuple((float(x_value), float(y_value)) for x_value, y_value in value.exterior.coords),
            }
        ]
    if geometry_kind.startswith("Multi") or geometry_kind == "GeometryCollection":
        geometries: list[Geometry] = []
        for child in value.geoms:
            geometries.extend(geometry_from_shapely(child))
        return geometries
    raise TypeError(f"unsupported Shapely geometry type: {geometry_kind}")


def clip_geometries(geometries: list[Geometry], mask_geometries: list[Geometry]) -> list[list[Geometry]]:
    if not mask_geometries:
        return [[] for _ in geometries]

    _, _, unary_union, prep = _load_shapely()
    mask_shape = unary_union([geometry_to_shapely(geometry) for geometry in mask_geometries])
    prepared_mask = prep(mask_shape)
    mask_bounds = tuple(float(value) for value in mask_shape.bounds)
    clipped: list[list[Geometry]] = []
    for geometry in geometries:
        if not _bounds_intersect(geometry_bounds(geometry), mask_bounds):
            clipped.append([])
            continue
        source_shape = geometry_to_shapely(geometry)
        if mask_shape.covers(source_shape):
            clipped.append([geometry])
            continue
        if not prepared_mask.intersects(source_shape):
            clipped.append([])
            continue
        result = source_shape.intersection(mask_shape)
        clipped.append(geometry_from_shapely(result))
    return clipped


def buffer_geometries(geometries: list[Geometry], distance: float, resolution: int = 16) -> list[list[Geometry]]:
    if distance < 0:
        raise ValueError("distance must be zero or greater")
    if resolution <= 0:
        raise ValueError("resolution must be greater than zero")

    buffered: list[list[Geometry]] = []
    for geometry in geometries:
        result = geometry_to_shapely(geometry).buffer(distance, quad_segs=resolution)
        buffered.append(geometry_from_shapely(result))
    return buffered


def overlay_intersections(left_geometries: list[Geometry], right_geometries: list[Geometry]) -> list[tuple[int, int, list[Geometry]]]:
    # Pre-compute right bounds once; used to skip clearly non-intersecting pairs
    # before the more expensive Shapely intersection call.
    right_bounds = [geometry_bounds(g) for g in right_geometries]

    # Attempt to build an rtree spatial index for O(n log n) candidate lookup.
    # Falls back silently to bounds-only pre-filter if rtree is not installed.
    _rtree_index: Any | None = None
    try:
        _rtree_mod = importlib.import_module("rtree.index")
        _rtree_index = _rtree_mod.Index()
        for right_index, rb in enumerate(right_bounds):
            _rtree_index.insert(right_index, rb)
    except Exception:
        _rtree_index = None

    intersections: list[tuple[int, int, list[Geometry]]] = []
    for left_index, left_geometry in enumerate(left_geometries):
        left_bounds = geometry_bounds(left_geometry)
        left_shape = geometry_to_shapely(left_geometry)

        if _rtree_index is not None:
            candidates = list(_rtree_index.intersection(left_bounds))
        else:
            candidates = [
                ri for ri, rb in enumerate(right_bounds)
                if _bounds_intersect(left_bounds, rb)
            ]

        for right_index in candidates:
            intersection = left_shape.intersection(geometry_to_shapely(right_geometries[right_index]))
            exploded = geometry_from_shapely(intersection)
            if exploded:
                intersections.append((left_index, right_index, exploded))
    return intersections


def dissolve_geometries(geometries: list[Geometry]) -> list[Geometry]:
    if not geometries:
        return []
    _, _, unary_union, _ = _load_shapely()
    dissolved = unary_union([geometry_to_shapely(geometry) for geometry in geometries])
    return geometry_from_shapely(dissolved)


__all__ = [
    "buffer_geometries",
    "clip_geometries",
    "dissolve_geometries",
    "geometry_from_shapely",
    "geometry_to_geojson",
    "geometry_to_shapely",
    "overlay_intersections",
]