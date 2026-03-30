"""Enhanced home advantage model — crowd, altitude, travel, and venue familiarity.

Applies continuous home-field effects during the simulation, not just a one-time boost.
"""

from __future__ import annotations

import math

from sports_sim.core.models import GameState, SimulationConfig


def apply_home_advantage(state: GameState, config: SimulationConfig) -> GameState:
    """Apply home advantage effects each tick.

    Factors:
    - Crowd intensity → morale boost for home, pressure on away
    - Altitude → endurance penalty for visiting team if altitude > 1500 m
    - Venue familiarity → slight accuracy bonus for home team
    - Visitor fatigue factor from venue → extra stamina drain for away
    """
    if not config.enable_venue_effects:
        return state

    home = state.home_team
    away = state.away_team
    env = state.environment
    venue = state.venue

    ha = config.home_advantage
    if ha <= 0:
        return state

    # --- Crowd pressure: boost home morale, reduce away composure ---
    crowd = env.crowd_intensity
    crowd_boost = ha * crowd * 0.002
    crowd_pressure = ha * crowd * 0.001

    for p in home.active_players:
        p.morale = min(1.0, p.morale + crowd_boost)
    for p in away.active_players:
        p.morale = max(0.0, p.morale - crowd_pressure)

    # --- Altitude effect on visitors ---
    altitude = env.altitude_m
    if altitude > 1500.0 and not env.is_climate_controlled:
        alt_factor = (altitude - 1500.0) / 3000.0  # normalized 0-1 for up to 4500m
        alt_drain = alt_factor * 0.0002
        for p in away.active_players:
            p.stamina = max(0.0, p.stamina - alt_drain)

    # --- Venue familiarity → home accuracy boost ---
    if venue:
        familiarity_bonus = ha * 0.001
        for p in home.active_players:
            p.attributes.accuracy = min(1.0, p.attributes.accuracy + familiarity_bonus * 0.01)

    # --- Visitor fatigue factor ---
    if venue and venue.visitor_fatigue_factor > 0:
        vf = venue.visitor_fatigue_factor * 0.0001
        for p in away.active_players:
            p.stamina = max(0.0, p.stamina - vf)

    return state
