"""Momentum model — adjusts team and player morale based on recent events."""

from __future__ import annotations

from sports_sim.core.models import EventType, GameEvent, GameState, SimulationConfig

# Events that boost the scoring team's momentum
_POSITIVE_EVENTS = {
    EventType.GOAL: 0.15,
    EventType.HOME_RUN: 0.12,
    EventType.THREE_POINTER: 0.08,
    EventType.STEAL: 0.04,
    EventType.BLOCK: 0.04,
    EventType.RUN: 0.06,
    EventType.HIT: 0.03,
}

# Events that reduce the team's momentum
_NEGATIVE_EVENTS = {
    EventType.FOUL: -0.05,
    EventType.RED_CARD: -0.12,
    EventType.YELLOW_CARD: -0.04,
    EventType.TURNOVER: -0.06,
    EventType.INJURY: -0.08,
    EventType.STRIKEOUT: -0.04,
    EventType.OUT: -0.02,
}


def update_momentum(
    state: GameState,
    events: list[GameEvent],
    config: SimulationConfig | None = None,
) -> GameState:
    """Update team momentum and player morale based on recent events.

    Momentum decays toward 0.5 (neutral) every tick.
    Significant events push momentum up or down.
    High momentum improves team morale → better effective_skill.
    """
    if config and not config.enable_momentum:
        return state

    # Natural decay toward neutral (0.5)
    decay = 0.001
    for team in (state.home_team, state.away_team):
        if team.momentum > 0.5:
            team.momentum = max(0.5, team.momentum - decay)
        elif team.momentum < 0.5:
            team.momentum = min(0.5, team.momentum + decay)

    # Apply event-driven shifts
    for ev in events:
        home = state.home_team
        away = state.away_team

        if ev.team_id == home.id:
            acting_team, other_team = home, away
        elif ev.team_id == away.id:
            acting_team, other_team = away, home
        else:
            continue

        # Positive events for acting team
        if ev.type in _POSITIVE_EVENTS:
            delta = _POSITIVE_EVENTS[ev.type]
            acting_team.momentum = min(1.0, acting_team.momentum + delta)
            other_team.momentum = max(0.0, other_team.momentum - delta * 0.5)

        # Negative events for acting team
        if ev.type in _NEGATIVE_EVENTS:
            delta = _NEGATIVE_EVENTS[ev.type]
            acting_team.momentum = max(0.0, acting_team.momentum + delta)  # delta is negative
            other_team.momentum = min(1.0, other_team.momentum - delta * 0.3)

    # Propagate momentum to player morale
    for team in (state.home_team, state.away_team):
        for player in team.active_players:
            # Morale drifts toward momentum
            diff = team.momentum - player.morale
            player.morale = player.morale + diff * 0.05

    return state
