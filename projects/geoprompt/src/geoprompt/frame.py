from __future__ import annotations

import importlib
from dataclasses import dataclass
from heapq import nlargest, nsmallest
from typing import Any, Iterable, Literal, Sequence

from .equations import (
    adaptive_capacity_score,
    accessibility_potential,
    area_similarity,
    climate_vulnerability_index,
    digital_divide_index,
    drought_stress_index,
    emergency_response_score,
    healthcare_access_index,
    heat_island_intensity,
    infrastructure_lifecycle_score,
    community_cohesion_score,
    competitive_influence,
    composite_suitability_score,
    coordinate_distance,
    corridor_reliability_score,
    coverage_equity_score,
    cultural_similarity_index,
    demand_supply_balance_score,
    corridor_strength,
    directional_alignment,
    gentrification_pressure_index,
    gravity_interaction,
    habitat_fragmentation_score,
    hotspot_intensity_score,
    land_value_gradient,
    market_concentration_index,
    migration_attraction_index,
    mortality_risk_index,
    noise_propagation_level,
    pollution_dispersion_model,
    prompt_influence,
    prompt_interaction,
    trade_flow_intensity,
    traffic_congestion_index,
    transit_accessibility_score,
    school_access_score,
    food_desert_risk,
    wildfire_risk_index,
    visual_prominence_score,
    walkability_score,
)
from .geometry import Geometry, geometry_area, geometry_bounds, geometry_centroid, geometry_contains, geometry_distance, geometry_intersects, geometry_intersects_bounds, geometry_length, geometry_type, geometry_within, geometry_within_bounds, normalize_geometry, transform_geometry
from .overlay import buffer_geometries, clip_geometries, dissolve_geometries, overlay_intersections
from .validation import validate_distance_method_crs


Record = dict[str, Any]
BoundsQueryMode = Literal["intersects", "within", "centroid"]
SpatialJoinPredicate = Literal["intersects", "within", "contains"]
SpatialJoinMode = Literal["inner", "left"]
AggregationName = Literal["sum", "mean", "min", "max", "first", "count"]


Coordinate = tuple[float, float]


def _row_sort_key(row: Record) -> str:
    return str(row.get("site_id", row.get("region_id", "")))


def _bounds_intersect(left: tuple[float, float, float, float], right: tuple[float, float, float, float]) -> bool:
    return not (
        left[2] < right[0]
        or left[0] > right[2]
        or left[3] < right[1]
        or left[1] > right[3]
    )


def _bounds_within(candidate: tuple[float, float, float, float], container: tuple[float, float, float, float]) -> bool:
    return (
        candidate[0] >= container[0]
        and candidate[1] >= container[1]
        and candidate[2] <= container[2]
        and candidate[3] <= container[3]
    )


@dataclass(frozen=True)
class Bounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float


