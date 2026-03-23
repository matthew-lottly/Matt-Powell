from __future__ import annotations

from typing import Any, Callable

from .equations import DistanceMethod, coordinate_distance


Coordinate = tuple[float, float]
Geometry = dict[str, object]


def _normalize_coordinate(value: Any) -> Coordinate:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise TypeError("coordinate must contain exactly two numeric values")
    return (float(value[0]), float(value[1]))


def _normalize_ring(values: Any) -> tuple[Coordinate, ...]:
    if not isinstance(values, (list, tuple)) or len(values) < 3:
        raise TypeError("polygon ring must contain at least three coordinates")
    ring = tuple(_normalize_coordinate(value) for value in values)
    if ring[0] != ring[-1]:
        ring = (*ring, ring[0])
    return ring


def normalize_geometry(value: Any) -> Geometry:
    if isinstance(value, dict):
        geometry_type = value.get("type")
        coordinates = value.get("coordinates")
        if geometry_type == "Point":
            return {"type": "Point", "coordinates": _normalize_coordinate(coordinates)}
        if geometry_type == "LineString":
            if not isinstance(coordinates, (list, tuple)) or len(coordinates) < 2:
                raise TypeError("line geometry must contain at least two coordinates")
            return {
                "type": "LineString",
                "coordinates": tuple(_normalize_coordinate(coord) for coord in coordinates),
            }
        if geometry_type == "Polygon":
            if not isinstance(coordinates, (list, tuple)) or not coordinates:
                raise TypeError("polygon geometry must contain at least one ring")
            first_value = coordinates[0]
            if isinstance(first_value, (list, tuple)) and len(first_value) == 2 and all(isinstance(item, (int, float)) for item in first_value):
                ring = _normalize_ring(coordinates)
            else:
                ring = _normalize_ring(first_value)
            return {"type": "Polygon", "coordinates": ring}
        raise TypeError("unsupported geometry type")

    if isinstance(value, (list, tuple)) and len(value) == 2 and all(isinstance(item, (int, float)) for item in value):
        return {"type": "Point", "coordinates": _normalize_coordinate(value)}

    raise TypeError("geometry must be a point tuple or a GeoJSON-like geometry mapping")


def geometry_type(geometry: Geometry) -> str:
    return str(geometry["type"])


def geometry_vertices(geometry: Geometry) -> tuple[Coordinate, ...]:
    geometry_kind = geometry_type(geometry)
    coordinates = geometry["coordinates"]
    if geometry_kind == "Point":
        return (coordinates,)  # type: ignore[return-value]
    return tuple(coordinates)  # type: ignore[return-value]


def transform_geometry(geometry: Geometry, transform: Callable[[Coordinate], Coordinate]) -> Geometry:
    geometry_kind = geometry_type(geometry)
    if geometry_kind == "Point":
        return {"type": "Point", "coordinates": transform(geometry_vertices(geometry)[0])}
    if geometry_kind == "LineString":
        return {"type": "LineString", "coordinates": tuple(transform(vertex) for vertex in geometry_vertices(geometry))}
    if geometry_kind == "Polygon":
        return {"type": "Polygon", "coordinates": tuple(transform(vertex) for vertex in geometry_vertices(geometry))}
    raise TypeError("unsupported geometry type")


def geometry_bounds(geometry: Geometry) -> tuple[float, float, float, float]:
    vertices = geometry_vertices(geometry)
    xs = [coord[0] for coord in vertices]
    ys = [coord[1] for coord in vertices]
    return (min(xs), min(ys), max(xs), max(ys))


def geometry_intersects_bounds(
    geometry: Geometry,
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
) -> bool:
    geometry_min_x, geometry_min_y, geometry_max_x, geometry_max_y = geometry_bounds(geometry)
    return not (
        geometry_max_x < min_x
        or geometry_min_x > max_x
        or geometry_max_y < min_y
        or geometry_min_y > max_y
    )


def geometry_within_bounds(
    geometry: Geometry,
    min_x: float,
    min_y: float,
    max_x: float,
    max_y: float,
) -> bool:
    geometry_min_x, geometry_min_y, geometry_max_x, geometry_max_y = geometry_bounds(geometry)
    return (
        geometry_min_x >= min_x
        and geometry_max_x <= max_x
        and geometry_min_y >= min_y
        and geometry_max_y <= max_y
    )


def _segments(vertices: tuple[Coordinate, ...]) -> tuple[tuple[Coordinate, Coordinate], ...]:
    return tuple((vertices[index - 1], vertices[index]) for index in range(1, len(vertices)))


