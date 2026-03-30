"""Travel and jet-lag fatigue model.

Applies pre-game fatigue based on travel distance and timezone difference
between teams' home venues.  Longer travel = more starting fatigue for the away team.
"""

from __future__ import annotations

import math

from sports_sim.core.models import GameState, SimulationConfig, Venue


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def compute_travel_fatigue(
    home_venue: Venue,
    away_venue: Venue,
    max_fatigue: float = 0.15,
) -> float:
    """Compute starting fatigue penalty for the away team based on travel distance.

    Returns a value between 0.0 and max_fatigue.
    Short flights (<500 km) produce negligible fatigue.
    Cross-country (>3000 km) produces significant fatigue.
    Intercontinental (>8000 km) produces max fatigue.
    """
    if not (home_venue.latitude and home_venue.longitude and
            away_venue.latitude and away_venue.longitude):
        return 0.0

    dist = _haversine_km(
        away_venue.latitude, away_venue.longitude,
        home_venue.latitude, home_venue.longitude,
    )

    if dist < 500:
        return 0.0

    # Log-scale
    fatigue = min(max_fatigue, max_fatigue * math.log(dist / 500.0) / math.log(8000.0 / 500.0))
    return fatigue


def apply_travel_fatigue(state: GameState, config: SimulationConfig) -> GameState:
    """Apply travel fatigue to the away team at game start.

    Should be called once before the simulation loop begins.
    """
    if not config.enable_venue_effects:
        return state

    home_venue = state.home_team.venue
    away_venue = state.away_team.venue

    if not home_venue or not away_venue:
        return state

    fatigue = compute_travel_fatigue(home_venue, away_venue)
    if fatigue > 0:
        for p in state.away_team.players:
            p.stamina = max(0.0, p.stamina - fatigue)
        for p in state.away_team.bench:
            p.stamina = max(0.0, p.stamina - fatigue * 0.5)

    return state
