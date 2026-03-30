"""Baseball sport module — 9 innings, 9v9, at-bat driven simulation."""

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

_FIELD_W, _FIELD_H = 128.0, 128.0  # approx diamond + outfield

POSITIONS_9 = [
    ("P", 18.4, 64), ("C", 0.5, 64), ("1B", 27, 50), ("2B", 27, 78),
    ("3B", 27, 50), ("SS", 27, 64), ("LF", 60, 30), ("CF", 70, 64), ("RF", 60, 98),
]


def _rand_attrs(rng: np.random.Generator, pos: str) -> PlayerAttributes:
    base = rng.uniform(0.45, 0.85, size=8)
    if pos == "P":
        base[2] = rng.uniform(0.65, 0.95)  # accuracy (pitching)
        base[4] = rng.uniform(0.7, 0.95)   # skill
    elif pos == "C":
        base[1] = rng.uniform(0.6, 0.85)   # strength
    return PlayerAttributes(
        speed=float(base[0]), strength=float(base[1]), accuracy=float(base[2]),
        endurance=float(base[3]), skill=float(base[4]), decision_making=float(base[5]),
        aggression=float(base[6]), composure=float(base[7]),
    )


def _make_team(name: str, abbr: str, seed: int) -> Team:
    rng = np.random.default_rng(seed)
    first = ["Mike", "Aaron", "Shohei", "Mookie", "Freddie", "Juan", "Trea", "Ronald", "Corey", "Bryce"]
    last = ["Trout", "Judge", "Ohtani", "Betts", "Freeman", "Soto", "Turner", "Acuña", "Seager", "Harper"]
    players = []
    for i, (pos, x, y) in enumerate(POSITIONS_9):
        players.append(Player(
            name=f"{rng.choice(first)} {rng.choice(last)}", number=i + 1,
            position=pos, attributes=_rand_attrs(rng, pos), x=x, y=y,
        ))
    bench = [Player(name=f"Bench {j}", number=10 + j, position="PH", attributes=_rand_attrs(rng, "SS")) for j in range(5)]
    return Team(name=name, abbreviation=abbr, players=players, bench=bench, formation="standard")


