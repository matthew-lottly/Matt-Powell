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
    if not left_geometries or not right_geometries:
        return []

    intersections: list[tuple[int, int, list[Geometry]]] = []
    right_bounds = [geometry_bounds(geometry) for geometry in right_geometries]
    right_shapes = [geometry_to_shapely(geometry) for geometry in right_geometries]
    for left_index, left_geometry in enumerate(left_geometries):
        left_bounds = geometry_bounds(left_geometry)
        left_shape = geometry_to_shapely(left_geometry)
        for right_index_value, right_bound in enumerate(right_bounds):
            if not _bounds_intersect(left_bounds, right_bound):
                continue
            intersection = left_shape.intersection(right_shapes[right_index_value])
            exploded = geometry_from_shapely(intersection)
            if exploded:
                intersections.append((left_index, right_index_value, exploded))
    return intersections


def overlay_union_faces(left_geometries: list[Geometry], right_geometries: list[Geometry]) -> list[tuple[list[int], list[int], Geometry]]:
    if not left_geometries and not right_geometries:
        return []

    _load_shapely()
    shapely_ops = importlib.import_module("shapely.ops")
    left_shapes = [geometry_to_shapely(geometry) for geometry in left_geometries]
    right_shapes = [geometry_to_shapely(geometry) for geometry in right_geometries]
    noded_boundaries = shapely_ops.unary_union([shape.boundary for shape in [*left_shapes, *right_shapes]])

    faces: list[tuple[list[int], list[int], Geometry]] = []
    for face in shapely_ops.polygonize(noded_boundaries):
        if face.is_empty:
            continue
        probe = face.representative_point()
        left_indexes = [index for index, shape in enumerate(left_shapes) if shape.covers(probe)]
        right_indexes = [index for index, shape in enumerate(right_shapes) if shape.covers(probe)]
        if not left_indexes and not right_indexes:
            continue
        exploded = geometry_from_shapely(face)
        if exploded:
            faces.append((left_indexes, right_indexes, exploded[0]))
    return faces


def polygon_split_faces(source_geometry: Geometry, splitter_geometries: list[Geometry]) -> list[tuple[list[int], Geometry]]:
    if geometry_type(source_geometry) != "Polygon":
        raise ValueError("polygon_split_faces requires a Polygon source geometry")
    if not splitter_geometries:
        return [([], source_geometry)]

    _load_shapely()
    shapely_ops = importlib.import_module("shapely.ops")
    source_shape = geometry_to_shapely(source_geometry)
    splitter_shapes: list[Any] = []
    for geometry in splitter_geometries:
        geometry_kind = geometry_type(geometry)
        if geometry_kind == "LineString":
            splitter_shapes.append(geometry_to_shapely(geometry))
            continue
        if geometry_kind == "Polygon":
            splitter_shapes.append(geometry_to_shapely(geometry).boundary)
            continue
        raise ValueError("polygon_split_faces supports only LineString or Polygon splitters")

    noded_boundaries = shapely_ops.unary_union([source_shape.boundary, *splitter_shapes])
    faces: list[tuple[list[int], Geometry]] = []
    for face in shapely_ops.polygonize(noded_boundaries):
        if face.is_empty:
            continue
        probe = face.representative_point()
        if not source_shape.covers(probe):
            continue
        exploded = geometry_from_shapely(face)
        if not exploded:
            continue
        splitter_indexes = [
            index
            for index, splitter_shape in enumerate(splitter_shapes)
            if face.boundary.intersects(splitter_shape)
        ]
        faces.append((splitter_indexes, exploded[0]))

    return faces or [([], source_geometry)]




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
    "overlay_union_faces",
    "polygon_split_faces",
]