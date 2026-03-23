import math

from geoprompt import exponential_kernel, gaussian_kernel, inverse_distance_weight


def test_inverse_distance_weight_supports_offset_form() -> None:
    weight = inverse_distance_weight(3.0, power=1.0, min_distance=0.0, offset=1.0)
    assert abs(weight - 0.25) < 1e-12


def test_gaussian_kernel_matches_standard_form() -> None:
    observed = gaussian_kernel(2.0, bandwidth=4.0)
    expected = math.exp(-0.5 * (2.0 / 4.0) ** 2)
    assert abs(observed - expected) < 1e-12


def test_exponential_kernel_matches_standard_form() -> None:
    observed = exponential_kernel(3.0, scale=2.0)
    expected = math.exp(-1.5)
    assert abs(observed - expected) < 1e-12


def test_shared_kernels_are_monotone_decreasing() -> None:
    assert gaussian_kernel(0.5, bandwidth=1.0) > gaussian_kernel(1.5, bandwidth=1.0)
    assert exponential_kernel(0.5, scale=1.0) > exponential_kernel(1.5, scale=1.0)
    assert inverse_distance_weight(0.5, min_distance=0.0, offset=1.0) > inverse_distance_weight(1.5, min_distance=0.0, offset=1.0)