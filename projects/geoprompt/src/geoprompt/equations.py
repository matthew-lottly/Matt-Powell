from __future__ import annotations

import math
from typing import Literal


Coordinate = tuple[float, float]
DistanceMethod = Literal["euclidean", "haversine"]


EARTH_RADIUS_KM = 6371.0088


def _validate_non_negative_distance(distance_value: float) -> None:
    if distance_value < 0:
        raise ValueError("distance_value must be zero or greater")


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
    _validate_non_negative_distance(distance_value)
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    if power <= 0:
        raise ValueError("power must be greater than zero")
    return 1.0 / math.pow(1.0 + (distance_value / scale), power)


def exponential_decay(distance_value: float, scale: float = 1.0) -> float:
    """Exponential distance decay: exp(-distance / scale)."""
    _validate_non_negative_distance(distance_value)
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    return math.exp(-distance_value / scale)


def gaussian_decay(distance_value: float, scale: float = 1.0) -> float:
    """Gaussian distance decay: exp(-(distance / scale)^2)."""
    _validate_non_negative_distance(distance_value)
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    ratio = distance_value / scale
    return math.exp(-(ratio * ratio))


def gravity_interaction(
    origin_weight: float,
    destination_weight: float,
    distance_value: float,
    beta: float = 2.0,
    offset: float = 1e-6,
) -> float:
    """Gravity-model interaction with configurable distance friction.

    interaction = (origin_weight * destination_weight) / (distance + offset)^beta
    """
    _validate_non_negative_distance(distance_value)
    if beta <= 0:
        raise ValueError("beta must be greater than zero")
    if offset <= 0:
        raise ValueError("offset must be greater than zero")
    denominator = math.pow(distance_value + offset, beta)
    return (float(origin_weight) * float(destination_weight)) / denominator


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
    _validate_non_negative_distance(distance_value)
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
    _validate_non_negative_distance(distance_value)
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


# ----- Custom decays (10) -----
def linear_cutoff_decay(distance_value: float, max_distance: float = 1.0) -> float:
    _validate_non_negative_distance(distance_value)
    if max_distance <= 0:
        raise ValueError("max_distance must be greater than zero")
    return max(0.0, 1.0 - distance_value / max_distance)


def logistic_decay(distance_value: float, midpoint: float = 1.0, steepness: float = 1.0) -> float:
    _validate_non_negative_distance(distance_value)
    if steepness <= 0:
        raise ValueError("steepness must be greater than zero")
    return 1.0 / (1.0 + math.exp(steepness * (distance_value - midpoint)))


def cauchy_decay(distance_value: float, scale: float = 1.0) -> float:
    _validate_non_negative_distance(distance_value)
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    ratio = distance_value / scale
    return 1.0 / (1.0 + ratio * ratio)


def inverse_square_decay(distance_value: float, scale: float = 1.0) -> float:
    _validate_non_negative_distance(distance_value)
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    ratio = distance_value / scale
    return 1.0 / (1.0 + ratio * ratio)


def tanh_decay(distance_value: float, scale: float = 1.0) -> float:
    _validate_non_negative_distance(distance_value)
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    return 1.0 - math.tanh(distance_value / scale)


def softplus_decay(distance_value: float, scale: float = 1.0) -> float:
    _validate_non_negative_distance(distance_value)
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    return 1.0 / (1.0 + math.log1p(math.exp(distance_value / scale)))


def cosine_taper_decay(distance_value: float, max_distance: float = 1.0) -> float:
    _validate_non_negative_distance(distance_value)
    if max_distance <= 0:
        raise ValueError("max_distance must be greater than zero")
    if distance_value >= max_distance:
        return 0.0
    return 0.5 * (1.0 + math.cos(math.pi * distance_value / max_distance))


def rational_quadratic_decay(distance_value: float, scale: float = 1.0, alpha: float = 1.0) -> float:
    _validate_non_negative_distance(distance_value)
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    if alpha <= 0:
        raise ValueError("alpha must be greater than zero")
    ratio2 = (distance_value / scale) ** 2
    return (1.0 + ratio2 / (2.0 * alpha)) ** (-alpha)


def gompertz_decay(distance_value: float, scale: float = 1.0, growth: float = 1.0) -> float:
    _validate_non_negative_distance(distance_value)
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    if growth <= 0:
        raise ValueError("growth must be greater than zero")
    return math.exp(-math.exp(growth * (distance_value / scale - 1.0)))


def weibull_decay(distance_value: float, scale: float = 1.0, shape: float = 2.0) -> float:
    _validate_non_negative_distance(distance_value)
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    if shape <= 0:
        raise ValueError("shape must be greater than zero")
    return math.exp(-((distance_value / scale) ** shape))


# ----- Custom interactions (10) -----
def harmonic_interaction(origin_weight: float, destination_weight: float, distance_value: float, scale: float = 1.0) -> float:
    _validate_non_negative_distance(distance_value)
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    denom = float(origin_weight) + float(destination_weight)
    if denom == 0:
        return 0.0
    harmonic_mean = 2.0 * float(origin_weight) * float(destination_weight) / denom
    return harmonic_mean * prompt_decay(distance_value, scale=scale, power=1.0)


def geometric_interaction(origin_weight: float, destination_weight: float, distance_value: float, scale: float = 1.0) -> float:
    _validate_non_negative_distance(distance_value)
    product = max(0.0, float(origin_weight) * float(destination_weight))
    return math.sqrt(product) * exponential_decay(distance_value, scale=scale)


def capped_interaction(
    origin_weight: float,
    destination_weight: float,
    distance_value: float,
    cap: float = 1.0,
    scale: float = 1.0,
) -> float:
    if cap <= 0:
        raise ValueError("cap must be greater than zero")
    raw = prompt_interaction(origin_weight, destination_weight, distance_value, scale=scale, power=1.0)
    return min(raw, cap)


def threshold_interaction(
    origin_weight: float,
    destination_weight: float,
    distance_value: float,
    threshold: float = 1.0,
    scale: float = 1.0,
) -> float:
    if threshold < 0:
        raise ValueError("threshold must be zero or greater")
    raw = prompt_interaction(origin_weight, destination_weight, distance_value, scale=scale, power=1.0)
    return raw if raw >= threshold else 0.0


def attraction_repulsion_score(
    attraction_weight: float,
    repulsion_weight: float,
    distance_value: float,
    scale: float = 1.0,
) -> float:
    _validate_non_negative_distance(distance_value)
    return (float(attraction_weight) - float(repulsion_weight)) * gaussian_decay(distance_value, scale=scale)


def balanced_opportunity_score(demand: float, supply: float, distance_value: float, scale: float = 1.0) -> float:
    _validate_non_negative_distance(distance_value)
    if demand < 0 or supply < 0:
        raise ValueError("demand and supply must be zero or greater")
    balance = 1.0 - abs(demand - supply) / (demand + supply + 1e-9)
    return balance * prompt_decay(distance_value, scale=scale, power=1.0)


