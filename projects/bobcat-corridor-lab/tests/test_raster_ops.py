import numpy as np

from bobcat_corridor_lab.raster_ops import (
    apply_barrier_penalties,
    suitability_to_base_resistance,
    weighted_overlay,
)


def test_weighted_overlay_scales_to_unit_interval():
    layers = {
        "land_cover": np.array([[0.2, 0.6], [0.7, 1.0]]),
        "water_distance": np.array([[0.1, 0.2], [0.3, 0.4]]),
    }
    weights = {"land_cover": 0.7, "water_distance": 0.3}

    result = weighted_overlay(layers, weights)

    assert result.shape == (2, 2)
    assert float(result.min()) >= 0.0
    assert float(result.max()) <= 1.0


def test_barrier_penalties_max_mode_applies_expected_increment():
    base = np.ones((3, 3), dtype=float)
    road = np.zeros((3, 3), dtype=bool)
    urban = np.zeros((3, 3), dtype=bool)
    ag = np.zeros((3, 3), dtype=bool)

    road[1, 1] = True
    urban[1, 1] = True
    ag[0, 0] = True

    result = apply_barrier_penalties(
        base,
        road,
        urban,
        ag,
        road_cost=10,
        urban_cost=8,
        ag_cost=3,
        method="max",
    )

    assert result[1, 1] == 11
    assert result[0, 0] == 4
    assert result[2, 2] == 1


def test_suitability_to_resistance_inverts_values():
    suitability = np.array([[0.0, 0.5, 1.0]])
    resistance = suitability_to_base_resistance(suitability, min_cost=1.0, max_cost=9.0)
    np.testing.assert_allclose(resistance, np.array([[9.0, 5.0, 1.0]]))
