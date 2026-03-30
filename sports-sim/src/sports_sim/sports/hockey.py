"""Ice Hockey sport module — 5v5 (+ goalie), three 20-minute periods."""

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

_RINK_W, _RINK_H = 60.96, 25.91  # meters (NHL regulation 200x85 ft)

POSITIONS_6 = [
    ("G", 3, 13), ("LD", 12, 8), ("RD", 12, 18),
    ("LW", 25, 6), ("C", 25, 13), ("RW", 25, 20),
]


def _rand_attrs(rng: np.random.Generator, pos: str) -> PlayerAttributes:
    base = rng.uniform(0.5, 0.88, size=8)
    if pos == "G":
        base[4] = rng.uniform(0.75, 0.96)  # skill (reflexes)
        base[0] = rng.uniform(0.4, 0.6)    # speed (lower)
    elif pos == "C":
        base[5] = rng.uniform(0.65, 0.90)  # decision making
        base[0] = rng.uniform(0.7, 0.92)   # speed
    elif pos in ("LW", "RW"):
        base[2] = rng.uniform(0.6, 0.92)   # accuracy (shooting)
        base[0] = rng.uniform(0.7, 0.92)   # speed
    elif pos in ("LD", "RD"):
        base[1] = rng.uniform(0.6, 0.88)   # strength
    return PlayerAttributes(
        speed=float(base[0]), strength=float(base[1]), accuracy=float(base[2]),
        endurance=float(base[3]), skill=float(base[4]), decision_making=float(base[5]),
        aggression=float(base[6]), composure=float(base[7]),
    )


def _make_team(name: str, abbr: str, seed: int) -> Team:
    rng = np.random.default_rng(seed)
    first = ["Connor", "Auston", "Nathan", "Leon", "Cale", "Sidney", "Alex", "David", "Nikita", "Mika", "Jack"]
    last = ["McDavid", "Matthews", "MacKinnon", "Draisaitl", "Makar", "Crosby", "Ovechkin", "Pastrnak", "Kucherov", "Zibanejad", "Hughes"]
    players = []
    for i, (pos, x, y) in enumerate(POSITIONS_6):
        players.append(Player(
            name=f"{rng.choice(first)} {rng.choice(last)}", number=i + 1,
            position=pos, attributes=_rand_attrs(rng, pos), x=x, y=y,
        ))
    bench = [Player(name=f"Bench {j}", number=7 + j, position="SUB", attributes=_rand_attrs(rng, "C")) for j in range(12)]
    return Team(name=name, abbreviation=abbr, players=players, bench=bench, formation="standard")


