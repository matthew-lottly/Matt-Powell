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