def congestion_penalized_interaction(
    flow: float,
    capacity: float,
    distance_value: float,
    scale: float = 1.0,
    penalty_power: float = 2.0,
) -> float:
    _validate_non_negative_distance(distance_value)
    if capacity <= 0:
        raise ValueError("capacity must be greater than zero")
    if penalty_power <= 0:
        raise ValueError("penalty_power must be greater than zero")
    congestion = (max(0.0, flow) / capacity) ** penalty_power
    return max(0.0, flow) * prompt_decay(distance_value, scale=scale, power=1.0) / (1.0 + congestion)


def competitive_influence(primary_weight: float, competitor_weight: float, distance_value: float, scale: float = 1.0) -> float:
    _validate_non_negative_distance(distance_value)
    numerator = max(0.0, primary_weight)
    denominator = numerator + max(0.0, competitor_weight) + 1e-9
    share = numerator / denominator
    return share * prompt_decay(distance_value, scale=scale, power=1.0)


def accessibility_potential(weight: float, distance_value: float, friction: float = 1.0) -> float:
    _validate_non_negative_distance(distance_value)
    if friction <= 0:
        raise ValueError("friction must be greater than zero")
    return float(weight) / (1.0 + friction * distance_value)


def opportunity_pressure_index(opportunity_weight: float, demand_weight: float, distance_value: float, scale: float = 1.0) -> float:
    _validate_non_negative_distance(distance_value)
    weighted_sum = max(0.0, opportunity_weight) + max(0.0, demand_weight)
    return weighted_sum * logistic_decay(distance_value, midpoint=scale, steepness=1.0 / max(scale, 1e-9))


# ----- Corridor and network scores (10) -----
def corridor_reliability_score(base_strength: float, failure_rate: float, corridor_length: float) -> float:
    if base_strength < 0:
        raise ValueError("base_strength must be zero or greater")
    if not (0.0 <= failure_rate <= 1.0):
        raise ValueError("failure_rate must be between 0 and 1")
    if corridor_length < 0:
        raise ValueError("corridor_length must be zero or greater")
    return base_strength * (1.0 - failure_rate) * math.exp(-0.1 * corridor_length)


def corridor_resilience_score(redundancy: float, recovery_rate: float, hazard_intensity: float) -> float:
    if redundancy < 0 or recovery_rate < 0 or hazard_intensity < 0:
        raise ValueError("inputs must be zero or greater")
    return (1.0 + redundancy) * math.log1p(recovery_rate) / (1.0 + hazard_intensity)


def path_detour_penalty(path_length: float, straight_line_length: float) -> float:
    if path_length < 0 or straight_line_length < 0:
        raise ValueError("lengths must be zero or greater")
    if straight_line_length == 0:
        return 0.0 if path_length == 0 else 1.0
    ratio = path_length / straight_line_length
    return max(0.0, ratio - 1.0)


def route_efficiency_score(path_length: float, straight_line_length: float) -> float:
    if path_length <= 0:
        return 0.0
    if straight_line_length < 0:
        raise ValueError("straight_line_length must be zero or greater")
    return min(1.0, straight_line_length / path_length)


def anisotropic_friction_cost(distance_value: float, slope_factor: float = 0.0, wind_factor: float = 0.0) -> float:
    _validate_non_negative_distance(distance_value)
    if slope_factor < 0 or wind_factor < 0:
        raise ValueError("slope_factor and wind_factor must be zero or greater")
    return distance_value * (1.0 + slope_factor + wind_factor)


def transit_support_score(stop_density: float, service_frequency: float, walk_distance: float, scale: float = 1.0) -> float:
    _validate_non_negative_distance(walk_distance)
    if stop_density < 0 or service_frequency < 0:
        raise ValueError("stop_density and service_frequency must be zero or greater")
    return (stop_density * math.log1p(service_frequency)) * exponential_decay(walk_distance, scale=scale)


def service_overlap_penalty(overlap_ratio: float, penalty_power: float = 1.0) -> float:
    if not (0.0 <= overlap_ratio <= 1.0):
        raise ValueError("overlap_ratio must be between 0 and 1")
    if penalty_power <= 0:
        raise ValueError("penalty_power must be greater than zero")
    return overlap_ratio**penalty_power


def network_redundancy_gain(alternative_paths: float, path_diversity: float) -> float:
    if alternative_paths < 0 or path_diversity < 0:
        raise ValueError("inputs must be zero or greater")
    return math.log1p(alternative_paths) * (1.0 + path_diversity)


def directional_flow_score(flow_magnitude: float, alignment_score: float) -> float:
    if flow_magnitude < 0:
        raise ValueError("flow_magnitude must be zero or greater")
    bounded_alignment = max(-1.0, min(1.0, alignment_score))
    return flow_magnitude * (bounded_alignment + 1.0) / 2.0


def demand_supply_balance_score(demand: float, supply: float) -> float:
    if demand < 0 or supply < 0:
        raise ValueError("demand and supply must be zero or greater")
    return 1.0 - abs(demand - supply) / (demand + supply + 1e-9)


# ----- Similarity, stability, and suitability scores (10) -----
def shape_compactness_similarity(compactness_a: float, compactness_b: float) -> float:
    if compactness_a < 0 or compactness_b < 0:
        raise ValueError("compactness values must be zero or greater")
    return 1.0 - abs(compactness_a - compactness_b) / (max(compactness_a, compactness_b, 1e-9))


def density_similarity(density_a: float, density_b: float) -> float:
    if density_a < 0 or density_b < 0:
        raise ValueError("density values must be zero or greater")
    return 1.0 - abs(density_a - density_b) / (density_a + density_b + 1e-9)


def entropy_similarity(entropy_a: float, entropy_b: float, max_entropy: float = 1.0) -> float:
    if max_entropy <= 0:
        raise ValueError("max_entropy must be greater than zero")
    if entropy_a < 0 or entropy_b < 0:
        raise ValueError("entropy values must be zero or greater")
    return max(0.0, 1.0 - abs(entropy_a - entropy_b) / max_entropy)


def temporal_stability_score(mean_value: float, std_dev: float) -> float:
    if mean_value < 0 or std_dev < 0:
        raise ValueError("mean_value and std_dev must be zero or greater")
    return mean_value / (mean_value + std_dev + 1e-9)


def volatility_penalty_score(volatility: float, threshold: float = 1.0) -> float:
    if volatility < 0:
        raise ValueError("volatility must be zero or greater")
    if threshold <= 0:
        raise ValueError("threshold must be greater than zero")
    return min(1.0, volatility / threshold)


def hotspot_intensity_score(local_density: float, background_density: float) -> float:
    if local_density < 0 or background_density < 0:
        raise ValueError("densities must be zero or greater")
    return local_density / (background_density + 1e-9)


def coverage_equity_score(min_coverage: float, max_coverage: float) -> float:
    if min_coverage < 0 or max_coverage < 0:
        raise ValueError("coverage values must be zero or greater")
    if max_coverage == 0:
        return 1.0
    return min_coverage / max_coverage


def boundary_friction_score(boundary_crossings: float, total_trips: float) -> float:
    if boundary_crossings < 0 or total_trips < 0:
        raise ValueError("inputs must be zero or greater")
    if total_trips == 0:
        return 0.0
    return boundary_crossings / total_trips


