from __future__ import annotations

import math
from typing import Literal


Coordinate = tuple[float, float]
DistanceMethod = Literal["euclidean", "haversine"]


EARTH_RADIUS_KM = 6371.0088


def euclidean_distance(origin: Coordinate, destination: Coordinate) -> float:
    dx = destination[0] - origin[0]
    dy = destination[1] - origin[1]
    return math.hypot(dx, dy)


def haversine_distance(origin: Coordinate, destination: Coordinate, radius_km: float = EARTH_RADIUS_KM) -> float:
    if radius_km <= 0:
        raise ValueError("radius_km must be greater than zero")

    origin_lon = math.radians(origin[0])
    origin_lat = math.radians(origin[1])
    destination_lon = math.radians(destination[0])
    destination_lat = math.radians(destination[1])

    delta_lon = destination_lon - origin_lon
    delta_lat = destination_lat - origin_lat
    half_chord = (
        math.sin(delta_lat / 2.0) ** 2
        + math.cos(origin_lat) * math.cos(destination_lat) * math.sin(delta_lon / 2.0) ** 2
    )
    angular_distance = 2.0 * math.atan2(math.sqrt(half_chord), math.sqrt(1.0 - half_chord))
    return radius_km * angular_distance


def coordinate_distance(origin: Coordinate, destination: Coordinate, method: DistanceMethod = "euclidean") -> float:
    if method == "euclidean":
        return euclidean_distance(origin, destination)
    if method == "haversine":
        return haversine_distance(origin, destination)
    raise ValueError(f"unsupported distance method: {method}")


def prompt_decay(distance_value: float, scale: float = 1.0, power: float = 2.0) -> float:
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    if power <= 0:
        raise ValueError("power must be greater than zero")
    return 1.0 / math.pow(1.0 + (distance_value / scale), power)


def prompt_influence(weight: float, distance_value: float, scale: float = 1.0, power: float = 2.0) -> float:
    return float(weight) * prompt_decay(distance_value=distance_value, scale=scale, power=power)


def prompt_interaction(
    origin_weight: float,
    destination_weight: float,
    distance_value: float,
    scale: float = 1.0,
    power: float = 2.0,
) -> float:
    return float(origin_weight) * float(destination_weight) * prompt_decay(
        distance_value=distance_value,
        scale=scale,
        power=power,
    )


def corridor_strength(
    weight: float,
    corridor_length: float,
    distance_value: float,
    scale: float = 1.0,
    power: float = 2.0,
) -> float:
    if corridor_length < 0:
        raise ValueError("corridor_length must be zero or greater")
    corridor_factor = math.log1p(corridor_length)
    return float(weight) * corridor_factor * prompt_decay(distance_value=distance_value, scale=scale, power=power)


def area_similarity(
    origin_area: float,
    destination_area: float,
    distance_value: float,
    scale: float = 1.0,
    power: float = 1.0,
) -> float:
    if origin_area < 0 or destination_area < 0:
        raise ValueError("areas must be zero or greater")
    if origin_area == 0 and destination_area == 0:
        size_ratio = 1.0
    else:
        size_ratio = min(origin_area, destination_area) / max(origin_area, destination_area)
    return size_ratio * prompt_decay(distance_value=distance_value, scale=scale, power=power)


def directional_bearing(origin: Coordinate, destination: Coordinate) -> float:
    dx = destination[0] - origin[0]
    dy = destination[1] - origin[1]
    bearing = math.degrees(math.atan2(dx, dy))
    return (bearing + 360.0) % 360.0


def directional_alignment(origin: Coordinate, destination: Coordinate, preferred_bearing: float) -> float:
    observed_bearing = directional_bearing(origin=origin, destination=destination)
    delta = math.radians(observed_bearing - preferred_bearing)
    return math.cos(delta)


# ─── Utility network helpers ─────────────────────────────────────────────────


def utility_capacity_stress_index(
    load: float, capacity: float, stress_power: float = 2.0
) -> float:
    """Return a stress index in [0, ∞) comparing *load* to *capacity*.

    ``stress = (load / capacity) ** stress_power`` when capacity > 0, else 0.
    """
    if capacity <= 0:
        return 0.0
    return (load / capacity) ** stress_power


def utility_service_deficit(demand: float, delivered: float) -> float:
    """Return the fraction of *demand* that was **not** delivered.

    Result is clamped to [0, 1].
    """
    if demand <= 0:
        return 0.0
    return max(0.0, min(1.0, (demand - delivered) / demand))


def utility_headloss_hazen_williams(
    length: float,
    flow: float,
    diameter: float,
    roughness_coefficient: float = 130.0,
) -> float:
    """Simplified Hazen-Williams head-loss for a single pipe segment.

    ``headloss = 10.67 * length * (flow / roughness)^1.852 / diameter^4.87``
    """
    if diameter <= 0 or roughness_coefficient <= 0:
        return 0.0
    return (
        10.67
        * length
        * (flow / roughness_coefficient) ** 1.852
        / diameter ** 4.87
    )


__all__ = [
    "Coordinate",
    "DistanceMethod",
    "EARTH_RADIUS_KM",
    "area_similarity",
    "coordinate_distance",
    "corridor_strength",
    "directional_alignment",
    "directional_bearing",
    "euclidean_distance",
    "haversine_distance",
    "prompt_decay",
    "prompt_influence",
    "prompt_interaction",
    "utility_capacity_stress_index",
    "utility_headloss_hazen_williams",
    "utility_service_deficit",
]