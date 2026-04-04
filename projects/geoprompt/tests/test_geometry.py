"""Item 43: Property-based and unit tests for geometry invariants and CRS transforms."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from geoprompt import GeoPromptFrame
from geoprompt.io import read_features
from geoprompt.geometry import (
    geometry_area,
    geometry_bounds,
    geometry_centroid,
    geometry_contains,
    geometry_intersects,
    geometry_length,
    geometry_type,
    geometry_vertices,
    geometry_within,
    normalize_geometry,
    transform_geometry,
)


class TestNormalizeGeometry:
    def test_point_from_tuple(self) -> None:
        geom = normalize_geometry((1.0, 2.0))
        assert geom["type"] == "Point"
        assert geom["coordinates"] == (1.0, 2.0)

    def test_point_from_dict(self) -> None:
        geom = normalize_geometry({"type": "Point", "coordinates": [1, 2]})
        assert geom["type"] == "Point"

    def test_linestring(self) -> None:
        geom = normalize_geometry({"type": "LineString", "coordinates": [[0, 0], [1, 1]]})
        assert geom["type"] == "LineString"
        coords = cast(list[Any] | tuple[Any, ...], geom["coordinates"])
        assert len(coords) == 2

    def test_polygon_auto_closes(self) -> None:
        geom = normalize_geometry({"type": "Polygon", "coordinates": [[0, 0], [1, 0], [1, 1]]})
        ring = cast(list[Any] | tuple[Any, ...], geom["coordinates"])
        assert ring[0] == ring[-1]

    def test_multipoint(self) -> None:
        geom = normalize_geometry({"type": "MultiPoint", "coordinates": [[0, 0], [1, 1], [2, 2]]})
        assert geom["type"] == "MultiPoint"
        coords = cast(list[Any] | tuple[Any, ...], geom["coordinates"])
        assert len(coords) == 3

    def test_multilinestring(self) -> None:
        geom = normalize_geometry({
            "type": "MultiLineString",
            "coordinates": [[[0, 0], [1, 1]], [[2, 2], [3, 3]]],
        })
        assert geom["type"] == "MultiLineString"
        coords = cast(list[Any] | tuple[Any, ...], geom["coordinates"])
        assert len(coords) == 2

    def test_multipolygon(self) -> None:
        geom = normalize_geometry({
            "type": "MultiPolygon",
            "coordinates": [
                [[0, 0], [1, 0], [1, 1], [0, 1]],
                [[2, 2], [3, 2], [3, 3], [2, 3]],
            ],
        })
        assert geom["type"] == "MultiPolygon"
        coords = cast(list[Any] | tuple[Any, ...], geom["coordinates"])
        assert len(coords) == 2

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(TypeError, match="unsupported geometry type"):
            normalize_geometry({"type": "GeometryCollection", "coordinates": []})

    def test_invalid_input_raises(self) -> None:
        with pytest.raises(TypeError):
            normalize_geometry("not a geometry")

    def test_linestring_too_few_coords(self) -> None:
        with pytest.raises(TypeError, match="at least two"):
            normalize_geometry({"type": "LineString", "coordinates": [[0, 0]]})


class TestGeometryType:
    def test_point_type(self) -> None:
        assert geometry_type({"type": "Point", "coordinates": (0.0, 0.0)}) == "Point"

    def test_linestring_type(self) -> None:
        assert geometry_type({"type": "LineString", "coordinates": ((0.0, 0.0), (1.0, 1.0))}) == "LineString"


class TestGeometryVertices:
    def test_point_single_vertex(self) -> None:
        geom = normalize_geometry({"type": "Point", "coordinates": [1, 2]})
        verts = geometry_vertices(geom)
        assert len(verts) == 1

    def test_linestring_vertices(self) -> None:
        geom = normalize_geometry({"type": "LineString", "coordinates": [[0, 0], [1, 1], [2, 0]]})
        verts = geometry_vertices(geom)
        assert len(verts) == 3

    def test_multipoint_vertices(self) -> None:
        geom = normalize_geometry({"type": "MultiPoint", "coordinates": [[0, 0], [1, 1]]})
        verts = geometry_vertices(geom)
        assert len(verts) == 2


class TestGeometryBounds:
    def test_point_bounds(self) -> None:
        geom = normalize_geometry({"type": "Point", "coordinates": [5.0, 10.0]})
        bounds = geometry_bounds(geom)
        assert bounds == (5.0, 10.0, 5.0, 10.0)

    def test_polygon_bounds(self) -> None:
        geom = normalize_geometry({"type": "Polygon", "coordinates": [[0, 0], [2, 0], [2, 3], [0, 3]]})
        bounds = geometry_bounds(geom)
        assert bounds[0] == 0.0
        assert bounds[2] == 2.0


class TestGeometryCentroid:
    def test_point_centroid(self) -> None:
        geom = normalize_geometry({"type": "Point", "coordinates": [5.0, 10.0]})
        assert geometry_centroid(geom) == (5.0, 10.0)

    def test_line_centroid_weighted(self) -> None:
        geom = normalize_geometry({"type": "LineString", "coordinates": [[0, 0], [2, 0], [3, 0]]})
        centroid = geometry_centroid(geom)
        assert centroid == (1.5, 0.0)


class TestGeometryLength:
    def test_point_zero_length(self) -> None:
        geom = normalize_geometry({"type": "Point", "coordinates": [0.0, 0.0]})
        assert geometry_length(geom) == 0.0

    def test_line_length(self) -> None:
        geom = normalize_geometry({"type": "LineString", "coordinates": [[0, 0], [3, 4]]})
        assert round(geometry_length(geom), 6) == 5.0


class TestGeometryArea:
    def test_point_zero_area(self) -> None:
        geom = normalize_geometry({"type": "Point", "coordinates": [0

, 0]})
        assert geometry_area(geom) == 0.0

    def test_unit_square_area(self) -> None:
        geom = normalize_geometry({"type": "Polygon", "coordinates": [[0, 0], [1, 0], [1, 1], [0, 1]]})
        assert round(geometry_area(geom), 6) == 1.0


class TestGeometryIntersects:
    def test_point_point_same(self) -> None:
        p = normalize_geometry({"type": "Point", "coordinates": [0, 0]})
        assert geometry_intersects(p, p)

    def test_point_point_different(self) -> None:
        p1 = normalize_geometry({"type": "Point", "coordinates": [0, 0]})
        p2 = normalize_geometry({"type": "Point", "coordinates": [1, 1]})
        assert not geometry_intersects(p1, p2)

    def test_point_in_polygon(self) -> None:
        point = normalize_geometry({"type": "Point", "coordinates": [0.5, 0.5]})
        poly = normalize_geometry({"type": "Polygon", "coordinates": [[0, 0], [1, 0], [1, 1], [0, 1]]})
        assert geometry_intersects(point, poly)

    def test_polygon_polygon_overlap(self) -> None:
        poly1 = normalize_geometry({"type": "Polygon", "coordinates": [[0, 0], [2, 0], [2, 2], [0, 2]]})
        poly2 = normalize_geometry({"type": "Polygon", "coordinates": [[1, 1], [3, 1], [3, 3], [1, 3]]})
        assert geometry_intersects(poly1, poly2)


class TestGeometryWithin:
    def test_point_within_polygon(self) -> None:
        point = normalize_geometry({"type": "Point", "coordinates": [0.5, 0.5]})
        poly = normalize_geometry({"type": "Polygon", "coordinates": [[0, 0], [1, 0], [1, 1], [0, 1]]})
        assert geometry_within(point, poly)

    def test_point_outside_polygon(self) -> None:
        point = normalize_geometry({"type": "Point", "coordinates": [5.0, 5.0]})
        poly = normalize_geometry({"type": "Polygon", "coordinates": [[0, 0], [1, 0], [1, 1], [0, 1]]})
        assert not geometry_within(point, poly)


class TestGeometryContains:
    def test_polygon_contains_point(self) -> None:
        point = normalize_geometry({"type": "Point", "coordinates": [0.5, 0.5]})
        poly = normalize_geometry({"type": "Polygon", "coordinates": [[0, 0], [1, 0], [1, 1], [0, 1]]})
        assert geometry_contains(poly, point)


class TestTransformGeometry:
    def test_point_transform(self) -> None:
        geom = normalize_geometry({"type": "Point", "coordinates": [1, 2]})
        transformed = transform_geometry(geom, lambda c: (c[0] * 2, c[1] * 2))
        assert transformed["coordinates"] == (2.0, 4.0)

    def test_linestring_transform(self) -> None:
        geom = normalize_geometry({"type": "LineString", "coordinates": [[0, 0], [1, 1]]})
        transformed = transform_geometry(geom, lambda c: (c[0] + 10, c[1] + 10))
        verts = geometry_vertices(transformed)
        assert verts[0] == (10.0, 10.0)

    def test_multipoint_transform(self) -> None:
        geom = normalize_geometry({"type": "MultiPoint", "coordinates": [[0, 0], [1, 1]]})
        transformed = transform_geometry(geom, lambda c: (c[0] * 3, c[1] * 3))
        assert transformed["type"] == "MultiPoint"


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestCRSTransform:
    """Item 45: CRS transformation correctness tests (merged from test_crs.py)."""

    def test_epsg_4326_to_3857_round_trip(self) -> None:
        frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
        projected = frame.to_crs("EPSG:3857")
        assert projected.crs == "EPSG:3857"
        first = projected.head(1)[0]["geometry"]["coordinates"]
        assert abs(first[0]) > 1_000_000

    def test_same_crs_no_op(self) -> None:
        frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
        same = frame.to_crs("EPSG:4326")
        assert same.crs == "EPSG:4326"
        orig_centroid = frame.centroid()
        same_centroid = same.centroid()
        assert round(orig_centroid[0], 6) == round(same_centroid[0], 6)

    def test_missing_crs_raises(self) -> None:
        frame = GeoPromptFrame.from_records([
            {"site_id": "a", "geometry": {"type": "Point", "coordinates": [0.0, 0.0]}},
        ])
        with pytest.raises(ValueError, match="CRS is not set"):
            frame.to_crs("EPSG:3857")

    def test_set_crs_override(self) -> None:
        frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
        with pytest.raises(ValueError, match="allow_override"):
            frame.set_crs("EPSG:3857")
        overridden = frame.set_crs("EPSG:3857", allow_override=True)
        assert overridden.crs == "EPSG:3857"
