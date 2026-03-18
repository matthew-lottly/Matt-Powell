from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from spatial_data_api.core.config import get_settings
from spatial_data_api.repository import Repository, get_repository
from spatial_data_api.schemas import (
    FeatureCollection,
    FeatureRecord,
    FeatureSummary,
    HealthStatus,
    ObservationCollection,
    ServiceMetadata,
)


settings = get_settings()
router = APIRouter()


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
    repository: Repository = Depends(get_repository),
) -> FeatureCollection:
    return FeatureCollection(features=repository.list_features(category=category, region=region, status=status))


@router.get(
    f"{settings.api_prefix}/features/summary",
    response_model=FeatureSummary,
    tags=["features"],
)
def get_feature_summary(repository: Repository = Depends(get_repository)) -> FeatureSummary:
    return repository.summary()


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