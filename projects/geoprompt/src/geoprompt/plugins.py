"""Plugin hooks for custom decay functions and influence kernels (items 61-62)."""

from __future__ import annotations

import math
from typing import Any, Callable, Protocol

from .exceptions import PluginError


class DecayFunction(Protocol):
    """Protocol for custom decay functions."""
    def __call__(self, distance_value: float, scale: float, power: float) -> float: ...


class InfluenceKernel(Protocol):
    """Protocol for alternative influence kernels."""
    def __call__(self, weight: float, distance_value: float, **kwargs: Any) -> float: ...


# Built-in decay functions
def inverse_power_decay(distance_value: float, scale: float = 1.0, power: float = 2.0) -> float:
    """Default inverse-power decay: 1 / (1 + distance/scale)^power."""
    return 1.0 / math.pow(1.0 + (distance_value / scale), power)


def gaussian_decay(distance_value: float, scale: float = 1.0, power: float = 2.0) -> float:
    """Gaussian decay: exp(-(distance/scale)^2)."""
    return math.exp(-((distance_value / scale) ** 2))


def exponential_decay(distance_value: float, scale: float = 1.0, power: float = 2.0) -> float:
    """Exponential decay: exp(-distance/scale)."""
    return math.exp(-distance_value / scale)


def linear_decay(distance_value: float, scale: float = 1.0, power: float = 2.0) -> float:
    """Linear decay: max(0, 1 - distance/scale)."""
    return max(0.0, 1.0 - distance_value / scale)


# Built-in influence kernels
def weighted_kernel(weight: float, distance_value: float, **kwargs: Any) -> float:
    """Standard weighted kernel: weight * decay(distance)."""
    scale: float = kwargs.get("scale", 1.0)
    power: float = kwargs.get("power", 2.0)
    decay_fn: DecayFunction = kwargs.get("decay_fn", inverse_power_decay)
    return weight * decay_fn(distance_value, scale, power)


def epanechnikov_kernel(weight: float, distance_value: float, *, bandwidth: float = 1.0, **kwargs: Any) -> float:
    """Epanechnikov kernel: weight * 3/4 * (1 - (d/h)^2) for d < h."""
    u = distance_value / bandwidth
    if u >= 1.0:
        return 0.0
    return weight * 0.75 * (1.0 - u * u)


# Registry
_decay_registry: dict[str, DecayFunction] = {
    "inverse_power": inverse_power_decay,
    "gaussian": gaussian_decay,
    "exponential": exponential_decay,
    "linear": linear_decay,
}

_kernel_registry: dict[str, InfluenceKernel] = {
    "weighted": weighted_kernel,
    "epanechnikov": epanechnikov_kernel,
}


def register_decay(name: str, func: DecayFunction) -> None:
    """Register a custom decay function by name."""
    if name in _decay_registry:
        raise PluginError(f"Decay function '{name}' is already registered")
    _decay_registry[name] = func


def register_kernel(name: str, func: InfluenceKernel) -> None:
    """Register a custom influence kernel by name."""
    if name in _kernel_registry:
        raise PluginError(f"Influence kernel '{name}' is already registered")
    _kernel_registry[name] = func


def get_decay(name: str) -> DecayFunction:
    """Retrieve a registered decay function."""
    if name not in _decay_registry:
        raise PluginError(f"Unknown decay function: '{name}'. Available: {list(_decay_registry)}")
    return _decay_registry[name]


def get_kernel(name: str) -> InfluenceKernel:
    """Retrieve a registered influence kernel."""
    if name not in _kernel_registry:
        raise PluginError(f"Unknown influence kernel: '{name}'. Available: {list(_kernel_registry)}")
    return _kernel_registry[name]


def list_decay_functions() -> list[str]:
    """List all registered decay function names."""
    return list(_decay_registry)


def list_kernels() -> list[str]:
    """List all registered influence kernel names."""
    return list(_kernel_registry)


__all__ = [
    "DecayFunction",
    "InfluenceKernel",
    "epanechnikov_kernel",
    "exponential_decay",
    "gaussian_decay",
    "get_decay",
    "get_kernel",
    "inverse_power_decay",
    "linear_decay",
    "list_decay_functions",
    "list_kernels",
    "register_decay",
    "register_kernel",
    "weighted_kernel",
]
