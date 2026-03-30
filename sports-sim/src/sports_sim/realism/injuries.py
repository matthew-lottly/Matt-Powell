"""Injury model — probabilistic injury checks based on fatigue, aggression, and contact events."""

from __future__ import annotations

import numpy as np

from sports_sim.core.models import EventType, GameEvent, GameState, SimulationConfig


_RNG = np.random.default_rng()


def check_injuries(
    state: GameState,
    rng: np.random.Generator | None = None,
    config: SimulationConfig | None = None,
) -> tuple[GameState, list[GameEvent]]:
    """Check every active player for injury probability.

    Risk factors:
    - Low stamina greatly increases risk.
    - High aggression increases contact-injury risk.
    - Recent foul events spike the probability.
    """
    gen = rng or _RNG
    events: list[GameEvent] = []

    if config and not config.enable_injuries:
        return state, events

    base_prob = 0.000015  # per tick

    for team in (state.home_team, state.away_team):
        to_remove: list[int] = []
        for idx, player in enumerate(team.active_players):
            prob = base_prob

            # Fatigue multiplier: exhausted players are 5× more likely to be injured
            if player.stamina < 0.2:
                prob *= 5.0
            elif player.stamina < 0.4:
                prob *= 2.5

            # Aggression factor
            prob *= 1.0 + player.attributes.aggression * 0.5

            if gen.random() < prob:
                severity = gen.choice(["minor", "moderate", "severe"], p=[0.6, 0.3, 0.1])
                events.append(GameEvent(
                    type=EventType.INJURY,
                    time=state.clock,
                    period=state.period,
                    team_id=team.id,
                    player_id=player.id,
                    description=f"{player.name} suffers a {severity} injury!",
                    metadata={"severity": severity},
                ))
                if severity in ("moderate", "severe"):
                    to_remove.append(idx)

        # Remove injured players (substitute from bench if available)
        for idx in reversed(to_remove):
            if team.bench:
                sub = team.bench.pop(0)
                sub.x = team.players[idx].x
                sub.y = team.players[idx].y
                team.players[idx] = sub
                events.append(GameEvent(
                    type=EventType.SUBSTITUTION,
                    time=state.clock,
                    period=state.period,
                    team_id=team.id,
                    player_id=sub.id,
                    description=f"{sub.name} comes on as substitute",
                ))

    return state, events
