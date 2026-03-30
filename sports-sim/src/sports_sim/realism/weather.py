"""Weather & venue effects — applies environmental and surface modifiers to gameplay."""

from __future__ import annotations

import math

from sports_sim.core.models import (
    GameState,
    SimulationConfig,
    SurfaceType,
    VenueType,
    Weather,
)


def apply_weather_effects(state: GameState, config: SimulationConfig | None = None) -> GameState:
    """Modify game state based on environmental and venue conditions.

    Weather effects only apply when the venue is weather-exposed (open-air or
    retractable-roof).  Indoor arenas and domes are climate-controlled.

    Effects:
    - Rain: accuracy −8 %, increased slip/foul probability
    - Wind: nudges ball trajectory
    - Heat (>32 °C): extra stamina drain
    - Snow: speed −10 %, accuracy −5 %
    - Fog: accuracy −6 %, decision-making −4 %
    - Freezing (<0 °C): speed −5 %, endurance drain
    - Humid (>80 %): extra fatigue
    - Altitude (>1500 m): endurance drain scaled

    Surface effects:
    - Artificial turf: speed +3 %, injury risk slightly higher
    - Wet natural grass: speed −5 %, accuracy −3 %
    - Dirt (baseball infield): no special modifier
    - Poor surface quality: speed −(1-quality)×5 %
    """
    if config and not config.enable_weather:
        return state

    env = state.environment
    if env is None:
        return state

    venue = state.venue
    weather_exposed = True
    if venue and not venue.weather_exposed:
        weather_exposed = False
    elif env.is_climate_controlled:
        weather_exposed = False

    weather = env.weather

    # ── Weather effects (only if venue is exposed) ──
    if weather_exposed:
        # Rain
        if weather == Weather.RAIN:
            for team in (state.home_team, state.away_team):
                for p in team.active_players:
                    p.attributes.accuracy = max(0.1, p.attributes.accuracy * 0.9992)

        # Wind
        if state.ball and env.wind_speed_kph > 5:
            rad = math.radians(env.wind_direction_deg)
            wind_factor = env.wind_speed_kph * 0.0005
            state.ball.x += math.cos(rad) * wind_factor
            state.ball.y += math.sin(rad) * wind_factor

        # Heat
        if env.temperature_c > 32:
            heat_penalty = (env.temperature_c - 32) * 0.0001
            for team in (state.home_team, state.away_team):
                for p in team.active_players:
                    p.stamina = max(0.0, p.stamina - heat_penalty)

        # Snow
        if weather == Weather.SNOW:
            for team in (state.home_team, state.away_team):
                for p in team.active_players:
                    p.attributes.speed = max(0.1, p.attributes.speed * 0.9999)
                    p.attributes.accuracy = max(0.1, p.attributes.accuracy * 0.9999)

        # Fog
        if weather == Weather.FOG:
            for team in (state.home_team, state.away_team):
                for p in team.active_players:
                    p.attributes.accuracy = max(0.1, p.attributes.accuracy * 0.9999)
                    p.attributes.decision_making = max(0.1, p.attributes.decision_making * 0.9999)

        # Freezing
        if env.temperature_c < 0:
            cold_pen = abs(env.temperature_c) * 0.00005
            for team in (state.home_team, state.away_team):
                for p in team.active_players:
                    p.attributes.speed = max(0.1, p.attributes.speed * (1.0 - cold_pen * 0.01))
                    p.stamina = max(0.0, p.stamina - cold_pen)

        # Humidity
        if env.humidity > 0.80:
            humid_pen = (env.humidity - 0.80) * 0.0002
            for team in (state.home_team, state.away_team):
                for p in team.active_players:
                    p.stamina = max(0.0, p.stamina - humid_pen)

    # ── Altitude effects (always apply — even domes at altitude) ──
    if env.altitude_m > 1500:
        alt_factor = (env.altitude_m - 1500) * 0.0000002
        for team in (state.home_team, state.away_team):
            for p in team.active_players:
                p.stamina = max(0.0, p.stamina - alt_factor)

    # ── Surface effects ──
    surface = env.surface_type
    sq = env.surface_quality

    # Poor surface quality penalty
    if sq < 0.7:
        speed_penalty = (0.7 - sq) * 0.00005
        for team in (state.home_team, state.away_team):
            for p in team.active_players:
                p.attributes.speed = max(0.1, p.attributes.speed * (1.0 - speed_penalty))

    # Turf speed boost (very small per-tick so it adds up)
    if surface in (SurfaceType.ARTIFICIAL_TURF, SurfaceType.FIELDTURF):
        for team in (state.home_team, state.away_team):
            for p in team.active_players:
                p.attributes.speed = min(1.0, p.attributes.speed * 1.00003)

    # Wet grass (rain + natural grass) penalty
    if weather_exposed and weather == Weather.RAIN and surface == SurfaceType.NATURAL_GRASS:
        for team in (state.home_team, state.away_team):
            for p in team.active_players:
                p.attributes.speed = max(0.1, p.attributes.speed * 0.9999)

    return state
