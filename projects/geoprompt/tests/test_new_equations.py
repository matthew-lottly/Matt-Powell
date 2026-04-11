from __future__ import annotations

import math

from geoprompt.equations import (
    adaptive_capacity_score,
    anomaly_severity_score,
    bayesian_update_weight,
    calibration_error_score,
    carbon_intensity_score,
    circularity_score,
    coastal_inundation_risk,
    digital_divide_index,
    drought_stress_index,
    emergency_response_score,
    energy_burden_score,
    entropy_evenness_index,
    evacuation_time_index,
    fairness_parity_score,
    fiscal_stability_index,
    flood_storage_effectiveness,
    food_desert_risk,
    gini_inequality_index,
    hazard_exposure_score,
    healthcare_access_index,
    heat_island_intensity,
    housing_affordability_pressure,
    infrastructure_lifecycle_score,
    innovation_velocity,
    labor_market_tightness,
    landslide_susceptibility,
    normalized_access_gap,
    procurement_risk_score,
    productivity_efficiency,
    queue_delay_factor,
    rental_displacement_risk,
    renewable_penetration_score,
    scenario_robustness_score,
    school_access_score,
    service_reliability_decay,
    signal_to_noise_ratio_score,
    supply_chain_resilience,
    trend_momentum_score,
    uncertainty_penalty,
    wildfire_risk_index,
)


def test_new_equations_execute_and_return_finite_values() -> None:
    values = [
        entropy_evenness_index((1.0, 2.0, 3.0)),
        gini_inequality_index((1.0, 2.0, 3.0, 4.0)),
        normalized_access_gap(100.0, 75.0),
        service_reliability_decay(0.95, disruption_rate=0.1, periods=12.0),
        adaptive_capacity_score(0.7, 0.8, 0.6, 0.9),
        hazard_exposure_score(3.0, 0.8, 1000.0),
        evacuation_time_index(12.0, road_capacity=2.5, congestion_factor=0.2),
        flood_storage_effectiveness(80.0, runoff_volume=100.0, conveyance_efficiency=0.9),
        drought_stress_index(120.0, water_supply=100.0, reserve_ratio=0.1),
        heat_island_intensity(0.7, tree_canopy_ratio=0.25, albedo=0.2),
        renewable_penetration_score(40.0, total_generation=100.0, storage_support=0.3),
        energy_burden_score(250.0, monthly_income=3000.0),
        housing_affordability_pressure(1200.0, median_income=55000.0),
        rental_displacement_risk(0.09, wage_growth=0.03, eviction_rate=0.04),
        school_access_score(900.0, student_population=1000.0, travel_time=15.0),
        healthcare_access_index(40.0, population=50000.0, travel_time=20.0),
        food_desert_risk(0.35, vehicle_access=0.6, transit_access=0.55),
        digital_divide_index(0.75, device_access=0.65, digital_literacy=0.6),
        emergency_response_score(0.7, response_time=6.0, coverage_ratio=0.9),
        wildfire_risk_index(30.0, dryness_index=0.8, wind_speed=20.0, suppression_capacity=0.4),
        landslide_susceptibility(28.0, soil_erodibility=0.6, rainfall_intensity=0.7, vegetation_cover=0.3),
        coastal_inundation_risk(1.8, elevation=3.0, defense_level=0.2),
        carbon_intensity_score(500.0, activity_output=200.0),
        circularity_score(35.0, total_input=100.0, waste_recovery=0.4),
        supply_chain_resilience(8.0, inventory_days=30.0, lead_time_variability=0.4),
        procurement_risk_score(0.5, geopolitical_risk=0.35, price_volatility=0.25),
        labor_market_tightness(1500.0, active_seekers=4000.0),
        innovation_velocity(120.0, rnd_spend=50000.0, collaboration_index=0.7),
        productivity_efficiency(10000.0, labor_hours=2200.0, capital_index=1.2),
        fiscal_stability_index(120.0, expenditure=90.0, debt_service=20.0),
        scenario_robustness_score(100.0, stress_outcomes=(94.0, 88.0, 90.0)),
        uncertainty_penalty(8.0, estimate_magnitude=40.0),
        bayesian_update_weight(0.4, evidence_quality=0.8, sample_size=30.0),
        signal_to_noise_ratio_score(12.0, noise_level=3.0),
        calibration_error_score(95.0, observed=100.0),
        fairness_parity_score(0.72, group_b_rate=0.68),
        anomaly_severity_score(2.5, persistence=4.0, spatial_extent=10.0),
        trend_momentum_score(0.12, long_term_change=0.08, volatility=0.05),
        queue_delay_factor(80.0, service_rate=120.0),
        infrastructure_lifecycle_score(18.0, design_life_years=40.0, maintenance_quality=0.8),
    ]

    for value in values:
        assert math.isfinite(value)


