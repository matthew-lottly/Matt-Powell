import csv
import io
import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from spatial_data_api.core.config import get_settings
from spatial_data_api.database import get_engine
from spatial_data_api.schemas import (
    FeatureCollection,
    FeatureRecord,
    FeatureSummary,
    ObservationCollection,
    ObservationExportBundle,
    ObservationExportFilters,
    ObservationExportSource,
    ObservationRecord,
    ObservationSummary,
    OperationsSummary,
    OperationsSummaryAlertRecord,
    OperationsSummaryRegionalAlert,
    StationThreshold,
    StationThresholdUpdate,
)


def _build_observation_summary(
    observations: list[ObservationRecord],
    category_lookup: dict[str, str],
) -> ObservationSummary:
    categories: dict[str, int] = {}
    statuses: dict[str, int] = {}
    metrics: dict[str, int] = {}
    timestamps = [observation.observed_at for observation in observations]

    for observation in observations:
        category = category_lookup.get(observation.feature_id, "unknown")
        categories[category] = categories.get(category, 0) + 1
        statuses[observation.status] = statuses.get(observation.status, 0) + 1
        metrics[observation.metric_name] = metrics.get(observation.metric_name, 0) + 1

    return ObservationSummary(
        totalObservations=len(observations),
        categories=dict(sorted(categories.items())),
        statuses=dict(sorted(statuses.items())),
        metrics=dict(sorted(metrics.items())),
        earliestObservedAt=min(timestamps, default=None),
        latestObservedAt=max(timestamps, default=None),
    )


def _default_thresholds() -> dict[str, StationThreshold]:
    return {
        "station-001": StationThreshold(featureId="station-001", metricName="river_stage_ft", maxValue=13.0),
        "station-002": StationThreshold(featureId="station-002", metricName="pm25", maxValue=35.0),
        "station-003": StationThreshold(featureId="station-003", metricName="dissolved_oxygen", minValue=4.0),
    }


def _normalize_bbox(
    min_longitude: float | None,
    min_latitude: float | None,
    max_longitude: float | None,
    max_latitude: float | None,
) -> tuple[float, float, float, float] | None:
    values = (min_longitude, min_latitude, max_longitude, max_latitude)
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise ValueError("All bounding-box coordinates must be provided together")
    assert min_longitude is not None
    assert min_latitude is not None
    assert max_longitude is not None
    assert max_latitude is not None
    if min_longitude >= max_longitude or min_latitude >= max_latitude:
        raise ValueError("Bounding-box minimums must be less than maximums")
    return (min_longitude, min_latitude, max_longitude, max_latitude)


def _feature_in_bbox(feature: FeatureRecord, bbox: tuple[float, float, float, float] | None) -> bool:
    if bbox is None:
        return True
    longitude, latitude = feature.geometry.coordinates[:2]
    min_longitude, min_latitude, max_longitude, max_latitude = bbox
    return min_longitude <= longitude <= max_longitude and min_latitude <= latitude <= max_latitude


