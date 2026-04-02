"""Racing sport module — circuit racing with multiple laps, pit stops, and position tracking."""

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

_TRACK_W, _TRACK_H = 300.0, 150.0  # abstract track dimensions


def _rand_attrs(rng: np.random.Generator) -> PlayerAttributes:
    return PlayerAttributes(
        speed=float(rng.uniform(0.65, 0.95)),  # car speed / qualifying pace
        strength=float(rng.uniform(0.4, 0.7)),  # physical endurance under G-forces
        accuracy=float(rng.uniform(0.6, 0.92)),  # precision / consistency
        endurance=float(rng.uniform(0.6, 0.90)),  # race-long endurance
        skill=float(rng.uniform(0.6, 0.95)),  # overall racing IQ
        decision_making=float(rng.uniform(0.6, 0.92)),  # strategy / overtake decisions
        aggression=float(rng.uniform(0.3, 0.8)),  # risk-taking in passes
        composure=float(rng.uniform(0.6, 0.92)),  # under pressure
    )


def _make_driver_team(name: str, abbr: str, seed: int) -> Team:
    rng = np.random.default_rng(seed)
    driver = Player(
        name=name, number=1, position="DRV",
        attributes=_rand_attrs(rng), x=0, y=_TRACK_H / 2,
    )
    return Team(name=name, abbreviation=abbr, players=[driver], bench=[], formation="individual")


