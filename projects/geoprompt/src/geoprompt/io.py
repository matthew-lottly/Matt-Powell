from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from .frame import GeoPromptFrame
from .geometry import geometry_type


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _parse_point_wkt(value: str) -> dict[str, Any] | None:
    text = value.strip()
    upper = text.upper()
    if not upper.startswith("POINT"):
        return None
    if "(" not in text or ")" not in text:
        return None
    body = text[text.find("(") + 1 : text.rfind(")")].strip()
    parts = body.split()
    if len(parts) < 2:
        return None
    try:
        x_value = float(parts[0])
        y_value = float(parts[1])
    except ValueError:
        return None
    return {"type": "Point", "coordinates": [x_value, y_value]}


def _coerce_geometry_value(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict) and "type" in value and "coordinates" in value:
        return dict(value)
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict) and "type" in parsed and "coordinates" in parsed:
            return parsed
    return _parse_point_wkt(text)


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


def _apply_row_limits(
    rows: Iterable[dict[str, Any]],
    limit_rows: int | None,
    sample_step: int,
) -> list[dict[str, Any]]:
    if sample_step <= 0:
        raise ValueError("sample_step must be >= 1")
    selected: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if sample_step > 1 and index % sample_step != 0:
            continue
        selected.append(dict(row))
        if limit_rows is not None and len(selected) >= limit_rows:
            break
    return selected


def _records_from_csv(
    path: str | Path,
    *,
    geometry: str,
    x_column: str | None,
    y_column: str | None,
    geometry_column: str | None,
    use_columns: Sequence[str] | None,
    limit_rows: int | None,
    sample_step: int,
    delimiter: str,
    encoding: str,
) -> list[dict[str, Any]]:
    selected_columns = set(use_columns or [])
    records: list[dict[str, Any]] = []

    with Path(path).open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for raw_index, raw_row in enumerate(reader):
            if sample_step > 1 and raw_index % sample_step != 0:
                continue

            row = dict(raw_row)
            if selected_columns:
                row = {key: row[key] for key in row.keys() if key in selected_columns}

            resolved_geometry: dict[str, Any] | None = None
            if x_column is not None and y_column is not None:
                if x_column not in raw_row or y_column not in raw_row:
                    raise KeyError(f"CSV is missing required columns '{x_column}' and '{y_column}'")
                x_value = float(raw_row[x_column])
                y_value = float(raw_row[y_column])
                resolved_geometry = {"type": "Point", "coordinates": [x_value, y_value]}
            elif geometry_column is not None:
                resolved_geometry = _coerce_geometry_value(raw_row.get(geometry_column))
            elif geometry in row:
                resolved_geometry = _coerce_geometry_value(row.get(geometry))

            if resolved_geometry is None:
                raise ValueError(
                    "tabular spatial reads require x_column/y_column or geometry_column"
                )

            row[geometry] = resolved_geometry
            records.append(row)

            if limit_rows is not None and len(records) >= limit_rows:
                break

    return records


def _iter_csv_records(
    path: str | Path,
    *,
    geometry: str,
    x_column: str | None,
    y_column: str | None,
    geometry_column: str | None,
    use_columns: Sequence[str] | None,
    sample_step: int,
    delimiter: str,
    encoding: str,
) -> Iterable[dict[str, Any]]:
    selected_columns = set(use_columns or [])
    with Path(path).open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for raw_index, raw_row in enumerate(reader):
            if sample_step > 1 and raw_index % sample_step != 0:
                continue

            row = dict(raw_row)
            if selected_columns:
                row = {key: row[key] for key in row.keys() if key in selected_columns}

            resolved_geometry: dict[str, Any] | None = None
            if x_column is not None and y_column is not None:
                if x_column not in raw_row or y_column not in raw_row:
                    raise KeyError(f"CSV is missing required columns '{x_column}' and '{y_column}'")
                x_value = float(raw_row[x_column])
                y_value = float(raw_row[y_column])
                resolved_geometry = {"type": "Point", "coordinates": [x_value, y_value]}
            elif geometry_column is not None:
                resolved_geometry = _coerce_geometry_value(raw_row.get(geometry_column))
            elif geometry in row:
                resolved_geometry = _coerce_geometry_value(row.get(geometry))

            if resolved_geometry is None:
                raise ValueError(
                    "tabular spatial reads require x_column/y_column or geometry_column"
                )

            row[geometry] = resolved_geometry
            yield row


def _iter_frame_chunks(
    rows: Iterable[dict[str, Any]],
    *,
    geometry: str,
    crs: str | None,
    chunk_size: int,
    limit_rows: int | None,
) -> Iterable[GeoPromptFrame]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be >= 1")

    emitted = 0
    bucket: list[dict[str, Any]] = []
    for row in rows:
        if limit_rows is not None and emitted >= limit_rows:
            break
        bucket.append(dict(row))
        emitted += 1
        if len(bucket) >= chunk_size:
            yield GeoPromptFrame.from_records(bucket, geometry=geometry, crs=crs)
            bucket = []
    if bucket:
        yield GeoPromptFrame.from_records(bucket, geometry=geometry, crs=crs)