def multi_scale_accessibility_score(local_score: float, regional_score: float, global_score: float, weights: tuple[float, float, float] = (0.5, 0.3, 0.2)) -> float:
    if any(value < 0 for value in (local_score, regional_score, global_score)):
        raise ValueError("scores must be zero or greater")
    if any(weight < 0 for weight in weights):
        raise ValueError("weights must be zero or greater")
    total_weight = sum(weights)
    if total_weight <= 0:
        raise ValueError("sum of weights must be greater than zero")
    return (local_score * weights[0] + regional_score * weights[1] + global_score * weights[2]) / total_weight


def composite_suitability_score(criteria_scores: tuple[float, ...], criteria_weights: tuple[float, ...] | None = None) -> float:
    if len(criteria_scores) == 0:
        raise ValueError("criteria_scores must not be empty")
    if any(score < 0 for score in criteria_scores):
        raise ValueError("criteria scores must be zero or greater")
    if criteria_weights is None:
        criteria_weights = tuple(1.0 for _ in criteria_scores)
    if len(criteria_weights) != len(criteria_scores):
        raise ValueError("criteria_weights length must match criteria_scores length")
    if any(weight < 0 for weight in criteria_weights):
        raise ValueError("criteria weights must be zero or greater")
    total_weight = sum(criteria_weights)
    if total_weight <= 0:
        raise ValueError("sum of criteria weights must be greater than zero")
    return sum(score * weight for score, weight in zip(criteria_scores, criteria_weights, strict=True)) / total_weight


# ----- Epidemiology: Disease spread and transmission (4) -----
def transmission_risk_score(contact_rate: float, susceptibility: float, distance_value: float, scale: float = 1.0) -> float:
    """Disease transmission risk based on contact rate, susceptibility, and spatial distance."""
    _validate_non_negative_distance(distance_value)
    if contact_rate < 0 or susceptibility < 0:
        raise ValueError("contact_rate and susceptibility must be zero or greater")
    bounded_susceptibility = min(1.0, susceptibility)
    return float(contact_rate) * bounded_susceptibility * exponential_decay(distance_value, scale=scale)


def incidence_rate_decay(epicenter_incidence: float, distance_value: float, scale: float = 1.0, gradient_power: float = 1.5) -> float:
    """Disease incidence decay from outbreak epicenter; models spatial diffusion pattern."""
    _validate_non_negative_distance(distance_value)
    if epicenter_incidence < 0:
        raise ValueError("epicenter_incidence must be zero or greater")
    return epicenter_incidence * (1.0 / (1.0 + (distance_value / max(scale, 1e-9)) ** gradient_power))


def vaccination_protection_score(vaccination_coverage: float, immunity_strength: float, distance_value: float, scale: float = 1.0) -> float:
    """Vaccination-based protection effectiveness considering coverage and spatial distance."""
    _validate_non_negative_distance(distance_value)
    if not (0.0 <= vaccination_coverage <= 1.0):
        raise ValueError("vaccination_coverage must be between 0 and 1")
    if not (0.0 <= immunity_strength <= 1.0):
        raise ValueError("immunity_strength must be between 0 and 1")
    return vaccination_coverage * immunity_strength * gaussian_decay(distance_value, scale=scale)


def immunity_barrier_score(herd_immunity_threshold: float, current_immunity: float, concentration_factor: float = 1.0) -> float:
    """Strength of immunity barrier to halt disease spread; depends on concentration."""
    if not (0.0 <= herd_immunity_threshold <= 1.0):
        raise ValueError("herd_immunity_threshold must be between 0 and 1")
    if not (0.0 <= current_immunity <= 1.0):
        raise ValueError("current_immunity must be between 0 and 1")
    if concentration_factor <= 0:
        raise ValueError("concentration_factor must be greater than zero")
    protection = max(0.0, current_immunity - herd_immunity_threshold) * concentration_factor
    return min(1.0, protection)


# ----- Urban Planning: Land use and development (4) -----
def land_value_gradient(city_center_value: float, distance_value: float, scale: float = 1.0, elasticity: float = 0.5) -> float:
    """Land value decrease from city center; urban economic gradient."""
    _validate_non_negative_distance(distance_value)
    if city_center_value < 0:
        raise ValueError("city_center_value must be zero or greater")
    if elasticity <= 0:
        raise ValueError("elasticity must be greater than zero")
    return city_center_value * (1.0 / (1.0 + (distance_value / max(scale, 1e-9)) ** elasticity))


def walkability_score(sidewalk_connectivity: float, intersection_density: float, pedestrian_amenities: float) -> float:
    """Combined pedestrian accessibility and comfort metrics."""
    if sidewalk_connectivity < 0 or intersection_density < 0 or pedestrian_amenities < 0:
        raise ValueError("all inputs must be zero or greater")
    bounded_connectivity = min(1.0, sidewalk_connectivity)
    bounded_density = min(1.0, intersection_density)
    bounded_amenities = min(1.0, pedestrian_amenities)
    return (bounded_connectivity * 0.4 + bounded_density * 0.35 + bounded_amenities * 0.25)


def gentrification_pressure_index(property_appreciation_rate: float, income_dynamics: float, displacement_risk: float) -> float:
    """Measure of neighborhood change pressure and gentrification risk."""
    if property_appreciation_rate < 0 or income_dynamics < 0 or displacement_risk < 0:
        raise ValueError("all inputs must be zero or greater")
    bounded_appreciation = min(1.0, property_appreciation_rate)
    bounded_income = min(1.0, income_dynamics)
    bounded_risk = min(1.0, displacement_risk)
    return (bounded_appreciation * 0.5 + bounded_income * 0.3 + bounded_risk * 0.2)


def mixed_use_score(residential_ratio: float, commercial_ratio: float, industrial_ratio: float) -> float:
    """Diversity and balance of land uses in a district."""
    if any(r < 0 or r > 1.0 for r in [residential_ratio, commercial_ratio, industrial_ratio]):
        raise ValueError("all ratios must be between 0 and 1")
    total = residential_ratio + commercial_ratio + industrial_ratio
    if total < 0.01:
        return 0.0
    normalized_res = residential_ratio / total
    normalized_com = commercial_ratio / total
    normalized_ind = industrial_ratio / total
    entropy = -(normalized_res * math.log(normalized_res + 1e-9) + normalized_com * math.log(normalized_com + 1e-9) + normalized_ind * math.log(normalized_ind + 1e-9))
    max_entropy = math.log(3.0)
    return min(1.0, entropy / max_entropy)


# ----- Transportation: Routing and mobility (4) -----
def traffic_congestion_index(current_flow: float, capacity: float, speed_reduction: float = 0.0) -> float:
    """Real-time traffic congestion impact on network efficiency."""
    if current_flow < 0 or capacity <= 0:
        raise ValueError("current_flow must be non-negative; capacity must be positive")
    if not (0.0 <= speed_reduction <= 1.0):
        raise ValueError("speed_reduction must be between 0 and 1")
    utilization = current_flow / capacity
    congestion = min(1.0, utilization ** 1.5 * (1.0 + speed_reduction))
    return congestion


