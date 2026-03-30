"""Fatigue model — drains stamina based on activity intensity and recovers during rest."""

from __future__ import annotations

from sports_sim.core.models import GameState, SimulationConfig


def apply_fatigue(state: GameState, dt: float, config: SimulationConfig | None = None) -> GameState:
    """Reduce each player's stamina proportional to dt and their endurance.

    Players with low endurance drain faster; high endurance drain slower.
    A small recovery factor applies when the ball is far from the player.
    """
    intensity = 1.0  # can be tuned per-sport later
    if config and config.fidelity == "fast":
        intensity = 0.5

    for team in (state.home_team, state.away_team):
        for player in team.active_players:
            drain = dt * 0.0003 * intensity * (1.1 - player.attributes.endurance)

            # Lower drain when far from the ball
            if state.ball:
                dx = player.x - state.ball.x
                dy = player.y - state.ball.y
                dist = (dx * dx + dy * dy) ** 0.5
                if dist > 30:
                    drain *= 0.4  # jogging / resting
                elif dist > 15:
                    drain *= 0.7

            player.stamina = max(0.0, player.stamina - drain)

            # Slight recovery during stoppages (clock not advancing)
            if dt == 0:
                player.stamina = min(1.0, player.stamina + 0.005)

    return state