def _read_with_geopandas(
    path: str | Path,
    *,
    geometry: str,
    crs: str | None,
    layer: str | None,
    bbox: tuple[float, float, float, float] | None,
    use_columns: Sequence[str] | None,
    limit_rows: int | None,
    sample_step: int,
) -> GeoPromptFrame:
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise ImportError(
            "geopandas is required for this format. Install extras: pip install geoprompt[io,compare]"
        ) from exc

    read_kwargs: dict[str, Any] = {}
    if layer is not None:
        read_kwargs["layer"] = layer
    if bbox is not None:
        read_kwargs["bbox"] = bbox
    if use_columns:
        read_kwargs["columns"] = list(use_columns)
    if limit_rows is not None:
        read_kwargs["rows"] = slice(0, limit_rows)

    frame = gpd.read_file(Path(path), **read_kwargs)
    if sample_step > 1:
        frame = frame.iloc[::sample_step]
    if crs is not None and frame.crs is not None and str(frame.crs) != crs:
        frame = frame.to_crs(crs)

    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        record = row.drop(labels=[frame.geometry.name]).to_dict()
        geom = row[frame.geometry.name]
        record[geometry] = geom.__geo_interface__ if geom is not None else None
        rows.append(record)

    filtered = [r for r in rows if r.get(geometry) is not None]
    resolved_crs = crs or (str(frame.crs) if frame.crs is not None else None)
    return GeoPromptFrame.from_records(filtered, geometry=geometry, crs=resolved_crs)


def _frame_from_path(path: str | Path, geometry: str = "geometry", crs: str | None = None) -> GeoPromptFrame:
    payload = _read_json(path)
    return GeoPromptFrame.from_records(
        _records_from_payload(payload, geometry=geometry),
        geometry=geometry,
        crs=crs or _extract_crs(payload),
    )


