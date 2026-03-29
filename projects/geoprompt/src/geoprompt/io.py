from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .frame import GeoPromptFrame
from .geometry import geometry_type


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _feature_to_record(feature: dict[str, Any], geometry: str) -> dict[str, Any]:
    if feature.get("type") != "Feature":
        raise TypeError("GeoJSON input must contain Feature objects")
    properties = dict(feature.get("properties") or {})
    properties[geometry] = feature.get("geometry")
    if "id" in feature and "site_id" not in properties:
        properties["site_id"] = str(feature["id"])
    return properties


def _extract_crs(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    if isinstance(payload.get("crs"), str):
        return str(payload["crs"])
    crs_mapping = payload.get("crs")
    if isinstance(crs_mapping, dict):
        properties = crs_mapping.get("properties")
        if isinstance(properties, dict) and "name" in properties:
            return str(properties["name"])
    return None


def _records_from_payload(payload: Any, geometry: str = "geometry") -> list[dict[str, Any]]:
    if isinstance(payload, list):
        if not all(isinstance(item, dict) for item in payload):
            raise TypeError("feature records must be mappings")
        return [dict(item) for item in payload]

    if isinstance(payload, dict) and "records" in payload:
        records = payload.get("records")
        if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
            raise TypeError("record wrapper payload must contain a record list")
        return [dict(item) for item in records]

    if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
        features = payload.get("features")
        if not isinstance(features, list):
            raise TypeError("FeatureCollection must contain a feature list")
        return [_feature_to_record(feature, geometry=geometry) for feature in features]

    if isinstance(payload, dict) and payload.get("type") == "Feature":
        return [_feature_to_record(payload, geometry=geometry)]

    raise TypeError("input must be a record list, a GeoJSON Feature, or a GeoJSON FeatureCollection")


def _frame_from_path(path: str | Path, geometry: str = "geometry", crs: str | None = None) -> GeoPromptFrame:
    payload = _read_json(path)
    return GeoPromptFrame.from_records(
        _records_from_payload(payload, geometry=geometry),
        geometry=geometry,
        crs=crs or _extract_crs(payload),
    )


def read_points(path: str | Path, geometry: str = "geometry", crs: str | None = None) -> GeoPromptFrame:
    frame = _frame_from_path(path, geometry=geometry, crs=crs)
    if any(geometry_type(row[geometry]) != "Point" for row in frame):
        raise TypeError("read_points only accepts point geometry inputs")
    return frame


def read_features(path: str | Path, geometry: str = "geometry", crs: str | None = None) -> GeoPromptFrame:
    return _frame_from_path(path, geometry=geometry, crs=crs)


def read_geojson(path: str | Path, geometry: str = "geometry", crs: str | None = None) -> GeoPromptFrame:
    return _frame_from_path(path, geometry=geometry, crs=crs)


def _as_geojson_geometry(geometry: dict[str, Any]) -> dict[str, Any]:
    geometry_kind = str(geometry["type"])
    coordinates = geometry["coordinates"]
    if geometry_kind == "Point":
        return {"type": "Point", "coordinates": list(coordinates)}
    if geometry_kind == "LineString":
        return {"type": "LineString", "coordinates": [list(coord) for coord in coordinates]}
    if geometry_kind == "Polygon":
        return {"type": "Polygon", "coordinates": [[list(coord) for coord in coordinates]]}
    raise TypeError(f"unsupported geometry type: {geometry_kind}")


def frame_to_geojson(frame: GeoPromptFrame, geometry: str = "geometry", id_column: str = "site_id") -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    for row in frame.to_records():
        properties = {key: value for key, value in row.items() if key != geometry}
        feature: dict[str, Any] = {
            "type": "Feature",
            "properties": properties,
            "geometry": _as_geojson_geometry(row[geometry]),
        }
        if id_column in properties:
            feature["id"] = str(properties[id_column])
        features.append(feature)
    collection: dict[str, Any] = {"type": "FeatureCollection", "features": features}
    if frame.crs is not None:
        collection["crs"] = {"type": "name", "properties": {"name": frame.crs}}
    return collection


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def write_geojson(path: str | Path, frame: GeoPromptFrame, geometry: str = "geometry", id_column: str = "site_id") -> Path:
    return write_json(path, frame_to_geojson(frame, geometry=geometry, id_column=id_column))


__all__ = [
    "frame_to_geojson",
    "read_features",
    "read_geojson",
    "read_points",
    "write_geojson",
    "write_json",
]