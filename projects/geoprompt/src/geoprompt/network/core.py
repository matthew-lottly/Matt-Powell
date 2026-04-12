"""Core network data structures and utilities.

This module provides the foundational types and helper functions used
throughout the network analysis package.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NotRequired, Required, TypedDict

if TYPE_CHECKING:
    from collections.abc import Iterable


class NetworkEdge(TypedDict, total=False):
    """Extensible typed dictionary for network edge attributes.

    Common fields are defined below; additional domain-specific fields
    can be added as needed by analysis functions. All fields are optional
    and allow custom attributes to flow through the system.
    """
    from_node: Required[str]
    to_node: Required[str]
    edge_id: NotRequired[str]
    cost: NotRequired[float]
    length: NotRequired[float]
    capacity: NotRequired[float]
    flow: NotRequired[float]
    load: NotRequired[float]
    device_type: NotRequired[str]
    state: NotRequired[str]
    bidirectional: NotRequired[bool]
    congestion: NotRequired[float]
    slope: NotRequired[float]
    failure_risk: NotRequired[float]
    condition: NotRequired[float]
    # Domain-specific utility fields
    diameter: NotRequired[float]
    age: NotRequired[float]
    design_life: NotRequired[float]
    pressure: NotRequired[float]
    headloss: NotRequired[float]
    customers: NotRequired[int]
    # Reserved for additional field names passed at runtime
    # (users may add any other field name with Any value)


@dataclass(frozen=True)
class Traversal:
    """Represents a single step along a network edge during traversal."""
    edge_id: str
    from_node: str
    to_node: str
    cost: float


@dataclass
class NetworkGraph:
    """Adjacency representation of a network with edge attributes."""
    directed: bool
    adjacency: dict[str, list[Traversal]]
    edge_attributes: dict[str, NetworkEdge]

    @property
    def nodes(self) -> set[str]:
        """Return the set of all nodes in the network."""
        return set(self.adjacency.keys())


def _as_node(value: object, field: str) -> str:
    """Validate and convert a value to a non-empty node identifier string."""
    node = str(value)
    if not node:
        raise ValueError(f"{field} must be a non-empty string")
    return node


def _as_non_negative(value: Any, field: str) -> float:
    """Validate and convert a value to a non-negative float."""
    resolved = float(value)
    if math.isnan(resolved):
        raise ValueError(f"{field} must be a valid number")
    if resolved < 0:
        raise ValueError(f"{field} must be zero or greater")
    return resolved


def _iter_chunks(items: Iterable[Any], chunk_size: int) -> Iterable[list[Any]]:
    """Yield items in fixed-size chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be >= 1")
    bucket: list[Any] = []
    for item in items:
        bucket.append(item)
        if len(bucket) >= chunk_size:
            yield bucket
            bucket = []
    if bucket:
        yield bucket


NETWORK_WORKLOAD_PRESETS: dict[str, dict[str, int]] = {
    "small": {"origin_batch_size": 100, "demand_batch_size": 10000},
    "medium": {"origin_batch_size": 500, "demand_batch_size": 50000},
    "large": {"origin_batch_size": 1000, "demand_batch_size": 100000},
    "huge": {"origin_batch_size": 2500, "demand_batch_size": 250000},
}


def get_network_workload_preset(name: str) -> dict[str, int]:
    """Return default batch sizes for a named network workload preset.
    
    Parameters
    ----------
    name : str
        Preset name: "small", "medium", "large", or "huge".
        
    Returns
    -------
    dict[str, int]
        Dictionary with ``origin_batch_size`` and ``demand_batch_size`` keys.
        
    Raises
    ------
    ValueError
        If the preset name is not recognized.
    """
    preset = NETWORK_WORKLOAD_PRESETS.get(name.lower())
    if preset is None:
        valid = ", ".join(sorted(NETWORK_WORKLOAD_PRESETS.keys()))
        raise ValueError(f"unknown network workload preset '{name}'. expected one of: {valid}")
    return dict(preset)
