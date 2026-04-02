"""Boxing sport module — 12 rounds, two fighters, judge scoring."""

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

_RING_W, _RING_H = 7.32, 7.32  # meters (24-foot ring)


def _rand_attrs(rng: np.random.Generator) -> PlayerAttributes:
    return PlayerAttributes(
        speed=float(rng.uniform(0.55, 0.92)),
        strength=float(rng.uniform(0.55, 0.92)),
        accuracy=float(rng.uniform(0.5, 0.90)),
        endurance=float(rng.uniform(0.55, 0.90)),
        skill=float(rng.uniform(0.55, 0.92)),
        decision_making=float(rng.uniform(0.5, 0.85)),
        aggression=float(rng.uniform(0.4, 0.85)),
        composure=float(rng.uniform(0.5, 0.90)),
    )


def _make_fighter_team(name: str, abbr: str, seed: int) -> Team:
    rng = np.random.default_rng(seed)
    fighter = Player(
        name=name, number=1, position="BOX",
        attributes=_rand_attrs(rng), x=2.0, y=_RING_H / 2,
    )
    return Team(name=name, abbreviation=abbr, players=[fighter], bench=[], formation="individual")


class BoxingSport(Sport):
    @property
    def name(self) -> str:
        return "boxing"

    @property
    def default_periods(self) -> int:
        return 12

    @property
    def default_period_length(self) -> float:
        return 3.0  # 3-minute rounds

    @property
    def field_width(self) -> float:
        return _RING_W

    @property
    def field_height(self) -> float:
        return _RING_H

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
        self._knockdowns_p1 = 0
        self._knockdowns_p2 = 0

    def create_default_teams(self) -> tuple[Team, Team]:
        return _make_fighter_team("Fighter A", "FA", 1700), _make_fighter_team("Fighter B", "FB", 1800)

    def setup_positions(self, state: GameState) -> GameState:
        if state.home_team.players:
            state.home_team.players[0].x = 2.0
            state.home_team.players[0].y = _RING_H / 2
        if state.away_team.players:
            state.away_team.players[0].x = _RING_W - 2.0
            state.away_team.players[0].y = _RING_H / 2
        state.ball = Ball(x=_RING_W / 2, y=_RING_H / 2)
        return state

    def tick(self, state: GameState, config: SimulationConfig) -> tuple[GameState, list[GameEvent]]:
        events: list[GameEvent] = []
        rng = self._rng or np.random.default_rng()
        rng = cast(np.random.Generator, rng)

        if state.is_finished:
            return state, events

        if rng.random() > 0.006:
            return state, events

        p1 = state.home_team.players[0] if state.home_team.players else None
        p2 = state.away_team.players[0] if state.away_team.players else None
        if not p1 or not p2:
            return state, events

        # Each exchange
        p1_power = p1.effective_skill * p1.attributes.strength * (1.0 + p1.attributes.aggression * 0.2)
        p2_power = p2.effective_skill * p2.attributes.strength * (1.0 + p2.attributes.aggression * 0.2)
        p1_defense = p1.attributes.speed * 0.4 + p1.attributes.composure * 0.3 + p1.attributes.decision_making * 0.3
        p2_defense = p2.attributes.speed * 0.4 + p2.attributes.composure * 0.3 + p2.attributes.decision_making * 0.3

        # P1 attacks
        if rng.random() < p1.attributes.accuracy * 0.6:
            damage = p1_power * (1.0 - p2_defense * 0.4) * rng.uniform(2, 6)
            self._p2_health = max(0.0, self._p2_health - damage)
            self._current_round_p1 += 1

            events.append(GameEvent(
                type=EventType.PUNCH, time=state.clock, period=state.period,
                team_id=state.home_team.id, player_id=p1.id,
                description=f"{p1.name} lands a punch on {p2.name}",
                metadata={"damage": round(damage, 1)},
            ))

            # Knockdown check
            if self._p2_health < 30 and rng.random() < 0.15:
                self._knockdowns_p2 += 1
                self._current_round_p1 += 2
                events.append(GameEvent(
                    type=EventType.KNOCKDOWN, time=state.clock, period=state.period,
                    team_id=state.home_team.id, player_id=p1.id,
                    description=f"KNOCKDOWN! {p2.name} hits the canvas!",
                ))
                if self._knockdowns_p2 >= 3 or self._p2_health <= 0:
                    state.home_team.score = sum(self._p1_round_scores) + self._current_round_p1 + 10
                    state.away_team.score = sum(self._p2_round_scores) + self._current_round_p2
                    events.append(GameEvent(
                        type=EventType.KNOCKOUT, time=state.clock, period=state.period,
                        team_id=state.home_team.id, player_id=p1.id,
                        description=f"KNOCKOUT! {p1.name} wins by KO!",
                    ))
                    state.is_finished = True
                    return state, events

        # P2 attacks
        if rng.random() < p2.attributes.accuracy * 0.6:
            damage = p2_power * (1.0 - p1_defense * 0.4) * rng.uniform(2, 6)
            self._p1_health = max(0.0, self._p1_health - damage)
            self._current_round_p2 += 1

            events.append(GameEvent(
                type=EventType.PUNCH, time=state.clock, period=state.period,
                team_id=state.away_team.id, player_id=p2.id,
                description=f"{p2.name} lands a punch on {p1.name}",
                metadata={"damage": round(damage, 1)},
            ))

            if self._p1_health < 30 and rng.random() < 0.15:
                self._knockdowns_p1 += 1
                self._current_round_p2 += 2
                events.append(GameEvent(
                    type=EventType.KNOCKDOWN, time=state.clock, period=state.period,
                    team_id=state.away_team.id, player_id=p2.id,
                    description=f"KNOCKDOWN! {p1.name} hits the canvas!",
                ))
                if self._knockdowns_p1 >= 3 or self._p1_health <= 0:
                    state.away_team.score = sum(self._p2_round_scores) + self._current_round_p2 + 10
                    state.home_team.score = sum(self._p1_round_scores) + self._current_round_p1
                    events.append(GameEvent(
                        type=EventType.KNOCKOUT, time=state.clock, period=state.period,
                        team_id=state.away_team.id, player_id=p2.id,
                        description=f"KNOCKOUT! {p2.name} wins by KO!",
                    ))
                    state.is_finished = True
                    return state, events

        # Clinch
        if rng.random() < 0.04:
            events.append(GameEvent(
                type=EventType.CLINCH, time=state.clock, period=state.period,
                description="Fighters clinch — referee separates",
            ))

        # Update scores (round scoring 10-point must system)
        state.home_team.score = sum(self._p1_round_scores) + self._current_round_p1
        state.away_team.score = sum(self._p2_round_scores) + self._current_round_p2

        return state, events

    def _end_round(self, state: GameState):
        """Called at period end to score a round."""
        # 10-point must system
        # 10-point must system with 10-8 for dominant rounds
        diff = abs(self._current_round_p1 - self._current_round_p2)
        if self._current_round_p1 > self._current_round_p2:
            self._p1_round_scores.append(10)
            self._p2_round_scores.append(8 if diff >= 4 else 9)
        elif self._current_round_p2 > self._current_round_p1:
            self._p1_round_scores.append(8 if diff >= 4 else 9)
            self._p2_round_scores.append(10)
        else:
            self._p1_round_scores.append(10)
            self._p2_round_scores.append(10)
        self._current_round_p1 = 0
        self._current_round_p2 = 0
        # Partial health recovery between rounds
        self._p1_health = min(100.0, self._p1_health + 8)
        self._p2_health = min(100.0, self._p2_health + 8)

    def is_valid_state(self, state: GameState) -> bool:
        return len(state.home_team.players) >= 1 and len(state.away_team.players) >= 1

    def post_event(self, state: GameState, event: GameEvent, config: SimulationConfig) -> GameState:
        if event.type == EventType.PERIOD_END:
            self._end_round(state)
            state.home_team.score = sum(self._p1_round_scores)
            state.away_team.score = sum(self._p2_round_scores)
        if event.type == EventType.KNOCKDOWN:
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
            "p1_knockdowns": self._knockdowns_p1,
            "p2_knockdowns": self._knockdowns_p2,
            "p1_round_scores": self._p1_round_scores[:],
            "p2_round_scores": self._p2_round_scores[:],
            "p1_punches": sum(1 for e in state.events if e.type == EventType.PUNCH and e.team_id == state.home_team.id),
            "p2_punches": sum(1 for e in state.events if e.type == EventType.PUNCH and e.team_id == state.away_team.id),
            "p1_total_damage": round(sum(e.metadata.get("damage", 0) for e in state.events if e.type == EventType.PUNCH and e.team_id == state.home_team.id), 1),
            "p2_total_damage": round(sum(e.metadata.get("damage", 0) for e in state.events if e.type == EventType.PUNCH and e.team_id == state.away_team.id), 1),
        }
