"""Item 44: Malformed fixture tests for robust input handling."""

from __future__ import annotations

import pytest

from geoprompt import GeoPromptFrame
from geoprompt.geometry import normalize_geometry
from geoprompt.validation import (
    validate_geometry,
    validate_non_empty_features,
    validate_numeric_range,
    validate_required_columns,
    validate_weight_column_values,
)
from geoprompt.exceptions import GeometryError, ValidationError


class TestMalformedGeometry:
    def test_none_geometry_raises(self) -> None:
        with pytest.raises(GeometryError, match="None"):
            validate_geometry(None)

    def test_non_dict_geometry_raises(self) -> None:
        with pytest.raises(GeometryError, match="dict"):
            validate_geometry("not a geometry")

    def test_unsupported_type_raises(self) -> None:
        with pytest.raises(GeometryError, match="Unsupported"):
            validate_geometry({"type": "UnknownType", "coordinates": [0, 0]})

    def test_missing_coordinates_raises(self) -> None:
        with pytest.raises(GeometryError, match="coordinates"):
            validate_geometry({"type": "Point"})

    def test_point_wrong_coord_count_raises(self) -> None:
        with pytest.raises(GeometryError, match="exactly 2"):
            validate_geometry({"type": "Point", "coordinates": [1, 2, 3]})

    def test_point_non_numeric_raises(self) -> None:
        with pytest.raises(GeometryError, match="numeric"):
            validate_geometry({"type": "Point", "coordinates": ["a", "b"]})

    def test_linestring_too_few_raises(self) -> None:
        with pytest.raises(GeometryError, match="at least 2"):
            validate_geometry({"type": "LineString", "coordinates": [[0, 0]]})

    def test_normalize_unsupported_type_raises(self) -> None:
        with pytest.raises(TypeError, match="unsupported"):
            normalize_geometry({"type": "GeometryCollection", "coordinates": []})

    def test_normalize_bad_linestring_raises(self) -> None:
        with pytest.raises(TypeError, match="at least two"):
            normalize_geometry({"type": "LineString", "coordinates": [[0, 0]]})


class TestMalformedInput:
    def test_empty_features_raises(self) -> None:
        with pytest.raises(ValidationError, match="zero features"):
            validate_non_empty_features([])

    def test_missing_columns_raises(self) -> None:
        with pytest.raises(ValidationError, match="Missing"):
            validate_required_columns({"a": 1}, ["a", "b", "c"])

    def test_numeric_range_below_min(self) -> None:
        with pytest.raises(ValidationError, match=">="):
            validate_numeric_range(-1.0, "value", min_val=0.0)

    def test_numeric_range_above_max(self) -> None:
        with pytest.raises(ValidationError, match="<="):
            validate_numeric_range(200.0, "value", max_val=100.0)

    def test_weight_column_non_numeric(self) -> None:
        records = [{"site_id": "a", "weight": "not_a_number"}]
        with pytest.raises(ValidationError, match="non-numeric"):
            validate_weight_column_values(records, "weight")

    def test_weight_column_null_warns(self) -> None:
        records = [{"site_id": "a", "weight": None}]
        validate_weight_column_values(records, "weight")


class TestMalformedFrame:
    def test_frame_from_empty_records(self) -> None:
        frame = GeoPromptFrame.from_records([])
        assert len(frame) == 0

    def test_frame_missing_geometry_raises(self) -> None:
        with pytest.raises((TypeError, KeyError)):
            GeoPromptFrame.from_records([{"site_id": "a"}])

    def test_frame_bad_geometry_type_raises(self) -> None:
        with pytest.raises(TypeError):
            GeoPromptFrame.from_records([
                {"site_id": "a", "geometry": {"type": "Unknown", "coordinates": [0, 0]}},
            ])
