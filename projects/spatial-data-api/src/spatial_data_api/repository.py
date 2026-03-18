import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from spatial_data_api.core.config import get_settings
from spatial_data_api.schemas import FeatureCollection, FeatureRecord, FeatureSummary
from spatial_data_api.database import get_engine


class FeatureRepository:
    def __init__(self, data_path: Path):
        self.data_path = data_path
        self._collection = self._load_collection()

    def _load_collection(self) -> FeatureCollection:
        payload = json.loads(self.data_path.read_text(encoding="utf-8"))
        return FeatureCollection.model_validate(payload)

    def list_features(self, category: str | None = None, region: str | None = None) -> list[FeatureRecord]:
        features = self._collection.features
        if category:
            features = [feature for feature in features if feature.properties.category.lower() == category.lower()]
        if region:
            features = [feature for feature in features if feature.properties.region.lower() == region.lower()]
        return features

    def get_feature(self, feature_id: str) -> FeatureRecord | None:
        return next(
            (feature for feature in self._collection.features if feature.properties.feature_id == feature_id),
            None,
        )

    def summary(self) -> FeatureSummary:
        categories: dict[str, int] = {}
        regions: set[str] = set()
        for feature in self._collection.features:
            categories[feature.properties.category] = categories.get(feature.properties.category, 0) + 1
            regions.add(feature.properties.region)
        return FeatureSummary(
            total_features=len(self._collection.features),
            categories=categories,
            regions=sorted(regions),
        )

    def is_ready(self) -> bool:
        return self.data_path.exists()

    def data_source_name(self) -> str:
        return self.data_path.name


class PostGISFeatureRepository:
    def __init__(self, database_url: str):
        self.engine = get_engine(database_url)

    def list_features(self, category: str | None = None, region: str | None = None) -> list[FeatureRecord]:
        query = """
        SELECT
            feature_id,
            name,
            category,
            region,
            ST_X(geometry) AS longitude,
            ST_Y(geometry) AS latitude
        FROM public.spatial_assets
        WHERE (:category IS NULL OR category = :category)
          AND (:region IS NULL OR region = :region)
        ORDER BY feature_id
        """
        with self.engine.connect() as connection:
            rows = connection.execute(text(query), {"category": category, "region": region}).mappings().all()
        return [self._row_to_feature(row) for row in rows]

    def get_feature(self, feature_id: str) -> FeatureRecord | None:
        query = """
        SELECT
            feature_id,
            name,
            category,
            region,
            ST_X(geometry) AS longitude,
            ST_Y(geometry) AS latitude
        FROM public.spatial_assets
        WHERE feature_id = :feature_id
        """
        with self.engine.connect() as connection:
            row = connection.execute(text(query), {"feature_id": feature_id}).mappings().first()
        if row is None:
            return None
        return self._row_to_feature(row)

    def summary(self) -> FeatureSummary:
        category_query = "SELECT category, COUNT(*) AS count FROM public.spatial_assets GROUP BY category ORDER BY category"
        region_query = "SELECT DISTINCT region FROM public.spatial_assets ORDER BY region"
        count_query = "SELECT COUNT(*) AS count FROM public.spatial_assets"
        with self.engine.connect() as connection:
            categories = connection.execute(text(category_query)).mappings().all()
            regions = connection.execute(text(region_query)).scalars().all()
            total_features = connection.execute(text(count_query)).scalar_one()
        return FeatureSummary(
            total_features=total_features,
            categories={row["category"]: row["count"] for row in categories},
            regions=list(regions),
        )

    def is_ready(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1 FROM public.spatial_assets LIMIT 1"))
            return True
        except SQLAlchemyError:
            return False

    @staticmethod
    def data_source_name() -> str:
        return "spatial_assets"

    @staticmethod
    def _row_to_feature(row: dict) -> FeatureRecord:
        return FeatureRecord.model_validate(
            {
                "type": "Feature",
                "properties": {
                    "featureId": row["feature_id"],
                    "name": row["name"],
                    "category": row["category"],
                    "region": row["region"],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [row["longitude"], row["latitude"]],
                },
            }
        )


Repository = FeatureRepository | PostGISFeatureRepository


@lru_cache
def get_repository() -> Repository:
    settings = get_settings()
    if settings.repository_backend == "postgis":
        return PostGISFeatureRepository(settings.database_url)
    return FeatureRepository(settings.data_path)