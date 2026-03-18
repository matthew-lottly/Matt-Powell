from typing import Any, Literal

from pydantic import BaseModel, Field


class Geometry(BaseModel):
    type: str
    coordinates: list[Any]


class FeatureProperties(BaseModel):
    feature_id: str = Field(alias="featureId")
    name: str
    category: str
    region: str
    status: Literal["normal", "alert", "offline"]
    last_observation_at: str = Field(alias="lastObservationAt")


class FeatureRecord(BaseModel):
    type: Literal["Feature"] = "Feature"
    properties: FeatureProperties
    geometry: Geometry


class FeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[FeatureRecord]


class ObservationRecord(BaseModel):
    observation_id: str = Field(alias="observationId")
    feature_id: str = Field(alias="featureId")
    observed_at: str = Field(alias="observedAt")
    metric_name: str = Field(alias="metricName")
    value: float
    unit: str
    status: Literal["normal", "alert", "offline"]


class ObservationSummary(BaseModel):
    total_observations: int = Field(alias="totalObservations")
    categories: dict[str, int]
    statuses: dict[str, int]
    metrics: dict[str, int]
    earliest_observed_at: str | None = Field(default=None, alias="earliestObservedAt")
    latest_observed_at: str | None = Field(default=None, alias="latestObservedAt")


class ObservationCollection(BaseModel):
    observations: list[ObservationRecord]
    summary: ObservationSummary | None = None


class FeatureSummary(BaseModel):
    total_features: int
    categories: dict[str, int]
    statuses: dict[str, int]
    regions: list[str]


class ServiceMetadata(BaseModel):
    name: str
    version: str
    environment: str
    backend: str
    feature_count: int
    data_source: str


class HealthStatus(BaseModel):
    status: str
    backend: str
    ready: bool
    data_source: str