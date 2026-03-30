"""Golf sport module — 18-hole stroke play between two players/teams."""

from __future__ import annotations

import numpy as np
from typing import cast

from sports_sim.core.models import (
    Ball,
    EventType,
    GameEvent,
    GameState,
    Player,
    PlayerAttributes,
    SimulationConfig,
    Team,
)
from sports_sim.core.sport import Sport

_COURSE_W, _COURSE_H = 200.0, 100.0  # abstract course dimensions

# Par values for 18 holes (typical course)
HOLE_PARS = [4, 4, 3, 5, 4, 3, 4, 5, 4, 4, 3, 5, 4, 4, 3, 4, 5, 4]
HOLE_DISTANCES = [380, 420, 175, 520, 410, 190, 440, 550, 400, 390, 165, 530, 415, 405, 185, 430, 540, 395]


def _rand_attrs(rng: np.random.Generator) -> PlayerAttributes:
    return PlayerAttributes(
        speed=float(rng.uniform(0.4, 0.6)),  # less relevant in golf
        strength=float(rng.uniform(0.5, 0.9)),  # driving distance
        accuracy=float(rng.uniform(0.55, 0.95)),  # shot accuracy
        endurance=float(rng.uniform(0.6, 0.85)),
        skill=float(rng.uniform(0.6, 0.95)),  # overall skill
        decision_making=float(rng.uniform(0.6, 0.90)),  # course management
        aggression=float(rng.uniform(0.3, 0.7)),  # risk-taking
        composure=float(rng.uniform(0.6, 0.95)),  # pressure handling
    )


def _make_golfer_team(name: str, abbr: str, seed: int) -> Team:
    rng = np.random.default_rng(seed)
    player = Player(
        name=name, number=1, position="G",
        attributes=_rand_attrs(rng), x=0, y=0,
    )
    return Team(name=name, abbreviation=abbr, players=[player], bench=[], formation="individual")


class GolfSport(Sport):
    @property
    def name(self) -> str:
        return "golf"

    @property
    def default_periods(self) -> int:
        return 18  # 18 holes

    @property
    def default_period_length(self) -> float:
        return 2.0  # ~2 minutes per hole in sim time

    @property
    def field_width(self) -> float:
        return _COURSE_W

    @property
    def field_height(self) -> float:
        return _COURSE_H

    @property
    def players_per_side(self) -> int:
        return 1

    def __init__(self):
        self._rng = np.random.default_rng()
        self._current_hole = 0
        self._p1_strokes: list[int] = []
        self._p2_strokes: list[int] = []

    def create_default_teams(self) -> tuple[Team, Team]:
        return _make_golfer_team("Golfer A", "GA", 1300), _make_golfer_team("Golfer B", "GB", 1400)

    def setup_positions(self, state: GameState) -> GameState:
        state.ball = Ball(x=0, y=_COURSE_H / 2)
        return state

    def tick(self, state: GameState, config: SimulationConfig) -> tuple[GameState, list[GameEvent]]:
        events: list[GameEvent] = []
        rng = self._rng or np.random.default_rng()
        rng = cast(np.random.Generator, rng)

        if state.is_finished or self._current_hole >= 18:
            if not state.is_finished:
                state.is_finished = True
            return state, events

        # Only process holes periodically
        if rng.random() > 0.01:
            return state, events

        hole_idx = self._current_hole
        par = HOLE_PARS[hole_idx]
        distance = HOLE_DISTANCES[hole_idx]

        for player_idx, (team, strokes_list) in enumerate([
            (state.home_team, self._p1_strokes),
            (state.away_team, self._p2_strokes),
        ]):
            if not team.players:
                continue
            golfer = team.players[0]

            # Simulate hole strokes
            skill = golfer.effective_skill
            accuracy = golfer.attributes.accuracy
            composure = golfer.attributes.composure
            strength = golfer.attributes.strength

            # Base strokes = par, modified by skill
            base = par - (skill - 0.6) * 2.0
            noise = rng.normal(0, 0.8) * (1.0 - composure * 0.5)
            strokes = max(1, round(base + noise))

            strokes_list.append(strokes)
            total = sum(strokes_list)
            relative = total - sum(HOLE_PARS[:hole_idx + 1])

            # Determine event type
            diff = strokes - par
            if diff <= -2:
                evt_type = EventType.EAGLE
                desc = f"EAGLE! {golfer.name} scores {strokes} on hole {hole_idx + 1} (par {par})"
            elif diff == -1:
                evt_type = EventType.BIRDIE
                desc = f"Birdie! {golfer.name} scores {strokes} on hole {hole_idx + 1} (par {par})"
            elif diff == 0:
                evt_type = EventType.PAR
                desc = f"Par for {golfer.name} on hole {hole_idx + 1}"
            else:
                evt_type = EventType.BOGEY
                desc = f"Bogey ({'+' if diff > 0 else ''}{diff}) for {golfer.name} on hole {hole_idx + 1}"

            events.append(GameEvent(
                type=evt_type, time=state.clock, period=state.period,
                team_id=team.id, player_id=golfer.id,
                description=desc,
                metadata={"hole": hole_idx + 1, "strokes": strokes, "par": par, "total": total, "relative": relative},
            ))

        events.append(GameEvent(
            type=EventType.HOLE_COMPLETE, time=state.clock, period=state.period,
            description=f"Hole {hole_idx + 1} complete",
        ))

        # Score = total strokes (lower is better — we store relative to par for display)
        state.home_team.score = sum(self._p1_strokes) - sum(HOLE_PARS[:len(self._p1_strokes)])
        state.away_team.score = sum(self._p2_strokes) - sum(HOLE_PARS[:len(self._p2_strokes)])

        self._current_hole += 1
        if self._current_hole >= 18:
            state.is_finished = True

        return state, events

    def is_valid_state(self, state: GameState) -> bool:
        return len(state.home_team.players) >= 1 and len(state.away_team.players) >= 1

    def post_event(self, state: GameState, event: GameEvent, config: SimulationConfig) -> GameState:
        if event.type == EventType.EAGLE:
            team = state.home_team if event.team_id == state.home_team.id else state.away_team
            team.momentum = min(1.0, team.momentum + 0.15)
        elif event.type == EventType.BIRDIE:
            team = state.home_team if event.team_id == state.home_team.id else state.away_team
            team.momentum = min(1.0, team.momentum + 0.08)
        return state
