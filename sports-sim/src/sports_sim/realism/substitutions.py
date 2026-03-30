"""Substitution rules and automated lineup rotation per sport.

Handles sport-specific substitution limits, auto-subs based on fatigue/injury,
and lineup rotation during natural stoppages.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from sports_sim.core.models import EventType, GameEvent, GameState, SimulationConfig, SportType


@dataclass
class SubstitutionTracker:
    """Tracks substitutions used per team per game."""
    home_subs_used: int = 0
    away_subs_used: int = 0
    max_subs: int = 5  # set per-sport


# Per-sport substitution limits
_SUB_LIMITS: dict[SportType, int] = {
    SportType.SOCCER: 5,
    SportType.BASKETBALL: 99,  # unlimited
    SportType.BASEBALL: 99,
    SportType.FOOTBALL: 99,
    SportType.HOCKEY: 99,
    SportType.TENNIS: 0,
    SportType.GOLF: 0,
    SportType.CRICKET: 1,
    SportType.BOXING: 0,
    SportType.MMA: 0,
    SportType.RACING: 0,
}

# Stamina threshold below which auto-sub is triggered
_AUTO_SUB_STAMINA_THRESHOLD = 0.25

# How often (in ticks) to check for auto-subs
_AUTO_SUB_CHECK_INTERVAL = 200


def create_sub_tracker(sport: SportType) -> SubstitutionTracker:
    """Create a SubstitutionTracker with the correct max for a sport."""
    return SubstitutionTracker(max_subs=_SUB_LIMITS.get(sport, 5))


def can_substitute(tracker: SubstitutionTracker, is_home: bool) -> bool:
    """Check if a team has substitutions remaining."""
    used = tracker.home_subs_used if is_home else tracker.away_subs_used
    return used < tracker.max_subs


def perform_substitution(
    state: GameState,
    tracker: SubstitutionTracker,
    is_home: bool,
    player_out_idx: int,
    rng: np.random.Generator,
) -> list[GameEvent]:
    """Substitute the worst-condition player with the best bench player."""
    team = state.home_team if is_home else state.away_team
    events: list[GameEvent] = []

    if not team.bench:
        return events
    if not can_substitute(tracker, is_home):
        return events
    if player_out_idx >= len(team.players):
        return events

    out_player = team.players[player_out_idx]
    # Pick the freshest bench player
    bench_sorted = sorted(team.bench, key=lambda p: p.stamina, reverse=True)
    in_player = bench_sorted[0]
    team.bench.remove(in_player)

    in_player.x = out_player.x
    in_player.y = out_player.y
    team.players[player_out_idx] = in_player
    team.bench.append(out_player)

    if is_home:
        tracker.home_subs_used += 1
    else:
        tracker.away_subs_used += 1

    events.append(GameEvent(
        type=EventType.SUBSTITUTION,
        time=state.clock,
        period=state.period,
        team_id=team.id,
        player_id=in_player.id,
        secondary_player_id=out_player.id,
        description=f"{in_player.name} replaces {out_player.name}",
        metadata={"reason": "tactical", "subs_used": tracker.home_subs_used if is_home else tracker.away_subs_used},
    ))

    return events


def check_auto_substitutions(
    state: GameState,
    tracker: SubstitutionTracker,
    rng: np.random.Generator,
    config: SimulationConfig | None = None,
) -> list[GameEvent]:
    """Check if any player needs an automatic substitution due to fatigue or injury.

    Only triggers every _AUTO_SUB_CHECK_INTERVAL ticks.
    """
    if state.tick % _AUTO_SUB_CHECK_INTERVAL != 0:
        return []

    events: list[GameEvent] = []

    for is_home in (True, False):
        team = state.home_team if is_home else state.away_team
        if not team.bench:
            continue
        if not can_substitute(tracker, is_home):
            continue

        # Find the most fatigued/injured player above threshold
        worst_idx = None
        worst_stamina = 1.0
        for i, p in enumerate(team.players):
            if p.is_injured:
                worst_idx = i
                break
            if p.stamina < _AUTO_SUB_STAMINA_THRESHOLD and p.stamina < worst_stamina:
                worst_stamina = p.stamina
                worst_idx = i

        if worst_idx is not None:
            # Coach's substitution_aggression affects willingness
            sub_willingness = team.sliders.substitution_aggression
            if rng.random() < sub_willingness:
                sub_events = perform_substitution(state, tracker, is_home, worst_idx, rng)
                events.extend(sub_events)

    return events


def check_hockey_line_changes(
    state: GameState,
    tracker: SubstitutionTracker,
    rng: np.random.Generator,
) -> list[GameEvent]:
    """Hockey-specific: rotate lines based on line_change_frequency slider."""
    events: list[GameEvent] = []

    for is_home in (True, False):
        team = state.home_team if is_home else state.away_team
        if not team.bench:
            continue

        freq = team.sliders.line_change_frequency
        # Higher frequency = more frequent changes (check every 50-300 ticks)
        interval = int(300 - freq * 250)
        if interval < 50:
            interval = 50

        if state.tick % interval != 0:
            continue

        # Find lowest-stamina active player
        if not team.active_players:
            continue
        worst_idx = min(range(len(team.players)), key=lambda i: team.players[i].stamina)
        if team.players[worst_idx].stamina < 0.6 and team.bench:
            sub_events = perform_substitution(state, tracker, is_home, worst_idx, rng)
            events.extend(sub_events)

    return events