class BaseballSport(Sport):
    @property
    def name(self) -> str:
        return "baseball"

    @property
    def default_periods(self) -> int:
        return 9

    @property
    def default_period_length(self) -> float:
        return 5.0  # ~5 min per half-inning (simplified)

    @property
    def field_width(self) -> float:
        return _FIELD_W

    @property
    def field_height(self) -> float:
        return _FIELD_H

    @property
    def players_per_side(self) -> int:
        return 9

    def __init__(self):
        self._rng = np.random.default_rng()
        self._outs = 0
        self._bases = [False, False, False]  # 1B, 2B, 3B
        self._top_of_inning = True
        self._at_bat_index = 0

    def create_default_teams(self) -> tuple[Team, Team]:
        return _make_team("Home Sluggers", "HSL", 500), _make_team("Away Eagles", "AEG", 600)

    def setup_positions(self, state: GameState) -> GameState:
        for i, (pos, x, y) in enumerate(POSITIONS_9):
            if i < len(state.home_team.players):
                state.home_team.players[i].x = x
                state.home_team.players[i].y = y
            if i < len(state.away_team.players):
                state.away_team.players[i].x = x
                state.away_team.players[i].y = y
        state.ball = Ball(x=18.4, y=64)
        self._outs = 0
        self._bases = [False, False, False]
        return state

    def tick(self, state: GameState, config: SimulationConfig) -> tuple[GameState, list[GameEvent]]:
        events: list[GameEvent] = []
        # Use the sport's RNG when provided by the engine; otherwise fall back to a local RNG.
        rng = self._rng or np.random.default_rng()
        rng = cast(np.random.Generator, rng)

        if state.is_finished:
            return state, events

        # Determine batting/pitching
        batting = state.away_team if self._top_of_inning else state.home_team
        fielding = state.home_team if self._top_of_inning else state.away_team

        # Only process at-bat events periodically (not every tick)
        if rng.random() > 0.015:
            return state, events

        pitcher = next((p for p in fielding.active_players if p.position == "P"), fielding.active_players[0])
        batter_idx = self._at_bat_index % len(batting.active_players)
        batter = batting.active_players[batter_idx]

        pitch_quality = pitcher.effective_skill * pitcher.attributes.accuracy
        bat_quality = batter.effective_skill * batter.attributes.strength * 0.5 + batter.attributes.accuracy * 0.5

        roll = rng.random()
        noise = config.noise_level * rng.normal()

        effective_bat = bat_quality + noise * 0.1

        if roll < 0.18:  # Strikeout
            self._outs += 1
            events.append(GameEvent(
                type=EventType.STRIKEOUT, time=state.clock, period=state.period,
                team_id=fielding.id, player_id=pitcher.id,
                secondary_player_id=batter.id,
                description=f"{batter.name} strikes out ({self._outs} outs)",
            ))
        elif roll < 0.35:  # Out (groundout / flyout)
            self._outs += 1
            events.append(GameEvent(
                type=EventType.OUT, time=state.clock, period=state.period,
                team_id=fielding.id, player_id=batter.id,
                description=f"{batter.name} out ({self._outs} outs)",
            ))
        elif roll < 0.42:  # Walk
            self._advance_runners()
            self._bases[0] = True
            events.append(GameEvent(
                type=EventType.WALK, time=state.clock, period=state.period,
                team_id=batting.id, player_id=batter.id,
                description=f"{batter.name} walks",
            ))
        elif roll < 0.70:  # Single
            runs = self._advance_runners()
            self._bases[0] = True
            batting.score += runs
            events.append(GameEvent(
                type=EventType.HIT, time=state.clock, period=state.period,
                team_id=batting.id, player_id=batter.id,
                description=f"{batter.name} singles!",
                metadata={"hit_type": "single", "runs_scored": runs},
            ))
            if runs > 0:
                events.append(GameEvent(
                    type=EventType.RUN, time=state.clock, period=state.period,
                    team_id=batting.id,
                    description=f"{runs} run(s) score! ({state.home_team.score}-{state.away_team.score})",
                    metadata={"runs": runs},
                ))
        elif roll < 0.82:  # Double
            runs = self._advance_runners(extra=1)
            self._bases = [False, True, False]
            batting.score += runs
            events.append(GameEvent(
                type=EventType.HIT, time=state.clock, period=state.period,
                team_id=batting.id, player_id=batter.id,
                description=f"{batter.name} doubles!",
                metadata={"hit_type": "double", "runs_scored": runs},
            ))
            if runs > 0:
                events.append(GameEvent(
                    type=EventType.RUN, time=state.clock, period=state.period,
                    team_id=batting.id,
                    description=f"{runs} run(s) score!",
                    metadata={"runs": runs},
                ))
        elif roll < 0.88:  # Triple
            runs = sum(self._bases) + 0
            self._bases = [False, False, True]
            batting.score += runs
            events.append(GameEvent(
                type=EventType.HIT, time=state.clock, period=state.period,
                team_id=batting.id, player_id=batter.id,
                description=f"{batter.name} triples!",
                metadata={"hit_type": "triple", "runs_scored": runs},
            ))
        else:  # Home run
            runs = sum(self._bases) + 1
            self._bases = [False, False, False]
            batting.score += runs
            events.append(GameEvent(
                type=EventType.HOME_RUN, time=state.clock, period=state.period,
                team_id=batting.id, player_id=batter.id,
                description=f"{batter.name} HOME RUN! {runs} run(s)! ({state.home_team.score}-{state.away_team.score})",
                metadata={"runs_scored": runs},
            ))

        self._at_bat_index += 1

        # Check half-inning over
        if self._outs >= 3:
            self._outs = 0
            self._bases = [False, False, False]
            self._at_bat_index = 0
            if not self._top_of_inning:
                # Full inning complete — period advances are handled by engine
                pass
            self._top_of_inning = not self._top_of_inning

        return state, events

    def _advance_runners(self, extra: int = 0) -> int:
        runs = 0
        new_bases = [False, False, False]
        for i in range(2, -1, -1):
            if self._bases[i]:
                dest = i + 1 + extra
                if dest >= 3:
                    runs += 1
                else:
                    new_bases[dest] = True
        self._bases = new_bases
        return runs

    def is_valid_state(self, state: GameState) -> bool:
        return len(state.home_team.active_players) >= 9 and len(state.away_team.active_players) >= 9

    def post_event(self, state: GameState, event: GameEvent, config: SimulationConfig) -> GameState:
        if event.type in (EventType.HOME_RUN, EventType.RUN):
            team = state.home_team if event.team_id == state.home_team.id else state.away_team
            team.momentum = min(1.0, team.momentum + 0.12)
        return state
