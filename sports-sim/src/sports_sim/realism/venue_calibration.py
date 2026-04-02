"""Venue calibration — adjust simulation parameters from real-world venue data.

This module maps known venue properties (altitude, surface quality, climate,
capacity) into the numeric modifiers that the engine's realism modules consume.
The calibration factors are derived from published sports-science literature
and can be overridden per-venue via a JSON calibration file.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sports_sim.core.models import Venue, VenueType, SurfaceType

# ---------------------------------------------------------------------------
# Calibration profile
# ---------------------------------------------------------------------------

@dataclass
class VenueCalibration:
    """Numeric calibration factors for a single venue."""

    # Altitude-derived
    altitude_endurance_drain: float = 0.0
    altitude_ball_velocity_bonus: float = 0.0

    # Surface-derived
    surface_speed_modifier: float = 0.0    # +/- applied to player speed
    surface_injury_modifier: float = 0.0   # multiplier on injury probability

    # Climate-derived
    heat_fatigue_modifier: float = 0.0     # extra drain per tick when hot
    cold_speed_penalty: float = 0.0        # speed reduction in freezing

    # Home advantage
    crowd_morale_boost: float = 0.0        # home team morale bump
    visitor_pressure: float = 0.0          # away team accuracy penalty

    # Overall venue difficulty
    difficulty_factor: float = 1.0


# ---------------------------------------------------------------------------
# Calibration functions
# ---------------------------------------------------------------------------

def _altitude_factors(altitude_m: float) -> tuple[float, float]:
    """Return (endurance_drain, ball_velocity_bonus) from altitude.

    Based on VO2max reduction at altitude (~6-7% per 1000m above 1500m)
    and reduced air density increasing ball speed.
    """
    if altitude_m < 1500:
        return 0.0, 0.0

    excess = altitude_m - 1500
    # Endurance drain: roughly 0.0002 per meter above 1500
    drain = min(excess * 0.0002, 0.15)
    # Ball velocity: air density drops ~12% per 1000m
    velocity_bonus = min(excess * 0.00005, 0.05)
    return drain, velocity_bonus


def _surface_factors(surface: SurfaceType, quality: float) -> tuple[float, float]:
    """Return (speed_modifier, injury_modifier) from surface type and quality."""
    speed = 0.0
    injury = 1.0

    # Artificial surfaces are faster
    if surface in (SurfaceType.ARTIFICIAL_TURF, SurfaceType.FIELDTURF):
        speed += 0.02
        injury *= 1.15  # slightly higher injury risk on artificial

    # Poor quality increases injury risk and slows play
    if quality < 0.8:
        degradation = 0.8 - quality
        speed -= degradation * 0.1
        injury *= 1.0 + degradation * 0.5

    # Ice/hardwood are fast surfaces
    if surface == SurfaceType.ICE:
        speed += 0.03
    elif surface == SurfaceType.HARDWOOD:
        speed += 0.01

    return speed, injury


def _climate_factors(venue: Venue) -> tuple[float, float]:
    """Return (heat_fatigue_modifier, cold_speed_penalty) from venue climate."""
    heat = 0.0
    cold = 0.0

    if venue.climate_controlled:
        return 0.0, 0.0

    # Proxy: latitude-based rough climate estimate when no runtime weather
    lat = abs(venue.latitude) if venue.latitude else 40.0

    # Tropical venues (low latitude) tend to be hotter
    if lat < 25:
        heat = 0.03
    elif lat < 35:
        heat = 0.01

    # Northern venues can be cold
    if lat > 55:
        cold = 0.01
    elif lat > 45:
        cold = 0.005

    return heat, cold


def _crowd_factors(venue: Venue) -> tuple[float, float]:
    """Return (home_morale_boost, visitor_pressure) from venue crowd metrics."""
    noise = venue.noise_factor
    cap = venue.capacity or 30000

    # Larger, louder venues boost home advantage
    cap_factor = min(cap / 80000, 1.0)
    morale = noise * cap_factor * 0.05
    pressure = noise * cap_factor * 0.03

    return morale, pressure


def calibrate_venue(venue: Venue) -> VenueCalibration:
    """Produce a full calibration profile for a venue."""
    alt_drain, alt_vel = _altitude_factors(venue.altitude_m)
    surf_speed, surf_injury = _surface_factors(venue.surface, venue.surface_quality)
    heat, cold = _climate_factors(venue)
    morale, pressure = _crowd_factors(venue)

    return VenueCalibration(
        altitude_endurance_drain=round(alt_drain, 5),
        altitude_ball_velocity_bonus=round(alt_vel, 5),
        surface_speed_modifier=round(surf_speed, 4),
        surface_injury_modifier=round(surf_injury, 3),
        heat_fatigue_modifier=round(heat, 4),
        cold_speed_penalty=round(cold, 4),
        crowd_morale_boost=round(morale, 4),
        visitor_pressure=round(pressure, 4),
        difficulty_factor=round(venue.difficulty_rating, 3),
    )


# ---------------------------------------------------------------------------
# Override file support
# ---------------------------------------------------------------------------

_OVERRIDES_PATH = Path(__file__).parent.parent / "data" / "venue_calibrations.json"
_override_cache: dict[str, VenueCalibration] | None = None


def _load_overrides() -> dict[str, VenueCalibration]:
    global _override_cache
    if _override_cache is not None:
        return _override_cache

    _override_cache = {}
    if _OVERRIDES_PATH.exists():
        raw: dict[str, Any] = json.loads(_OVERRIDES_PATH.read_text())
        for venue_name, data in raw.items():
            _override_cache[venue_name] = VenueCalibration(**data)
    return _override_cache


def get_venue_calibration(venue: Venue) -> VenueCalibration:
    """Get calibration for a venue, using file overrides if present."""
    overrides = _load_overrides()
    if venue.name in overrides:
        return overrides[venue.name]
    return calibrate_venue(venue)
