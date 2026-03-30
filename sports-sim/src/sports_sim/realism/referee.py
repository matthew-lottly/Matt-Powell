"""Referee variability module — introduces human error in officiating.

Models referee strictness, home bias, fatigue-induced inconsistency,
and sport-specific call types.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sports_sim.core.models import EventType, GameEvent, GameState, SimulationConfig


@dataclass
class RefereeProfile:
    """Parameterizes a referee's tendencies."""
    strictness: float = 0.5  # 0 = lenient, 1 = strict
    home_bias: float = 0.05  # probability shift toward home team
    consistency: float = 0.8  # 1 = perfectly consistent, 0 = erratic
    experience: float = 0.7  # higher = fewer outright mistakes
    fatigue_rate: float = 0.0001  # per-tick fatigue accumulation
    # Mutable state
    current_fatigue: float = 0.0


def create_referee(rng: np.random.Generator) -> RefereeProfile:
    """Generate a random referee with realistic trait spreads."""
    return RefereeProfile(
        strictness=float(np.clip(rng.normal(0.5, 0.15), 0.1, 0.9)),
        home_bias=float(np.clip(rng.normal(0.05, 0.03), 0.0, 0.15)),
        consistency=float(np.clip(rng.normal(0.8, 0.1), 0.4, 1.0)),
        experience=float(np.clip(rng.normal(0.7, 0.15), 0.3, 1.0)),
    )


def apply_referee_variability(
    state: GameState,
    events: list[GameEvent],
    referee: RefereeProfile,
    rng: np.random.Generator,
    config: SimulationConfig | None = None,
) -> list[GameEvent]:
    """Process events through the referee's lens.

    May add, modify, or remove events based on referee traits:
    - Missed fouls (experienced refs miss fewer)
    - Phantom fouls (strict refs call more borderline calls)
    - Home bias (slightly more calls favor the home team)
    - Late-game fatigue (consistency drops)
    """
    if config and not config.enable_referee_errors:
        return events

    # Accumulate fatigue
    referee.current_fatigue = min(1.0, referee.current_fatigue + referee.fatigue_rate)
    effective_consistency = referee.consistency * (1.0 - referee.current_fatigue * 0.3)

    processed: list[GameEvent] = []
    for ev in events:
        # --- Missed foul: ref doesn't see it ---
        if ev.type == EventType.FOUL:
            miss_prob = (1.0 - referee.experience) * 0.15 * (1.0 - effective_consistency)
            # Home team fouls are slightly more likely to be missed (home bias)
            if ev.team_id == state.home_team.id:
                miss_prob += referee.home_bias * 0.1
            if rng.random() < miss_prob:
                # Foul not called — skip event
                continue
            processed.append(ev)
            continue

        # --- Phantom foul: ref calls a foul on a clean play ---
        # (rare occurrence, increases with strictness and fatigue)
        if ev.type in (EventType.PASS, EventType.SHOT, EventType.BLOCK):
            phantom_prob = referee.strictness * 0.001 * (1.0 + referee.current_fatigue)
            if rng.random() < phantom_prob:
                # Determine which team gets the phantom foul (bias toward away)
                if rng.random() < 0.5 + referee.home_bias:
                    foul_team = state.away_team
                else:
                    foul_team = state.home_team
                players = foul_team.active_players
                if players:
                    fouler = players[int(rng.integers(len(players)))]
                    processed.append(GameEvent(
                        type=EventType.FOUL,
                        time=state.clock,
                        period=state.period,
                        team_id=foul_team.id,
                        player_id=fouler.id,
                        description=f"Controversial foul called on {fouler.name}",
                        metadata={"referee_call": "phantom"},
                    ))

        processed.append(ev)

    return processed