class HockeySport(Sport):
    @property
    def name(self) -> str:
        return "hockey"

    @property
    def default_periods(self) -> int:
        return 3

    @property
    def default_period_length(self) -> float:
        return 20.0

    @property
    def field_width(self) -> float:
        return _RINK_W

    @property
    def field_height(self) -> float:
        return _RINK_H

    @property
    def players_per_side(self) -> int:
        return 6  # 5 skaters + 1 goalie

    def __init__(self):
        self._rng = np.random.default_rng()
        self._power_play_ticks: dict[str, int] = {}  # team_id -> ticks remaining

    def create_default_teams(self) -> tuple[Team, Team]:
        return _make_team("Home Blades", "HBL", 900), _make_team("Away Frost", "AFR", 950)

    def setup_positions(self, state: GameState) -> GameState:
        for i, (pos, x, y) in enumerate(POSITIONS_6):
            if i < len(state.home_team.players):
                state.home_team.players[i].x = x
                state.home_team.players[i].y = y
            if i < len(state.away_team.players):
                state.away_team.players[i].x = _RINK_W - x
                state.away_team.players[i].y = y
        state.ball = Ball(x=_RINK_W / 2, y=_RINK_H / 2)  # puck
        return state

    def tick(self, state: GameState, config: SimulationConfig) -> tuple[GameState, list[GameEvent]]:
        events: list[GameEvent] = []
        rng = self._rng or np.random.default_rng()
        rng = cast(np.random.Generator, rng)
        dt = 1.0 / config.ticks_per_second

        if state.possession_team_id is None:
            state.possession_team_id = state.home_team.id

        att = state.home_team if state.possession_team_id == state.home_team.id else state.away_team
        dfn = state.away_team if att is state.home_team else state.home_team

        goal_x = _RINK_W if att is state.home_team else 0.0

        # Move puck toward goal
        state.ball.x += (goal_x - state.ball.x) * 0.025
        state.ball.y += rng.normal(0, 1.0) * dt
        state.ball.x = float(np.clip(state.ball.x, 0, _RINK_W))
        state.ball.y = float(np.clip(state.ball.y, 0, _RINK_H))

        # Move players
        for p in att.active_players + dfn.active_players:
            p.x += (state.ball.x - p.x) * 0.02 * p.attributes.speed
            p.y += (state.ball.y - p.y) * 0.02 * p.attributes.speed
            p.x = float(np.clip(p.x, 0, _RINK_W))
            p.y = float(np.clip(p.y, 0, _RINK_H))
            p.minutes_played += dt / 60.0

        # Power play tick-down
        for team_id in list(self._power_play_ticks.keys()):
            self._power_play_ticks[team_id] -= 1
            if self._power_play_ticks[team_id] <= 0:
                del self._power_play_ticks[team_id]

        # Shot on goal
        dist_to_goal = abs(state.ball.x - goal_x)
        if dist_to_goal < 10.0 and rng.random() < 0.003:
            shooters = [p for p in att.active_players if p.position in ("LW", "RW", "C")] or att.active_players
            shooter = shooters[int(rng.integers(len(shooters)))]
            shot_quality = shooter.effective_skill * shooter.attributes.accuracy
            shot_quality *= (1.0 - config.noise_level * rng.random())

            # Power play bonus
            if att.id in self._power_play_ticks:
                shot_quality *= 1.15

            events.append(GameEvent(
                type=EventType.SHOT, time=state.clock, period=state.period,
                team_id=att.id, player_id=shooter.id,
                x=state.ball.x, y=state.ball.y,
                description=f"{shooter.name} shoots!",
            ))

            # Goalie save check
            goalie = next((p for p in dfn.active_players if p.position == "G"), dfn.active_players[0])
            save_quality = goalie.effective_skill * goalie.attributes.skill

            if shot_quality > save_quality * 1.1:
                att.score += 1
                events.append(GameEvent(
                    type=EventType.GOAL, time=state.clock, period=state.period,
                    team_id=att.id, player_id=shooter.id,
                    description=f"GOAL! {shooter.name} scores for {att.name}! ({state.home_team.score}-{state.away_team.score})",
                ))
                state.ball = Ball(x=_RINK_W / 2, y=_RINK_H / 2)
                state.possession_team_id = dfn.id
            else:
                events.append(GameEvent(
                    type=EventType.SAVE, time=state.clock, period=state.period,
                    team_id=dfn.id, player_id=goalie.id,
                    description=f"Save by {goalie.name}!",
                ))

        # Face-off
        if rng.random() < 0.0005:
            events.append(GameEvent(
                type=EventType.FACE_OFF, time=state.clock, period=state.period,
                description="Face-off",
            ))
            if rng.random() < 0.5:
                state.possession_team_id = dfn.id

        # Penalty
        if rng.random() < 0.0004:
            fouler_team = att if rng.random() < 0.5 else dfn
            other_team = dfn if fouler_team is att else att
            foulers = fouler_team.active_players
            fouler = foulers[int(rng.integers(len(foulers)))]
            minutes = int(rng.choice([2, 2, 2, 5]))
            events.append(GameEvent(
                type=EventType.PENALTY_MINUTES, time=state.clock, period=state.period,
                team_id=fouler_team.id, player_id=fouler.id,
                description=f"{minutes}-minute penalty on {fouler.name}",
                metadata={"minutes": minutes},
            ))
            # Power play for other team
            pp_ticks = minutes * 60 * config.ticks_per_second
            self._power_play_ticks[other_team.id] = pp_ticks
            events.append(GameEvent(
                type=EventType.POWER_PLAY, time=state.clock, period=state.period,
                team_id=other_team.id,
                description=f"Power play for {other_team.name}",
            ))

        # Icing
        if rng.random() < 0.0003:
            events.append(GameEvent(
                type=EventType.ICING, time=state.clock, period=state.period,
                team_id=att.id,
                description=f"Icing called on {att.name}",
            ))
            state.possession_team_id = dfn.id

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
            len(state.home_team.active_players) >= 4
            and len(state.away_team.active_players) >= 4
        )

    def post_event(self, state: GameState, event: GameEvent, config: SimulationConfig) -> GameState:
        if event.type == EventType.GOAL:
            team = state.home_team if event.team_id == state.home_team.id else state.away_team
            team.momentum = min(1.0, team.momentum + 0.12)
            other = state.away_team if team is state.home_team else state.home_team
            other.momentum = max(0.0, other.momentum - 0.08)
        return state