class RacingSport(Sport):
    @property
    def name(self) -> str:
        return "racing"

    @property
    def default_periods(self) -> int:
        return 1  # single race

    @property
    def default_period_length(self) -> float:
        return 90.0  # ~90 minutes race

    @property
    def field_width(self) -> float:
        return _TRACK_W

    @property
    def field_height(self) -> float:
        return _TRACK_H

    @property
    def players_per_side(self) -> int:
        return 1

    def __init__(self):
        self._rng = np.random.default_rng()
        self._total_laps = 50
        self._p1_lap = 0
        self._p2_lap = 0
        self._p1_position = 0.0  # position around track (0-1)
        self._p2_position = 0.0
        self._p1_tire_wear = 1.0
        self._p2_tire_wear = 1.0
        self._p1_pit_stops = 0
        self._p2_pit_stops = 0
        self._p1_dnf = False
        self._p2_dnf = False
        self._p1_fastest_lap = 999.0
        self._p2_fastest_lap = 999.0

    def create_default_teams(self) -> tuple[Team, Team]:
        return _make_driver_team("Driver A", "DA", 2100), _make_driver_team("Driver B", "DB", 2200)

    def setup_positions(self, state: GameState) -> GameState:
        if state.home_team.players:
            state.home_team.players[0].x = 0
            state.home_team.players[0].y = _TRACK_H / 2 - 5
        if state.away_team.players:
            state.away_team.players[0].x = 0
            state.away_team.players[0].y = _TRACK_H / 2 + 5
        state.ball = Ball(x=0, y=0)
        return state

    def tick(self, state: GameState, config: SimulationConfig) -> tuple[GameState, list[GameEvent]]:
        events: list[GameEvent] = []
        rng = self._rng or np.random.default_rng()
        rng = cast(np.random.Generator, rng)

        if state.is_finished:
            return state, events

        dt = 1.0 / config.ticks_per_second
        p1 = state.home_team.players[0] if state.home_team.players else None
        p2 = state.away_team.players[0] if state.away_team.players else None
        if not p1 or not p2:
            return state, events

        # Advance positions based on speed and tire wear
        if not self._p1_dnf:
            p1_speed = p1.effective_skill * p1.attributes.speed * self._p1_tire_wear
            p1_advance = p1_speed * 0.0003 * (1.0 + rng.normal(0, 0.02))
            self._p1_position += p1_advance
            self._p1_tire_wear = max(0.3, self._p1_tire_wear - 0.00002)

        if not self._p2_dnf:
            p2_speed = p2.effective_skill * p2.attributes.speed * self._p2_tire_wear
            p2_advance = p2_speed * 0.0003 * (1.0 + rng.normal(0, 0.02))
            self._p2_position += p2_advance
            self._p2_tire_wear = max(0.3, self._p2_tire_wear - 0.00002)

        # Lap completion
        if self._p1_position >= 1.0 and not self._p1_dnf:
            self._p1_lap += 1
            self._p1_position -= 1.0
            lap_time = 1.0 / max(0.01, p1.effective_skill * self._p1_tire_wear) + rng.normal(0, 0.1)
            if lap_time < self._p1_fastest_lap:
                self._p1_fastest_lap = lap_time
                events.append(GameEvent(
                    type=EventType.FASTEST_LAP, time=state.clock, period=state.period,
                    team_id=state.home_team.id, player_id=p1.id,
                    description=f"Fastest lap for {p1.name}!",
                ))
            events.append(GameEvent(
                type=EventType.LAP_COMPLETE, time=state.clock, period=state.period,
                team_id=state.home_team.id, player_id=p1.id,
                description=f"{p1.name} completes lap {self._p1_lap}/{self._total_laps}",
                metadata={"lap": self._p1_lap, "total_laps": self._total_laps},
            ))

        if self._p2_position >= 1.0 and not self._p2_dnf:
            self._p2_lap += 1
            self._p2_position -= 1.0
            lap_time = 1.0 / max(0.01, p2.effective_skill * self._p2_tire_wear) + rng.normal(0, 0.1)
            if lap_time < self._p2_fastest_lap:
                self._p2_fastest_lap = lap_time
                events.append(GameEvent(
                    type=EventType.FASTEST_LAP, time=state.clock, period=state.period,
                    team_id=state.away_team.id, player_id=p2.id,
                    description=f"Fastest lap for {p2.name}!",
                ))
            events.append(GameEvent(
                type=EventType.LAP_COMPLETE, time=state.clock, period=state.period,
                team_id=state.away_team.id, player_id=p2.id,
                description=f"{p2.name} completes lap {self._p2_lap}/{self._total_laps}",
                metadata={"lap": self._p2_lap, "total_laps": self._total_laps},
            ))

        # Pit stop decisions
        if self._p1_tire_wear < 0.45 and rng.random() < 0.002 and not self._p1_dnf:
            self._p1_pit_stops += 1
            self._p1_tire_wear = 1.0
            self._p1_position -= 0.15  # time lost in pits
            events.append(GameEvent(
                type=EventType.PIT_STOP, time=state.clock, period=state.period,
                team_id=state.home_team.id, player_id=p1.id,
                description=f"{p1.name} pits for fresh tires (stop #{self._p1_pit_stops})",
            ))

        if self._p2_tire_wear < 0.45 and rng.random() < 0.002 and not self._p2_dnf:
            self._p2_pit_stops += 1
            self._p2_tire_wear = 1.0
            self._p2_position -= 0.15
            events.append(GameEvent(
                type=EventType.PIT_STOP, time=state.clock, period=state.period,
                team_id=state.away_team.id, player_id=p2.id,
                description=f"{p2.name} pits for fresh tires (stop #{self._p2_pit_stops})",
            ))

        # Overtake events
        if abs(self._p1_position - self._p2_position) < 0.02 and rng.random() < 0.01:
            if not self._p1_dnf and not self._p2_dnf:
                overtaker = state.home_team if self._p1_lap * 1.0 + self._p1_position > self._p2_lap * 1.0 + self._p2_position else state.away_team
                events.append(GameEvent(
                    type=EventType.OVERTAKE, time=state.clock, period=state.period,
                    team_id=overtaker.id,
                    description=f"Overtake by {overtaker.name}!",
                ))

        # Crash/DNF check (rare)
        if rng.random() < 0.00005:
            victim = state.home_team if rng.random() < 0.5 else state.away_team
            if victim is state.home_team and not self._p1_dnf:
                self._p1_dnf = True
                events.append(GameEvent(
                    type=EventType.CRASH, time=state.clock, period=state.period,
                    team_id=victim.id,
                    description=f"{p1.name} crashes out of the race!",
                ))
                events.append(GameEvent(
                    type=EventType.DNF, time=state.clock, period=state.period,
                    team_id=victim.id, description=f"{p1.name} DNF",
                ))
            elif victim is state.away_team and not self._p2_dnf:
                self._p2_dnf = True
                events.append(GameEvent(
                    type=EventType.CRASH, time=state.clock, period=state.period,
                    team_id=victim.id,
                    description=f"{p2.name} crashes out of the race!",
                ))
                events.append(GameEvent(
                    type=EventType.DNF, time=state.clock, period=state.period,
                    team_id=victim.id, description=f"{p2.name} DNF",
                ))

        # Score = laps completed
        state.home_team.score = self._p1_lap
        state.away_team.score = self._p2_lap

        # Race finish
        if self._p1_lap >= self._total_laps or self._p2_lap >= self._total_laps or (self._p1_dnf and self._p2_dnf):
            events.append(GameEvent(
                type=EventType.CHECKERED_FLAG, time=state.clock, period=state.period,
                description="Checkered flag! Race complete!",
            ))
            state.is_finished = True

        # Update visual positions
        if p1:
            angle = self._p1_position * 2 * np.pi
            p1.x = float(_TRACK_W / 2 + np.cos(angle) * _TRACK_W * 0.4)
            p1.y = float(_TRACK_H / 2 + np.sin(angle) * _TRACK_H * 0.35)
        if p2:
            angle = self._p2_position * 2 * np.pi
            p2.x = float(_TRACK_W / 2 + np.cos(angle) * _TRACK_W * 0.4)
            p2.y = float(_TRACK_H / 2 + np.sin(angle) * _TRACK_H * 0.35)

        return state, events

    def is_valid_state(self, state: GameState) -> bool:
        return len(state.home_team.players) >= 1 and len(state.away_team.players) >= 1

    def post_event(self, state: GameState, event: GameEvent, config: SimulationConfig) -> GameState:
        if event.type == EventType.OVERTAKE:
            team = state.home_team if event.team_id == state.home_team.id else state.away_team
            team.momentum = min(1.0, team.momentum + 0.1)
        return state

    def get_sport_state(self, state: GameState) -> dict:
        return {
            "p1_lap": self._p1_lap,
            "p2_lap": self._p2_lap,
            "total_laps": self._total_laps,
            "p1_position": round(self._p1_position, 2),
            "p2_position": round(self._p2_position, 2),
            "p1_tire_wear": round(self._p1_tire_wear, 3),
            "p2_tire_wear": round(self._p2_tire_wear, 3),
            "p1_pit_stops": self._p1_pit_stops,
            "p2_pit_stops": self._p2_pit_stops,
            "p1_dnf": self._p1_dnf,
            "p2_dnf": self._p2_dnf,
            "p1_fastest_lap": round(self._p1_fastest_lap, 3) if self._p1_fastest_lap < 900 else None,
            "p2_fastest_lap": round(self._p2_fastest_lap, 3) if self._p2_fastest_lap < 900 else None,
            "gap": round(abs(self._p1_position - self._p2_position), 2),
            "leader": "p1" if self._p1_position >= self._p2_position else "p2",
        }
