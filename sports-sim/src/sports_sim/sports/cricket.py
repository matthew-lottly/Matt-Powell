"""Cricket sport module — T20 format, 20 overs per side."""

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

_FIELD_W, _FIELD_H = 150.0, 150.0  # circular field approx

POSITIONS_11 = [
    ("BAT", 22, 75), ("BAT", 0, 75), ("BOWL", 22, 75),
    ("WK", 0, 75), ("FIELD", 50, 25), ("FIELD", 50, 125),
    ("FIELD", 75, 50), ("FIELD", 75, 100), ("FIELD", 100, 75),
    ("FIELD", 30, 40), ("FIELD", 30, 110),
]


def _rand_attrs(rng: np.random.Generator, pos: str) -> PlayerAttributes:
    base = rng.uniform(0.45, 0.85, size=8)
    if pos == "BAT":
        base[2] = rng.uniform(0.6, 0.92)  # accuracy (batting)
        base[4] = rng.uniform(0.6, 0.92)  # skill
    elif pos == "BOWL":
        base[2] = rng.uniform(0.65, 0.95)  # accuracy (bowling)
        base[0] = rng.uniform(0.6, 0.88)   # speed
    elif pos == "WK":
        base[4] = rng.uniform(0.7, 0.92)   # skill (keeping)
    return PlayerAttributes(
        speed=float(base[0]), strength=float(base[1]), accuracy=float(base[2]),
        endurance=float(base[3]), skill=float(base[4]), decision_making=float(base[5]),
        aggression=float(base[6]), composure=float(base[7]),
    )


def _make_team(name: str, abbr: str, seed: int) -> Team:
    rng = np.random.default_rng(seed)
    first = ["Virat", "Rohit", "Steve", "Kane", "Joe", "Babar", "Shakib", "Rashid", "Pat", "Ben", "Jasprit"]
    last = ["Kohli", "Sharma", "Smith", "Williamson", "Root", "Azam", "Al Hasan", "Khan", "Cummins", "Stokes", "Bumrah"]
    players = []
    for i, (pos, x, y) in enumerate(POSITIONS_11):
        players.append(Player(
            name=f"{rng.choice(first)} {rng.choice(last)}", number=i + 1,
            position=pos, attributes=_rand_attrs(rng, pos), x=x, y=y,
        ))
    bench = [Player(name=f"Sub {j}", number=12 + j, position="SUB", attributes=_rand_attrs(rng, "FIELD")) for j in range(4)]
    return Team(name=name, abbreviation=abbr, players=players, bench=bench, formation="standard")


