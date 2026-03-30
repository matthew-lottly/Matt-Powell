"""Basketball sport module — 5v5, four 12-minute quarters, shot clock."""

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

_COURT_W, _COURT_H = 28.65, 15.24  # meters (NBA regulation)

POSITIONS_5 = [
    ("PG", 7, 7.6), ("SG", 5, 4), ("SF", 5, 11), ("PF", 3, 5), ("C", 2, 7.6),
]


def _rand_attrs(rng: np.random.Generator, pos: str) -> PlayerAttributes:
    base = rng.uniform(0.5, 0.9, size=8)
    if pos == "C":
        base[1] = rng.uniform(0.7, 0.95)  # strength
        base[0] = rng.uniform(0.4, 0.65)  # speed (slower)
    elif pos == "PG":
        base[5] = rng.uniform(0.7, 0.95)  # decision making
        base[0] = rng.uniform(0.7, 0.95)  # speed
    elif pos in ("SG", "SF"):
        base[2] = rng.uniform(0.6, 0.92)  # accuracy
    return PlayerAttributes(
        speed=float(base[0]), strength=float(base[1]), accuracy=float(base[2]),
        endurance=float(base[3]), skill=float(base[4]), decision_making=float(base[5]),
        aggression=float(base[6]), composure=float(base[7]),
    )


def _make_team(name: str, abbr: str, seed: int) -> Team:
    rng = np.random.default_rng(seed)
    first = ["Marcus", "Jaylen", "Devin", "Nikola", "Giannis", "Luka", "Shai", "Anthony", "Ja", "Trae", "Zion"]
    last = ["Thompson", "Brown", "Booker", "Jokic", "Davis", "Doncic", "Edwards", "Towns", "Morant", "Young", "Ball"]
    players = []
    for i, (pos, x, y) in enumerate(POSITIONS_5):
        players.append(Player(
            name=f"{rng.choice(first)} {rng.choice(last)}", number=i + 1,
            position=pos, attributes=_rand_attrs(rng, pos), x=x, y=y,
        ))
    bench = [Player(name=f"Bench {j}", number=6 + j, position="SUB", attributes=_rand_attrs(rng, "SG")) for j in range(7)]
    return Team(name=name, abbreviation=abbr, players=players, bench=bench, formation="standard", timeouts_remaining=7)


