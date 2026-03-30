"""Surface and altitude effects — modifies gameplay based on playing surface and elevation.

Complements the weather module with surface-specific and altitude-specific physics.
"""

from __future__ import annotations

import math

from sports_sim.core.models import GameState, SimulationConfig, SurfaceType


def apply_surface_effects(state: GameState, config: SimulationConfig) -> GameState:
    """Apply surface and altitude effects each tick.

    Surface effects:
    - Artificial turf: speed +2%, slightly higher injury risk via aggression spike
    - Poor surface quality: speed penalty proportional to degradation
    - Wet conditions + grass: slip risk (accuracy penalty)
    - Hard court (tennis): faster ball speed, more serve advantage
    - Ice (hockey): speed bonus
    - Clay (tennis): slower rallies, endurance matters more
    - Dirt (baseball): no special modifier

    Altitude effects:
    - > 1500m: ball travels farther (accuracy bonus for long passes/shots)
    - > 2500m: significant endurance drain for all players
    """
    if not config.enable_surface_effects:
        return state

    env = state.environment
    surface = env.surface_type
    quality = env.surface_quality

    # --- Surface quality degradation ---
    if quality < 0.8:
        speed_pen = (0.8 - quality) * 0.0005
        for team in (state.home_team, state.away_team):
            for p in team.active_players:
                p.attributes.speed = max(0.1, p.attributes.speed - speed_pen)

    # --- Artificial turf: speed boost + injury risk ---
    if surface == SurfaceType.ARTIFICIAL_TURF:
        for team in (state.home_team, state.away_team):
            for p in team.active_players:
                p.attributes.speed = min(1.0, p.attributes.speed * 1.00002)

    # --- Ice: speed bonus ---
    if surface == SurfaceType.ICE:
        for team in (state.home_team, state.away_team):
            for p in team.active_players:
                p.attributes.speed = min(1.0, p.attributes.speed * 1.00001)

    # --- Clay: endurance matters more ---
    if surface == SurfaceType.CLAY:
        for team in (state.home_team, state.away_team):
            for p in team.active_players:
                # Extra drain on lower-endurance players
                if p.attributes.endurance < 0.6:
                    p.stamina = max(0.0, p.stamina - 0.00005)

    # --- Altitude: endurance drain + ball physics ---
    altitude = env.altitude_m
    if altitude > 1500.0:
        alt_factor = min(1.0, (altitude - 1500.0) / 3000.0)
        drain = alt_factor * 0.00015
        for team in (state.home_team, state.away_team):
            for p in team.active_players:
                p.stamina = max(0.0, p.stamina - drain)
        # Ball travels further at altitude (slight accuracy bonus for long-range)
        if state.ball and altitude > 2000.0:
            state.ball.vx *= 1.0 + alt_factor * 0.0001
            state.ball.vy *= 1.0 + alt_factor * 0.0001

    return state
