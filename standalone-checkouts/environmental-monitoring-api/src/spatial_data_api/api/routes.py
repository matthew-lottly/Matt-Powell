from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

import spatial_data_api.schemas as api_schemas
from spatial_data_api.core.config import get_settings
from spatial_data_api.repository import Repository, get_repository
from spatial_data_api.schemas import (
    FeatureCollection,
    FeatureRecord,
    FeatureSummary,
    HealthStatus,
    ObservationCollection,
    OperationsSummary,
    ServiceMetadata,
    StationThreshold,
    StationThresholdUpdate,
)


settings = get_settings()
router = APIRouter()


def _build_bbox(
    min_longitude: float | None,
    min_latitude: float | None,
    max_longitude: float | None,
    max_latitude: float | None,
) -> tuple[float, float, float, float] | None:
    values = (min_longitude, min_latitude, max_longitude, max_latitude)
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise HTTPException(status_code=422, detail="All bounding-box coordinates must be provided together")
    assert min_longitude is not None
    assert min_latitude is not None
    assert max_longitude is not None
    assert max_latitude is not None
    if min_longitude >= max_longitude or min_latitude >= max_latitude:
        raise HTTPException(status_code=422, detail="Bounding-box minimums must be less than maximums")
    return (min_longitude, min_latitude, max_longitude, max_latitude)


def build_health_status(repository: Repository) -> HealthStatus:
    ready = repository.is_ready()
    return HealthStatus(
        status="ok" if ready else "degraded",
        backend=settings.repository_backend,
        ready=ready,
        data_source=repository.data_source_name(),
    )


@router.get("/health", response_model=HealthStatus, tags=["health"])
def healthcheck(repository: Repository = Depends(get_repository)) -> HealthStatus:
    return build_health_status(repository)


@router.get("/health/ready", response_model=HealthStatus, tags=["health"])
def readiness_check(repository: Repository = Depends(get_repository)) -> HealthStatus:
    return build_health_status(repository)


@router.get(f"{settings.api_prefix}/metadata", response_model=ServiceMetadata, tags=["metadata"])
def get_metadata(repository: Repository = Depends(get_repository)) -> ServiceMetadata:
    return ServiceMetadata(
        name=settings.app_name,
        version="0.1.0",
        environment=settings.app_env,
        backend=settings.repository_backend,
        feature_count=len(repository.list_features()),
        data_source=repository.data_source_name(),
    )


@router.get(f"{settings.api_prefix}/features", response_model=FeatureCollection, tags=["features"])
def list_features(
    category: str | None = Query(default=None),
    region: str | None = Query(default=None),
    status: str | None = Query(default=None),
    min_longitude: float | None = Query(default=None, alias="min_longitude"),
    min_latitude: float | None = Query(default=None, alias="min_latitude"),
    max_longitude: float | None = Query(default=None, alias="max_longitude"),
    max_latitude: float | None = Query(default=None, alias="max_latitude"),
    repository: Repository = Depends(get_repository),
) -> FeatureCollection:
    bbox = _build_bbox(min_longitude, min_latitude, max_longitude, max_latitude)
    return FeatureCollection(features=repository.list_features(category=category, region=region, status=status, bbox=bbox))


@router.get(
    f"{settings.api_prefix}/features/summary",
    response_model=FeatureSummary,
    tags=["features"],
)
def get_feature_summary(repository: Repository = Depends(get_repository)) -> FeatureSummary:
    return repository.summary()


@router.get(
    f"{settings.api_prefix}/summary",
    response_model=OperationsSummary,
    tags=["features"],
)
def get_operations_summary(
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
    repository: Repository = Depends(get_repository),
) -> OperationsSummary:
    return repository.operations_summary(start_at=start_at, end_at=end_at)


@router.get(
    f"{settings.api_prefix}/observations/recent",
    response_model=ObservationCollection,
    tags=["observations"],
)
def get_recent_observations(
    limit: int = Query(default=5, ge=1, le=50),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
    repository: Repository = Depends(get_repository),
) -> ObservationCollection:
    observations = repository.list_recent_observations(limit=limit, start_at=start_at, end_at=end_at)
    return ObservationCollection(observations=observations, summary=repository.observation_summary(observations))


@router.get(
    f"{settings.api_prefix}/observations/export",
    response_model=api_schemas.ObservationExportBundle,
    tags=["observations"],
)
def export_observations(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    category: str | None = Query(default=None),
    region: str | None = Query(default=None),
    status: str | None = Query(default=None),
    min_longitude: float | None = Query(default=None, alias="min_longitude"),
    min_latitude: float | None = Query(default=None, alias="min_latitude"),
    max_longitude: float | None = Query(default=None, alias="max_longitude"),
    max_latitude: float | None = Query(default=None, alias="max_latitude"),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
    repository: Repository = Depends(get_repository),
) -> api_schemas.ObservationExportBundle | PlainTextResponse:
    bbox = _build_bbox(min_longitude, min_latitude, max_longitude, max_latitude)
    if format == "csv":
        return PlainTextResponse(
            repository.export_observations_csv(
                category=category,
                region=region,
                status=status,
                bbox=bbox,
                start_at=start_at,
                end_at=end_at,
            ),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="monitoring-observations.csv"'},
        )
    return repository.export_observations(
        category=category,
        region=region,
        status=status,
        bbox=bbox,
        start_at=start_at,
        end_at=end_at,
    )


@router.get(
    f"{settings.api_prefix}/features/{{feature_id}}",
    response_model=FeatureRecord,
    tags=["features"],
)
def get_feature(feature_id: str, repository: Repository = Depends(get_repository)) -> FeatureRecord:
    feature = repository.get_feature(feature_id)
    if feature is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature


@router.get(
    f"{settings.api_prefix}/features/{{feature_id}}/observations",
    response_model=ObservationCollection,
    tags=["observations"],
)
def get_feature_observations(
    feature_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
    repository: Repository = Depends(get_repository),
) -> ObservationCollection:
    feature = repository.get_feature(feature_id)
    if feature is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    observations = repository.list_feature_observations(
        feature_id=feature_id,
        limit=limit,
        start_at=start_at,
        end_at=end_at,
    )
    return ObservationCollection(observations=observations, summary=repository.observation_summary(observations))


@router.post(
    f"{settings.api_prefix}/stations/{{feature_id}}/thresholds",
    response_model=StationThreshold,
    tags=["features"],
)
def upsert_station_threshold(
    feature_id: str,
    threshold: StationThresholdUpdate,
    repository: Repository = Depends(get_repository),
) -> StationThreshold:
    feature = repository.get_feature(feature_id)
    if feature is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    return repository.update_threshold(feature_id, threshold)