def transit_accessibility_score(stop_distance: float, service_frequency: float, network_coverage: float, scale: float = 500.0) -> float:
    """Public transportation access quality combining proximity, frequency, and coverage."""
    _validate_non_negative_distance(stop_distance)
    if service_frequency < 0 or network_coverage < 0:
        raise ValueError("service_frequency and network_coverage must be zero or greater")
    distance_factor = exponential_decay(stop_distance, scale=scale)
    frequency_factor = min(1.0, service_frequency / 60.0)
    coverage_factor = min(1.0, network_coverage)
    return (distance_factor * 0.5 + frequency_factor * 0.3 + coverage_factor * 0.2)


def parking_availability_factor(available_spaces: float, demand: float, walking_distance_to_lot: float) -> float:
    """Parking pressure and availability factor for urban districts."""
    if available_spaces < 0 or demand < 0:
        raise ValueError("available_spaces and demand must be zero or greater")
    _validate_non_negative_distance(walking_distance_to_lot)
    if demand == 0:
        return 1.0
    availability_ratio = available_spaces / (demand + 1e-9)
    distance_friction = 1.0 / (1.0 + walking_distance_to_lot / 100.0)
    return min(1.0, (availability_ratio + 1.0) * distance_friction / 2.0)


def mode_share_incentive(car_travel_time: float, transit_travel_time: float, bike_travel_time: float, emission_cost: float = 0.1) -> float:
    """Incentive strength to shift toward lower-emission transportation; lower time = higher incentive."""
    if car_travel_time <= 0 or transit_travel_time < 0 or bike_travel_time < 0:
        raise ValueError("travel times must be positive or zero")
    if emission_cost < 0:
        raise ValueError("emission_cost must be zero or greater")
    car_penalty = car_travel_time * (1.0 + emission_cost)
    alt_time = min(transit_travel_time, bike_travel_time)
    if alt_time == 0:
        return 1.0
    incentive = 1.0 - (alt_time / car_penalty)
    return max(0.0, min(1.0, incentive))


# ----- Environmental: Pollution and habitat (4) -----
def pollution_dispersion_model(source_intensity: float, distance_value: float, wind_factor: float = 0.0, scale: float = 1.0) -> float:
    """Air/water pollution concentration decay from point source with directional factors."""
    _validate_non_negative_distance(distance_value)
    if source_intensity < 0:
        raise ValueError("source_intensity must be zero or greater")
    if wind_factor < 0:
        raise ValueError("wind_factor must be zero or greater")
    distance_decay = gaussian_decay(distance_value, scale=scale)
    dispersion_factor = 1.0 / (1.0 + wind_factor * distance_value)
    return source_intensity * distance_decay * dispersion_factor


def habitat_fragmentation_score(patch_size: float, nearest_patch_distance: float, connectivity_index: float) -> float:
    """Degree of habitat isolation and fragmentation; lower is more fragmented."""
    if patch_size < 0 or connectivity_index < 0:
        raise ValueError("patch_size and connectivity_index must be zero or greater")
    _validate_non_negative_distance(nearest_patch_distance)
    size_factor = math.log1p(patch_size)
    isolation_factor = 1.0 / (1.0 + nearest_patch_distance)
    return size_factor * isolation_factor * (1.0 + connectivity_index)


def climate_vulnerability_index(exposure_level: float, sensitivity_level: float, adaptive_capacity: float) -> float:
    """Composite climate change vulnerability: exposure + sensitivity - adaptation."""
    if any(v < 0 or v > 1.0 for v in [exposure_level, sensitivity_level, adaptive_capacity]):
        raise ValueError("all inputs must be between 0 and 1")
    vulnerability = exposure_level * sensitivity_level * (1.0 - adaptive_capacity + 0.1)
    return min(1.0, max(0.0, vulnerability))


def green_space_benefits_radius(park_area: float, distance_value: float, benefit_type: str = "cooling") -> float:
    """Benefits of nearby parks/forests; varies by benefit type."""
    _validate_non_negative_distance(distance_value)
    if park_area < 0:
        raise ValueError("park_area must be zero or greater")
    if benefit_type not in ["cooling", "air_quality", "recreation"]:
        raise ValueError("benefit_type must be 'cooling', 'air_quality', or 'recreation'")
    benefit_scales = {"cooling": 250.0, "air_quality": 500.0, "recreation": 1000.0}
    scale = benefit_scales[benefit_type]
    area_factor = math.log1p(park_area)
    return area_factor * exponential_decay(distance_value, scale=scale)


# ----- Population Dynamics: Migration and demographics (4) -----
def migration_attraction_index(economic_opportunity: float, quality_of_life: float, cultural_alignment: float, distance_value: float, scale: float = 100.0) -> float:
    """Attractiveness of destination for population movement."""
    _validate_non_negative_distance(distance_value)
    if any(v < 0 or v > 1.0 for v in [economic_opportunity, quality_of_life, cultural_alignment]):
        raise ValueError("all scores must be between 0 and 1")
    attraction = economic_opportunity * 0.4 + quality_of_life * 0.35 + cultural_alignment * 0.25
    distance_factor = exponential_decay(distance_value, scale=scale)
    return attraction * distance_factor


def birth_rate_modifier(baseline_rate: float, economic_stress: float, healthcare_quality: float, education_level: float) -> float:
    """Environmental factors modifying birth rates."""
    if baseline_rate < 0:
        raise ValueError("baseline_rate must be zero or greater")
    if any(v < 0 or v > 1.0 for v in [economic_stress, healthcare_quality, education_level]):
        raise ValueError("factors must be between 0 and 1")
    stress_factor = 1.0 - economic_stress * 0.3
    healthcare_factor = 1.0 + healthcare_quality * 0.2
    education_factor = 1.0 - education_level * 0.25
    return baseline_rate * stress_factor * healthcare_factor * education_factor


def mortality_risk_index(age_weighted_population: float, disease_burden: float, healthcare_access: float, environmental_hazard: float = 0.0) -> float:
    """Death risk from various causes and environmental factors."""
    if age_weighted_population < 0 or disease_burden < 0:
        raise ValueError("age_weighted_population and disease_burden must be zero or greater")
    if not (0.0 <= healthcare_access <= 1.0):
        raise ValueError("healthcare_access must be between 0 and 1")
    if environmental_hazard < 0:
        raise ValueError("environmental_hazard must be zero or greater")
    base_risk = age_weighted_population * disease_burden
    healthcare_mitigation = 1.0 - min(healthcare_access, 0.5)
    total_hazard = 1.0 + environmental_hazard
    return base_risk * healthcare_mitigation * total_hazard


def population_carrying_capacity(resource_availability: float, infrastructure_adequacy: float, environmental_limit: float, current_population: float = 1.0) -> float:
    """Maximum sustainable population given resources and constraints."""
    if any(v < 0 for v in [resource_availability, infrastructure_adequacy, environmental_limit, current_population]):
        raise ValueError("all inputs must be zero or greater")
    if resource_availability + infrastructure_adequacy + environmental_limit == 0:
        return 0.0
    combined_capacity = (resource_availability + infrastructure_adequacy) * (1.0 + environmental_limit)
    return max(1.0, combined_capacity)


