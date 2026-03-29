from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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


class StationThresholdUpdate(BaseModel):
    metric_name: str = Field(alias="metricName")
    min_value: float | None = Field(default=None, alias="minValue")
    max_value: float | None = Field(default=None, alias="maxValue")

    @model_validator(mode="after")
    def validate_threshold_bounds(self) -> "StationThresholdUpdate":
        if self.min_value is None and self.max_value is None:
            raise ValueError("At least one threshold bound must be provided")
        if self.min_value is not None and self.max_value is not None and self.min_value >= self.max_value:
            raise ValueError("minValue must be less than maxValue")
        return self


class StationThreshold(StationThresholdUpdate):
    feature_id: str = Field(alias="featureId")


class ObservationExportSource(BaseModel):
    name: str
    exported_at: str = Field(alias="exportedAt")
    data_source: str = Field(alias="dataSource")


class ObservationExportFilters(BaseModel):
    category: str | None = None
    region: str | None = None
    status: str | None = None
    start_at: str | None = Field(default=None, alias="startAt")
    end_at: str | None = Field(default=None, alias="endAt")
    bbox: list[float] | None = None


class ObservationExportBundle(BaseModel):
    source: ObservationExportSource
    filters: ObservationExportFilters
    features: FeatureCollection
    observations: ObservationCollection
    thresholds: list[StationThreshold]


class OperationsSummaryRegionalAlert(BaseModel):
    region: str
    alert_features: int = Field(alias="alertFeatures")
    alert_observations: int = Field(alias="alertObservations")


class OperationsSummaryAlertRecord(BaseModel):
    observation_id: str = Field(alias="observationId")
    feature_id: str = Field(alias="featureId")
    station_name: str = Field(alias="stationName")
    region: str
    category: str
    observed_at: str = Field(alias="observedAt")
    metric_name: str = Field(alias="metricName")
    value: float
    unit: str
    alert_score: float = Field(alias="alertScore")


class OperationsSummary(BaseModel):
    total_features: int = Field(alias="totalFeatures")
    alert_features: int = Field(alias="alertFeatures")
    offline_features: int = Field(alias="offlineFeatures")
    alert_rate: float = Field(alias="alertRate")
    regional_alerts: list[OperationsSummaryRegionalAlert] = Field(alias="regionalAlerts")
    recent_alerts: list[OperationsSummaryAlertRecord] = Field(alias="recentAlerts")
    start_at: str | None = Field(default=None, alias="startAt")
    end_at: str | None = Field(default=None, alias="endAt")


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