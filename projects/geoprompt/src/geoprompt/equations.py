from __future__ import annotations

import math
from typing import Literal, Sequence


Coordinate = tuple[float, float]
DistanceMethod = Literal["euclidean", "haversine"]
DecayMethod = Literal["power", "exponential", "gaussian"]


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


def exponential_decay(distance_value: float, rate: float = 1.0) -> float:
    """Exponential distance-decay function: exp(-rate * distance)."""
    if rate <= 0:
        raise ValueError("rate must be greater than zero")
    if distance_value < 0:
        raise ValueError("distance_value must be zero or greater")
    return math.exp(-rate * distance_value)


def gaussian_decay(distance_value: float, sigma: float = 1.0) -> float:
    """Gaussian distance-decay function."""
    if sigma <= 0:
        raise ValueError("sigma must be greater than zero")
    if distance_value < 0:
        raise ValueError("distance_value must be zero or greater")
    return math.exp(-(distance_value**2) / (2.0 * sigma**2))


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


def gravity_interaction(
    origin_mass: float,
    destination_mass: float,
    generalized_cost: float,
    alpha: float = 1.0,
    beta: float = 1.0,
    gamma: float = 1.0,
    scale_factor: float = 1.0,
) -> float:
    """Gravity model interaction with configurable exponents."""
    if generalized_cost <= 0:
        raise ValueError("generalized_cost must be greater than zero")
    if alpha <= 0 or beta <= 0 or gamma <= 0:
        raise ValueError("alpha, beta, and gamma must be greater than zero")
    if scale_factor <= 0:
        raise ValueError("scale_factor must be greater than zero")
    if origin_mass < 0 or destination_mass < 0:
        raise ValueError("origin_mass and destination_mass must be zero or greater")

    return scale_factor * (origin_mass**alpha) * (destination_mass**beta) / (generalized_cost**gamma)


def logistic_service_probability(
    predictors: dict[str, float],
    coefficients: dict[str, float],
    intercept: float = 0.0,
) -> float:
    """Logistic service probability from named predictors and coefficients."""
    linear = float(intercept)
    for name, value in predictors.items():
        linear += float(value) * float(coefficients.get(name, 0.0))
    # Stable sigmoid implementation.
    if linear >= 0:
        z = math.exp(-linear)
        return 1.0 / (1.0 + z)
    z = math.exp(linear)
    return z / (1.0 + z)


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


def age_adjusted_failure_rate(
    base_failure_rate: float,
    asset_age_years: float,
    aging_factor: float = 0.03,
) -> float:
    """Age-adjusted failure rate using an exponential aging curve."""
    if base_failure_rate < 0:
        raise ValueError("base_failure_rate must be zero or greater")
    if asset_age_years < 0:
        raise ValueError("asset_age_years must be zero or greater")
    if aging_factor < 0:
        raise ValueError("aging_factor must be zero or greater")
    return base_failure_rate * math.exp(aging_factor * asset_age_years)


def expected_outage_impact(failure_probability: float, consequence: float) -> float:
    """Expected outage impact = probability x consequence."""
    if not 0.0 <= failure_probability <= 1.0:
        raise ValueError("failure_probability must be in [0, 1]")
    if consequence < 0:
        raise ValueError("consequence must be zero or greater")
    return failure_probability * consequence


def weighted_accessibility_score(
    supply_values: Sequence[float],
    travel_costs: Sequence[float],
    decay_method: DecayMethod = "power",
    scale: float = 1.0,
    power: float = 2.0,
    rate: float = 1.0,
    sigma: float = 1.0,
) -> float:
    """Accessibility score as weighted, decayed supply reach."""
    if len(supply_values) != len(travel_costs):
        raise ValueError("supply_values and travel_costs must have the same length")

    score = 0.0
    for supply, cost in zip(supply_values, travel_costs):
        if cost < 0:
            raise ValueError("travel_costs must be zero or greater")
        if decay_method == "power":
            decay = prompt_decay(cost, scale=scale, power=power)
        elif decay_method == "exponential":
            decay = exponential_decay(cost, rate=rate)
        else:
            decay = gaussian_decay(cost, sigma=sigma)
        score += float(supply) * decay
    return score


def accessibility_gini(values: Sequence[float]) -> float:
    """Gini coefficient for accessibility equity diagnostics."""
    if not values:
        return 0.0
    cleaned = sorted(max(0.0, float(v)) for v in values)
    n = len(cleaned)
    total = sum(cleaned)
    if total == 0:
        return 0.0
    weighted_sum = 0.0
    for index, value in enumerate(cleaned, start=1):
        weighted_sum += index * value
    return (2.0 * weighted_sum) / (n * total) - (n + 1.0) / n


def composite_resilience_index(
    redundancy: float,
    recovery_speed: float,
    robustness: float,
    service_deficit: float,
    weights: tuple[float, float, float, float] = (0.3, 0.25, 0.25, 0.2),
) -> float:
    """Composite resilience score from positive and penalty components."""
    w1, w2, w3, w4 = weights
    if any(weight < 0 for weight in weights):
        raise ValueError("weights must be zero or greater")
    if sum(weights) == 0:
        raise ValueError("at least one weight must be greater than zero")
    norm = sum(weights)
    score = (
        w1 * float(redundancy)
        + w2 * float(recovery_speed)
        + w3 * float(robustness)
        - w4 * float(service_deficit)
    ) / norm
    return score


__all__ = [
    "Coordinate",
    "DecayMethod",
    "DistanceMethod",
    "EARTH_RADIUS_KM",
    "accessibility_gini",
    "age_adjusted_failure_rate",
    "area_similarity",
    "composite_resilience_index",
    "coordinate_distance",
    "corridor_strength",
    "directional_alignment",
    "directional_bearing",
    "expected_outage_impact",
    "exponential_decay",
    "euclidean_distance",
    "gaussian_decay",
    "gravity_interaction",
    "haversine_distance",
    "logistic_service_probability",
    "prompt_decay",
    "prompt_influence",
    "prompt_interaction",
    "utility_capacity_stress_index",
    "utility_headloss_hazen_williams",
    "utility_service_deficit",
    "weighted_accessibility_score",
]