# ----- Economics: Markets and trade (4) -----
def market_concentration_index(largest_firm_share: float, herfindahl_index: float) -> float:
    """Market power concentration; higher = more concentrated."""
    if not (0.0 <= largest_firm_share <= 1.0):
        raise ValueError("largest_firm_share must be between 0 and 1")
    if herfindahl_index < 0 or herfindahl_index > 1.0:
        raise ValueError("herfindahl_index must be between 0 and 1")
    concentration = largest_firm_share * 0.6 + herfindahl_index * 0.4
    return concentration


def trade_flow_intensity(export_value: float, import_value: float, distance_value: float, bilateral_agreement: float = 0.0) -> float:
    """Intensity of economic exchange based on trade volumes and distance."""
    _validate_non_negative_distance(distance_value)
    if export_value < 0 or import_value < 0:
        raise ValueError("export_value and import_value must be zero or greater")
    if not (0.0 <= bilateral_agreement <= 1.0):
        raise ValueError("bilateral_agreement must be between 0 and 1")
    trade_volume = (export_value + import_value) / 2.0
    agreement_boost = 1.0 + bilateral_agreement
    return trade_volume * agreement_boost * exponential_decay(distance_value, scale=1000.0)


def business_cluster_advantage(firm_count: float, average_firm_size: float, knowledge_spillover_rate: float, distance_value: float, scale: float = 5.0) -> float:
    """Agglomeration benefits from co-location; positive feedback loop."""
    if firm_count < 0 or average_firm_size < 0 or knowledge_spillover_rate < 0:
        raise ValueError("inputs must be zero or greater")
    _validate_non_negative_distance(distance_value)
    if not (0.0 <= knowledge_spillover_rate <= 1.0):
        raise ValueError("knowledge_spillover_rate must be between 0 and 1")
    cluster_size = math.log1p(firm_count * average_firm_size)
    spillover_benefit = 1.0 + knowledge_spillover_rate
    proximity_factor = exponential_decay(distance_value, scale=scale)
    return cluster_size * spillover_benefit * proximity_factor


def consumer_purchasing_power(median_income: float, employment_rate: float, consumer_sentiment: float) -> float:
    """Local economic spending capacity and demand strength."""
    if median_income < 0 or employment_rate < 0 or consumer_sentiment < 0:
        raise ValueError("all inputs must be zero or greater")
    if not (0.0 <= employment_rate <= 1.0):
        raise ValueError("employment_rate must be between 0 and 1")
    bounded_sentiment = max(-0.5, min(1.0, consumer_sentiment))
    purchasing_power = median_income * employment_rate * (1.0 + bounded_sentiment * 0.5)
    return purchasing_power


# ----- Social Networks: Information and influence (4) -----
def information_diffusion_rate(adopter_fraction: float, network_connectivity: float, time_period: float = 1.0, virality_factor: float = 0.1) -> float:
    """Speed of information/innovation spread through social networks."""
    if adopter_fraction < 0 or network_connectivity < 0 or time_period <= 0 or virality_factor < 0:
        raise ValueError("inputs must be zero or greater; time_period must be positive")
    bounded_adoption = min(1.0, adopter_fraction)
    bounded_connectivity = min(1.0, network_connectivity)
    diffusion = bounded_adoption * bounded_connectivity * (1.0 + virality_factor) / time_period
    return min(1.0, diffusion)


def community_cohesion_score(internal_ties: float, external_ties: float, shared_identity_strength: float) -> float:
    """Strength of internal social bonds versus external connections."""
    if internal_ties < 0 or external_ties < 0:
        raise ValueError("ties must be zero or greater")
    if not (0.0 <= shared_identity_strength <= 1.0):
        raise ValueError("shared_identity_strength must be between 0 and 1")
    if internal_ties + external_ties == 0:
        return 0.0
    cohesion_ratio = internal_ties / (internal_ties + external_ties)
    return cohesion_ratio * shared_identity_strength


def cultural_similarity_index(value_alignment: float, language_similarity: float, tradition_overlap: float, history_shared: float) -> float:
    """Compatibility between communities based on cultural factors."""
    if any(v < 0 or v > 1.0 for v in [value_alignment, language_similarity, tradition_overlap, history_shared]):
        raise ValueError("all inputs must be between 0 and 1")
    similarity = (value_alignment * 0.3 + language_similarity * 0.25 + tradition_overlap * 0.25 + history_shared * 0.2)
    return similarity


def network_centrality_influence(degree_centrality: float, betweenness_centrality: float, eigenvector_centrality: float) -> float:
    """Influence based on network position and connectivity patterns."""
    if any(c < 0 for c in [degree_centrality, betweenness_centrality, eigenvector_centrality]):
        raise ValueError("all centrality measures must be zero or greater")
    if any(c > 1.0 for c in [degree_centrality, betweenness_centrality, eigenvector_centrality]):
        raise ValueError("all centrality measures must be at most 1")
    influence = (degree_centrality * 0.4 + betweenness_centrality * 0.35 + eigenvector_centrality * 0.25)
    return influence


# ----- Noise & Visibility: Acoustic and visual propagation (4) -----
def noise_propagation_level(source_decibels: float, distance_value: float, atmospheric_conditions: float = 0.0, barriers: float = 0.0) -> float:
    """Acoustic noise level decrease from point source with environmental factors."""
    _validate_non_negative_distance(distance_value)
    if source_decibels < 0:
        raise ValueError("source_decibels must be zero or greater")
    if atmospheric_conditions < 0 or barriers < 0:
        raise ValueError("atmospheric_conditions and barriers must be zero or greater")
    distance_attenuation = 20.0 * math.log10(distance_value + 1.0)
    atmospheric_absorption = atmospheric_conditions * 0.5
    barrier_absorption = barriers
    total_absorption = distance_attenuation + atmospheric_absorption + barrier_absorption
    return max(0.0, source_decibels - total_absorption)


def visual_prominence_score(vertical_extent: float, visibility_range: float, distinctiveness: float, distance_value: float, scale: float = 1.0) -> float:
    """Visibility and landmark quality; how prominent a feature appears."""
    _validate_non_negative_distance(distance_value)
    if vertical_extent < 0 or visibility_range < 0 or distinctiveness < 0:
        raise ValueError("all inputs must be zero or greater")
    bounded_distinctiveness = min(1.0, distinctiveness)
    prominence = (math.log1p(vertical_extent) * 0.4 + math.log1p(visibility_range) * 0.35 + bounded_distinctiveness * 0.25)
    distance_visibility = exponential_decay(distance_value, scale=scale)
    return prominence * distance_visibility


def sky_view_factor(obstruction_height: float, obstruction_distance: float, azimuth_coverage: float = 1.0) -> float:
    """Proportion of sky visible from location; inverse of urban canyon effect."""
    if obstruction_height < 0:
        raise ValueError("obstruction_height must be zero or greater")
    _validate_non_negative_distance(obstruction_distance)
    if not (0.0 <= azimuth_coverage <= 1.0):
        raise ValueError("azimuth_coverage must be between 0 and 1")
    if obstruction_distance == 0:
        sky_view = 0.0
    else:
        obstruction_angle = math.atan(obstruction_height / obstruction_distance)
        max_angle = math.pi / 2.0
        sky_view = 1.0 - (obstruction_angle / max_angle)
    return sky_view * azimuth_coverage


