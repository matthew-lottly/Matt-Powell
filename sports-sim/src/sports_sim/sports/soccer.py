"""Soccer (association football) sport module — 11v11, two 45-min halves."""

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

_PITCH_W, _PITCH_H = 105.0, 68.0
_GOAL_Y_MIN, _GOAL_Y_MAX = 30.66, 37.34  # ~7.32 m goal centered

POSITIONS_442 = [
    ("GK", 5, 34), ("LB", 20, 8), ("CB", 20, 25), ("CB", 20, 43), ("RB", 20, 60),
    ("LM", 40, 10), ("CM", 40, 28), ("CM", 40, 40), ("RM", 40, 58),
    ("ST", 60, 28), ("ST", 60, 40),
]

_FIRST_NAMES = ["James", "Carlos", "Luca", "Kenji", "Omar", "Noah", "Mateo", "Leo", "Kai", "Yusuf", "Alex"]
_LAST_NAMES = ["Silva", "Müller", "Park", "Johnson", "Garcia", "Ahmed", "Rossi", "Tanaka", "Santos", "Kim", "Walker"]


def _rand_attrs(rng: np.random.Generator, position: str) -> PlayerAttributes:
    base = rng.uniform(0.45, 0.85, size=8)
    if position == "GK":
        base[4] = rng.uniform(0.7, 0.95)  # skill (reflexes)
    elif position in ("ST",):
        base[2] = rng.uniform(0.65, 0.95)  # accuracy
    elif position in ("CB", "LB", "RB"):
        base[1] = rng.uniform(0.6, 0.9)   # strength
    return PlayerAttributes(
        speed=float(base[0]), strength=float(base[1]), accuracy=float(base[2]),
        endurance=float(base[3]), skill=float(base[4]), decision_making=float(base[5]),
        aggression=float(base[6]), composure=float(base[7]),
    )


def _make_team(name: str, abbr: str, seed: int) -> Team:
    rng = np.random.default_rng(seed)
    players = []
    for i, (pos, x, y) in enumerate(POSITIONS_442):
        p = Player(
            name=f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}",
            number=i + 1, position=pos,
            attributes=_rand_attrs(rng, pos), x=x, y=y,
        )
        players.append(p)
    bench = [
        Player(name=f"Sub {j}", number=12 + j, position="SUB",
               attributes=_rand_attrs(rng, "CM"))
        for j in range(5)
    ]
    return Team(name=name, abbreviation=abbr, players=players, bench=bench, formation="4-4-2")