class GeoPromptAnalysis:
    """GeoPandas-style analysis namespace for callable frame workflows."""

    def __init__(self, frame: "GeoPromptFrame") -> None:
        self._frame = frame

    @staticmethod
    def _unit(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _distance_from_global_centroid(self, row_centroid: Coordinate, distance_method: str) -> float:
        frame = self._frame
        center = frame.centroid()
        return coordinate_distance(row_centroid, center, method=distance_method)

    def accessibility(
        self,
        opportunities: str,
        id_column: str = "site_id",
        friction: float = 1.0,
        include_self: bool = False,
        distance_method: str = "euclidean",
        max_distance: float | None = None,
    ) -> list[Record]:
        frame = self._frame
        frame._validate_distance_method(distance_method)
        frame._require_column(opportunities)
        frame._require_column(id_column)

        centroids = frame._cached_centroids
        records: list[Record] = []
        for i, origin in enumerate(frame._rows):
            score = 0.0
            for j, destination in enumerate(frame._rows):
                if not include_self and i == j:
                    continue
                dist = coordinate_distance(centroids[i], centroids[j], method=distance_method)
                if max_distance is not None and dist > max_distance:
                    continue
                score += accessibility_potential(
                    weight=float(destination[opportunities]),
                    distance_value=dist,
                    friction=friction,
                )
            records.append(
                {
                    id_column: origin[id_column],
                    "accessibility_score": score,
                    "opportunities_column": opportunities,
                    "distance_method": distance_method,
                }
            )
        return records

    def gravity_flow(
        self,
        origin_weight: str,
        destination_weight: str,
        id_column: str = "site_id",
        beta: float = 2.0,
        offset: float = 1e-6,
        include_self: bool = False,
        distance_method: str = "euclidean",
        max_distance: float | None = None,
        max_results: int | None = None,
    ) -> list[Record]:
        frame = self._frame
        frame._validate_distance_method(distance_method)
        frame._require_column(origin_weight)
        frame._require_column(destination_weight)
        frame._require_column(id_column)

        centroids = frame._cached_centroids
        flows: list[Record] = []
        for i, origin in enumerate(frame._rows):
            for j, destination in enumerate(frame._rows):
                if not include_self and i == j:
                    continue
                dist = coordinate_distance(centroids[i], centroids[j], method=distance_method)
                if max_distance is not None and dist > max_distance:
                    continue
                flow_value = gravity_interaction(
                    origin_weight=float(origin[origin_weight]),
                    destination_weight=float(destination[destination_weight]),
                    distance_value=dist,
                    beta=beta,
                    offset=offset,
                )
                flows.append(
                    {
                        "origin": origin[id_column],
                        "destination": destination[id_column],
                        "distance": dist,
                        "gravity_flow": flow_value,
                        "distance_method": distance_method,
                    }
                )
                if max_results is not None and len(flows) >= max_results:
                    return flows
        return flows

    def suitability(
        self,
        criteria_columns: Sequence[str],
        id_column: str = "site_id",
        criteria_weights: Sequence[float] | None = None,
    ) -> list[Record]:
        frame = self._frame
        frame._require_column(id_column)
        if len(criteria_columns) == 0:
            raise ValueError("criteria_columns must not be empty")
        for column in criteria_columns:
            frame._require_column(column)

        if criteria_weights is None:
            weights = tuple(1.0 for _ in criteria_columns)
        else:
            if len(criteria_weights) != len(criteria_columns):
                raise ValueError("criteria_weights length must match criteria_columns length")
            weights = tuple(float(weight) for weight in criteria_weights)

        records: list[Record] = []
        for row in frame._rows:
            scores = tuple(self._unit(float(row[column])) for column in criteria_columns)
            suitability_score = composite_suitability_score(scores, criteria_weights=weights)
            records.append(
                {
                    id_column: row[id_column],
                    "suitability_score": suitability_score,
                    "criteria_columns": list(criteria_columns),
                }
            )
        return records

    def catchment_competition(
        self,
        demand_column: str,
        supply_column: str,
        id_column: str = "site_id",
        distance_method: str = "euclidean",
        max_distance: float | None = None,
    ) -> list[Record]:
        frame = self._frame
        frame._validate_distance_method(distance_method)
        frame._require_column(demand_column)
        frame._require_column(supply_column)
        frame._require_column(id_column)

        centroids = frame._cached_centroids
        records: list[Record] = []
        for i, origin in enumerate(frame._rows):
            competition = 0.0
            for j, destination in enumerate(frame._rows):
                if i == j:
                    continue
                dist = coordinate_distance(centroids[i], centroids[j], method=distance_method)
                if max_distance is not None and dist > max_distance:
                    continue
                competition += competitive_influence(
                    primary_weight=float(origin[supply_column]),
                    competitor_weight=float(destination[supply_column]),
                    distance_value=dist,
                    scale=1.0,
                )
            demand_supply = demand_supply_balance_score(float(origin[demand_column]), float(origin[supply_column]))
            records.append(
                {
                    id_column: origin[id_column],
                    "competition_score": competition,
                    "demand_supply_balance": demand_supply,
                }
            )
        return records

    def hotspot_scan(self, value_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(value_column)
        frame._require_column(id_column)
        baseline = sum(float(row[value_column]) for row in frame._rows) / max(len(frame._rows), 1)
        baseline = max(baseline, 1e-9)
        return [
            {
                id_column: row[id_column],
                "hotspot_score": hotspot_intensity_score(float(row[value_column]), baseline),
            }
            for row in frame._rows
        ]

    def equity_gap(self, min_column: str, max_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(min_column)
        frame._require_column(max_column)
        frame._require_column(id_column)
        return [
            {
                id_column: row[id_column],
                "coverage_equity": coverage_equity_score(max(0.0, float(row[min_column])), max(0.0, float(row[max_column]))),
            }
            for row in frame._rows
        ]

    def network_reliability(self, capacity_column: str, failure_proxy_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(capacity_column)
        frame._require_column(failure_proxy_column)
        frame._require_column(id_column)
        return [
            {
                id_column: row[id_column],
                "network_reliability": corridor_reliability_score(
                    base_strength=max(0.0, float(row[capacity_column])),
                    failure_rate=1.0 - self._unit(float(row[failure_proxy_column])),
                    corridor_length=max(0.0, geometry_length(row[frame.geometry_column])),
                ),
            }
            for row in frame._rows
        ]

    def transit_service_gap(
        self,
        service_frequency_column: str,
        coverage_column: str,
        id_column: str = "site_id",
        distance_method: str = "euclidean",
    ) -> list[Record]:
        frame = self._frame
        frame._validate_distance_method(distance_method)
        frame._require_column(service_frequency_column)
        frame._require_column(coverage_column)
        frame._require_column(id_column)
        centroids = frame._cached_centroids
        center = frame.centroid()
        records: list[Record] = []
        for i, row in enumerate(frame._rows):
            distance_value = coordinate_distance(centroids[i], center, method=distance_method)
            service_score = transit_accessibility_score(
                stop_distance=distance_value,
                service_frequency=max(0.0, float(row[service_frequency_column]) * 60.0),
                network_coverage=self._unit(float(row[coverage_column])),
                scale=500.0,
            )
            records.append({id_column: row[id_column], "transit_service_gap": 1.0 - self._unit(service_score)})
        return records

    def congestion_hotspots(self, flow_column: str, capacity_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(flow_column)
        frame._require_column(capacity_column)
        frame._require_column(id_column)
        return [
            {
                id_column: row[id_column],
                "congestion_index": traffic_congestion_index(
                    current_flow=max(0.0, float(row[flow_column])),
                    capacity=max(1e-9, float(row[capacity_column])),
                    speed_reduction=0.0,
                ),
            }
            for row in frame._rows
        ]

    def walkability_audit(self, connectivity_column: str, density_column: str, amenities_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(connectivity_column)
        frame._require_column(density_column)
        frame._require_column(amenities_column)
        frame._require_column(id_column)
        return [
            {
                id_column: row[id_column],
                "walkability_score": walkability_score(
                    sidewalk_connectivity=self._unit(float(row[connectivity_column])),
                    intersection_density=self._unit(float(row[density_column])),
                    pedestrian_amenities=self._unit(float(row[amenities_column])),
                ),
            }
            for row in frame._rows
        ]

    def gentrification_scan(self, appreciation_column: str, income_column: str, displacement_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(appreciation_column)
        frame._require_column(income_column)
        frame._require_column(displacement_column)
        frame._require_column(id_column)
        return [
            {
                id_column: row[id_column],
                "gentrification_pressure": gentrification_pressure_index(
                    property_appreciation_rate=self._unit(float(row[appreciation_column])),
                    income_dynamics=self._unit(float(row[income_column])),
                    displacement_risk=self._unit(float(row[displacement_column])),
                ),
            }
            for row in frame._rows
        ]

    def land_value_surface(self, base_value_column: str, id_column: str = "site_id", distance_method: str = "euclidean") -> list[Record]:
        frame = self._frame
        frame._validate_distance_method(distance_method)
        frame._require_column(base_value_column)
        frame._require_column(id_column)
        centroids = frame._cached_centroids
        center = frame.centroid()
        records: list[Record] = []
        for i, row in enumerate(frame._rows):
            distance_value = coordinate_distance(centroids[i], center, method=distance_method)
            records.append(
                {
                    id_column: row[id_column],
                    "land_value_estimate": land_value_gradient(
                        city_center_value=max(0.0, float(row[base_value_column])),
                        distance_value=distance_value,
                        scale=1.0,
                        elasticity=0.5,
                    ),
                }
            )
        return records

    def pollution_surface(self, source_column: str, id_column: str = "site_id", distance_method: str = "euclidean") -> list[Record]:
        frame = self._frame
        frame._validate_distance_method(distance_method)
        frame._require_column(source_column)
        frame._require_column(id_column)
        centroids = frame._cached_centroids
        center = frame.centroid()
        records: list[Record] = []
        for i, row in enumerate(frame._rows):
            distance_value = coordinate_distance(centroids[i], center, method=distance_method)
            records.append(
                {
                    id_column: row[id_column],
                    "pollution_intensity": pollution_dispersion_model(
                        source_intensity=max(0.0, float(row[source_column])),
                        distance_value=distance_value,
                        wind_factor=0.1,
                        scale=1.0,
                    ),
                }
            )
        return records

    def habitat_fragmentation_map(self, patch_column: str, connectivity_column: str, id_column: str = "site_id", distance_method: str = "euclidean") -> list[Record]:
        frame = self._frame
        frame._validate_distance_method(distance_method)
        frame._require_column(patch_column)
        frame._require_column(connectivity_column)
        frame._require_column(id_column)
        centroids = frame._cached_centroids
        center = frame.centroid()
        records: list[Record] = []
        for i, row in enumerate(frame._rows):
            distance_value = coordinate_distance(centroids[i], center, method=distance_method)
            records.append(
                {
                    id_column: row[id_column],
                    "fragmentation_score": habitat_fragmentation_score(
                        patch_size=max(0.0, float(row[patch_column])),
                        nearest_patch_distance=distance_value,
                        connectivity_index=max(0.0, float(row[connectivity_column])),
                    ),
                }
            )
        return records

    def climate_vulnerability_map(self, exposure_column: str, sensitivity_column: str, adaptive_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(exposure_column)
        frame._require_column(sensitivity_column)
        frame._require_column(adaptive_column)
        frame._require_column(id_column)
        return [
            {
                id_column: row[id_column],
                "climate_vulnerability": climate_vulnerability_index(
                    exposure_level=self._unit(float(row[exposure_column])),
                    sensitivity_level=self._unit(float(row[sensitivity_column])),
                    adaptive_capacity=self._unit(float(row[adaptive_column])),
                ),
            }
            for row in frame._rows
        ]

    def migration_pull_map(self, economic_column: str, quality_column: str, cultural_column: str, id_column: str = "site_id", distance_method: str = "euclidean") -> list[Record]:
        frame = self._frame
        frame._validate_distance_method(distance_method)
        frame._require_column(economic_column)
        frame._require_column(quality_column)
        frame._require_column(cultural_column)
        frame._require_column(id_column)
        centroids = frame._cached_centroids
        center = frame.centroid()
        records: list[Record] = []
        for i, row in enumerate(frame._rows):
            distance_value = coordinate_distance(centroids[i], center, method=distance_method)
            records.append(
                {
                    id_column: row[id_column],
                    "migration_attraction": migration_attraction_index(
                        economic_opportunity=self._unit(float(row[economic_column])),
                        quality_of_life=self._unit(float(row[quality_column])),
                        cultural_alignment=self._unit(float(row[cultural_column])),
                        distance_value=distance_value,
                    ),
                }
            )
        return records

    def mortality_risk_map(self, population_column: str, disease_column: str, healthcare_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(population_column)
        frame._require_column(disease_column)
        frame._require_column(healthcare_column)
        frame._require_column(id_column)
        return [
            {
                id_column: row[id_column],
                "mortality_risk": mortality_risk_index(
                    age_weighted_population=max(0.0, float(row[population_column])),
                    disease_burden=max(0.0, float(row[disease_column])),
                    healthcare_access=self._unit(float(row[healthcare_column])),
                ),
            }
            for row in frame._rows
        ]

    def market_power_map(self, largest_share_column: str, concentration_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(largest_share_column)
        frame._require_column(concentration_column)
        frame._require_column(id_column)
        return [
            {
                id_column: row[id_column],
                "market_power": market_concentration_index(
                    largest_firm_share=self._unit(float(row[largest_share_column])),
                    herfindahl_index=self._unit(float(row[concentration_column])),
                ),
            }
            for row in frame._rows
        ]

    def trade_corridor_map(self, export_column: str, import_column: str, id_column: str = "site_id", distance_method: str = "euclidean", max_distance: float | None = None, max_results: int | None = None) -> list[Record]:
        frame = self._frame
        frame._validate_distance_method(distance_method)
        frame._require_column(export_column)
        frame._require_column(import_column)
        frame._require_column(id_column)
        centroids = frame._cached_centroids
        records: list[Record] = []
        for i, origin in enumerate(frame._rows):
            for j, destination in enumerate(frame._rows):
                if i == j:
                    continue
                dist = coordinate_distance(centroids[i], centroids[j], method=distance_method)
                if max_distance is not None and dist > max_distance:
                    continue
                records.append(
                    {
                        "origin": origin[id_column],
                        "destination": destination[id_column],
                        "trade_intensity": trade_flow_intensity(
                            export_value=max(0.0, float(origin[export_column])),
                            import_value=max(0.0, float(destination[import_column])),
                            distance_value=dist,
                            bilateral_agreement=0.2,
                        ),
                    }
                )
                if max_results is not None and len(records) >= max_results:
                    return records
        return records

    def community_cohesion_map(self, internal_column: str, external_column: str, identity_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(internal_column)
        frame._require_column(external_column)
        frame._require_column(identity_column)
        frame._require_column(id_column)
        return [
            {
                id_column: row[id_column],
                "community_cohesion": community_cohesion_score(
                    internal_ties=max(0.0, float(row[internal_column])),
                    external_ties=max(0.0, float(row[external_column])),
                    shared_identity_strength=self._unit(float(row[identity_column])),
                ),
            }
            for row in frame._rows
        ]

    def cultural_similarity_matrix(self, value_column: str, language_column: str, tradition_column: str, history_column: str, id_column: str = "site_id", max_results: int | None = None) -> list[Record]:
        frame = self._frame
        frame._require_column(value_column)
        frame._require_column(language_column)
        frame._require_column(tradition_column)
        frame._require_column(history_column)
        frame._require_column(id_column)
        records: list[Record] = []
        for i, origin in enumerate(frame._rows):
            for j, destination in enumerate(frame._rows):
                if i == j:
                    continue
                records.append(
                    {
                        "origin": origin[id_column],
                        "destination": destination[id_column],
                        "cultural_similarity": cultural_similarity_index(
                            value_alignment=self._unit((float(origin[value_column]) + float(destination[value_column])) / 2.0),
                            language_similarity=self._unit((float(origin[language_column]) + float(destination[language_column])) / 2.0),
                            tradition_overlap=self._unit((float(origin[tradition_column]) + float(destination[tradition_column])) / 2.0),
                            history_shared=self._unit((float(origin[history_column]) + float(destination[history_column])) / 2.0),
                        ),
                    }
                )
                if max_results is not None and len(records) >= max_results:
                    return records
        return records

    def noise_impact_map(self, source_column: str, barrier_column: str, id_column: str = "site_id", distance_method: str = "euclidean") -> list[Record]:
        frame = self._frame
        frame._validate_distance_method(distance_method)
        frame._require_column(source_column)
        frame._require_column(barrier_column)
        frame._require_column(id_column)
        centroids = frame._cached_centroids
        center = frame.centroid()
        records: list[Record] = []
        for i, row in enumerate(frame._rows):
            distance_value = coordinate_distance(centroids[i], center, method=distance_method)
            records.append(
                {
                    id_column: row[id_column],
                    "noise_level": noise_propagation_level(
                        source_decibels=max(0.0, float(row[source_column]) * 100.0),
                        distance_value=distance_value,
                        atmospheric_conditions=0.1,
                        barriers=max(0.0, float(row[barrier_column])),
                    ),
                }
            )
        return records

    def visual_prominence_map(self, vertical_column: str, range_column: str, distinctiveness_column: str, id_column: str = "site_id", distance_method: str = "euclidean") -> list[Record]:
        frame = self._frame
        frame._validate_distance_method(distance_method)
        frame._require_column(vertical_column)
        frame._require_column(range_column)
        frame._require_column(distinctiveness_column)
        frame._require_column(id_column)
        centroids = frame._cached_centroids
        center = frame.centroid()
        records: list[Record] = []
        for i, row in enumerate(frame._rows):
            distance_value = coordinate_distance(centroids[i], center, method=distance_method)
            records.append(
                {
                    id_column: row[id_column],
                    "visual_prominence": visual_prominence_score(
                        vertical_extent=max(0.0, float(row[vertical_column]) * 100.0),
                        visibility_range=max(0.0, float(row[range_column]) * 1000.0),
                        distinctiveness=self._unit(float(row[distinctiveness_column])),
                        distance_value=distance_value,
                        scale=1.0,
                    ),
                }
            )
        return records

    def drought_stress_map(self, demand_column: str, supply_column: str, reserve_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(demand_column)
        frame._require_column(supply_column)
        frame._require_column(reserve_column)
        frame._require_column(id_column)
        return [
            {
                id_column: row[id_column],
                "drought_stress": drought_stress_index(
                    water_demand=max(0.0, float(row[demand_column])),
                    water_supply=max(0.0, float(row[supply_column])),
                    reserve_ratio=self._unit(float(row[reserve_column])),
                ),
            }
            for row in frame._rows
        ]

    def heat_island_map(self, impervious_column: str, canopy_column: str, albedo_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(impervious_column)
        frame._require_column(canopy_column)
        frame._require_column(albedo_column)
        frame._require_column(id_column)
        return [
            {
                id_column: row[id_column],
                "heat_island_intensity": heat_island_intensity(
                    impervious_ratio=self._unit(float(row[impervious_column])),
                    tree_canopy_ratio=self._unit(float(row[canopy_column])),
                    albedo=self._unit(float(row[albedo_column])),
                ),
            }
            for row in frame._rows
        ]

    def school_access_map(self, capacity_column: str, demand_column: str, id_column: str = "site_id", distance_method: str = "euclidean") -> list[Record]:
        frame = self._frame
        frame._validate_distance_method(distance_method)
        frame._require_column(capacity_column)
        frame._require_column(demand_column)
        frame._require_column(id_column)
        centroids = frame._cached_centroids
        center = frame.centroid()
        records: list[Record] = []
        for i, row in enumerate(frame._rows):
            travel_time = coordinate_distance(centroids[i], center, method=distance_method)
            records.append(
                {
                    id_column: row[id_column],
                    "school_access": school_access_score(
                        seat_capacity=max(0.0, float(row[capacity_column])),
                        student_population=max(0.0, float(row[demand_column])),
                        travel_time=travel_time,
                    ),
                }
            )
        return records

    def healthcare_access_map(self, provider_column: str, population_column: str, id_column: str = "site_id", distance_method: str = "euclidean") -> list[Record]:
        frame = self._frame
        frame._validate_distance_method(distance_method)
        frame._require_column(provider_column)
        frame._require_column(population_column)
        frame._require_column(id_column)
        centroids = frame._cached_centroids
        center = frame.centroid()
        records: list[Record] = []
        for i, row in enumerate(frame._rows):
            travel_time = coordinate_distance(centroids[i], center, method=distance_method)
            records.append(
                {
                    id_column: row[id_column],
                    "healthcare_access": healthcare_access_index(
                        provider_count=max(0.0, float(row[provider_column])),
                        population=max(0.0, float(row[population_column])),
                        travel_time=travel_time,
                    ),
                }
            )
        return records

    def food_desert_map(self, grocery_column: str, vehicle_column: str, transit_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(grocery_column)
        frame._require_column(vehicle_column)
        frame._require_column(transit_column)
        frame._require_column(id_column)
        return [
            {
                id_column: row[id_column],
                "food_desert_risk": food_desert_risk(
                    grocery_density=self._unit(float(row[grocery_column])),
                    vehicle_access=self._unit(float(row[vehicle_column])),
                    transit_access=self._unit(float(row[transit_column])),
                ),
            }
            for row in frame._rows
        ]

    def digital_divide_map(self, broadband_column: str, device_column: str, literacy_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(broadband_column)
        frame._require_column(device_column)
        frame._require_column(literacy_column)
        frame._require_column(id_column)
        return [
            {
                id_column: row[id_column],
                "digital_divide": digital_divide_index(
                    broadband_coverage=self._unit(float(row[broadband_column])),
                    device_access=self._unit(float(row[device_column])),
                    digital_literacy=self._unit(float(row[literacy_column])),
                ),
            }
            for row in frame._rows
        ]

    def wildfire_risk_map(self, fuel_column: str, dryness_column: str, wind_column: str, suppression_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(fuel_column)
        frame._require_column(dryness_column)
        frame._require_column(wind_column)
        frame._require_column(suppression_column)
        frame._require_column(id_column)
        return [
            {
                id_column: row[id_column],
                "wildfire_risk": wildfire_risk_index(
                    fuel_load=max(0.0, float(row[fuel_column])),
                    dryness_index=max(0.0, float(row[dryness_column])),
                    wind_speed=max(0.0, float(row[wind_column])),
                    suppression_capacity=self._unit(float(row[suppression_column])),
                ),
            }
            for row in frame._rows
        ]

    def emergency_response_map(self, station_column: str, coverage_column: str, id_column: str = "site_id", distance_method: str = "euclidean") -> list[Record]:
        frame = self._frame
        frame._validate_distance_method(distance_method)
        frame._require_column(station_column)
        frame._require_column(coverage_column)
        frame._require_column(id_column)
        centroids = frame._cached_centroids
        center = frame.centroid()
        records: list[Record] = []
        for i, row in enumerate(frame._rows):
            response_time = coordinate_distance(centroids[i], center, method=distance_method)
            records.append(
                {
                    id_column: row[id_column],
                    "emergency_response": emergency_response_score(
                        station_density=self._unit(float(row[station_column])),
                        response_time=response_time,
                        coverage_ratio=self._unit(float(row[coverage_column])),
                    ),
                }
            )
        return records

    def infrastructure_lifecycle_map(self, age_column: str, life_column: str, maintenance_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(age_column)
        frame._require_column(life_column)
        frame._require_column(maintenance_column)
        frame._require_column(id_column)
        return [
            {
                id_column: row[id_column],
                "infrastructure_lifecycle": infrastructure_lifecycle_score(
                    age_years=max(0.0, float(row[age_column])),
                    design_life_years=max(1e-9, float(row[life_column])),
                    maintenance_quality=self._unit(float(row[maintenance_column])),
                ),
            }
            for row in frame._rows
        ]

    def adaptive_capacity_map(self, income_column: str, education_column: str, health_column: str, governance_column: str, id_column: str = "site_id") -> list[Record]:
        frame = self._frame
        frame._require_column(income_column)
        frame._require_column(education_column)
        frame._require_column(health_column)
        frame._require_column(governance_column)
        frame._require_column(id_column)
        return [
            {
                id_column: row[id_column],
                "adaptive_capacity": adaptive_capacity_score(
                    income_index=self._unit(float(row[income_column])),
                    education_index=self._unit(float(row[education_column])),
                    health_index=self._unit(float(row[health_column])),
                    governance_index=self._unit(float(row[governance_column])),
                ),
            }
            for row in frame._rows
        ]


class GeoPromptFrame:
    def __init__(self, rows: Sequence[Record], geometry_column: str = "geometry", crs: str | None = None) -> None:
        self.geometry_column = geometry_column
        self.crs = crs
        self._rows = [dict(row) for row in rows]
        for row in self._rows:
            row[self.geometry_column] = normalize_geometry(row[self.geometry_column])
        self._centroid_cache: list[Coordinate] | None = None

    @classmethod
    def from_records(cls, records: Iterable[Record], geometry: str = "geometry", crs: str | None = None) -> "GeoPromptFrame":
        return cls(list(records), geometry_column=geometry, crs=crs)

    @classmethod
    def _from_internal_rows(
        cls,
        rows: Sequence[Record],
        geometry_column: str = "geometry",
        crs: str | None = None,
    ) -> "GeoPromptFrame":
        frame = cls.__new__(cls)
        frame.geometry_column = geometry_column
        frame.crs = crs
        frame._rows = [dict(row) for row in rows]
        frame._centroid_cache = None
        return frame

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self):
        return iter(self._rows)

    @property
    def analysis(self) -> GeoPromptAnalysis:
        return GeoPromptAnalysis(self)

    @property
    def columns(self) -> list[str]:
        return list(self._rows[0].keys()) if self._rows else []

    def head(self, count: int = 5) -> list[Record]:
        return [dict(row) for row in self._rows[:count]]

    def to_records(self) -> list[Record]:
        return [dict(row) for row in self._rows]

    def bounds(self) -> Bounds:
        xs: list[float] = []
        ys: list[float] = []
        for row in self._rows:
            min_x, min_y, max_x, max_y = geometry_bounds(row[self.geometry_column])
            xs.extend([min_x, max_x])
            ys.extend([min_y, max_y])
        return Bounds(min_x=min(xs), min_y=min(ys), max_x=max(xs), max_y=max(ys))

    def centroid(self) -> Coordinate:
        centroids = self._cached_centroids
        xs = [coord[0] for coord in centroids]
        ys = [coord[1] for coord in centroids]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    @property
    def _cached_centroids(self) -> list[Coordinate]:
        """Pre-computed centroids for all rows; reused across all pairwise operations."""
        if self._centroid_cache is None:
            self._centroid_cache = [
                geometry_centroid(row[self.geometry_column]) for row in self._rows
            ]
        return self._centroid_cache

    def _centroids(self, rows: Sequence[Record] | None = None, geometry_column: str | None = None) -> list[Coordinate]:
        active_rows = rows if rows is not None else self._rows
        active_geometry_column = geometry_column or self.geometry_column
        return [geometry_centroid(row[active_geometry_column]) for row in active_rows]

    def _resolve_anchor_geometry(self, anchor: str | Geometry | Coordinate, id_column: str) -> tuple[Geometry, str | None]:
        if isinstance(anchor, str):
            self._require_column(id_column)
            anchor_row = next((row for row in self._rows if str(row[id_column]) == anchor), None)
            if anchor_row is None:
                raise KeyError(f"anchor '{anchor}' was not found in column '{id_column}'")
            return anchor_row[self.geometry_column], anchor
        return normalize_geometry(anchor), None

    def _aggregate_rows(
        self,
        rows: Sequence[Record],
        aggregations: dict[str, AggregationName] | None,
        suffix: str,
    ) -> dict[str, Any]:
        aggregate_values: dict[str, Any] = {}
        for column, operation in (aggregations or {}).items():
            values = [row[column] for row in rows if column in row and row[column] is not None]
            output_name = f"{column}_{operation}_{suffix}"
            if not values:
                aggregate_values[output_name] = None
                continue
            if operation == "sum":
                aggregate_values[output_name] = sum(float(value) for value in values)
            elif operation == "mean":
                aggregate_values[output_name] = sum(float(value) for value in values) / len(values)
            elif operation == "min":
                aggregate_values[output_name] = min(values)
            elif operation == "max":
                aggregate_values[output_name] = max(values)
            elif operation == "first":
                aggregate_values[output_name] = values[0]
            elif operation == "count":
                aggregate_values[output_name] = len(values)
            else:
                raise ValueError(f"unsupported aggregation: {operation}")
        return aggregate_values

    def distance_matrix(self, distance_method: str = "euclidean") -> list[list[float]]:
        self._validate_distance_method(distance_method)
        return [
            [
                geometry_distance(origin=row[self.geometry_column], destination=other[self.geometry_column], method=distance_method)
                for other in self._rows
            ]
            for row in self._rows
        ]

    def geometry_types(self) -> list[str]:
        return [geometry_type(row[self.geometry_column]) for row in self._rows]

    def geometry_lengths(self) -> list[float]:
        return [geometry_length(row[self.geometry_column]) for row in self._rows]

    def geometry_areas(self) -> list[float]:
        return [geometry_area(row[self.geometry_column]) for row in self._rows]

    def nearest_neighbors(
        self,
        id_column: str = "site_id",
        k: int = 1,
        distance_method: str = "euclidean",
    ) -> list[Record]:
        self._validate_distance_method(distance_method)
        self._require_column(id_column)
        if k <= 0:
            raise ValueError("k must be greater than zero")

        centroids = self._centroids()
        geometry_types = self.geometry_types()
        nearest: list[Record] = []
        for origin_index, origin in enumerate(self._rows):
            candidates = [
                (
                    destination,
                    geometry_types[destination_index],
                    coordinate_distance(centroids[origin_index], centroids[destination_index], method=distance_method),
                )
                for destination_index, destination in enumerate(self._rows)
                if destination_index != origin_index
            ]
            for rank, (destination, destination_geometry_type, distance_value) in enumerate(
                nsmallest(k, candidates, key=lambda item: (float(item[2]), _row_sort_key(item[0]))),
                start=1,
            ):
                nearest.append(
                    {
                        "origin": origin[id_column],
                        "neighbor": destination[id_column],
                        "distance": distance_value,
                        "origin_geometry_type": geometry_types[origin_index],
                        "neighbor_geometry_type": destination_geometry_type,
                        "rank": rank,
                        "distance_method": distance_method,
                    }
                )
        return nearest

    def _nearest_row_matches(
        self,
        origin_centroid: Coordinate,
        right_rows: Sequence[Record],
        right_centroids: Sequence[Coordinate],
        k: int,
        distance_method: str,
        max_distance: float | None = None,
    ) -> list[tuple[Record, float]]:
        candidates: list[tuple[Record, float]] = []
        for right_row, right_centroid in zip(right_rows, right_centroids, strict=True):
            if max_distance is not None and distance_method == "euclidean":
                if abs(origin_centroid[0] - right_centroid[0]) > max_distance or abs(origin_centroid[1] - right_centroid[1]) > max_distance:
                    continue
            distance_value = coordinate_distance(origin_centroid, right_centroid, method=distance_method)
            if max_distance is None or distance_value <= max_distance:
                candidates.append((right_row, distance_value))
        return nsmallest(k, candidates, key=lambda item: (float(item[1]), _row_sort_key(item[0])))

    def nearest_join(
        self,
        other: "GeoPromptFrame",
        k: int = 1,
        how: SpatialJoinMode = "inner",
        lsuffix: str = "left",
        rsuffix: str = "right",
        max_distance: float | None = None,
        distance_method: str = "euclidean",
    ) -> "GeoPromptFrame":
        self._validate_distance_method(distance_method, other_crs=other.crs)
        if k <= 0:
            raise ValueError("k must be greater than zero")
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if max_distance is not None and max_distance < 0:
            raise ValueError("max_distance must be zero or greater")
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before nearest joins")

        right_rows = list(other._rows)
        right_columns = [column for column in other.columns if column != other.geometry_column]
        left_centroids = self._centroids()
        right_centroids = other._centroids()
        joined_rows: list[Record] = []

        for left_row, left_centroid in zip(self._rows, left_centroids, strict=True):
            row_matches = self._nearest_row_matches(
                origin_centroid=left_centroid,
                right_rows=right_rows,
                right_centroids=right_centroids,
                k=k,
                distance_method=distance_method,
                max_distance=max_distance,
            )

            if not row_matches and how == "left":
                merged_row = dict(left_row)
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = None
                merged_row[f"{other.geometry_column}_{rsuffix}"] = None
                merged_row[f"distance_{rsuffix}"] = None
                merged_row[f"distance_method_{rsuffix}"] = distance_method
                merged_row[f"nearest_rank_{rsuffix}"] = None
                joined_rows.append(merged_row)

            for rank, (right_row, distance_value) in enumerate(row_matches, start=1):
                merged_row = dict(left_row)
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = right_row[column]
                merged_row[f"{other.geometry_column}_{rsuffix}"] = right_row[other.geometry_column]
                merged_row[f"distance_{rsuffix}"] = distance_value
                merged_row[f"distance_method_{rsuffix}"] = distance_method
                merged_row[f"nearest_rank_{rsuffix}"] = rank
                joined_rows.append(merged_row)

        return GeoPromptFrame._from_internal_rows(joined_rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def assign_nearest(
        self,
        targets: "GeoPromptFrame",
        how: SpatialJoinMode = "inner",
        max_distance: float | None = None,
        distance_method: str = "euclidean",
        origin_suffix: str = "origin",
    ) -> "GeoPromptFrame":
        self._validate_distance_method(distance_method, other_crs=targets.crs)
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if max_distance is not None and max_distance < 0:
            raise ValueError("max_distance must be zero or greater")
        return targets.nearest_join(
            self,
            k=1,
            how=how,
            rsuffix=origin_suffix,
            max_distance=max_distance,
            distance_method=distance_method,
        )

    def summarize_assignments(
        self,
        targets: "GeoPromptFrame",
        origin_id_column: str = "site_id",
        target_id_column: str = "site_id",
        aggregations: dict[str, AggregationName] | None = None,
        how: SpatialJoinMode = "left",
        max_distance: float | None = None,
        distance_method: str = "euclidean",
        assignment_suffix: str = "assigned",
    ) -> "GeoPromptFrame":
        self._validate_distance_method(distance_method, other_crs=targets.crs)
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if max_distance is not None and max_distance < 0:
            raise ValueError("max_distance must be zero or greater")
        if self.crs and targets.crs and self.crs != targets.crs:
            raise ValueError("frames must share the same CRS before assignment summaries")

        self._require_column(origin_id_column)
        targets._require_column(target_id_column)

        origin_centroids = self._centroids()
        target_rows = list(targets._rows)
        target_centroids = targets._centroids()
        assignments: dict[str, list[tuple[Record, float]]] = {}

        for target_row, target_centroid in zip(target_rows, target_centroids, strict=True):
            row_matches = self._nearest_row_matches(
                origin_centroid=target_centroid,
                right_rows=self._rows,
                right_centroids=origin_centroids,
                k=1,
                distance_method=distance_method,
                max_distance=max_distance,
            )
            if not row_matches:
                continue
            origin_row, distance_value = row_matches[0]
            origin_key = str(origin_row[origin_id_column])
            assignments.setdefault(origin_key, []).append((target_row, distance_value))

        rows: list[Record] = []
        for origin_row in self._rows:
            origin_key = str(origin_row[origin_id_column])
            assigned_matches = assignments.get(origin_key, [])
            if not assigned_matches and how == "inner":
                continue

            assigned_rows = [row for row, _ in assigned_matches]
            assigned_distances = [distance for _, distance in assigned_matches]
            resolved_row = dict(origin_row)
            resolved_row[f"{target_id_column}s_{assignment_suffix}"] = [str(row[target_id_column]) for row in assigned_rows]
            resolved_row[f"count_{assignment_suffix}"] = len(assigned_rows)
            resolved_row[f"distance_method_{assignment_suffix}"] = distance_method
            resolved_row[f"distance_min_{assignment_suffix}"] = min(assigned_distances) if assigned_distances else None
            resolved_row[f"distance_max_{assignment_suffix}"] = max(assigned_distances) if assigned_distances else None
            resolved_row[f"distance_mean_{assignment_suffix}"] = (
                sum(assigned_distances) / len(assigned_distances) if assigned_distances else None
            )
            resolved_row.update(self._aggregate_rows(assigned_rows, aggregations=aggregations, suffix=assignment_suffix))
            rows.append(resolved_row)

        return GeoPromptFrame._from_internal_rows(rows, geometry_column=self.geometry_column, crs=self.crs or targets.crs)

    def query_radius(
        self,
        anchor: str | Geometry | Coordinate,
        max_distance: float,
        id_column: str = "site_id",
        include_anchor: bool = False,
        distance_method: str = "euclidean",
    ) -> "GeoPromptFrame":
        self._validate_distance_method(distance_method)
        if max_distance < 0:
            raise ValueError("max_distance must be zero or greater")

        anchor_geometry, anchor_id = self._resolve_anchor_geometry(anchor, id_column=id_column)
        anchor_centroid = geometry_centroid(anchor_geometry)

        rows: list[Record] = []
        for row in self._rows:
            row_id = str(row.get(id_column)) if id_column in row else None
            distance_value = coordinate_distance(anchor_centroid, geometry_centroid(row[self.geometry_column]), method=distance_method)
            if anchor_id is not None and not include_anchor and row_id == anchor_id:
                continue
            if distance_value <= max_distance:
                resolved_row = dict(row)
                resolved_row["distance"] = distance_value
                resolved_row["distance_method"] = distance_method
                if anchor_id is not None:
                    resolved_row["anchor_id"] = anchor_id
                rows.append(resolved_row)

        rows.sort(key=lambda item: (float(item["distance"]), str(item.get(id_column, ""))))
        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs)

    def within_distance(
        self,
        anchor: str | Geometry | Coordinate,
        max_distance: float,
        id_column: str = "site_id",
        include_anchor: bool = False,
        distance_method: str = "euclidean",
    ) -> list[bool]:
        self._validate_distance_method(distance_method)
        if max_distance < 0:
            raise ValueError("max_distance must be zero or greater")

        anchor_geometry, anchor_id = self._resolve_anchor_geometry(anchor, id_column=id_column)
        anchor_centroid = geometry_centroid(anchor_geometry)
        centroids = self._centroids()

        return [
            False
            if anchor_id is not None and not include_anchor and id_column in row and str(row[id_column]) == anchor_id
            else coordinate_distance(anchor_centroid, centroid, method=distance_method) <= max_distance
            for row, centroid in zip(self._rows, centroids, strict=True)
        ]

    def proximity_join(
        self,
        other: "GeoPromptFrame",
        max_distance: float,
        how: SpatialJoinMode = "inner",
        lsuffix: str = "left",
        rsuffix: str = "right",
        distance_method: str = "euclidean",
    ) -> "GeoPromptFrame":
        self._validate_distance_method(distance_method, other_crs=other.crs)
        if max_distance < 0:
            raise ValueError("max_distance must be zero or greater")
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before proximity joins")

        right_rows = list(other._rows)
        right_columns = [column for column in other.columns if column != other.geometry_column]
        left_centroids = self._centroids()
        right_centroids = other._centroids()
        joined_rows: list[Record] = []

        for left_row, left_centroid in zip(self._rows, left_centroids, strict=True):
            row_matches: list[tuple[Record, float]] = []
            for right_row, right_centroid in zip(right_rows, right_centroids, strict=True):
                if distance_method == "euclidean":
                    if abs(left_centroid[0] - right_centroid[0]) > max_distance or abs(left_centroid[1] - right_centroid[1]) > max_distance:
                        continue
                distance_value = coordinate_distance(left_centroid, right_centroid, method=distance_method)
                if distance_value <= max_distance:
                    row_matches.append((right_row, distance_value))

            row_matches.sort(key=lambda item: (float(item[1]), str(item[0].get("site_id", item[0].get("region_id", "")))))

            if not row_matches and how == "left":
                merged_row = dict(left_row)
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = None
                merged_row[f"{other.geometry_column}_{rsuffix}"] = None
                merged_row[f"distance_{rsuffix}"] = None
                merged_row[f"distance_method_{rsuffix}"] = distance_method
                joined_rows.append(merged_row)

            for right_row, distance_value in row_matches:
                merged_row = dict(left_row)
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = right_row[column]
                merged_row[f"{other.geometry_column}_{rsuffix}"] = right_row[other.geometry_column]
                merged_row[f"distance_{rsuffix}"] = distance_value
                merged_row[f"distance_method_{rsuffix}"] = distance_method
                joined_rows.append(merged_row)

        return GeoPromptFrame._from_internal_rows(joined_rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def buffer(self, distance: float, resolution: int = 16) -> "GeoPromptFrame":
        buffered_groups = buffer_geometries(
            [row[self.geometry_column] for row in self._rows],
            distance=distance,
            resolution=resolution,
        )
        rows: list[Record] = []
        for row, buffered_geometries in zip(self._rows, buffered_groups, strict=True):
            for buffered_geometry in buffered_geometries:
                buffered_row = dict(row)
                buffered_row[self.geometry_column] = buffered_geometry
                rows.append(buffered_row)
        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs)

    def buffer_join(
        self,
        other: "GeoPromptFrame",
        distance: float,
        how: SpatialJoinMode = "inner",
        lsuffix: str = "left",
        rsuffix: str = "right",
        resolution: int = 16,
    ) -> "GeoPromptFrame":
        if distance < 0:
            raise ValueError("distance must be zero or greater")
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before buffer joins")

        right_rows = list(other._rows)
        right_columns = [column for column in other.columns if column != other.geometry_column]
        right_bounds = [geometry_bounds(row[other.geometry_column]) for row in right_rows]
        buffered_groups = buffer_geometries(
            [row[self.geometry_column] for row in self._rows],
            distance=distance,
            resolution=resolution,
        )

        joined_rows: list[Record] = []
        for left_row, buffered_geometries in zip(self._rows, buffered_groups, strict=True):
            row_matches: list[tuple[Record, Geometry]] = []
            for buffered_geometry in buffered_geometries:
                buffered_bounds = geometry_bounds(buffered_geometry)
                for right_row, right_bound in zip(right_rows, right_bounds, strict=True):
                    if not _bounds_intersect(buffered_bounds, right_bound):
                        continue
                    if geometry_intersects(buffered_geometry, right_row[other.geometry_column]):
                        row_matches.append((right_row, buffered_geometry))

            if not row_matches and how == "left":
                merged_row = dict(left_row)
                merged_row[f"buffer_geometry_{lsuffix}"] = None
                merged_row[f"buffer_distance_{lsuffix}"] = distance
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = None
                merged_row[f"{other.geometry_column}_{rsuffix}"] = None
                joined_rows.append(merged_row)

            for right_row, buffered_geometry in row_matches:
                merged_row = dict(left_row)
                merged_row[f"buffer_geometry_{lsuffix}"] = buffered_geometry
                merged_row[f"buffer_distance_{lsuffix}"] = distance
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = right_row[column]
                merged_row[f"{other.geometry_column}_{rsuffix}"] = right_row[other.geometry_column]
                joined_rows.append(merged_row)

        return GeoPromptFrame(rows=joined_rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def coverage_summary(
        self,
        targets: "GeoPromptFrame",
        predicate: SpatialJoinPredicate = "intersects",
        target_id_column: str = "site_id",
        aggregations: dict[str, AggregationName] | None = None,
        rsuffix: str = "covered",
    ) -> "GeoPromptFrame":
        if self.crs and targets.crs and self.crs != targets.crs:
            raise ValueError("frames must share the same CRS before coverage summaries")
        if predicate not in {"intersects", "within", "contains"}:
            raise ValueError(f"unsupported spatial join predicate: {predicate}")

        targets._require_column(target_id_column)
        target_rows = list(targets._rows)
        target_bounds = [geometry_bounds(row[targets.geometry_column]) for row in target_rows]
        predicate_bounds_filter = {
            "intersects": _bounds_intersect,
            "within": _bounds_within,
            "contains": lambda left, right: _bounds_within(right, left),
        }

        def matches(left_geometry: Geometry, right_geometry: Geometry) -> bool:
            if predicate == "intersects":
                return geometry_intersects(left_geometry, right_geometry)
            if predicate == "within":
                return geometry_within(left_geometry, right_geometry)
            return geometry_contains(left_geometry, right_geometry)

        rows: list[Record] = []
        for row in self._rows:
            left_geometry = row[self.geometry_column]
            left_bounds = geometry_bounds(left_geometry)
            matched_rows: list[Record] = []
            for target_row, target_bound in zip(target_rows, target_bounds, strict=True):
                if not predicate_bounds_filter[predicate](left_bounds, target_bound):
                    continue
                if matches(left_geometry, target_row[targets.geometry_column]):
                    matched_rows.append(target_row)

            resolved_row = dict(row)
            resolved_row[f"{target_id_column}s_{rsuffix}"] = [str(item[target_id_column]) for item in matched_rows]
            resolved_row[f"count_{rsuffix}"] = len(matched_rows)
            resolved_row[f"predicate_{rsuffix}"] = predicate
            resolved_row.update(self._aggregate_rows(matched_rows, aggregations=aggregations, suffix=rsuffix))
            rows.append(resolved_row)

        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs or targets.crs)

    def query_bounds(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        mode: BoundsQueryMode = "intersects",
    ) -> "GeoPromptFrame":
        if min_x > max_x or min_y > max_y:
            raise ValueError("query bounds must be ordered from minimum to maximum")

        rows: list[Record] = []
        for row in self._rows:
            geometry = row[self.geometry_column]
            if mode == "intersects":
                include_row = geometry_intersects_bounds(geometry, min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)
            elif mode == "within":
                include_row = geometry_within_bounds(geometry, min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)
            elif mode == "centroid":
                centroid_x, centroid_y = geometry_centroid(geometry)
                include_row = min_x <= centroid_x <= max_x and min_y <= centroid_y <= max_y
            else:
                raise ValueError(f"unsupported bounds query mode: {mode}")

            if include_row:
                rows.append(dict(row))

        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs)

    def set_crs(self, crs: str, allow_override: bool = False) -> "GeoPromptFrame":
        if self.crs is not None and self.crs != crs and not allow_override:
            raise ValueError("frame already has a CRS; pass allow_override=True to replace it")
        return GeoPromptFrame(rows=self.to_records(), geometry_column=self.geometry_column, crs=crs)

    def to_crs(self, target_crs: str) -> "GeoPromptFrame":
        if self.crs is None:
            raise ValueError("frame CRS is not set; call set_crs before reprojecting")
        if self.crs == target_crs:
            return GeoPromptFrame(rows=self.to_records(), geometry_column=self.geometry_column, crs=self.crs)

        try:
            pyproj = importlib.import_module("pyproj")
        except ImportError as exc:
            raise RuntimeError("Install projection support with 'pip install -e .[projection]' before calling to_crs.") from exc

        transformer = pyproj.Transformer.from_crs(self.crs, target_crs, always_xy=True)

        def reproject_coordinate(coordinate: Coordinate) -> Coordinate:
            x_value, y_value = transformer.transform(coordinate[0], coordinate[1])
            return (float(x_value), float(y_value))

        rows = self.to_records()
        for row in rows:
            row[self.geometry_column] = transform_geometry(row[self.geometry_column], reproject_coordinate)
        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=target_crs)

    def spatial_join(
        self,
        other: "GeoPromptFrame",
        predicate: SpatialJoinPredicate = "intersects",
        how: SpatialJoinMode = "inner",
        lsuffix: str = "left",
        rsuffix: str = "right",
    ) -> "GeoPromptFrame":
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before spatial joins")

        right_columns = [column for column in other.columns if column != other.geometry_column]
        joined_rows: list[Record] = []
        right_rows = list(other._rows)
        right_bounds = [geometry_bounds(row[other.geometry_column]) for row in right_rows]

        predicate_bounds_filter = {
            "intersects": _bounds_intersect,
            "within": _bounds_within,
            "contains": lambda left, right: _bounds_within(right, left),
        }
        if predicate not in predicate_bounds_filter:
            raise ValueError(f"unsupported spatial join predicate: {predicate}")

        def matches(left_geometry: Geometry, right_geometry: Geometry) -> bool:
            if predicate == "intersects":
                return geometry_intersects(left_geometry, right_geometry)
            if predicate == "within":
                return geometry_within(left_geometry, right_geometry)
            if predicate == "contains":
                return geometry_contains(left_geometry, right_geometry)
            raise ValueError(f"unsupported spatial join predicate: {predicate}")

        for left_row in self._rows:
            left_geometry = left_row[self.geometry_column]
            left_bounds = geometry_bounds(left_geometry)
            row_matches = []
            for right_row, right_bound in zip(right_rows, right_bounds, strict=True):
                if not predicate_bounds_filter[predicate](left_bounds, right_bound):
                    continue
                if matches(left_geometry, right_row[other.geometry_column]):
                    row_matches.append(right_row)

            if not row_matches and how == "left":
                merged_row = dict(left_row)
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = None
                merged_row[f"join_predicate_{rsuffix}"] = predicate
                joined_rows.append(merged_row)

            for right_row in row_matches:
                merged_row = dict(left_row)
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = right_row[column]
                merged_row[f"{other.geometry_column}_{rsuffix}"] = right_row[other.geometry_column]
                merged_row[f"join_predicate_{rsuffix}"] = predicate
                joined_rows.append(merged_row)

        return GeoPromptFrame(rows=joined_rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def clip(self, mask: "GeoPromptFrame") -> "GeoPromptFrame":
        if self.crs and mask.crs and self.crs != mask.crs:
            raise ValueError("frames must share the same CRS before clip operations")

        mask_rows = list(mask)
        clipped_groups = clip_geometries(
            [row[self.geometry_column] for row in self._rows],
            [row[mask.geometry_column] for row in mask_rows],
        )
        rows: list[Record] = []
        for row, clipped_geometries in zip(self._rows, clipped_groups, strict=True):
            for clipped_geometry in clipped_geometries:
                clipped_row = dict(row)
                clipped_row[self.geometry_column] = clipped_geometry
                rows.append(clipped_row)
        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs or mask.crs)

    def overlay_intersections(
        self,
        other: "GeoPromptFrame",
        lsuffix: str = "left",
        rsuffix: str = "right",
    ) -> "GeoPromptFrame":
        if self.crs and other.crs and self.crs != other.crs:
            raise ValueError("frames must share the same CRS before overlay operations")

        intersections = overlay_intersections(
            [row[self.geometry_column] for row in self._rows],
            [row[other.geometry_column] for row in other],
        )
        right_columns = [column for column in other.columns if column != other.geometry_column]
        rows: list[Record] = []
        for left_index, right_index, geometries in intersections:
            left_row = self._rows[left_index]
            right_row = other.to_records()[right_index]
            for geometry in geometries:
                merged_row = dict(left_row)
                for column in right_columns:
                    target_name = column if column not in merged_row else f"{column}_{rsuffix}"
                    merged_row[target_name] = right_row[column]
                merged_row[f"{other.geometry_column}_{rsuffix}"] = right_row[other.geometry_column]
                merged_row[self.geometry_column] = geometry
                rows.append(merged_row)
        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs or other.crs)

    def dissolve(
        self,
        by: str,
        aggregations: dict[str, AggregationName] | None = None,
    ) -> "GeoPromptFrame":
        self._require_column(by)
        grouped_rows: dict[Any, list[Record]] = {}
        for row in self._rows:
            grouped_rows.setdefault(row[by], []).append(row)

        rows: list[Record] = []
        for group_value, group_rows in grouped_rows.items():
            dissolved_geometries = dissolve_geometries([row[self.geometry_column] for row in group_rows])
            aggregate_values: dict[str, Any] = {by: group_value}
            for column in self.columns:
                if column in {by, self.geometry_column}:
                    continue
                operation = (aggregations or {}).get(column)
                values = [row[column] for row in group_rows if column in row]
                if not values:
                    continue
                if operation is None:
                    aggregate_values[column] = values[0]
                elif operation == "sum":
                    aggregate_values[column] = sum(float(value) for value in values)
                elif operation == "mean":
                    aggregate_values[column] = sum(float(value) for value in values) / len(values)
                elif operation == "min":
                    aggregate_values[column] = min(values)
                elif operation == "max":
                    aggregate_values[column] = max(values)
                elif operation == "first":
                    aggregate_values[column] = values[0]
                elif operation == "count":
                    aggregate_values[column] = len(values)
                else:
                    raise ValueError(f"unsupported aggregation: {operation}")

            for geometry in dissolved_geometries:
                rows.append({**aggregate_values, self.geometry_column: geometry})

        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs)

    def with_column(self, name: str, values: Sequence[Any]) -> "GeoPromptFrame":
        if len(values) != len(self._rows):
            raise ValueError("column length must match the frame length")
        rows = self.to_records()
        for row, value in zip(rows, values, strict=True):
            row[name] = value
        return GeoPromptFrame(rows=rows, geometry_column=self.geometry_column, crs=self.crs)

    def assign(self, **columns: Any) -> "GeoPromptFrame":
        frame = self
        for name, value in columns.items():
            if callable(value):
                resolved = value(frame)
            else:
                resolved = value

            if isinstance(resolved, Sequence) and not isinstance(resolved, (str, bytes)):
                values = list(resolved)
            else:
                values = [resolved for _ in frame._rows]

            frame = frame.with_column(name=name, values=values)
        return frame

    def _require_column(self, name: str) -> None:
        if name not in self.columns:
            raise KeyError(f"column '{name}' is not present")

    def _validate_distance_method(self, distance_method: str, other_crs: str | None = None) -> None:
        validate_distance_method_crs(distance_method, self.crs)
        if other_crs is not None:
            validate_distance_method_crs(distance_method, other_crs)

    def neighborhood_pressure(
        self,
        weight_column: str,
        scale: float = 1.0,
        power: float = 2.0,
        include_self: bool = False,
        distance_method: str = "euclidean",
    ) -> list[float]:
        self._validate_distance_method(distance_method)
        self._require_column(weight_column)
        pressures: list[float] = []
        for row in self._rows:
            total = 0.0
            for other in self._rows:
                if not include_self and row is other:
                    continue
                distance_value = geometry_distance(row[self.geometry_column], other[self.geometry_column], method=distance_method)
                total += prompt_influence(
                    weight=float(other[weight_column]),
                    distance_value=distance_value,
                    scale=scale,
                    power=power,
                )
            pressures.append(total)
        return pressures

    def anchor_influence(
        self,
        weight_column: str,
        anchor: str,
        id_column: str = "site_id",
        scale: float = 1.0,
        power: float = 2.0,
        distance_method: str = "euclidean",
    ) -> list[float]:
        self._validate_distance_method(distance_method)
        self._require_column(weight_column)
        self._require_column(id_column)
        anchor_row = next((row for row in self._rows if row[id_column] == anchor), None)
        if anchor_row is None:
            raise KeyError(f"anchor '{anchor}' was not found in column '{id_column}'")

        return [
            prompt_influence(
                weight=float(row[weight_column]),
                distance_value=geometry_distance(anchor_row[self.geometry_column], row[self.geometry_column], method=distance_method),
                scale=scale,
                power=power,
            )
            for row in self._rows
        ]

    def corridor_accessibility(
        self,
        weight_column: str,
        anchor: str,
        id_column: str = "site_id",
        scale: float = 1.0,
        power: float = 2.0,
        distance_method: str = "euclidean",
    ) -> list[float]:
        self._validate_distance_method(distance_method)
        self._require_column(weight_column)
        self._require_column(id_column)
        anchor_row = next((row for row in self._rows if row[id_column] == anchor), None)
        if anchor_row is None:
            raise KeyError(f"anchor '{anchor}' was not found in column '{id_column}'")

        return [
            corridor_strength(
                weight=float(row[weight_column]),
                corridor_length=geometry_length(row[self.geometry_column]),
                distance_value=geometry_distance(anchor_row[self.geometry_column], row[self.geometry_column], method=distance_method),
                scale=scale,
                power=power,
            )
            for row in self._rows
        ]

    def area_similarity_table(
        self,
        id_column: str = "site_id",
        scale: float = 1.0,
        power: float = 1.0,
        distance_method: str = "euclidean",
        max_distance: float | None = None,
        max_results: int | None = None,
    ) -> list[Record]:
        self._validate_distance_method(distance_method)
        self._require_column(id_column)
        centroids = self._cached_centroids
        areas = [geometry_area(row[self.geometry_column]) for row in self._rows]
        interactions: list[Record] = []
        for i, origin in enumerate(self._rows):
            for j, destination in enumerate(self._rows):
                if i == j:
                    continue
                dist = coordinate_distance(centroids[i], centroids[j], method=distance_method)
                if max_distance is not None and dist > max_distance:
                    continue
                interactions.append(
                    {
                        "origin": origin[id_column],
                        "destination": destination[id_column],
                        "area_similarity": area_similarity(
                            origin_area=areas[i],
                            destination_area=areas[j],
                            distance_value=dist,
                            scale=scale,
                            power=power,
                        ),
                        "distance_method": distance_method,
                    }
                )
                if max_results is not None and len(interactions) >= max_results:
                    return interactions
        return interactions

    def interaction_table(
        self,
        origin_weight: str,
        destination_weight: str,
        id_column: str = "site_id",
        scale: float = 1.0,
        power: float = 2.0,
        preferred_bearing: float | None = None,
        distance_method: str = "euclidean",
        max_distance: float | None = None,
        max_results: int | None = None,
    ) -> list[Record]:
        self._validate_distance_method(distance_method)
        self._require_column(origin_weight)
        self._require_column(destination_weight)
        self._require_column(id_column)

        centroids = self._cached_centroids
        interactions: list[Record] = []
        for i, origin in enumerate(self._rows):
            for j, destination in enumerate(self._rows):
                if i == j:
                    continue
                dist = coordinate_distance(centroids[i], centroids[j], method=distance_method)
                if max_distance is not None and dist > max_distance:
                    continue
                interaction = prompt_interaction(
                    origin_weight=float(origin[origin_weight]),
                    destination_weight=float(destination[destination_weight]),
                    distance_value=dist,
                    scale=scale,
                    power=power,
                )
                record: Record = {
                    "origin": origin[id_column],
                    "destination": destination[id_column],
                    "distance": dist,
                    "interaction": interaction,
                    "distance_method": distance_method,
                }
                if preferred_bearing is not None:
                    record["directional_alignment"] = directional_alignment(
                        origin=centroids[i],
                        destination=centroids[j],
                        preferred_bearing=preferred_bearing,
                    )
                interactions.append(record)
                if max_results is not None and len(interactions) >= max_results:
                    return interactions
        return interactions

    def accessibility_analysis(
        self,
        opportunities: str,
        id_column: str = "site_id",
        friction: float = 1.0,
        include_self: bool = False,
        distance_method: str = "euclidean",
    ) -> list[Record]:
        return self.analysis.accessibility(
            opportunities=opportunities,
            id_column=id_column,
            friction=friction,
            include_self=include_self,
            distance_method=distance_method,
        )

    def gravity_flow_analysis(
        self,
        origin_weight: str,
        destination_weight: str,
        id_column: str = "site_id",
        beta: float = 2.0,
        offset: float = 1e-6,
        include_self: bool = False,
        distance_method: str = "euclidean",
    ) -> list[Record]:
        return self.analysis.gravity_flow(
            origin_weight=origin_weight,
            destination_weight=destination_weight,
            id_column=id_column,
            beta=beta,
            offset=offset,
            include_self=include_self,
            distance_method=distance_method,
        )

    def suitability_analysis(
        self,
        criteria_columns: Sequence[str],
        id_column: str = "site_id",
        criteria_weights: Sequence[float] | None = None,
    ) -> list[Record]:
        return self.analysis.suitability(
            criteria_columns=criteria_columns,
            id_column=id_column,
            criteria_weights=criteria_weights,
        )


__all__ = ["Bounds", "GeoPromptAnalysis", "GeoPromptFrame"]