def acoustic_reverberation_index(surface_reflectivity: float, room_volume: float, absorption_coefficient: float) -> float:
    """Sound reflection and reverberation strength in enclosed/semi-enclosed spaces."""
    if surface_reflectivity < 0 or room_volume < 0:
        raise ValueError("surface_reflectivity and room_volume must be zero or greater")
    if not (0.0 <= absorption_coefficient <= 1.0):
        raise ValueError("absorption_coefficient must be between 0 and 1")
    if room_volume == 0:
        return 0.0
    reverberation = surface_reflectivity * math.log1p(room_volume) * (1.0 - absorption_coefficient)
    return min(1.0, max(0.0, reverberation))


# ----- Extended equation set (40) -----
def entropy_evenness_index(values: tuple[float, ...]) -> float:
    if not values:
        raise ValueError("values must not be empty")
    if any(v < 0 for v in values):
        raise ValueError("values must be zero or greater")
    total = sum(values)
    if total == 0:
        return 0.0
    probabilities = [v / total for v in values if v > 0]
    entropy = -sum(p * math.log(p) for p in probabilities)
    max_entropy = math.log(len(values))
    return 0.0 if max_entropy == 0 else entropy / max_entropy


def gini_inequality_index(values: tuple[float, ...]) -> float:
    if not values:
        raise ValueError("values must not be empty")
    if any(v < 0 for v in values):
        raise ValueError("values must be zero or greater")
    ordered = sorted(values)
    n = len(ordered)
    total = sum(ordered)
    if total == 0:
        return 0.0
    weighted_sum = sum((i + 1) * value for i, value in enumerate(ordered))
    return (2.0 * weighted_sum) / (n * total) - (n + 1) / n


def normalized_access_gap(expected_service: float, observed_service: float) -> float:
    if expected_service < 0 or observed_service < 0:
        raise ValueError("service values must be zero or greater")
    if expected_service == 0:
        return 0.0 if observed_service == 0 else 1.0
    gap = (expected_service - observed_service) / expected_service
    return max(0.0, min(1.0, gap))


def service_reliability_decay(reliability: float, disruption_rate: float, periods: float) -> float:
    if not (0.0 <= reliability <= 1.0):
        raise ValueError("reliability must be between 0 and 1")
    if disruption_rate < 0 or periods < 0:
        raise ValueError("disruption_rate and periods must be zero or greater")
    return reliability * math.exp(-disruption_rate * periods)


def adaptive_capacity_score(income_index: float, education_index: float, health_index: float, governance_index: float) -> float:
    if any(v < 0 or v > 1.0 for v in (income_index, education_index, health_index, governance_index)):
        raise ValueError("all indices must be between 0 and 1")
    return income_index * 0.25 + education_index * 0.25 + health_index * 0.25 + governance_index * 0.25


def hazard_exposure_score(hazard_frequency: float, hazard_intensity: float, population_exposed: float) -> float:
    if hazard_frequency < 0 or hazard_intensity < 0 or population_exposed < 0:
        raise ValueError("inputs must be zero or greater")
    return hazard_frequency * hazard_intensity * math.log1p(population_exposed)


def evacuation_time_index(distance_km: float, road_capacity: float, congestion_factor: float = 0.0) -> float:
    if distance_km < 0 or road_capacity <= 0:
        raise ValueError("distance_km must be zero or greater and road_capacity must be positive")
    if congestion_factor < 0:
        raise ValueError("congestion_factor must be zero or greater")
    return distance_km * (1.0 + congestion_factor) / road_capacity


def flood_storage_effectiveness(storage_volume: float, runoff_volume: float, conveyance_efficiency: float) -> float:
    if storage_volume < 0 or runoff_volume < 0:
        raise ValueError("volumes must be zero or greater")
    if not (0.0 <= conveyance_efficiency <= 1.0):
        raise ValueError("conveyance_efficiency must be between 0 and 1")
    if runoff_volume == 0:
        return 1.0
    return min(1.0, (storage_volume / runoff_volume) * conveyance_efficiency)


def drought_stress_index(water_demand: float, water_supply: float, reserve_ratio: float = 0.0) -> float:
    if water_demand < 0 or water_supply < 0:
        raise ValueError("water_demand and water_supply must be zero or greater")
    if reserve_ratio < 0:
        raise ValueError("reserve_ratio must be zero or greater")
    effective_supply = water_supply * (1.0 + reserve_ratio)
    if effective_supply == 0:
        return 1.0 if water_demand > 0 else 0.0
    return min(1.0, water_demand / effective_supply)


def heat_island_intensity(impervious_ratio: float, tree_canopy_ratio: float, albedo: float) -> float:
    if any(v < 0 or v > 1.0 for v in (impervious_ratio, tree_canopy_ratio, albedo)):
        raise ValueError("all ratios must be between 0 and 1")
    intensity = impervious_ratio * 0.6 + (1.0 - tree_canopy_ratio) * 0.3 + (1.0 - albedo) * 0.1
    return max(0.0, min(1.0, intensity))


def renewable_penetration_score(renewable_generation: float, total_generation: float, storage_support: float = 0.0) -> float:
    if renewable_generation < 0 or total_generation < 0:
        raise ValueError("generation values must be zero or greater")
    if storage_support < 0:
        raise ValueError("storage_support must be zero or greater")
    if total_generation == 0:
        return 0.0
    base = renewable_generation / total_generation
    adjusted = base * (1.0 + min(1.0, storage_support))
    return min(1.0, adjusted)


def energy_burden_score(monthly_energy_cost: float, monthly_income: float) -> float:
    if monthly_energy_cost < 0 or monthly_income < 0:
        raise ValueError("cost and income must be zero or greater")
    if monthly_income == 0:
        return 1.0 if monthly_energy_cost > 0 else 0.0
    return min(1.0, monthly_energy_cost / monthly_income)


def housing_affordability_pressure(median_rent: float, median_income: float) -> float:
    if median_rent < 0 or median_income < 0:
        raise ValueError("median_rent and median_income must be zero or greater")
    if median_income == 0:
        return 1.0 if median_rent > 0 else 0.0
    return min(1.0, (12.0 * median_rent) / median_income)


def rental_displacement_risk(rent_growth: float, wage_growth: float, eviction_rate: float) -> float:
    if rent_growth < 0 or wage_growth < 0:
        raise ValueError("growth values must be zero or greater")
    if not (0.0 <= eviction_rate <= 1.0):
        raise ValueError("eviction_rate must be between 0 and 1")
    growth_gap = max(0.0, rent_growth - wage_growth)
    risk = 1.0 - math.exp(-(growth_gap + eviction_rate))
    return min(1.0, risk)


def school_access_score(seat_capacity: float, student_population: float, travel_time: float, scale: float = 30.0) -> float:
    if seat_capacity < 0 or student_population < 0:
        raise ValueError("seat_capacity and student_population must be zero or greater")
    _validate_non_negative_distance(travel_time)
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    if student_population == 0:
        capacity_ratio = 1.0
    else:
        capacity_ratio = min(1.0, seat_capacity / student_population)
    return capacity_ratio * exponential_decay(travel_time, scale=scale)


