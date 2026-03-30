"""Weather effects — applies environmental modifiers to gameplay."""

from __future__ import annotations

from sports_sim.core.models import GameState, SimulationConfig, Weather


def apply_weather_effects(state: GameState, config: SimulationConfig | None = None) -> GameState:
    """Modify game state based on environmental conditions.

    Effects:
    - Rain: reduces ball control (accuracy), increases slip/foul probability
    - Wind: nudges ball position
    - Heat: accelerates fatigue
    - Snow: slows all player movement
    """
    if config and not config.enable_weather:
        return state

    env = state.environment
    if env is None:
        return state

    weather = env.weather

    # Rain — reduce accuracy of all players slightly
    if weather == Weather.RAIN:
        factor = 0.92
        for team in (state.home_team, state.away_team):
            for p in team.active_players:
                # Store original so we can restore later if needed
                p.attributes.accuracy = max(0.1, p.attributes.accuracy * factor)

    # Wind — shift ball position slightly
    if state.ball and env.wind_speed_kph > 5:
        import math

        rad = math.radians(env.wind_direction_deg)
        wind_factor = env.wind_speed_kph * 0.0005
        state.ball.x += math.cos(rad) * wind_factor
        state.ball.y += math.sin(rad) * wind_factor

    # Heat — extra fatigue drain
    if env.temperature_c > 32:
        heat_penalty = (env.temperature_c - 32) * 0.0001
        for team in (state.home_team, state.away_team):
            for p in team.active_players:
                p.stamina = max(0.0, p.stamina - heat_penalty)

    # Snow — reduce speed
    if weather == Weather.SNOW:
        for team in (state.home_team, state.away_team):
            for p in team.active_players:
                p.attributes.speed = max(0.1, p.attributes.speed * 0.9)

    return state
