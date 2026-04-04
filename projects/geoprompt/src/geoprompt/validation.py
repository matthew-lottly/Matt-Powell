"""Input validation utilities for geoprompt (items 1-10)."""

from __future__ import annotations

import logging
from typing import Any, Sequence

from .exceptions import CRSError, GeometryError, ValidationError


logger = logging.getLogger("geoprompt.validation")

SUPPORTED_GEOMETRY_TYPES = {"Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon"}
SCHEMA_VERSION = "1.0.0"


def validate_required_columns(record: dict[str, Any], required: Sequence[str], context: str = "") -> None:
    """Item 1: Validate that all required columns are present in a record."""
    missing = [col for col in required if col not in record]
    if missing:
        label = f" ({context})" if context else ""
        raise ValidationError(f"Missing required columns{label}: {', '.join(missing)}")


def validate_geometry(geometry: Any, *, allow_empty: bool = False) -> None:
    """Item 2: Validate a geometry object and fail early on malformed data."""
    if geometry is None:
        if allow_empty:
            return
        raise GeometryError("Geometry is None")

    if not isinstance(geometry, dict):
        raise GeometryError(f"Geometry must be a dict, got {type(geometry).__name__}")

    geom_type = geometry.get("type")
    if geom_type not in SUPPORTED_GEOMETRY_TYPES:
        raise GeometryError(f"Unsupported geometry type: {geom_type}")

    coordinates = geometry.get("coordinates")
    if coordinates is None:
        raise GeometryError("Geometry is missing 'coordinates' key")

    if geom_type == "Point":
        if not isinstance(coordinates, (list, tuple)) or len(coordinates) != 2:
            raise GeometryError("Point geometry must have exactly 2 coordinates")
        if not all(isinstance(c, (int, float)) for c in coordinates):
            raise GeometryError("Point coordinates must be numeric")

    elif geom_type == "LineString":
        if not isinstance(coordinates, (list, tuple)) or len(coordinates) < 2:
            raise GeometryError("LineString must have at least 2 coordinates")

    elif geom_type == "Polygon":
        if not isinstance(coordinates, (list, tuple)) or len(coordinates) < 3:
            if isinstance(coordinates, (list, tuple)) and coordinates and isinstance(coordinates[0], (list, tuple)):
                if len(coordinates[0]) < 3:
                    raise GeometryError("Polygon ring must have at least 3 coordinates")
            else:
                raise GeometryError("Polygon must have at least 3 coordinates")


def validate_non_empty_features(features: Sequence[Any]) -> None:
    """Item 3: Raise a clear error when input has zero features."""
    if not features:
        raise ValidationError("Input contains zero features. At least one feature is required.")


def validate_crs(crs: str | None, *, require: bool = False) -> None:
    """Item 7: Detect missing CRS."""
    if crs is None and require:
        raise CRSError("CRS is not set. Provide a CRS (e.g., 'EPSG:4326') via the crs parameter.")
    if crs is not None and not crs.strip():
        raise CRSError("CRS must be a non-empty string.")
    if crs is not None:
        logger.debug("CRS set to %s", crs)


def validate_distance_method_crs(distance_method: str, crs: str | None) -> None:
    """Validate that a distance method is compatible with CRS assumptions.

    Haversine distance requires geographic coordinates in EPSG:4326.
    """
    method = distance_method.strip().lower()
    if method not in {"euclidean", "haversine"}:
        raise ValidationError(f"Unsupported distance method: {distance_method}")
    if method != "haversine":
        return

    if crs is None:
        raise CRSError("distance_method='haversine' requires CRS to be set to EPSG:4326")

    normalized = crs.strip().upper().replace(" ", "")
    if normalized not in {"EPSG:4326", "WGS84"}:
        raise CRSError(
            f"distance_method='haversine' requires geographic CRS EPSG:4326, got '{crs}'"
        )


def validate_numeric_range(value: float, name: str, *, min_val: float | None = None, max_val: float | None = None) -> None:
    """Item 8: Enforce numeric range checks for weight fields."""
    if min_val is not None and value < min_val:
        raise ValidationError(f"{name} must be >= {min_val}, got {value}")
    if max_val is not None and value > max_val:
        raise ValidationError(f"{name} must be <= {max_val}, got {value}")


def validate_weight_column_values(records: Sequence[dict[str, Any]], column: str) -> None:
    """Item 9: Null-safe handling for missing weight values."""
    for i, record in enumerate(records):
        value = record.get(column)
        if value is None:
            logger.warning("Record %d has null value for weight column '%s'; treating as 0.0", i, column)
        elif not isinstance(value, (int, float)):
            raise ValidationError(f"Record {i} has non-numeric value for weight column '{column}': {value!r}")


def safe_weight(value: Any, default: float = 0.0) -> float:
    """Item 9: Safely extract a numeric weight, defaulting to 0.0 for None."""
    if value is None:
        return default
    return float(value)


def add_schema_version(output: dict[str, Any]) -> dict[str, Any]:
    """Item 10: Add a schema version field to output JSON."""
    output["schema_version"] = SCHEMA_VERSION
    return output


__all__ = [
    "SCHEMA_VERSION",
    "SUPPORTED_GEOMETRY_TYPES",
    "add_schema_version",
    "safe_weight",
    "validate_crs",
    "validate_distance_method_crs",
    "validate_geometry",
    "validate_non_empty_features",
    "validate_numeric_range",
    "validate_required_columns",
    "validate_weight_column_values",
]