def healthcare_access_index(provider_count: float, population: float, travel_time: float, scale: float = 45.0) -> float:
    if provider_count < 0 or population < 0:
        raise ValueError("provider_count and population must be zero or greater")
    _validate_non_negative_distance(travel_time)
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    providers_per_capita = provider_count / (population + 1e-9)
    return providers_per_capita * exponential_decay(travel_time, scale=scale)


def food_desert_risk(grocery_density: float, vehicle_access: float, transit_access: float) -> float:
    if grocery_density < 0:
        raise ValueError("grocery_density must be zero or greater")
    if not (0.0 <= vehicle_access <= 1.0 and 0.0 <= transit_access <= 1.0):
        raise ValueError("access values must be between 0 and 1")
    protection = min(1.0, grocery_density) * 0.5 + vehicle_access * 0.3 + transit_access * 0.2
    return 1.0 - protection


def digital_divide_index(broadband_coverage: float, device_access: float, digital_literacy: float) -> float:
    if any(v < 0 or v > 1.0 for v in (broadband_coverage, device_access, digital_literacy)):
        raise ValueError("all inputs must be between 0 and 1")
    access_score = broadband_coverage * 0.4 + device_access * 0.3 + digital_literacy * 0.3
    return 1.0 - access_score


def emergency_response_score(station_density: float, response_time: float, coverage_ratio: float, scale: float = 10.0) -> float:
    if station_density < 0:
        raise ValueError("station_density must be zero or greater")
    _validate_non_negative_distance(response_time)
    if not (0.0 <= coverage_ratio <= 1.0):
        raise ValueError("coverage_ratio must be between 0 and 1")
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    return min(1.0, station_density) * coverage_ratio * exponential_decay(response_time, scale=scale)


def wildfire_risk_index(fuel_load: float, dryness_index: float, wind_speed: float, suppression_capacity: float) -> float:
    if fuel_load < 0 or dryness_index < 0 or wind_speed < 0:
        raise ValueError("fuel_load, dryness_index, and wind_speed must be zero or greater")
    if not (0.0 <= suppression_capacity <= 1.0):
        raise ValueError("suppression_capacity must be between 0 and 1")
    base = math.log1p(fuel_load) * dryness_index * math.log1p(wind_speed)
    mitigation = 1.0 - suppression_capacity
    return base * mitigation


def landslide_susceptibility(slope_degrees: float, soil_erodibility: float, rainfall_intensity: float, vegetation_cover: float) -> float:
    if slope_degrees < 0 or soil_erodibility < 0 or rainfall_intensity < 0:
        raise ValueError("slope_degrees, soil_erodibility, and rainfall_intensity must be zero or greater")
    if not (0.0 <= vegetation_cover <= 1.0):
        raise ValueError("vegetation_cover must be between 0 and 1")
    slope_factor = math.tan(math.radians(min(slope_degrees, 89.0)))
    return slope_factor * soil_erodibility * rainfall_intensity * (1.0 - vegetation_cover)


def coastal_inundation_risk(surge_height: float, elevation: float, defense_level: float) -> float:
    if surge_height < 0 or elevation < 0:
        raise ValueError("surge_height and elevation must be zero or greater")
    if not (0.0 <= defense_level <= 1.0):
        raise ValueError("defense_level must be between 0 and 1")
    effective_elevation = elevation * (1.0 + defense_level)
    if effective_elevation == 0:
        return 1.0 if surge_height > 0 else 0.0
    return min(1.0, surge_height / effective_elevation)


def carbon_intensity_score(emissions: float, activity_output: float) -> float:
    if emissions < 0 or activity_output < 0:
        raise ValueError("emissions and activity_output must be zero or greater")
    if activity_output == 0:
        return 0.0
    return emissions / activity_output


def circularity_score(recycled_input: float, total_input: float, waste_recovery: float = 0.0) -> float:
    if recycled_input < 0 or total_input < 0:
        raise ValueError("recycled_input and total_input must be zero or greater")
    if not (0.0 <= waste_recovery <= 1.0):
        raise ValueError("waste_recovery must be between 0 and 1")
    if total_input == 0:
        return 0.0
    return min(1.0, recycled_input / total_input + waste_recovery * 0.2)


def supply_chain_resilience(supplier_diversity: float, inventory_days: float, lead_time_variability: float) -> float:
    if supplier_diversity < 0 or inventory_days < 0 or lead_time_variability < 0:
        raise ValueError("inputs must be zero or greater")
    diversity_factor = math.log1p(supplier_diversity)
    inventory_factor = math.log1p(inventory_days)
    penalty = 1.0 + lead_time_variability
    return (diversity_factor * inventory_factor) / penalty


def procurement_risk_score(single_source_ratio: float, geopolitical_risk: float, price_volatility: float) -> float:
    if not (0.0 <= single_source_ratio <= 1.0 and 0.0 <= geopolitical_risk <= 1.0):
        raise ValueError("single_source_ratio and geopolitical_risk must be between 0 and 1")
    if price_volatility < 0:
        raise ValueError("price_volatility must be zero or greater")
    raw = single_source_ratio * 0.5 + geopolitical_risk * 0.3 + min(1.0, price_volatility) * 0.2
    return min(1.0, raw)


def labor_market_tightness(open_positions: float, active_seekers: float) -> float:
    if open_positions < 0 or active_seekers < 0:
        raise ValueError("open_positions and active_seekers must be zero or greater")
    if active_seekers == 0:
        return float(open_positions > 0)
    return open_positions / active_seekers


def innovation_velocity(patent_count: float, rnd_spend: float, collaboration_index: float) -> float:
    if patent_count < 0 or rnd_spend < 0:
        raise ValueError("patent_count and rnd_spend must be zero or greater")
    if not (0.0 <= collaboration_index <= 1.0):
        raise ValueError("collaboration_index must be between 0 and 1")
    return math.log1p(patent_count) * math.log1p(rnd_spend) * (1.0 + collaboration_index)


def productivity_efficiency(output_units: float, labor_hours: float, capital_index: float = 1.0) -> float:
    if output_units < 0 or labor_hours < 0:
        raise ValueError("output_units and labor_hours must be zero or greater")
    if capital_index <= 0:
        raise ValueError("capital_index must be greater than zero")
    if labor_hours == 0:
        return 0.0
    return output_units / (labor_hours * capital_index)


def fiscal_stability_index(revenue: float, expenditure: float, debt_service: float) -> float:
    if revenue < 0 or expenditure < 0 or debt_service < 0:
        raise ValueError("revenue, expenditure, and debt_service must be zero or greater")
    obligations = expenditure + debt_service
    if obligations == 0:
        return 1.0
    return min(1.0, revenue / obligations)


def scenario_robustness_score(base_outcome: float, stress_outcomes: tuple[float, ...]) -> float:
    if base_outcome < 0:
        raise ValueError("base_outcome must be zero or greater")
    if not stress_outcomes:
        raise ValueError("stress_outcomes must not be empty")
    if any(value < 0 for value in stress_outcomes):
        raise ValueError("stress outcomes must be zero or greater")
    if base_outcome == 0:
        return 0.0
    min_stress = min(stress_outcomes)
    return max(0.0, min(1.0, min_stress / base_outcome))