def _bounds_intersect(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> bool:
    return not (
        left[2] < right[0]
        or left[0] > right[2]
        or left[3] < right[1]
        or left[1] > right[3]
    )


def _point_in_bounds(point: Coordinate, bounds: tuple[float, float, float, float], tolerance: float = 1e-9) -> bool:
    min_x, min_y, max_x, max_y = bounds
    return min_x - tolerance <= point[0] <= max_x + tolerance and min_y - tolerance <= point[1] <= max_y + tolerance


def _rectangle_bounds(polygon: Geometry) -> tuple[float, float, float, float] | None:
    if geometry_type(polygon) != "Polygon":
        return None

    ring = geometry_vertices(polygon)
    if len(ring) != 5:
        return None

    min_x, min_y, max_x, max_y = geometry_bounds(polygon)
    expected_corners = {
        (min_x, min_y),
        (min_x, max_y),
        (max_x, min_y),
        (max_x, max_y),
    }
    actual_corners = set(ring[:-1])
    if len(actual_corners) != 4 or actual_corners != expected_corners:
        return None
    return (min_x, min_y, max_x, max_y)


def _cross_product(origin: Coordinate, middle: Coordinate, destination: Coordinate) -> float:
    return (middle[0] - origin[0]) * (destination[1] - origin[1]) - (middle[1] - origin[1]) * (destination[0] - origin[0])


def _point_on_segment(point: Coordinate, start: Coordinate, end: Coordinate, tolerance: float = 1e-9) -> bool:
    cross = _cross_product(start, point, end)
    if abs(cross) > tolerance:
        return False
    min_x, max_x = sorted((start[0], end[0]))
    min_y, max_y = sorted((start[1], end[1]))
    return min_x - tolerance <= point[0] <= max_x + tolerance and min_y - tolerance <= point[1] <= max_y + tolerance


def _segments_intersect(
    first_start: Coordinate,
    first_end: Coordinate,
    second_start: Coordinate,
    second_end: Coordinate,
    tolerance: float = 1e-9,
) -> bool:
    orientation_one = _cross_product(first_start, first_end, second_start)
    orientation_two = _cross_product(first_start, first_end, second_end)
    orientation_three = _cross_product(second_start, second_end, first_start)
    orientation_four = _cross_product(second_start, second_end, first_end)

    if ((orientation_one > tolerance and orientation_two < -tolerance) or (orientation_one < -tolerance and orientation_two > tolerance)) and (
        (orientation_three > tolerance and orientation_four < -tolerance)
        or (orientation_three < -tolerance and orientation_four > tolerance)
    ):
        return True

    return (
        _point_on_segment(second_start, first_start, first_end, tolerance=tolerance)
        or _point_on_segment(second_end, first_start, first_end, tolerance=tolerance)
        or _point_on_segment(first_start, second_start, second_end, tolerance=tolerance)
        or _point_on_segment(first_end, second_start, second_end, tolerance=tolerance)
    )


def _segment_intersects_rectangle(
    start: Coordinate,
    end: Coordinate,
    bounds: tuple[float, float, float, float],
) -> bool:
    if _point_in_bounds(start, bounds) or _point_in_bounds(end, bounds):
        return True

    segment_bounds = (
        min(start[0], end[0]),
        min(start[1], end[1]),
        max(start[0], end[0]),
        max(start[1], end[1]),
    )
    if not _bounds_intersect(segment_bounds, bounds):
        return False

    min_x, min_y, max_x, max_y = bounds
    rectangle_edges = (
        ((min_x, min_y), (max_x, min_y)),
        ((max_x, min_y), (max_x, max_y)),
        ((max_x, max_y), (min_x, max_y)),
        ((min_x, max_y), (min_x, min_y)),
    )
    return any(_segments_intersect(start, end, edge_start, edge_end) for edge_start, edge_end in rectangle_edges)


def _line_intersects_rectangle(vertices: tuple[Coordinate, ...], bounds: tuple[float, float, float, float]) -> bool:
    return any(_segment_intersects_rectangle(start, end, bounds) for start, end in _segments(vertices))


def _polygon_intersects_rectangle(polygon: Geometry, bounds: tuple[float, float, float, float]) -> bool:
    ring = geometry_vertices(polygon)
    if any(_point_in_bounds(vertex, bounds) for vertex in ring[:-1]):
        return True

    min_x, min_y, max_x, max_y = bounds
    rectangle_corners = (
        (min_x, min_y),
        (max_x, min_y),
        (max_x, max_y),
        (min_x, max_y),
    )
    if any(_point_in_polygon(corner, polygon) for corner in rectangle_corners):
        return True

    return _line_intersects_rectangle(ring, bounds)


def _point_in_polygon(point: Coordinate, polygon: Geometry) -> bool:
    ring = geometry_vertices(polygon)
    for start, end in _segments(ring):
        if _point_on_segment(point, start, end):
            return True

    inside = False
    for index in range(len(ring) - 1):
        start_x, start_y = ring[index]
        end_x, end_y = ring[index + 1]
        intersects = (start_y > point[1]) != (end_y > point[1])
        if not intersects:
            continue
        edge_x = ((end_x - start_x) * (point[1] - start_y) / (end_y - start_y)) + start_x
        if point[0] <= edge_x:
            inside = not inside
    return inside


def geometry_intersects(origin: Geometry, destination: Geometry) -> bool:
    origin_type = geometry_type(origin)
    destination_type = geometry_type(destination)

    if not _bounds_intersect(geometry_bounds(origin), geometry_bounds(destination)):
        return False

    if origin_type == "Point" and destination_type == "Point":
        return geometry_vertices(origin)[0] == geometry_vertices(destination)[0]
    if origin_type == "Point" and destination_type == "LineString":
        point = geometry_vertices(origin)[0]
        return any(_point_on_segment(point, start, end) for start, end in _segments(geometry_vertices(destination)))
    if origin_type == "LineString" and destination_type == "Point":
        return geometry_intersects(destination, origin)
    if origin_type == "Point" and destination_type == "Polygon":
        destination_rectangle = _rectangle_bounds(destination)
        if destination_rectangle is not None:
            return _point_in_bounds(geometry_vertices(origin)[0], destination_rectangle)
        return _point_in_polygon(geometry_vertices(origin)[0], destination)
    if origin_type == "Polygon" and destination_type == "Point":
        return geometry_intersects(destination, origin)
    if origin_type == "LineString" and destination_type == "LineString":
        return any(
            _segments_intersect(first_start, first_end, second_start, second_end)
            for first_start, first_end in _segments(geometry_vertices(origin))
            for second_start, second_end in _segments(geometry_vertices(destination))
        )
    if origin_type == "LineString" and destination_type == "Polygon":
        destination_rectangle = _rectangle_bounds(destination)
        if destination_rectangle is not None:
            return _line_intersects_rectangle(geometry_vertices(origin), destination_rectangle)
        destination_ring = geometry_vertices(destination)
        return any(
            _segments_intersect(first_start, first_end, second_start, second_end)
            for first_start, first_end in _segments(geometry_vertices(origin))
            for second_start, second_end in _segments(destination_ring)
        ) or any(_point_in_polygon(vertex, destination) for vertex in geometry_vertices(origin))
    if origin_type == "Polygon" and destination_type == "LineString":
        return geometry_intersects(destination, origin)
    if origin_type == "Polygon" and destination_type == "Polygon":
        origin_rectangle = _rectangle_bounds(origin)
        destination_rectangle = _rectangle_bounds(destination)
        if origin_rectangle is not None and destination_rectangle is not None:
            return True
        if destination_rectangle is not None:
            return _polygon_intersects_rectangle(origin, destination_rectangle)
        if origin_rectangle is not None:
            return _polygon_intersects_rectangle(destination, origin_rectangle)
        origin_ring = geometry_vertices(origin)
        destination_ring = geometry_vertices(destination)
        return any(
            _segments_intersect(first_start, first_end, second_start, second_end)
            for first_start, first_end in _segments(origin_ring)
            for second_start, second_end in _segments(destination_ring)
        ) or _point_in_polygon(origin_ring[0], destination) or _point_in_polygon(destination_ring[0], origin)

    raise TypeError("unsupported geometry type")


def geometry_within(candidate: Geometry, container: Geometry) -> bool:
    candidate_type = geometry_type(candidate)
    container_type = geometry_type(container)

    if not _bounds_intersect(geometry_bounds(candidate), geometry_bounds(container)):
        return False

    if container_type == "Polygon":
        container_rectangle = _rectangle_bounds(container)
        if container_rectangle is not None:
            candidate_vertices = geometry_vertices(candidate)
            if candidate_type == "Polygon":
                candidate_vertices = candidate_vertices[:-1]
            return all(_point_in_bounds(vertex, container_rectangle) for vertex in candidate_vertices)
        return all(_point_in_polygon(vertex, container) for vertex in geometry_vertices(candidate))
    if candidate_type == "Point" and container_type == "LineString":
        point = geometry_vertices(candidate)[0]
        return any(_point_on_segment(point, start, end) for start, end in _segments(geometry_vertices(container)))
    if candidate_type == "Point" and container_type == "Point":
        return geometry_vertices(candidate)[0] == geometry_vertices(container)[0]
    if candidate_type == "LineString" and container_type == "LineString":
        return all(
            any(_point_on_segment(vertex, start, end) for start, end in _segments(geometry_vertices(container)))
            for vertex in geometry_vertices(candidate)
        )
    if candidate_type == "Polygon" and container_type == "Polygon":
        return all(_point_in_polygon(vertex, container) for vertex in geometry_vertices(candidate)[:-1])
    return False


def geometry_contains(container: Geometry, candidate: Geometry) -> bool:
    return geometry_within(candidate, container)


def geometry_length(geometry: Geometry) -> float:
    vertices = geometry_vertices(geometry)
    if len(vertices) < 2:
        return 0.0
    return sum(coordinate_distance(vertices[index - 1], vertices[index]) for index in range(1, len(vertices)))


def geometry_area(geometry: Geometry) -> float:
    if geometry_type(geometry) != "Polygon":
        return 0.0
    ring = geometry_vertices(geometry)
    area = 0.0
    for index in range(len(ring) - 1):
        x1, y1 = ring[index]
        x2, y2 = ring[index + 1]
        area += (x1 * y2) - (x2 * y1)
    return abs(area) / 2.0


def geometry_centroid(geometry: Geometry) -> Coordinate:
    if geometry_type(geometry) == "Point":
        return geometry["coordinates"]  # type: ignore[return-value]

    if geometry_type(geometry) == "LineString":
        vertices = geometry_vertices(geometry)
        total_length = 0.0
        centroid_x = 0.0
        centroid_y = 0.0
        for index in range(1, len(vertices)):
            start = vertices[index - 1]
            end = vertices[index]
            segment_length = coordinate_distance(start, end)
            if segment_length == 0.0:
                continue
            total_length += segment_length
            centroid_x += ((start[0] + end[0]) / 2.0) * segment_length
            centroid_y += ((start[1] + end[1]) / 2.0) * segment_length
        if total_length != 0.0:
            return (centroid_x / total_length, centroid_y / total_length)

    if geometry_type(geometry) == "Polygon":
        ring = geometry_vertices(geometry)
        area_factor = 0.0
        centroid_x = 0.0
        centroid_y = 0.0
        for index in range(len(ring) - 1):
            x1, y1 = ring[index]
            x2, y2 = ring[index + 1]
            cross = (x1 * y2) - (x2 * y1)
            area_factor += cross
            centroid_x += (x1 + x2) * cross
            centroid_y += (y1 + y2) * cross
        if area_factor != 0.0:
            factor = 1.0 / (3.0 * area_factor)
            return (centroid_x * factor, centroid_y * factor)

    vertices = geometry_vertices(geometry)
    return (
        sum(coord[0] for coord in vertices) / len(vertices),
        sum(coord[1] for coord in vertices) / len(vertices),
    )


def geometry_distance(origin: Geometry, destination: Geometry, method: DistanceMethod | str = "euclidean") -> float:
    return coordinate_distance(geometry_centroid(origin), geometry_centroid(destination), method=method)


def geometry_envelope(geometry: Geometry) -> Geometry:
    min_x, min_y, max_x, max_y = geometry_bounds(geometry)
    return {
        "type": "Polygon",
        "coordinates": (
            (min_x, min_y),
            (max_x, min_y),
            (max_x, max_y),
            (min_x, max_y),
            (min_x, min_y),
        ),
    }


def geometry_convex_hull(geometry: Geometry) -> Geometry:
    vertices = geometry_vertices(geometry)
    if geometry_type(geometry) == "Polygon":
        vertices = vertices[:-1]
    unique: list[Coordinate] = []
    seen: set[Coordinate] = set()
    for vertex in vertices:
        if vertex not in seen:
            unique.append(vertex)
            seen.add(vertex)
    if len(unique) <= 1:
        return geometry
    if len(unique) == 2:
        return {"type": "LineString", "coordinates": tuple(unique)}
    points = sorted(unique, key=lambda p: (p[0], p[1]))
    lower: list[Coordinate] = []
    for point in points:
        while len(lower) >= 2 and _cross_product(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[Coordinate] = []
    for point in reversed(points):
        while len(upper) >= 2 and _cross_product(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        return {"type": "LineString", "coordinates": (points[0], points[-1])}

    if all(abs(_cross_product(hull[0], hull[1], point)) <= 1e-9 for point in hull[2:]):
        return {"type": "LineString", "coordinates": (points[0], points[-1])}

    hull.append(hull[0])
    return {"type": "Polygon", "coordinates": tuple(hull)}


__all__ = [
    "Coordinate",
    "Geometry",
    "geometry_area",
    "geometry_bounds",
    "geometry_centroid",
    "geometry_contains",
    "geometry_convex_hull",
    "geometry_distance",
    "geometry_envelope",
    "geometry_intersects_bounds",
    "geometry_intersects",
    "geometry_length",
    "geometry_type",
    "geometry_vertices",
    "geometry_within",
    "geometry_within_bounds",
    "normalize_geometry",
    "transform_geometry",
]