def read_data(
    path: str | Path,
    *,
    geometry: str = "geometry",
    crs: str | None = None,
    x_column: str | None = None,
    y_column: str | None = None,
    geometry_column: str | None = None,
    use_columns: Sequence[str] | None = None,
    limit_rows: int | None = None,
    sample_step: int = 1,
    layer: str | None = None,
    bbox: tuple[float, float, float, float] | None = None,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> GeoPromptFrame:
    """Unified spatial reader for GeoJSON/JSON, tabular files, and geofiles.

    Large-dataset knobs:
    - ``limit_rows``: cap row count
    - ``sample_step``: keep every Nth row
    - ``use_columns``: read selected attributes only
    - ``bbox`` and ``layer`` for geospatial stores
    """
    data_path = Path(path)
    suffix = data_path.suffix.lower()

    if suffix in {".json", ".geojson"}:
        payload = _read_json(data_path)
        rows = _records_from_payload(payload, geometry=geometry)
        rows = _apply_row_limits(rows, limit_rows=limit_rows, sample_step=sample_step)
        if use_columns:
            keep = set(use_columns)
            rows = [
                {**{k: v for k, v in row.items() if k in keep}, geometry: row[geometry]}
                for row in rows
            ]
        return GeoPromptFrame.from_records(rows, geometry=geometry, crs=crs or _extract_crs(payload))

    if suffix in {".csv", ".tsv", ".txt"}:
        delim = "\t" if suffix == ".tsv" else delimiter
        rows = _records_from_csv(
            data_path,
            geometry=geometry,
            x_column=x_column,
            y_column=y_column,
            geometry_column=geometry_column,
            use_columns=use_columns,
            limit_rows=limit_rows,
            sample_step=sample_step,
            delimiter=delim,
            encoding=encoding,
        )
        return GeoPromptFrame.from_records(rows, geometry=geometry, crs=crs)

    if suffix in {".shp", ".gpkg", ".fgb", ".gdb", ".parquet"}:
        return _read_with_geopandas(
            data_path,
            geometry=geometry,
            crs=crs,
            layer=layer,
            bbox=bbox,
            use_columns=use_columns,
            limit_rows=limit_rows,
            sample_step=sample_step,
        )

    raise ValueError(f"unsupported input format for path: {data_path}")


def iter_data(
    path: str | Path,
    *,
    geometry: str = "geometry",
    crs: str | None = None,
    x_column: str | None = None,
    y_column: str | None = None,
    geometry_column: str | None = None,
    use_columns: Sequence[str] | None = None,
    limit_rows: int | None = None,
    sample_step: int = 1,
    layer: str | None = None,
    bbox: tuple[float, float, float, float] | None = None,
    chunk_size: int = 50000,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> Iterable[GeoPromptFrame]:
    """Yield data as chunked ``GeoPromptFrame`` batches for large datasets."""
    data_path = Path(path)
    suffix = data_path.suffix.lower()

    if suffix in {".json", ".geojson"}:
        payload = _read_json(data_path)
        rows = _records_from_payload(payload, geometry=geometry)
        if use_columns:
            keep = set(use_columns)
            rows = [
                {**{k: v for k, v in row.items() if k in keep}, geometry: row[geometry]}
                for row in rows
            ]
        yield from _iter_frame_chunks(
            rows,
            geometry=geometry,
            crs=crs or _extract_crs(payload),
            chunk_size=chunk_size,
            limit_rows=limit_rows,
        )
        return

    if suffix in {".csv", ".tsv", ".txt"}:
        delim = "\t" if suffix == ".tsv" else delimiter
        rows_iter = _iter_csv_records(
            data_path,
            geometry=geometry,
            x_column=x_column,
            y_column=y_column,
            geometry_column=geometry_column,
            use_columns=use_columns,
            sample_step=sample_step,
            delimiter=delim,
            encoding=encoding,
        )
        yield from _iter_frame_chunks(
            rows_iter,
            geometry=geometry,
            crs=crs,
            chunk_size=chunk_size,
            limit_rows=limit_rows,
        )
        return

    if suffix in {".shp", ".gpkg", ".fgb", ".gdb", ".parquet"}:
        frame = _read_with_geopandas(
            data_path,
            geometry=geometry,
            crs=crs,
            layer=layer,
            bbox=bbox,
            use_columns=use_columns,
            limit_rows=limit_rows,
            sample_step=sample_step,
        )
        yield from _iter_frame_chunks(
            frame.to_records(),
            geometry=geometry,
            crs=frame.crs,
            chunk_size=chunk_size,
            limit_rows=limit_rows,
        )
        return

    raise ValueError(f"unsupported input format for path: {data_path}")


def read_table(
    path: str | Path,
    *,
    x_column: str,
    y_column: str,
    geometry: str = "geometry",
    crs: str | None = None,
    use_columns: Sequence[str] | None = None,
    limit_rows: int | None = None,
    sample_step: int = 1,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> GeoPromptFrame:
    """Simple tabular reader wrapper for point-based CSV/TSV data."""
    return read_data(
        path,
        geometry=geometry,
        crs=crs,
        x_column=x_column,
        y_column=y_column,
        use_columns=use_columns,
        limit_rows=limit_rows,
        sample_step=sample_step,
        delimiter=delimiter,
        encoding=encoding,
    )


def read_points(path: str | Path, geometry: str = "geometry", crs: str | None = None) -> GeoPromptFrame:
    frame = read_data(path, geometry=geometry, crs=crs)
    if any(geometry_type(row[geometry]) != "Point" for row in frame):
        raise TypeError("read_points only accepts point geometry inputs")
    return frame


def read_features(path: str | Path, geometry: str = "geometry", crs: str | None = None) -> GeoPromptFrame:
    return read_data(path, geometry=geometry, crs=crs)


def read_geojson(path: str | Path, geometry: str = "geometry", crs: str | None = None) -> GeoPromptFrame:
    return read_data(path, geometry=geometry, crs=crs)


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


def write_data(
    path: str | Path,
    frame: GeoPromptFrame,
    *,
    geometry: str = "geometry",
    id_column: str = "site_id",
    delimiter: str = ",",
    encoding: str = "utf-8",
    layer: str | None = None,
    driver: str | None = None,
) -> Path:
    """Unified writer for GeoJSON/JSON/CSV and optional geospatial file formats."""
    output_path = Path(path)
    suffix = output_path.suffix.lower()

    if suffix in {".geojson", ".json"}:
        return write_geojson(output_path, frame, geometry=geometry, id_column=id_column)

    if suffix in {".csv", ".tsv", ".txt"}:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        rows = frame.to_records()
        if not rows:
            output_path.write_text("", encoding=encoding)
            return output_path
        fieldnames = list(rows[0].keys())
        delim = "\t" if suffix == ".tsv" else delimiter
        with output_path.open("w", encoding=encoding, newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=delim)
            writer.writeheader()
            for row in rows:
                serialized = dict(row)
                if geometry in serialized:
                    serialized[geometry] = json.dumps(serialized[geometry], separators=(",", ":"))
                writer.writerow(serialized)
        return output_path

    if suffix in {".shp", ".gpkg", ".fgb", ".gdb", ".parquet"}:
        try:
            import geopandas as gpd
        except ImportError as exc:
            raise ImportError(
                "geopandas is required to write this format. Install extras: pip install geoprompt[io,compare]"
            ) from exc

        collection = frame_to_geojson(frame, geometry=geometry, id_column=id_column)
        gdf = gpd.GeoDataFrame.from_features(collection["features"], crs=frame.crs)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        to_file_kwargs: dict[str, Any] = {}
        if layer is not None:
            to_file_kwargs["layer"] = layer
        if driver is not None:
            to_file_kwargs["driver"] = driver
        gdf.to_file(output_path, **to_file_kwargs)
        return output_path

    raise ValueError(f"unsupported output format for path: {output_path}")


__all__ = [
    "frame_to_geojson",
    "iter_data",
    "read_data",
    "read_features",
    "read_geojson",
    "read_points",
    "read_table",
    "write_data",
    "write_geojson",
    "write_json",
]