def uncertainty_penalty(interval_width: float, estimate_magnitude: float) -> float:
    if interval_width < 0 or estimate_magnitude < 0:
        raise ValueError("interval_width and estimate_magnitude must be zero or greater")
    if estimate_magnitude == 0:
        return 1.0 if interval_width > 0 else 0.0
    return min(1.0, interval_width / estimate_magnitude)


def bayesian_update_weight(prior_confidence: float, evidence_quality: float, sample_size: float) -> float:
    if not (0.0 <= prior_confidence <= 1.0 and 0.0 <= evidence_quality <= 1.0):
        raise ValueError("prior_confidence and evidence_quality must be between 0 and 1")
    if sample_size < 0:
        raise ValueError("sample_size must be zero or greater")
    sample_factor = sample_size / (sample_size + 10.0)
    return prior_confidence * (1.0 - sample_factor) + evidence_quality * sample_factor


def signal_to_noise_ratio_score(signal_strength: float, noise_level: float) -> float:
    if signal_strength < 0 or noise_level < 0:
        raise ValueError("signal_strength and noise_level must be zero or greater")
    if noise_level == 0:
        return float("inf") if signal_strength > 0 else 0.0
    return signal_strength / noise_level


def calibration_error_score(predicted: float, observed: float) -> float:
    if predicted < 0 or observed < 0:
        raise ValueError("predicted and observed must be zero or greater")
    denom = observed + 1e-9
    return abs(predicted - observed) / denom


def fairness_parity_score(group_a_rate: float, group_b_rate: float) -> float:
    if group_a_rate < 0 or group_b_rate < 0:
        raise ValueError("group rates must be zero or greater")
    max_rate = max(group_a_rate, group_b_rate)
    if max_rate == 0:
        return 1.0
    return min(group_a_rate, group_b_rate) / max_rate


def anomaly_severity_score(z_score: float, persistence: float, spatial_extent: float) -> float:
    if z_score < 0 or persistence < 0 or spatial_extent < 0:
        raise ValueError("inputs must be zero or greater")
    return z_score * math.log1p(persistence) * math.log1p(spatial_extent)


def trend_momentum_score(recent_change: float, long_term_change: float, volatility: float) -> float:
    if volatility < 0:
        raise ValueError("volatility must be zero or greater")
    return (recent_change - long_term_change) / (1.0 + volatility)


def queue_delay_factor(arrival_rate: float, service_rate: float) -> float:
    if arrival_rate < 0 or service_rate <= 0:
        raise ValueError("arrival_rate must be zero or greater and service_rate must be positive")
    utilization = arrival_rate / service_rate
    if utilization >= 1.0:
        return float("inf")
    return utilization / (1.0 - utilization)


def infrastructure_lifecycle_score(age_years: float, design_life_years: float, maintenance_quality: float) -> float:
    if age_years < 0 or design_life_years <= 0:
        raise ValueError("age_years must be zero or greater and design_life_years must be positive")
    if not (0.0 <= maintenance_quality <= 1.0):
        raise ValueError("maintenance_quality must be between 0 and 1")
    wear = min(1.0, age_years / design_life_years)
    return max(0.0, 1.0 - wear * (1.0 - 0.5 * maintenance_quality))


__all__ = [
    "Coordinate",
    "DistanceMethod",
    "EARTH_RADIUS_KM",
    "area_similarity",
    "coordinate_distance",
    "corridor_strength",
    "directional_alignment",
    "directional_bearing",
    "directional_flow_score",
    "demand_supply_balance_score",
    "density_similarity",
    "entropy_similarity",
    "euclidean_distance",
    "exponential_decay",
    "hotspot_intensity_score",
    "harmonic_interaction",
    "linear_cutoff_decay",
    "logistic_decay",
    "multi_scale_accessibility_score",
    "network_redundancy_gain",
    "opportunity_pressure_index",
    "path_detour_penalty",
    "gaussian_decay",
    "geometric_interaction",
    "gompertz_decay",
    "gravity_interaction",
    "haversine_distance",
    "inverse_square_decay",
    "rational_quadratic_decay",
    "route_efficiency_score",
    "service_overlap_penalty",
    "shape_compactness_similarity",
    "softplus_decay",
    "tanh_decay",
    "temporal_stability_score",
    "threshold_interaction",
    "transit_support_score",
    "volatility_penalty_score",
    "weibull_decay",
    "accessibility_potential",
    "anisotropic_friction_cost",
    "attraction_repulsion_score",
    "balanced_opportunity_score",
    "boundary_friction_score",
    "capped_interaction",
    "competitive_influence",
    "composite_suitability_score",
    "corridor_reliability_score",
    "corridor_resilience_score",
    "cosine_taper_decay",
    "coverage_equity_score",
    "cauchy_decay",
    "congestion_penalized_interaction",
    "prompt_decay",
    "prompt_influence",
    "prompt_interaction",
    # Epidemiology
    "transmission_risk_score",
    "incidence_rate_decay",
    "vaccination_protection_score",
    "immunity_barrier_score",
    # Urban Planning
    "land_value_gradient",
    "walkability_score",
    "gentrification_pressure_index",
    "mixed_use_score",
    # Transportation
    "traffic_congestion_index",
    "transit_accessibility_score",
    "parking_availability_factor",
    "mode_share_incentive",
    # Environmental
    "pollution_dispersion_model",
    "habitat_fragmentation_score",
    "climate_vulnerability_index",
    "green_space_benefits_radius",
    # Population Dynamics
    "migration_attraction_index",
    "birth_rate_modifier",
    "mortality_risk_index",
    "population_carrying_capacity",
    # Economics
    "market_concentration_index",
    "trade_flow_intensity",
    "business_cluster_advantage",
    "consumer_purchasing_power",
    # Social Networks
    "information_diffusion_rate",
    "community_cohesion_score",
    "cultural_similarity_index",
    "network_centrality_influence",
    # Noise & Visibility
    "noise_propagation_level",
    "visual_prominence_score",
    "sky_view_factor",
    "acoustic_reverberation_index",
    "entropy_evenness_index",
    "gini_inequality_index",
    "normalized_access_gap",
    "service_reliability_decay",
    "adaptive_capacity_score",
    "hazard_exposure_score",
    "evacuation_time_index",
    "flood_storage_effectiveness",
    "drought_stress_index",
    "heat_island_intensity",
    "renewable_penetration_score",
    "energy_burden_score",
    "housing_affordability_pressure",
    "rental_displacement_risk",
    "school_access_score",
    "healthcare_access_index",
    "food_desert_risk",
    "digital_divide_index",
    "emergency_response_score",
    "wildfire_risk_index",
    "landslide_susceptibility",
    "coastal_inundation_risk",
    "carbon_intensity_score",
    "circularity_score",
    "supply_chain_resilience",
    "procurement_risk_score",
    "labor_market_tightness",
    "innovation_velocity",
    "productivity_efficiency",
    "fiscal_stability_index",
    "scenario_robustness_score",
    "uncertainty_penalty",
    "bayesian_update_weight",
    "signal_to_noise_ratio_score",
    "calibration_error_score",
    "fairness_parity_score",
    "anomaly_severity_score",
    "trend_momentum_score",
    "queue_delay_factor",
    "infrastructure_lifecycle_score",
]