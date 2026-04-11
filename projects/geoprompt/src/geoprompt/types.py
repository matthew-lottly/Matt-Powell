"""TypedDict models for structured geoprompt outputs (items 11-12)."""

from __future__ import annotations

from typing import Any, TypedDict


class PointGeometry(TypedDict):
    type: str
    coordinates: tuple[float, float]


class LineStringGeometry(TypedDict):
    type: str
    coordinates: tuple[tuple[float, float], ...]


class PolygonGeometry(TypedDict):
    type: str
    coordinates: tuple[tuple[float, float], ...]


class BoundsDict(TypedDict):
    min_x: float
    min_y: float
    max_x: float
    max_y: float


class NearestNeighborRecord(TypedDict):
    origin: str
    neighbor: str
    distance: float
    origin_geometry_type: str
    neighbor_geometry_type: str
    rank: int
    distance_method: str


class InteractionRecord(TypedDict, total=False):
    origin: str
    destination: str
    distance: float
    interaction: float
    distance_method: str
    directional_alignment: float


class AreaSimilarityRecord(TypedDict):
    origin: str
    destination: str
    area_similarity: float
    distance_method: str


class DemoReportSummary(TypedDict):
    feature_count: int
    crs: str | None
    centroid: tuple[float, float]
    bounds: BoundsDict
    projected_bounds_3857: BoundsDict
    geometry_types: list[str]
    valley_window_feature_count: int


class EquationDescriptions(TypedDict):
    prompt_decay: str
    prompt_influence: str
    prompt_interaction: str
    corridor_strength: str
    area_similarity: str


class DemoReport(TypedDict):
    package: str
    schema_version: str
    equations: EquationDescriptions
    summary: DemoReportSummary
    top_interactions: list[InteractionRecord]
    top_area_similarity: list[AreaSimilarityRecord]
    top_nearest_neighbors: list[NearestNeighborRecord]
    top_geographic_neighbors: list[NearestNeighborRecord]
    records: list[dict[str, Any]]
    outputs: dict[str, str]


class GeoJSONFeature(TypedDict, total=False):
    type: str
    id: str
    properties: dict[str, Any]
    geometry: dict[str, Any]


class GeoJSONCollection(TypedDict, total=False):
    type: str
    crs: dict[str, Any]
    features: list[GeoJSONFeature]


__all__ = [
    "AreaSimilarityRecord",
    "BoundsDict",
    "DemoReport",
    "DemoReportSummary",
    "EquationDescriptions",
    "GeoJSONCollection",
    "GeoJSONFeature",
    "InteractionRecord",
    "LineStringGeometry",
    "NearestNeighborRecord",
    "PointGeometry",
    "PolygonGeometry",
]