class FeatureRepository:
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self.observations_path = data_path.with_name("sample_observations.json")
        self._collection = self._load_collection()
        self._observations = self._load_observations()
        self._thresholds = _default_thresholds()
        self._latest_observations = self._build_latest_observation_lookup(self._observations.observations)

    def _load_collection(self) -> FeatureCollection:
        payload = json.loads(self.data_path.read_text(encoding="utf-8"))
        return FeatureCollection.model_validate(payload)

    def _load_observations(self) -> ObservationCollection:
        payload = json.loads(self.observations_path.read_text(encoding="utf-8"))
        return ObservationCollection.model_validate(payload)

    def list_features(
        self,
        category: str | None = None,
        region: str | None = None,
        status: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> list[FeatureRecord]:
        features = [self._apply_feature_status(feature) for feature in self._collection.features]
        if category:
            features = [feature for feature in features if feature.properties.category.lower() == category.lower()]
        if region:
            features = [feature for feature in features if feature.properties.region.lower() == region.lower()]
        if status:
            features = [feature for feature in features if feature.properties.status.lower() == status.lower()]
        if bbox is not None:
            features = [feature for feature in features if _feature_in_bbox(feature, bbox)]
        return features

    def get_feature(self, feature_id: str) -> FeatureRecord | None:
        feature = next(
            (feature for feature in self._collection.features if feature.properties.feature_id == feature_id),
            None,
        )
        if feature is None:
            return None
        return self._apply_feature_status(feature)

    def update_threshold(self, feature_id: str, threshold: StationThresholdUpdate) -> StationThreshold:
        station_threshold = StationThreshold(
            featureId=feature_id,
            metricName=threshold.metric_name,
            minValue=threshold.min_value,
            maxValue=threshold.max_value,
        )
        self._thresholds[feature_id] = station_threshold
        return station_threshold

    def list_recent_observations(
        self,
        limit: int = 5,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[ObservationRecord]:
        observations = self._filter_observations(start_at=start_at, end_at=end_at)
        observations.sort(key=lambda observation: self._parse_timestamp(observation.observed_at), reverse=True)
        return observations[:limit]

    def list_feature_observations(
        self,
        feature_id: str,
        limit: int = 10,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[ObservationRecord]:
        observations = self._filter_observations(feature_ids={feature_id}, start_at=start_at, end_at=end_at)
        observations.sort(key=lambda observation: self._parse_timestamp(observation.observed_at), reverse=True)
        return observations[:limit]

    def list_thresholds(self, feature_ids: set[str] | None = None) -> list[StationThreshold]:
        thresholds = self._thresholds.values()
        if feature_ids is not None:
            thresholds = [threshold for threshold in thresholds if threshold.feature_id in feature_ids]
        return sorted(thresholds, key=lambda threshold: threshold.feature_id)

    def export_observations(
        self,
        category: str | None = None,
        region: str | None = None,
        status: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> ObservationExportBundle:
        features = self.list_features(category=category, region=region, status=status, bbox=bbox)
        feature_ids = {feature.properties.feature_id for feature in features}
        observations = self._filter_observations(feature_ids=feature_ids, start_at=start_at, end_at=end_at)
        observations.sort(key=lambda observation: self._parse_timestamp(observation.observed_at), reverse=True)
        return ObservationExportBundle(
            source=ObservationExportSource(
                name="environmental-monitoring-api",
                exportedAt=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                dataSource=self.data_source_name(),
            ),
            filters=ObservationExportFilters(
                category=category,
                region=region,
                status=status,
                startAt=start_at.isoformat().replace("+00:00", "Z") if start_at is not None else None,
                endAt=end_at.isoformat().replace("+00:00", "Z") if end_at is not None else None,
                bbox=list(bbox) if bbox is not None else None,
            ),
            features=FeatureCollection(features=features),
            observations=ObservationCollection(
                observations=observations,
                summary=self.observation_summary(observations),
            ),
            thresholds=self.list_thresholds(feature_ids),
        )

    def export_observations_csv(
        self,
        category: str | None = None,
        region: str | None = None,
        status: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> str:
        bundle = self.export_observations(
            category=category,
            region=region,
            status=status,
            bbox=bbox,
            start_at=start_at,
            end_at=end_at,
        )
        feature_lookup = {
            feature.properties.feature_id: feature
            for feature in bundle.features.features
        }
        threshold_lookup = {threshold.feature_id: threshold for threshold in bundle.thresholds}

        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "observation_id",
                "feature_id",
                "station_name",
                "category",
                "region",
                "observed_at",
                "metric_name",
                "value",
                "unit",
                "status",
                "min_threshold",
                "max_threshold",
            ],
        )
        writer.writeheader()
        for observation in bundle.observations.observations:
            feature = feature_lookup.get(observation.feature_id)
            threshold = threshold_lookup.get(observation.feature_id)
            writer.writerow(
                {
                    "observation_id": observation.observation_id,
                    "feature_id": observation.feature_id,
                    "station_name": feature.properties.name if feature is not None else "",
                    "category": feature.properties.category if feature is not None else "",
                    "region": feature.properties.region if feature is not None else "",
                    "observed_at": observation.observed_at,
                    "metric_name": observation.metric_name,
                    "value": observation.value,
                    "unit": observation.unit,
                    "status": observation.status,
                    "min_threshold": threshold.min_value if threshold is not None else "",
                    "max_threshold": threshold.max_value if threshold is not None else "",
                }
            )
        return buffer.getvalue()

    def observation_summary(self, observations: list[ObservationRecord]) -> ObservationSummary:
        category_lookup = {
            feature.properties.feature_id: feature.properties.category for feature in self._collection.features
        }
        return _build_observation_summary(observations, category_lookup)

    def operations_summary(
        self,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> OperationsSummary:
        features = self.list_features()
        feature_lookup = {feature.properties.feature_id: feature for feature in features}
        observations = [
            observation
            for observation in self._observations.observations
            if self._matches_time_window(observation, start_at=start_at, end_at=end_at)
        ]
        recent_alerts = [observation for observation in observations if observation.status == "alert"]
        recent_alerts.sort(key=lambda observation: self._parse_timestamp(observation.observed_at), reverse=True)

        regional_alerts: list[OperationsSummaryRegionalAlert] = []
        for region in sorted({feature.properties.region for feature in features}):
            alert_features = sum(
                1
                for feature in features
                if feature.properties.region == region and feature.properties.status == "alert"
            )
            alert_observations = sum(
                1
                for observation in recent_alerts
                if feature_lookup.get(observation.feature_id, feature_lookup.get(observation.feature_id))
                and feature_lookup[observation.feature_id].properties.region == region
            )
            regional_alerts.append(
                OperationsSummaryRegionalAlert(
                    region=region,
                    alertFeatures=alert_features,
                    alertObservations=alert_observations,
                )
            )

        return OperationsSummary(
            totalFeatures=len(features),
            alertFeatures=sum(1 for feature in features if feature.properties.status == "alert"),
            offlineFeatures=sum(1 for feature in features if feature.properties.status == "offline"),
            alertRate=round(
                sum(1 for feature in features if feature.properties.status == "alert") / len(features),
                4,
            ) if features else 0.0,
            regionalAlerts=regional_alerts,
            recentAlerts=[
                OperationsSummaryAlertRecord(
                    observationId=observation.observation_id,
                    featureId=observation.feature_id,
                    stationName=feature_lookup[observation.feature_id].properties.name,
                    region=feature_lookup[observation.feature_id].properties.region,
                    category=feature_lookup[observation.feature_id].properties.category,
                    observedAt=observation.observed_at,
                    metricName=observation.metric_name,
                    value=observation.value,
                    unit=observation.unit,
                    alertScore=self._alert_score_for_observation(observation),
                )
                for observation in recent_alerts[:5]
                if observation.feature_id in feature_lookup
            ],
            startAt=start_at.isoformat().replace("+00:00", "Z") if start_at is not None else None,
            endAt=end_at.isoformat().replace("+00:00", "Z") if end_at is not None else None,
        )

    def summary(self) -> FeatureSummary:
        categories: dict[str, int] = {}
        statuses: dict[str, int] = {}
        regions: set[str] = set()
        for feature in self.list_features():
            categories[feature.properties.category] = categories.get(feature.properties.category, 0) + 1
            statuses[feature.properties.status] = statuses.get(feature.properties.status, 0) + 1
            regions.add(feature.properties.region)
        return FeatureSummary(
            total_features=len(self._collection.features),
            categories=categories,
            statuses=statuses,
            regions=sorted(regions),
        )

    def is_ready(self) -> bool:
        return self.data_path.exists() and self.observations_path.exists()

    def data_source_name(self) -> str:
        return self.data_path.name

    def _alert_score_for_observation(self, observation: ObservationRecord) -> float:
        threshold = self._thresholds.get(observation.feature_id)
        if threshold is None or threshold.metric_name != observation.metric_name:
            return 1.0 if observation.status == "alert" else 0.0

        if threshold.max_value is not None and observation.value > threshold.max_value:
            return round(observation.value / threshold.max_value, 2)
        if threshold.min_value is not None and observation.value < threshold.min_value and observation.value != 0:
            return round(threshold.min_value / observation.value, 2)
        if threshold.min_value is not None and observation.value <= 0:
            return 1.0
        return 0.0

    @staticmethod
    def _build_latest_observation_lookup(
        observations: list[ObservationRecord],
    ) -> dict[str, ObservationRecord]:
        latest: dict[str, ObservationRecord] = {}
        for observation in sorted(
            observations,
            key=lambda current: FeatureRepository._parse_timestamp(current.observed_at),
            reverse=True,
        ):
            latest.setdefault(observation.feature_id, observation)
        return latest

    def _apply_feature_status(self, feature: FeatureRecord) -> FeatureRecord:
        latest_observation = self._latest_observations.get(feature.properties.feature_id)
        derived_status = self._derive_feature_status(feature, latest_observation)
        return FeatureRecord.model_validate(
            {
                "type": feature.type,
                "properties": {
                    "featureId": feature.properties.feature_id,
                    "name": feature.properties.name,
                    "category": feature.properties.category,
                    "region": feature.properties.region,
                    "status": derived_status,
                    "lastObservationAt": feature.properties.last_observation_at,
                },
                "geometry": {
                    "type": feature.geometry.type,
                    "coordinates": feature.geometry.coordinates,
                },
            }
        )

    def _derive_feature_status(
        self,
        feature: FeatureRecord,
        latest_observation: ObservationRecord | None,
    ) -> str:
        if latest_observation is None:
            return feature.properties.status
        if latest_observation.status == "offline":
            return "offline"

        threshold = self._thresholds.get(feature.properties.feature_id)
        if threshold is None or threshold.metric_name != latest_observation.metric_name:
            return feature.properties.status

        below_min = threshold.min_value is not None and latest_observation.value < threshold.min_value
        above_max = threshold.max_value is not None and latest_observation.value > threshold.max_value
        return "alert" if below_min or above_max else "normal"

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def _matches_time_window(
        self,
        observation: ObservationRecord,
        start_at: datetime | None,
        end_at: datetime | None,
    ) -> bool:
        observed_at = self._parse_timestamp(observation.observed_at)
        if start_at is not None and observed_at < start_at:
            return False
        if end_at is not None and observed_at > end_at:
            return False
        return True

    def _filter_observations(
        self,
        feature_ids: set[str] | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[ObservationRecord]:
        return [
            observation
            for observation in self._observations.observations
            if (feature_ids is None or observation.feature_id in feature_ids)
            and self._matches_time_window(observation, start_at=start_at, end_at=end_at)
        ]


class PostGISFeatureRepository:
    def __init__(self, database_url: str):
        self.engine = get_engine(database_url)
        self._thresholds = _default_thresholds()

    def list_features(
        self,
        category: str | None = None,
        region: str | None = None,
        status: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> list[FeatureRecord]:
        query = """
        SELECT
            feature_id,
            name,
            category,
            region,
            status,
            TO_CHAR(last_observation_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS last_observation_at,
            ST_X(geometry) AS longitude,
            ST_Y(geometry) AS latitude
        FROM public.monitoring_stations
        WHERE (:category IS NULL OR category = :category)
          AND (:region IS NULL OR region = :region)
          AND (
            :min_longitude IS NULL
            OR ST_X(geometry) BETWEEN :min_longitude AND :max_longitude
          )
          AND (
            :min_latitude IS NULL
            OR ST_Y(geometry) BETWEEN :min_latitude AND :max_latitude
          )
        ORDER BY feature_id
        """
        bbox_params = {
            "min_longitude": bbox[0] if bbox is not None else None,
            "min_latitude": bbox[1] if bbox is not None else None,
            "max_longitude": bbox[2] if bbox is not None else None,
            "max_latitude": bbox[3] if bbox is not None else None,
        }
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(query),
                {"category": category, "region": region, **bbox_params},
            ).mappings().all()
        features = [self._apply_feature_status(self._row_to_feature(dict(row))) for row in rows]
        if status:
            features = [feature for feature in features if feature.properties.status.lower() == status.lower()]
        return features

    def get_feature(self, feature_id: str) -> FeatureRecord | None:
        query = """
        SELECT
            feature_id,
            name,
            category,
            region,
            status,
            TO_CHAR(last_observation_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS last_observation_at,
            ST_X(geometry) AS longitude,
            ST_Y(geometry) AS latitude
        FROM public.monitoring_stations
        WHERE feature_id = :feature_id
        """
        with self.engine.connect() as connection:
            row = connection.execute(text(query), {"feature_id": feature_id}).mappings().first()
        if row is None:
            return None
        return self._apply_feature_status(self._row_to_feature(dict(row)))

    def update_threshold(self, feature_id: str, threshold: StationThresholdUpdate) -> StationThreshold:
        station_threshold = StationThreshold(
            featureId=feature_id,
            metricName=threshold.metric_name,
            minValue=threshold.min_value,
            maxValue=threshold.max_value,
        )
        self._thresholds[feature_id] = station_threshold
        return station_threshold

    def list_recent_observations(
        self,
        limit: int = 5,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[ObservationRecord]:
        query = """
        SELECT
            observation_id,
            feature_id,
            TO_CHAR(observed_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS observed_at,
            metric_name,
            value,
            unit,
            status
        FROM public.monitoring_observations
        WHERE (:start_at IS NULL OR observed_at >= :start_at)
          AND (:end_at IS NULL OR observed_at <= :end_at)
        ORDER BY observed_at DESC, observation_id DESC
        LIMIT :limit
        """
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(query),
                {"limit": limit, "start_at": start_at, "end_at": end_at},
            ).mappings().all()
        return [self._row_to_observation(dict(row)) for row in rows]

    def list_feature_observations(
        self,
        feature_id: str,
        limit: int = 10,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[ObservationRecord]:
        query = """
        SELECT
            observation_id,
            feature_id,
            TO_CHAR(observed_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS observed_at,
            metric_name,
            value,
            unit,
            status
        FROM public.monitoring_observations
        WHERE feature_id = :feature_id
          AND (:start_at IS NULL OR observed_at >= :start_at)
          AND (:end_at IS NULL OR observed_at <= :end_at)
        ORDER BY observed_at DESC, observation_id DESC
        LIMIT :limit
        """
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(query),
                {"feature_id": feature_id, "limit": limit, "start_at": start_at, "end_at": end_at},
            ).mappings().all()
        return [self._row_to_observation(dict(row)) for row in rows]

    def observation_summary(self, observations: list[ObservationRecord]) -> ObservationSummary:
        category_lookup = {
            feature.properties.feature_id: feature.properties.category for feature in self.list_features()
        }
        return _build_observation_summary(observations, category_lookup)

    def list_thresholds(self, feature_ids: set[str] | None = None) -> list[StationThreshold]:
        thresholds = self._thresholds.values()
        if feature_ids is not None:
            thresholds = [threshold for threshold in thresholds if threshold.feature_id in feature_ids]
        return sorted(thresholds, key=lambda threshold: threshold.feature_id)

    def export_observations(
        self,
        category: str | None = None,
        region: str | None = None,
        status: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> ObservationExportBundle:
        features = self.list_features(category=category, region=region, status=status, bbox=bbox)
        feature_ids = {feature.properties.feature_id for feature in features}
        observations = [
            observation
            for observation in self._list_observations(start_at=start_at, end_at=end_at)
            if observation.feature_id in feature_ids
        ]
        return ObservationExportBundle(
            source=ObservationExportSource(
                name="environmental-monitoring-api",
                exportedAt=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                dataSource=self.data_source_name(),
            ),
            filters=ObservationExportFilters(
                category=category,
                region=region,
                status=status,
                startAt=start_at.isoformat().replace("+00:00", "Z") if start_at is not None else None,
                endAt=end_at.isoformat().replace("+00:00", "Z") if end_at is not None else None,
                bbox=list(bbox) if bbox is not None else None,
            ),
            features=FeatureCollection(features=features),
            observations=ObservationCollection(
                observations=observations,
                summary=self.observation_summary(observations),
            ),
            thresholds=self.list_thresholds(feature_ids),
        )

    def export_observations_csv(
        self,
        category: str | None = None,
        region: str | None = None,
        status: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> str:
        bundle = self.export_observations(
            category=category,
            region=region,
            status=status,
            bbox=bbox,
            start_at=start_at,
            end_at=end_at,
        )
        feature_lookup = {
            feature.properties.feature_id: feature
            for feature in bundle.features.features
        }
        threshold_lookup = {threshold.feature_id: threshold for threshold in bundle.thresholds}

        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "observation_id",
                "feature_id",
                "station_name",
                "category",
                "region",
                "observed_at",
                "metric_name",
                "value",
                "unit",
                "status",
                "min_threshold",
                "max_threshold",
            ],
        )
        writer.writeheader()
        for observation in bundle.observations.observations:
            feature = feature_lookup.get(observation.feature_id)
            threshold = threshold_lookup.get(observation.feature_id)
            writer.writerow(
                {
                    "observation_id": observation.observation_id,
                    "feature_id": observation.feature_id,
                    "station_name": feature.properties.name if feature is not None else "",
                    "category": feature.properties.category if feature is not None else "",
                    "region": feature.properties.region if feature is not None else "",
                    "observed_at": observation.observed_at,
                    "metric_name": observation.metric_name,
                    "value": observation.value,
                    "unit": observation.unit,
                    "status": observation.status,
                    "min_threshold": threshold.min_value if threshold is not None else "",
                    "max_threshold": threshold.max_value if threshold is not None else "",
                }
            )
        return buffer.getvalue()

    def operations_summary(
        self,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> OperationsSummary:
        features = self.list_features()
        feature_lookup = {feature.properties.feature_id: feature for feature in features}
        observations = self._list_observations(start_at=start_at, end_at=end_at)
        recent_alerts = [observation for observation in observations if observation.status == "alert"]

        regional_alerts: list[OperationsSummaryRegionalAlert] = []
        for region in sorted({feature.properties.region for feature in features}):
            alert_features = sum(
                1
                for feature in features
                if feature.properties.region == region and feature.properties.status == "alert"
            )
            alert_observations = sum(
                1
                for observation in recent_alerts
                if observation.feature_id in feature_lookup and feature_lookup[observation.feature_id].properties.region == region
            )
            regional_alerts.append(
                OperationsSummaryRegionalAlert(
                    region=region,
                    alertFeatures=alert_features,
                    alertObservations=alert_observations,
                )
            )

        return OperationsSummary(
            totalFeatures=len(features),
            alertFeatures=sum(1 for feature in features if feature.properties.status == "alert"),
            offlineFeatures=sum(1 for feature in features if feature.properties.status == "offline"),
            alertRate=round(
                sum(1 for feature in features if feature.properties.status == "alert") / len(features),
                4,
            ) if features else 0.0,
            regionalAlerts=regional_alerts,
            recentAlerts=[
                OperationsSummaryAlertRecord(
                    observationId=observation.observation_id,
                    featureId=observation.feature_id,
                    stationName=feature_lookup[observation.feature_id].properties.name,
                    region=feature_lookup[observation.feature_id].properties.region,
                    category=feature_lookup[observation.feature_id].properties.category,
                    observedAt=observation.observed_at,
                    metricName=observation.metric_name,
                    value=observation.value,
                    unit=observation.unit,
                    alertScore=self._alert_score_for_observation(observation),
                )
                for observation in recent_alerts[:5]
                if observation.feature_id in feature_lookup
            ],
            startAt=start_at.isoformat().replace("+00:00", "Z") if start_at is not None else None,
            endAt=end_at.isoformat().replace("+00:00", "Z") if end_at is not None else None,
        )

    def summary(self) -> FeatureSummary:
        categories: dict[str, int] = {}
        statuses: dict[str, int] = {}
        regions: set[str] = set()
        features = self.list_features()
        for feature in features:
            categories[feature.properties.category] = categories.get(feature.properties.category, 0) + 1
            statuses[feature.properties.status] = statuses.get(feature.properties.status, 0) + 1
            regions.add(feature.properties.region)
        return FeatureSummary(
            total_features=len(features),
            categories=categories,
            statuses=statuses,
            regions=sorted(regions),
        )

    def is_ready(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1 FROM public.monitoring_stations LIMIT 1"))
                connection.execute(text("SELECT 1 FROM public.monitoring_observations LIMIT 1"))
            return True
        except SQLAlchemyError:
            return False

    @staticmethod
    def data_source_name() -> str:
        return "monitoring_stations"

    def _list_observations(
        self,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[ObservationRecord]:
        query = """
        SELECT
            observation_id,
            feature_id,
            TO_CHAR(observed_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS observed_at,
            metric_name,
            value,
            unit,
            status
        FROM public.monitoring_observations
        WHERE (:start_at IS NULL OR observed_at >= :start_at)
          AND (:end_at IS NULL OR observed_at <= :end_at)
        ORDER BY observed_at DESC, observation_id DESC
        """
        with self.engine.connect() as connection:
            rows = connection.execute(text(query), {"start_at": start_at, "end_at": end_at}).mappings().all()
        return [self._row_to_observation(dict(row)) for row in rows]

    def _alert_score_for_observation(self, observation: ObservationRecord) -> float:
        threshold = self._thresholds.get(observation.feature_id)
        if threshold is None or threshold.metric_name != observation.metric_name:
            return 1.0 if observation.status == "alert" else 0.0

        if threshold.max_value is not None and observation.value > threshold.max_value:
            return round(observation.value / threshold.max_value, 2)
        if threshold.min_value is not None and observation.value < threshold.min_value and observation.value != 0:
            return round(threshold.min_value / observation.value, 2)
        if threshold.min_value is not None and observation.value <= 0:
            return 1.0
        return 0.0

    def _apply_feature_status(self, feature: FeatureRecord) -> FeatureRecord:
        latest_observation = self._latest_observation_for_feature(feature.properties.feature_id)
        derived_status = self._derive_feature_status(feature, latest_observation)
        return FeatureRecord.model_validate(
            {
                "type": feature.type,
                "properties": {
                    "featureId": feature.properties.feature_id,
                    "name": feature.properties.name,
                    "category": feature.properties.category,
                    "region": feature.properties.region,
                    "status": derived_status,
                    "lastObservationAt": feature.properties.last_observation_at,
                },
                "geometry": {
                    "type": feature.geometry.type,
                    "coordinates": feature.geometry.coordinates,
                },
            }
        )

    def _latest_observation_for_feature(self, feature_id: str) -> ObservationRecord | None:
        observations = self.list_feature_observations(feature_id=feature_id, limit=1)
        if not observations:
            return None
        return observations[0]

    def _derive_feature_status(
        self,
        feature: FeatureRecord,
        latest_observation: ObservationRecord | None,
    ) -> str:
        if latest_observation is None:
            return feature.properties.status
        if latest_observation.status == "offline":
            return "offline"

        threshold = self._thresholds.get(feature.properties.feature_id)
        if threshold is None or threshold.metric_name != latest_observation.metric_name:
            return feature.properties.status

        below_min = threshold.min_value is not None and latest_observation.value < threshold.min_value
        above_max = threshold.max_value is not None and latest_observation.value > threshold.max_value
        return "alert" if below_min or above_max else "normal"

    @staticmethod
    def _row_to_feature(row: dict[str, object]) -> FeatureRecord:
        return FeatureRecord.model_validate(
            {
                "type": "Feature",
                "properties": {
                    "featureId": row["feature_id"],
                    "name": row["name"],
                    "category": row["category"],
                    "region": row["region"],
                    "status": row["status"],
                    "lastObservationAt": row["last_observation_at"],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [row["longitude"], row["latitude"]],
                },
            }
        )

    @staticmethod
    def _row_to_observation(row: dict[str, object]) -> ObservationRecord:
        return ObservationRecord.model_validate(
            {
                "observationId": row["observation_id"],
                "featureId": row["feature_id"],
                "observedAt": row["observed_at"],
                "metricName": row["metric_name"],
                "value": row["value"],
                "unit": row["unit"],
                "status": row["status"],
            }
        )


class Repository(Protocol):
    def is_ready(self) -> bool: ...

    def data_source_name(self) -> str: ...

    def list_features(
        self,
        category: str | None = None,
        region: str | None = None,
        status: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> list[FeatureRecord]: ...

    def summary(self) -> FeatureSummary: ...

    def operations_summary(
        self,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> OperationsSummary: ...

    def list_recent_observations(
        self,
        limit: int = 5,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[ObservationRecord]: ...

    def observation_summary(self, observations: list[ObservationRecord]) -> ObservationSummary: ...

    def export_observations(
        self,
        category: str | None = None,
        region: str | None = None,
        status: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> ObservationExportBundle: ...

    def export_observations_csv(
        self,
        category: str | None = None,
        region: str | None = None,
        status: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> str: ...

    def get_feature(self, feature_id: str) -> FeatureRecord | None: ...

    def list_feature_observations(
        self,
        feature_id: str,
        limit: int = 10,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
    ) -> list[ObservationRecord]: ...

    def update_threshold(self, feature_id: str, threshold: StationThresholdUpdate) -> StationThreshold: ...


@lru_cache
def get_repository() -> Repository:
    settings = get_settings()
    if settings.repository_backend == "postgis":
        return PostGISFeatureRepository(settings.database_url)
    return FeatureRepository(settings.data_path)