class BasketballSport(Sport):
    @property
    def name(self) -> str:
        return "basketball"

    @property
    def default_periods(self) -> int:
        return 4

    @property
    def default_period_length(self) -> float:
        return 12.0

    @property
    def field_width(self) -> float:
        return _COURT_W

    @property
    def field_height(self) -> float:
        return _COURT_H

    @property
    def players_per_side(self) -> int:
        return 5

    def __init__(self):
        self._rng = np.random.default_rng()
        self._shot_clock = 24.0

    def create_default_teams(self) -> tuple[Team, Team]:
        return _make_team("Home Blaze", "HBZ", 300), _make_team("Away Storm", "AWS", 400)

    def setup_positions(self, state: GameState) -> GameState:
        for i, (pos, x, y) in enumerate(POSITIONS_5):
            if i < len(state.home_team.players):
                state.home_team.players[i].x = x
                state.home_team.players[i].y = y
            if i < len(state.away_team.players):
                state.away_team.players[i].x = _COURT_W - x
                state.away_team.players[i].y = y
        state.ball = Ball(x=_COURT_W / 2, y=_COURT_H / 2)
        return state

    def tick(self, state: GameState, config: SimulationConfig) -> tuple[GameState, list[GameEvent]]:
        events: list[GameEvent] = []
        # Use the sport's RNG when provided by the engine; otherwise fall back to a local RNG.
        rng = self._rng or np.random.default_rng()
        rng = cast(np.random.Generator, rng)
        dt = 1.0 / config.ticks_per_second

        if state.possession_team_id is None:
            state.possession_team_id = state.home_team.id

        att = state.home_team if state.possession_team_id == state.home_team.id else state.away_team
        dfn = state.away_team if att is state.home_team else state.home_team

        hoop_x = _COURT_W if att is state.home_team else 0.0

        # Move ball
        state.ball.x += (hoop_x - state.ball.x) * 0.03
        state.ball.y += rng.normal(0, 0.5) * dt
        state.ball.x = float(np.clip(state.ball.x, 0, _COURT_W))
        state.ball.y = float(np.clip(state.ball.y, 0, _COURT_H))

        for p in att.active_players + dfn.active_players:
            p.x += (state.ball.x - p.x) * 0.015 * p.attributes.speed
            p.y += (state.ball.y - p.y) * 0.015 * p.attributes.speed
            p.x = float(np.clip(p.x, 0, _COURT_W))
            p.y = float(np.clip(p.y, 0, _COURT_H))
            p.minutes_played += dt / 60.0

        # Shot attempt
        dist_to_hoop = abs(state.ball.x - hoop_x)
        if dist_to_hoop < 7.0 and rng.random() < 0.004:
            _att_players = att.active_players
            shooter = _att_players[int(rng.integers(len(_att_players)))]
            is_three = dist_to_hoop > 6.75
            accuracy = shooter.effective_skill * shooter.attributes.accuracy
            accuracy *= 1.0 - config.noise_level * rng.random()

            events.append(GameEvent(
                type=EventType.SHOT, time=state.clock, period=state.period,
                team_id=att.id, player_id=shooter.id,
                x=state.ball.x, y=state.ball.y,
                description=f"{shooter.name} {'three-pointer' if is_three else 'shot'}!",
                metadata={"is_three": is_three},
            ))

            threshold = 0.38 if is_three else 0.48
            if accuracy > threshold:
                points = 3 if is_three else 2
                att.score += points
                events.append(GameEvent(
                    type=EventType.GOAL, time=state.clock, period=state.period,
                    team_id=att.id, player_id=shooter.id,
                    description=f"{shooter.name} scores {points}pts! ({state.home_team.score}-{state.away_team.score})",
                    metadata={"points": points},
                ))
                state.possession_team_id = dfn.id
            else:
                # Rebound
                _reb_pool = dfn.active_players + att.active_players
                rebounder = _reb_pool[int(rng.integers(len(_reb_pool)))]
                reb_team = state.home_team if rebounder in state.home_team.players else state.away_team
                state.possession_team_id = reb_team.id
                events.append(GameEvent(
                    type=EventType.REBOUND, time=state.clock, period=state.period,
                    team_id=reb_team.id, player_id=rebounder.id,
                    description=f"{rebounder.name} grabs the rebound",
                ))

        # Turnover
        if rng.random() < 0.001:
            _att_players2 = att.active_players
            handler = _att_players2[int(rng.integers(len(_att_players2)))]
            state.possession_team_id = dfn.id
            events.append(GameEvent(
                type=EventType.TURNOVER, time=state.clock, period=state.period,
                team_id=att.id, player_id=handler.id,
                description=f"Turnover by {handler.name}",
            ))

        # Foul
        if rng.random() < 0.0008:
            _dfn_players = dfn.active_players
            fouler = _dfn_players[int(rng.integers(len(_dfn_players)))]
            events.append(GameEvent(
                type=EventType.FOUL, time=state.clock, period=state.period,
                team_id=dfn.id, player_id=fouler.id,
                description=f"Foul by {fouler.name}",
            ))
            # Free throws
            _ft_players = att.active_players
            shooter = _ft_players[int(rng.integers(len(_ft_players)))]
            for ft in range(2):
                if rng.random() < shooter.attributes.accuracy * 0.85:
                    att.score += 1
                    events.append(GameEvent(
                        type=EventType.FREE_THROW, time=state.clock, period=state.period,
                        team_id=att.id, player_id=shooter.id,
                        description=f"Free throw made by {shooter.name}",
                        metadata={"attempt": ft + 1, "made": True},
                    ))
            state.possession_team_id = dfn.id

        # Steal
        if rng.random() < 0.0005:
            _dfn_players2 = dfn.active_players
            stealer = _dfn_players2[int(rng.integers(len(_dfn_players2)))]
            state.possession_team_id = dfn.id
            events.append(GameEvent(
                type=EventType.STEAL, time=state.clock, period=state.period,
                team_id=dfn.id, player_id=stealer.id,
                description=f"{stealer.name} steals the ball!",
            ))

        return state, events

    def is_valid_state(self, state: GameState) -> bool:
        return (
            len(state.home_team.active_players) >= 5
            and len(state.away_team.active_players) >= 5
        )

    def post_event(self, state: GameState, event: GameEvent, config: SimulationConfig) -> GameState:
        if event.type == EventType.GOAL:
            team = state.home_team if event.team_id == state.home_team.id else state.away_team
            team.momentum = min(1.0, team.momentum + 0.08)
        return state
