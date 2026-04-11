from __future__ import annotations

import math
from pathlib import Path

from geoprompt.io import read_features


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _centroid_distances(frame) -> list[float]:
    center = frame.centroid()
    centroids = [row["geometry"]["coordinates"] if row["geometry"]["type"] == "Point" else None for row in frame.to_records()]
    resolved = []
    for idx, value in enumerate(centroids):
        if value is None:
            resolved.append(frame._cached_centroids[idx])
        else:
            resolved.append((float(value[0]), float(value[1])))
    return [math.dist(c, center) for c in resolved]


def test_open_source_math_parity_for_new_tools() -> None:
    frame = read_features(PROJECT_ROOT / "data" / "sample_features.json", crs="EPSG:4326")
    rows = frame.to_records()
    distances = _centroid_distances(frame)

    drought_rows = frame.analysis.drought_stress_map("demand_index", "capacity_index", "priority_index")
    for row, out in zip(rows, drought_rows, strict=True):
        demand = max(0.0, float(row["demand_index"]))
        supply = max(0.0, float(row["capacity_index"]))
        reserve = max(0.0, min(1.0, float(row["priority_index"])))
        expected = min(1.0, demand / (supply * (1.0 + reserve)))
        assert math.isclose(float(out["drought_stress"]), expected, rel_tol=1e-9)

    school_rows = frame.analysis.school_access_map("capacity_index", "demand_index")
    for row, dist, out in zip(rows, distances, school_rows, strict=True):
        capacity = max(0.0, float(row["capacity_index"]))
        demand = max(0.0, float(row["demand_index"]))
        ratio = 1.0 if demand == 0.0 else min(1.0, capacity / demand)
        expected = ratio * math.exp(-(dist / 30.0))
        assert math.isclose(float(out["school_access"]), expected, rel_tol=1e-9)

    healthcare_rows = frame.analysis.healthcare_access_map("capacity_index", "demand_index")
    for row, dist, out in zip(rows, distances, healthcare_rows, strict=True):
        providers = max(0.0, float(row["capacity_index"]))
        population = max(0.0, float(row["demand_index"]))
        expected = (providers / (population + 1e-9)) * math.exp(-(dist / 45.0))
        assert math.isclose(float(out["healthcare_access"]), expected, rel_tol=1e-9)

    emergency_rows = frame.analysis.emergency_response_map("capacity_index", "demand_index")
    for row, dist, out in zip(rows, distances, emergency_rows, strict=True):
        station_density = max(0.0, min(1.0, float(row["capacity_index"])))
        coverage_ratio = max(0.0, min(1.0, float(row["demand_index"])))
        expected = station_density * coverage_ratio * math.exp(-(dist / 10.0))
        assert math.isclose(float(out["emergency_response"]), expected, rel_tol=1e-9)

    heat_rows = frame.analysis.heat_island_map("demand_index", "capacity_index", "priority_index")
    for row, out in zip(rows, heat_rows, strict=True):
        impervious = max(0.0, min(1.0, float(row["demand_index"])))
        canopy = max(0.0, min(1.0, float(row["capacity_index"])))
        albedo = max(0.0, min(1.0, float(row["priority_index"])))
        expected = max(0.0, min(1.0, impervious * 0.6 + (1.0 - canopy) * 0.3 + (1.0 - albedo) * 0.1))
        assert math.isclose(float(out["heat_island_intensity"]), expected, rel_tol=1e-9)

    food_rows = frame.analysis.food_desert_map("demand_index", "capacity_index", "priority_index")
    for row, out in zip(rows, food_rows, strict=True):
        grocery = max(0.0, min(1.0, float(row["demand_index"])))
        vehicle = max(0.0, min(1.0, float(row["capacity_index"])))
        transit = max(0.0, min(1.0, float(row["priority_index"])))
        expected = 1.0 - (grocery * 0.5 + vehicle * 0.3 + transit * 0.2)
        assert math.isclose(float(out["food_desert_risk"]), expected, rel_tol=1e-9)

    digital_rows = frame.analysis.digital_divide_map("demand_index", "capacity_index", "priority_index")
    for row, out in zip(rows, digital_rows, strict=True):
        broadband = max(0.0, min(1.0, float(row["demand_index"])))
        device = max(0.0, min(1.0, float(row["capacity_index"])))
        literacy = max(0.0, min(1.0, float(row["priority_index"])))
        expected = 1.0 - (broadband * 0.4 + device * 0.3 + literacy * 0.3)
        assert math.isclose(float(out["digital_divide"]), expected, rel_tol=1e-9)

    wildfire_rows = frame.analysis.wildfire_risk_map("demand_index", "capacity_index", "priority_index", "capacity_index")
    for row, out in zip(rows, wildfire_rows, strict=True):
        fuel = max(0.0, float(row["demand_index"]))
        dryness = max(0.0, float(row["capacity_index"]))
        wind = max(0.0, float(row["priority_index"]))
        suppression = max(0.0, min(1.0, float(row["capacity_index"])))
        expected = math.log1p(fuel) * dryness * math.log1p(wind) * (1.0 - suppression)
        assert math.isclose(float(out["wildfire_risk"]), expected, rel_tol=1e-9)

    infra_rows = frame.analysis.infrastructure_lifecycle_map("demand_index", "capacity_index", "priority_index")
    for row, out in zip(rows, infra_rows, strict=True):
        age = max(0.0, float(row["demand_index"]))
        life = max(1e-9, float(row["capacity_index"]))
        maintenance = max(0.0, min(1.0, float(row["priority_index"])))
        wear = min(1.0, age / life)
        expected = max(0.0, 1.0 - wear * (1.0 - 0.5 * maintenance))
        assert math.isclose(float(out["infrastructure_lifecycle"]), expected, rel_tol=1e-9)

    adaptive_rows = frame.analysis.adaptive_capacity_map("demand_index", "capacity_index", "priority_index", "demand_index")
    for row, out in zip(rows, adaptive_rows, strict=True):
        income = max(0.0, min(1.0, float(row["demand_index"])))
        education = max(0.0, min(1.0, float(row["capacity_index"])))
        health = max(0.0, min(1.0, float(row["priority_index"])))
        governance = max(0.0, min(1.0, float(row["demand_index"])))
        expected = income * 0.25 + education * 0.25 + health * 0.25 + governance * 0.25
        assert math.isclose(float(out["adaptive_capacity"]), expected, rel_tol=1e-9)