class CricketSport(Sport):
    @property
    def name(self) -> str:
        return "cricket"

    @property
    def default_periods(self) -> int:
        return 2  # two innings

    @property
    def default_period_length(self) -> float:
        return 40.0  # ~40 min per innings

    @property
    def field_width(self) -> float:
        return _FIELD_W

    @property
    def field_height(self) -> float:
        return _FIELD_H

    @property
    def players_per_side(self) -> int:
        return 11

    def __init__(self):
        self._rng = np.random.default_rng()
        self._wickets = 0
        self._overs = 0
        self._balls_in_over = 0
        self._batting_first = True
        self._batting_order_idx = 0

    def create_default_teams(self) -> tuple[Team, Team]:
        return _make_team("Home XI", "HXI", 1500), _make_team("Away XI", "AXI", 1600)

    def setup_positions(self, state: GameState) -> GameState:
        for i, (pos, x, y) in enumerate(POSITIONS_11):
            if i < len(state.home_team.players):
                state.home_team.players[i].x = x
                state.home_team.players[i].y = y
            if i < len(state.away_team.players):
                state.away_team.players[i].x = x
                state.away_team.players[i].y = y
        state.ball = Ball(x=11, y=75)
        self._wickets = 0
        self._balls_in_over = 0
        self._batting_order_idx = 0
        return state

    def tick(self, state: GameState, config: SimulationConfig) -> tuple[GameState, list[GameEvent]]:
        events: list[GameEvent] = []
        rng = self._rng or np.random.default_rng()
        rng = cast(np.random.Generator, rng)

        if state.is_finished:
            return state, events

        # Process deliveries periodically
        if rng.random() > 0.012:
            return state, events

        batting_team = state.home_team if self._batting_first else state.away_team
        bowling_team = state.away_team if self._batting_first else state.home_team

        batsmen = [p for p in batting_team.active_players if p.position in ("BAT", "FIELD")]
        bowlers = [p for p in bowling_team.active_players if p.position in ("BOWL", "FIELD")]

        if not batsmen or not bowlers:
            return state, events

        batsman = batsmen[self._batting_order_idx % len(batsmen)]
        bowler = bowlers[int(rng.integers(len(bowlers)))]

        bat_skill = batsman.effective_skill * batsman.attributes.accuracy
        bowl_skill = bowler.effective_skill * bowler.attributes.accuracy

        roll = rng.random()

        # Wide/No-ball
        if roll < 0.03:
            evt = EventType.WIDE if rng.random() < 0.6 else EventType.NO_BALL
            batting_team.score += 1
            events.append(GameEvent(
                type=evt, time=state.clock, period=state.period,
                team_id=bowling_team.id, player_id=bowler.id,
                description=f"{'Wide' if evt == EventType.WIDE else 'No ball'} by {bowler.name}",
            ))
            return state, events  # free delivery, doesn't count

        self._balls_in_over += 1

        # Wicket
        if roll < 0.03 + (bowl_skill * 0.08):
            self._wickets += 1
            self._batting_order_idx += 1

            wicket_type = rng.choice(["bowled", "caught", "lbw", "run_out"])
            evt_map = {
                "bowled": EventType.BOWLED, "caught": EventType.CAUGHT,
                "lbw": EventType.LBW, "run_out": EventType.RUN_OUT,
            }
            events.append(GameEvent(
                type=EventType.WICKET, time=state.clock, period=state.period,
                team_id=bowling_team.id, player_id=bowler.id,
                secondary_player_id=batsman.id,
                description=f"WICKET! {batsman.name} is {wicket_type}! ({self._wickets}/10)",
                metadata={"wicket_type": wicket_type, "wickets": self._wickets},
            ))
            events.append(GameEvent(
                type=evt_map.get(wicket_type, EventType.WICKET), time=state.clock, period=state.period,
                team_id=bowling_team.id, player_id=bowler.id,
                description=f"{batsman.name} {wicket_type}",
            ))
        # Boundary 4
        elif roll < 0.25 and bat_skill > 0.5:
            batting_team.score += 4
            events.append(GameEvent(
                type=EventType.BOUNDARY_FOUR, time=state.clock, period=state.period,
                team_id=batting_team.id, player_id=batsman.id,
                description=f"FOUR! {batsman.name} drives to the boundary!",
                metadata={"runs": 4},
            ))
        # Six
        elif roll < 0.32 and bat_skill > 0.6:
            batting_team.score += 6
            events.append(GameEvent(
                type=EventType.SIX, time=state.clock, period=state.period,
                team_id=batting_team.id, player_id=batsman.id,
                description=f"SIX! {batsman.name} clears the rope!",
                metadata={"runs": 6},
            ))
        # Running (1-3 runs)
        elif roll < 0.65:
            runs = int(rng.choice([1, 1, 1, 2, 2, 3]))
            batting_team.score += runs
            events.append(GameEvent(
                type=EventType.RUN, time=state.clock, period=state.period,
                team_id=batting_team.id, player_id=batsman.id,
                description=f"{batsman.name} takes {runs} run(s)",
                metadata={"runs": runs},
            ))
        # Dot ball
        else:
            pass  # no runs scored

        # Check over complete
        if self._balls_in_over >= 6:
            self._balls_in_over = 0
            self._overs += 1
            events.append(GameEvent(
                type=EventType.OVER_COMPLETE, time=state.clock, period=state.period,
                description=f"Over {self._overs} complete",
            ))

        # Check innings over (20 overs T20 or all out)
        if self._overs >= 20 or self._wickets >= 10:
            if self._batting_first:
                self._batting_first = False
                self._wickets = 0
                self._overs = 0
                self._balls_in_over = 0
                self._batting_order_idx = 0
                events.append(GameEvent(
                    type=EventType.PERIOD_END, time=state.clock, period=state.period,
                    description=f"First innings over. {batting_team.name}: {batting_team.score}",
                ))
            else:
                state.is_finished = True

        return state, events

    def is_valid_state(self, state: GameState) -> bool:
        return len(state.home_team.active_players) >= 2 and len(state.away_team.active_players) >= 2

    def post_event(self, state: GameState, event: GameEvent, config: SimulationConfig) -> GameState:
        if event.type == EventType.SIX:
            team = state.home_team if event.team_id == state.home_team.id else state.away_team
            team.momentum = min(1.0, team.momentum + 0.1)
        elif event.type == EventType.WICKET:
            team = state.home_team if event.team_id == state.home_team.id else state.away_team
            team.momentum = min(1.0, team.momentum + 0.12)
        return state

    def get_sport_state(self, state: GameState) -> dict:
        return {
            "wickets": self._wickets,
            "overs": self._overs,
            "balls_in_over": self._balls_in_over,
            "over_display": f"{self._overs}.{self._balls_in_over}",
            "batting_first": self._batting_first,
            "batting_order_index": self._batting_order_idx,
            "boundaries_four": sum(1 for e in state.events if e.type == EventType.BOUNDARY_FOUR),
            "sixes": sum(1 for e in state.events if e.type == EventType.SIX),
            "extras": sum(1 for e in state.events if e.type in (EventType.WIDE, EventType.NO_BALL)),
            "maiden_overs": sum(1 for e in state.events if e.type == EventType.MAIDEN_OVER),
        }