def test_new_equation_bounds_and_expected_ranges() -> None:
    assert 0.0 <= entropy_evenness_index((2.0, 2.0, 2.0)) <= 1.0
    assert 0.0 <= gini_inequality_index((2.0, 2.0, 2.0)) <= 1.0
    assert 0.0 <= normalized_access_gap(10.0, 7.5) <= 1.0
    assert 0.0 <= service_reliability_decay(0.9, 0.2, 3.0) <= 1.0
    assert 0.0 <= adaptive_capacity_score(0.8, 0.7, 0.9, 0.6) <= 1.0
    assert 0.0 <= flood_storage_effectiveness(10.0, 20.0, 1.0) <= 1.0
    assert 0.0 <= drought_stress_index(100.0, 150.0, 0.0) <= 1.0
    assert 0.0 <= heat_island_intensity(0.8, 0.1, 0.2) <= 1.0
    assert 0.0 <= renewable_penetration_score(30.0, 100.0, 0.5) <= 1.0
    assert 0.0 <= energy_burden_score(200.0, 1000.0) <= 1.0
    assert 0.0 <= housing_affordability_pressure(1000.0, 60000.0) <= 1.0
    assert 0.0 <= rental_displacement_risk(0.08, 0.05, 0.03) <= 1.0
    assert 0.0 <= food_desert_risk(0.4, 0.5, 0.5) <= 1.0
    assert 0.0 <= digital_divide_index(0.8, 0.8, 0.8) <= 1.0
    assert 0.0 <= emergency_response_score(0.5, 4.0, 0.9) <= 1.0
    assert 0.0 <= coastal_inundation_risk(1.0, 3.0, 0.4) <= 1.0
    assert 0.0 <= circularity_score(40.0, 100.0, 0.2) <= 1.0
    assert 0.0 <= procurement_risk_score(0.6, 0.5, 0.3) <= 1.0
    assert 0.0 <= fiscal_stability_index(100.0, 70.0, 20.0) <= 1.0
    assert 0.0 <= scenario_robustness_score(100.0, (90.0, 95.0, 92.0)) <= 1.0
    assert 0.0 <= uncertainty_penalty(5.0, 20.0) <= 1.0
    assert 0.0 <= bayesian_update_weight(0.2, 0.9, 100.0) <= 1.0
    assert 0.0 <= fairness_parity_score(0.7, 0.9) <= 1.0
    assert 0.0 <= infrastructure_lifecycle_score(10.0, 40.0, 0.7) <= 1.0


def test_selected_equation_behavior_properties() -> None:
    assert entropy_evenness_index((1.0, 1.0, 1.0)) > entropy_evenness_index((3.0, 0.0, 0.0))
    assert renewable_penetration_score(70.0, 100.0, 0.5) >= renewable_penetration_score(70.0, 100.0, 0.0)
    assert school_access_score(1000.0, 1000.0, travel_time=5.0) > school_access_score(1000.0, 1000.0, travel_time=25.0)
    assert healthcare_access_index(50.0, 50000.0, travel_time=5.0) > healthcare_access_index(50.0, 50000.0, travel_time=30.0)
    assert queue_delay_factor(95.0, 100.0) > queue_delay_factor(60.0, 100.0)