class SoccerSport(Sport):
    @property
    def name(self) -> str:
        return "soccer"

    @property
    def default_periods(self) -> int:
        return 2

    @property
    def default_period_length(self) -> float:
        return 45.0

    @property
    def field_width(self) -> float:
        return _PITCH_W

    @property
    def field_height(self) -> float:
        return _PITCH_H

    @property
    def players_per_side(self) -> int:
        return 11

    def __init__(self):
        self._rng = np.random.default_rng()

    def create_default_teams(self) -> tuple[Team, Team]:
        return _make_team("Home United", "HMU", 100), _make_team("Away City", "AWC", 200)

    def setup_positions(self, state: GameState) -> GameState:
        for i, (pos, x, y) in enumerate(POSITIONS_442):
            if i < len(state.home_team.players):
                state.home_team.players[i].x = x
                state.home_team.players[i].y = y
            if i < len(state.away_team.players):
                state.away_team.players[i].x = _PITCH_W - x
                state.away_team.players[i].y = y
        state.ball = Ball(x=_PITCH_W / 2, y=_PITCH_H / 2)
        return state

    def tick(self, state: GameState, config: SimulationConfig) -> tuple[GameState, list[GameEvent]]:
        events: list[GameEvent] = []
        dt = 1.0 / config.ticks_per_second
        # Use the sport's RNG when provided by the engine; otherwise fall back to a local RNG.
        rng = self._rng or np.random.default_rng()
        rng = cast(np.random.Generator, rng)

        # Determine possession
        if state.possession_team_id is None:
            state.possession_team_id = state.home_team.id

        att = state.home_team if state.possession_team_id == state.home_team.id else state.away_team
        dfn = state.away_team if att is state.home_team else state.home_team

        # Move ball toward goal
        goal_x = _PITCH_W if att is state.home_team else 0.0
        dx = (goal_x - state.ball.x) * 0.02
        dy = rng.normal(0, 1.5) * dt
        state.ball.x = float(np.clip(state.ball.x + dx, 0, _PITCH_W))
        state.ball.y = float(np.clip(state.ball.y + dy, 0, _PITCH_H))

        # Move players toward ball (simplified)
        for p in att.active_players:
            p.x += (state.ball.x - p.x) * 0.01 * p.attributes.speed
            p.y += (state.ball.y - p.y) * 0.01 * p.attributes.speed
            p.x = float(np.clip(p.x, 0, _PITCH_W))
            p.y = float(np.clip(p.y, 0, _PITCH_H))
            p.minutes_played += dt / 60.0

        for p in dfn.active_players:
            p.x += (state.ball.x - p.x) * 0.008 * p.attributes.speed
            p.y += (state.ball.y - p.y) * 0.008 * p.attributes.speed
            p.x = float(np.clip(p.x, 0, _PITCH_W))
            p.y = float(np.clip(p.y, 0, _PITCH_H))
            p.minutes_played += dt / 60.0

        # --- Events (probabilistic) ---
        r = rng.random()

        # Pass events (~30% of ticks produce a pass attempt)
        if r < 0.003:
            _players = att.active_players
            passer = _players[int(rng.integers(len(_players)))]
            if rng.random() < passer.effective_skill * 0.85:
                events.append(GameEvent(
                    type=EventType.PASS, time=state.clock, period=state.period,
                    team_id=att.id, player_id=passer.id,
                    description=f"{passer.name} completes a pass",
                ))
            else:
                state.possession_team_id = dfn.id
                events.append(GameEvent(
                    type=EventType.TURNOVER, time=state.clock, period=state.period,
                    team_id=att.id, player_id=passer.id,
                    description=f"{passer.name} loses possession",
                ))

        # Shot on goal
        if abs(state.ball.x - goal_x) < 18.0 and rng.random() < 0.0008:
            _candidates = [p for p in att.active_players if p.position in ("ST", "CM", "RM", "LM")] or att.active_players
            shooter = _candidates[int(rng.integers(len(_candidates)))]
            shot_quality = shooter.effective_skill * shooter.attributes.accuracy
            shot_quality *= (1.0 - config.noise_level * rng.random())

            events.append(GameEvent(
                type=EventType.SHOT, time=state.clock, period=state.period,
                team_id=att.id, player_id=shooter.id,
                x=state.ball.x, y=state.ball.y,
                description=f"{shooter.name} shoots!",
            ))

            if shot_quality > 0.55:
                att.score += 1
                events.append(GameEvent(
                    type=EventType.GOAL, time=state.clock, period=state.period,
                    team_id=att.id, player_id=shooter.id,
                    description=f"GOAL! {shooter.name} scores for {att.name}! ({state.home_team.score}-{state.away_team.score})",
                ))
                state.ball = Ball(x=_PITCH_W / 2, y=_PITCH_H / 2)
                state.possession_team_id = dfn.id

        # Foul
        if rng.random() < 0.0003:
            _dfn_players = dfn.active_players
            fouler = _dfn_players[int(rng.integers(len(_dfn_players)))]
            events.append(GameEvent(
                type=EventType.FOUL, time=state.clock, period=state.period,
                team_id=dfn.id, player_id=fouler.id,
                description=f"Foul by {fouler.name}",
            ))
            if rng.random() < 0.15:
                events.append(GameEvent(
                    type=EventType.CARD, time=state.clock, period=state.period,
                    team_id=dfn.id, player_id=fouler.id,
                    description=f"Yellow card for {fouler.name}",
                    metadata={"card": "yellow"},
                ))

        # Possession change
        if rng.random() < 0.002:
            state.possession_team_id = dfn.id
            events.append(GameEvent(
                type=EventType.POSSESSION_CHANGE, time=state.clock, period=state.period,
                team_id=dfn.id, description="Possession change",
            ))

        return state, events

    def is_valid_state(self, state: GameState) -> bool:
        return (
            len(state.home_team.active_players) >= 7
            and len(state.away_team.active_players) >= 7
        )

    def post_event(self, state: GameState, event: GameEvent, config: SimulationConfig) -> GameState:
        if event.type == EventType.GOAL:
            team = state.home_team if event.team_id == state.home_team.id else state.away_team
            team.momentum = min(1.0, team.momentum + 0.15)
            other = state.away_team if team is state.home_team else state.home_team
            other.momentum = max(0.0, other.momentum - 0.1)
        return state
