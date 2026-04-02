"""MMA sport module — 3 or 5 rounds, two fighters, multi-discipline combat."""

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

_OCTAGON_W, _OCTAGON_H = 9.14, 9.14  # meters (30-foot octagon)


def _rand_attrs(rng: np.random.Generator) -> PlayerAttributes:
    return PlayerAttributes(
        speed=float(rng.uniform(0.55, 0.92)),
        strength=float(rng.uniform(0.55, 0.92)),
        accuracy=float(rng.uniform(0.5, 0.88)),
        endurance=float(rng.uniform(0.55, 0.90)),
        skill=float(rng.uniform(0.55, 0.92)),
        decision_making=float(rng.uniform(0.5, 0.88)),
        aggression=float(rng.uniform(0.4, 0.85)),
        composure=float(rng.uniform(0.5, 0.88)),
    )


def _make_fighter_team(name: str, abbr: str, seed: int) -> Team:
    rng = np.random.default_rng(seed)
    fighter = Player(
        name=name, number=1, position="MMA",
        attributes=_rand_attrs(rng), x=3.0, y=_OCTAGON_H / 2,
    )
    return Team(name=name, abbreviation=abbr, players=[fighter], bench=[], formation="individual")


class MMASport(Sport):
    @property
    def name(self) -> str:
        return "mma"

    @property
    def default_periods(self) -> int:
        return 3

    @property
    def default_period_length(self) -> float:
        return 5.0  # 5-minute rounds

    @property
    def field_width(self) -> float:
        return _OCTAGON_W

    @property
    def field_height(self) -> float:
        return _OCTAGON_H

    @property
    def players_per_side(self) -> int:
        return 1

    def __init__(self):
        self._rng = np.random.default_rng()
        self._p1_health = 100.0
        self._p2_health = 100.0
        self._p1_round_scores: list[int] = []
        self._p2_round_scores: list[int] = []
        self._current_round_p1 = 0
        self._current_round_p2 = 0
        self._on_ground = False

    def create_default_teams(self) -> tuple[Team, Team]:
        return _make_fighter_team("Fighter X", "FX", 1900), _make_fighter_team("Fighter Y", "FY", 2000)

    def setup_positions(self, state: GameState) -> GameState:
        if state.home_team.players:
            state.home_team.players[0].x = 3.0
            state.home_team.players[0].y = _OCTAGON_H / 2
        if state.away_team.players:
            state.away_team.players[0].x = _OCTAGON_W - 3.0
            state.away_team.players[0].y = _OCTAGON_H / 2
        state.ball = Ball(x=_OCTAGON_W / 2, y=_OCTAGON_H / 2)
        return state

    def tick(self, state: GameState, config: SimulationConfig) -> tuple[GameState, list[GameEvent]]:
        events: list[GameEvent] = []
        rng = self._rng or np.random.default_rng()
        rng = cast(np.random.Generator, rng)

        if state.is_finished:
            return state, events

        if rng.random() > 0.007:
            return state, events

        p1 = state.home_team.players[0] if state.home_team.players else None
        p2 = state.away_team.players[0] if state.away_team.players else None
        if not p1 or not p2:
            return state, events

        p1_striking = p1.effective_skill * p1.attributes.accuracy
        p2_striking = p2.effective_skill * p2.attributes.accuracy
        p1_grappling = p1.attributes.strength * p1.attributes.skill
        p2_grappling = p2.attributes.strength * p2.attributes.skill

        if self._on_ground:
            # Ground game
            # Submission attempt
            attacker = p1 if rng.random() < 0.5 else p2
            defender = p2 if attacker is p1 else p1
            att_team = state.home_team if attacker is p1 else state.away_team
            def_team = state.away_team if attacker is p1 else state.home_team

            sub_skill = attacker.attributes.skill * attacker.attributes.composure
            def_skill = defender.attributes.strength * defender.attributes.skill

            if rng.random() < sub_skill * 0.06:
                # Submission!
                events.append(GameEvent(
                    type=EventType.SUBMISSION, time=state.clock, period=state.period,
                    team_id=att_team.id, player_id=attacker.id,
                    description=f"SUBMISSION! {attacker.name} forces {defender.name} to tap!",
                ))
                att_team.score = sum(self._p1_round_scores if attacker is p1 else self._p2_round_scores) + 10
                state.is_finished = True
                return state, events

            # Ground strikes
            if rng.random() < attacker.attributes.accuracy * 0.4:
                damage = attacker.attributes.strength * rng.uniform(1, 4)
                if attacker is p1:
                    self._p2_health = max(0.0, self._p2_health - damage)
                    self._current_round_p1 += 1
                else:
                    self._p1_health = max(0.0, self._p1_health - damage)
                    self._current_round_p2 += 1
                events.append(GameEvent(
                    type=EventType.GROUND_STRIKE, time=state.clock, period=state.period,
                    team_id=att_team.id, player_id=attacker.id,
                    description=f"{attacker.name} lands ground strikes",
                ))

            # Stand up
            if rng.random() < defender.attributes.speed * 0.15:
                self._on_ground = False

        else:
            # Standing
            # Takedown attempt
            if rng.random() < 0.12:
                attacker = p1 if rng.random() < 0.5 else p2
                att_team = state.home_team if attacker is p1 else state.away_team

                td_skill = attacker.attributes.strength * attacker.attributes.speed
                defender = p2 if attacker is p1 else p1
                td_defense = defender.attributes.strength * defender.attributes.composure

                if rng.random() < td_skill / (td_skill + td_defense):
                    self._on_ground = True
                    if attacker is p1:
                        self._current_round_p1 += 2
                    else:
                        self._current_round_p2 += 2
                    events.append(GameEvent(
                        type=EventType.TAKEDOWN, time=state.clock, period=state.period,
                        team_id=att_team.id, player_id=attacker.id,
                        description=f"{attacker.name} scores a takedown!",
                    ))
                    return state, events

            # Striking exchange
            # P1 strikes
            if rng.random() < p1.attributes.accuracy * 0.5:
                damage = p1.attributes.strength * (1.0 + p1.attributes.aggression * 0.2) * rng.uniform(2, 5)
                self._p2_health = max(0.0, self._p2_health - damage)
                self._current_round_p1 += 1
                events.append(GameEvent(
                    type=EventType.PUNCH, time=state.clock, period=state.period,
                    team_id=state.home_team.id, player_id=p1.id,
                    description=f"{p1.name} lands on {p2.name}",
                ))

                # KO check
                if self._p2_health <= 0:
                    events.append(GameEvent(
                        type=EventType.KNOCKOUT, time=state.clock, period=state.period,
                        team_id=state.home_team.id, player_id=p1.id,
                        description=f"KNOCKOUT! {p1.name} finishes {p2.name}!",
                    ))
                    state.home_team.score = sum(self._p1_round_scores) + 10
                    state.is_finished = True
                    return state, events

            # P2 strikes
            if rng.random() < p2.attributes.accuracy * 0.5:
                damage = p2.attributes.strength * (1.0 + p2.attributes.aggression * 0.2) * rng.uniform(2, 5)
                self._p1_health = max(0.0, self._p1_health - damage)
                self._current_round_p2 += 1
                events.append(GameEvent(
                    type=EventType.PUNCH, time=state.clock, period=state.period,
                    team_id=state.away_team.id, player_id=p2.id,
                    description=f"{p2.name} lands on {p1.name}",
                ))

                if self._p1_health <= 0:
                    events.append(GameEvent(
                        type=EventType.KNOCKOUT, time=state.clock, period=state.period,
                        team_id=state.away_team.id, player_id=p2.id,
                        description=f"KNOCKOUT! {p2.name} finishes {p1.name}!",
                    ))
                    state.away_team.score = sum(self._p2_round_scores) + 10
                    state.is_finished = True
                    return state, events

        # Clinch
        if rng.random() < 0.03:
            events.append(GameEvent(
                type=EventType.CLINCH, time=state.clock, period=state.period,
                description="Fighters clinch against the cage",
            ))

        state.home_team.score = sum(self._p1_round_scores) + self._current_round_p1
        state.away_team.score = sum(self._p2_round_scores) + self._current_round_p2

        return state, events

    def _end_round(self, state: GameState):
        if self._current_round_p1 > self._current_round_p2:
            self._p1_round_scores.append(10)
            self._p2_round_scores.append(9)
        elif self._current_round_p2 > self._current_round_p1:
            self._p1_round_scores.append(9)
            self._p2_round_scores.append(10)
        else:
            self._p1_round_scores.append(10)
            self._p2_round_scores.append(10)
        self._current_round_p1 = 0
        self._current_round_p2 = 0
        self._on_ground = False
        self._p1_health = min(100, self._p1_health + 10)
        self._p2_health = min(100, self._p2_health + 10)

    def is_valid_state(self, state: GameState) -> bool:
        return len(state.home_team.players) >= 1 and len(state.away_team.players) >= 1

    def post_event(self, state: GameState, event: GameEvent, config: SimulationConfig) -> GameState:
        if event.type == EventType.PERIOD_END:
            self._end_round(state)
            state.home_team.score = sum(self._p1_round_scores)
            state.away_team.score = sum(self._p2_round_scores)
        if event.type in (EventType.KNOCKOUT, EventType.SUBMISSION, EventType.TAKEDOWN):
            team = state.home_team if event.team_id == state.home_team.id else state.away_team
            team.momentum = min(1.0, team.momentum + 0.2)
        return state

    def get_sport_state(self, state: GameState) -> dict:
        return {
            "p1_health": round(self._p1_health, 1),
            "p2_health": round(self._p2_health, 1),
            "p1_round_score": self._current_round_p1,
            "p2_round_score": self._current_round_p2,
            "p1_total_score": sum(self._p1_round_scores),
            "p2_total_score": sum(self._p2_round_scores),
            "on_ground": self._on_ground,
            "p1_round_scores": self._p1_round_scores[:],
            "p2_round_scores": self._p2_round_scores[:],
            "p1_strikes": sum(1 for e in state.events if e.type in (EventType.PUNCH, EventType.GROUND_STRIKE) and e.team_id == state.home_team.id),
            "p2_strikes": sum(1 for e in state.events if e.type in (EventType.PUNCH, EventType.GROUND_STRIKE) and e.team_id == state.away_team.id),
            "p1_takedowns": sum(1 for e in state.events if e.type == EventType.TAKEDOWN and e.team_id == state.home_team.id),
            "p2_takedowns": sum(1 for e in state.events if e.type == EventType.TAKEDOWN and e.team_id == state.away_team.id),
            "p1_submissions": sum(1 for e in state.events if e.type == EventType.SUBMISSION and e.team_id == state.home_team.id),
            "p2_submissions": sum(1 for e in state.events if e.type == EventType.SUBMISSION and e.team_id == state.away_team.id),
        }
