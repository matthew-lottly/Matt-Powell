from __future__ import annotations

import math
from pathlib import Path

import pytest

from geoprompt.io import read_features


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sample_frame():
    return read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")


@pytest.mark.parametrize(
    ("tool_name", "expected_key", "pairwise"),
    [
        ("accessibility", "accessibility_score", False),
        ("gravity_flow", "gravity_flow", True),
        ("suitability", "suitability_score", False),
        ("catchment_competition", "competition_score", False),
        ("hotspot_scan", "hotspot_score", False),
        ("equity_gap", "coverage_equity", False),
        ("network_reliability", "network_reliability", False),
        ("transit_service_gap", "transit_service_gap", False),
        ("congestion_hotspots", "congestion_index", False),
        ("walkability_audit", "walkability_score", False),
        ("gentrification_scan", "gentrification_pressure", False),
        ("land_value_surface", "land_value_estimate", False),
        ("pollution_surface", "pollution_intensity", False),
        ("habitat_fragmentation_map", "fragmentation_score", False),
        ("climate_vulnerability_map", "climate_vulnerability", False),
        ("migration_pull_map", "migration_attraction", False),
        ("mortality_risk_map", "mortality_risk", False),
        ("market_power_map", "market_power", False),
        ("trade_corridor_map", "trade_intensity", True),
        ("community_cohesion_map", "community_cohesion", False),
        ("cultural_similarity_matrix", "cultural_similarity", True),
        ("noise_impact_map", "noise_level", False),
        ("visual_prominence_map", "visual_prominence", False),
        ("drought_stress_map", "drought_stress", False),
        ("heat_island_map", "heat_island_intensity", False),
        ("school_access_map", "school_access", False),
        ("healthcare_access_map", "healthcare_access", False),
        ("food_desert_map", "food_desert_risk", False),
        ("digital_divide_map", "digital_divide", False),
        ("wildfire_risk_map", "wildfire_risk", False),
        ("emergency_response_map", "emergency_response", False),
        ("infrastructure_lifecycle_map", "infrastructure_lifecycle", False),
        ("adaptive_capacity_map", "adaptive_capacity", False),
    ],
)
def test_all_analysis_tools_execute(sample_frame, tool_name: str, expected_key: str, pairwise: bool) -> None:
    analysis = sample_frame.analysis

    if tool_name == "accessibility":
        rows = analysis.accessibility(opportunities="demand_index")
    elif tool_name == "gravity_flow":
        rows = analysis.gravity_flow(origin_weight="capacity_index", destination_weight="demand_index")
    elif tool_name == "suitability":
        rows = analysis.suitability(criteria_columns=["demand_index", "capacity_index", "priority_index"])
    elif tool_name == "catchment_competition":
        rows = analysis.catchment_competition(demand_column="demand_index", supply_column="capacity_index")
    elif tool_name == "hotspot_scan":
        rows = analysis.hotspot_scan(value_column="demand_index")
    elif tool_name == "equity_gap":
        rows = analysis.equity_gap(min_column="capacity_index", max_column="priority_index")
    elif tool_name == "network_reliability":
        rows = analysis.network_reliability(capacity_column="capacity_index", failure_proxy_column="demand_index")
    elif tool_name == "transit_service_gap":
        rows = analysis.transit_service_gap(service_frequency_column="capacity_index", coverage_column="demand_index")
    elif tool_name == "congestion_hotspots":
        rows = analysis.congestion_hotspots(flow_column="demand_index", capacity_column="capacity_index")
    elif tool_name == "walkability_audit":
        rows = analysis.walkability_audit(
            connectivity_column="demand_index",
            density_column="capacity_index",
            amenities_column="priority_index",
        )
    elif tool_name == "gentrification_scan":
        rows = analysis.gentrification_scan(
            appreciation_column="priority_index",
            income_column="capacity_index",
            displacement_column="demand_index",
        )
    elif tool_name == "land_value_surface":
        rows = analysis.land_value_surface(base_value_column="priority_index")
    elif tool_name == "pollution_surface":
        rows = analysis.pollution_surface(source_column="priority_index")
    elif tool_name == "habitat_fragmentation_map":
        rows = analysis.habitat_fragmentation_map(patch_column="capacity_index", connectivity_column="demand_index")
    elif tool_name == "climate_vulnerability_map":
        rows = analysis.climate_vulnerability_map(
            exposure_column="priority_index",
            sensitivity_column="demand_index",
            adaptive_column="capacity_index",
        )
    elif tool_name == "migration_pull_map":
        rows = analysis.migration_pull_map(
            economic_column="demand_index",
            quality_column="capacity_index",
            cultural_column="priority_index",
        )
    elif tool_name == "mortality_risk_map":
        rows = analysis.mortality_risk_map(
            population_column="priority_index",
            disease_column="demand_index",
            healthcare_column="capacity_index",
        )
    elif tool_name == "market_power_map":
        rows = analysis.market_power_map(largest_share_column="demand_index", concentration_column="capacity_index")
    elif tool_name == "trade_corridor_map":
        rows = analysis.trade_corridor_map(export_column="capacity_index", import_column="demand_index")
    elif tool_name == "community_cohesion_map":
        rows = analysis.community_cohesion_map(
            internal_column="capacity_index",
            external_column="demand_index",
            identity_column="priority_index",
        )
    elif tool_name == "cultural_similarity_matrix":
        rows = analysis.cultural_similarity_matrix(
            value_column="demand_index",
            language_column="capacity_index",
            tradition_column="priority_index",
            history_column="demand_index",
        )
    elif tool_name == "noise_impact_map":
        rows = analysis.noise_impact_map(source_column="priority_index", barrier_column="capacity_index")
    elif tool_name == "visual_prominence_map":
        rows = analysis.visual_prominence_map(
            vertical_column="priority_index",
            range_column="capacity_index",
            distinctiveness_column="demand_index",
        )
    elif tool_name == "drought_stress_map":
        rows = analysis.drought_stress_map(
            demand_column="demand_index",
            supply_column="capacity_index",
            reserve_column="priority_index",
        )
    elif tool_name == "heat_island_map":
        rows = analysis.heat_island_map(
            impervious_column="demand_index",
            canopy_column="capacity_index",
            albedo_column="priority_index",
        )
    elif tool_name == "school_access_map":
        rows = analysis.school_access_map(
            capacity_column="capacity_index",
            demand_column="demand_index",
        )
    elif tool_name == "healthcare_access_map":
        rows = analysis.healthcare_access_map(
            provider_column="capacity_index",
            population_column="demand_index",
        )
    elif tool_name == "food_desert_map":
        rows = analysis.food_desert_map(
            grocery_column="demand_index",
            vehicle_column="capacity_index",
            transit_column="priority_index",
        )
    elif tool_name == "digital_divide_map":
        rows = analysis.digital_divide_map(
            broadband_column="demand_index",
            device_column="capacity_index",
            literacy_column="priority_index",
        )
    elif tool_name == "wildfire_risk_map":
        rows = analysis.wildfire_risk_map(
            fuel_column="demand_index",
            dryness_column="capacity_index",
            wind_column="priority_index",
            suppression_column="capacity_index",
        )
    elif tool_name == "emergency_response_map":
        rows = analysis.emergency_response_map(
            station_column="capacity_index",
            coverage_column="demand_index",
        )
    elif tool_name == "infrastructure_lifecycle_map":
        rows = analysis.infrastructure_lifecycle_map(
            age_column="demand_index",
            life_column="capacity_index",
            maintenance_column="priority_index",
        )
    elif tool_name == "adaptive_capacity_map":
        rows = analysis.adaptive_capacity_map(
            income_column="demand_index",
            education_column="capacity_index",
            health_column="priority_index",
            governance_column="demand_index",
        )
    else:
        raise AssertionError(f"Unknown tool {tool_name}")

    expected_len = len(sample_frame) * (len(sample_frame) - 1) if pairwise else len(sample_frame)
    assert len(rows) == expected_len
    assert all(expected_key in row for row in rows)

    for row in rows:
        value = row[expected_key]
        if isinstance(value, (float, int)):
            assert math.isfinite(float(value))


def test_frame_wrappers_cover_primary_callable_tools(sample_frame) -> None:
    assert len(sample_frame.accessibility_analysis(opportunities="demand_index")) == len(sample_frame)
    assert len(sample_frame.suitability_analysis(["demand_index", "capacity_index", "priority_index"])) == len(sample_frame)
    assert len(sample_frame.gravity_flow_analysis("capacity_index", "demand_index")) == len(sample_frame) * (len(sample_frame) - 1)
