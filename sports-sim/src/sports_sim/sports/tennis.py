"""Tennis sport module — singles match, best-of-3 or best-of-5 sets."""

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

_COURT_W, _COURT_H = 23.77, 10.97  # meters (singles court)


def _rand_attrs(rng: np.random.Generator) -> PlayerAttributes:
    return PlayerAttributes(
        speed=float(rng.uniform(0.6, 0.95)),
        strength=float(rng.uniform(0.5, 0.85)),
        accuracy=float(rng.uniform(0.6, 0.92)),
        endurance=float(rng.uniform(0.6, 0.90)),
        skill=float(rng.uniform(0.6, 0.95)),
        decision_making=float(rng.uniform(0.6, 0.90)),
        aggression=float(rng.uniform(0.3, 0.7)),
        composure=float(rng.uniform(0.6, 0.92)),
    )


def _make_player_team(name: str, abbr: str, seed: int) -> Team:
    rng = np.random.default_rng(seed)
    player = Player(
        name=name, number=1, position="SNG",
        attributes=_rand_attrs(rng), x=2.0, y=_COURT_H / 2,
    )
    return Team(name=name, abbreviation=abbr, players=[player], bench=[], formation="singles")


class TennisSport(Sport):
    @property
    def name(self) -> str:
        return "tennis"

    @property
    def default_periods(self) -> int:
        return 3  # best-of-3 sets

    @property
    def default_period_length(self) -> float:
        return 15.0  # approx minutes per set

    @property
    def field_width(self) -> float:
        return _COURT_W

    @property
    def field_height(self) -> float:
        return _COURT_H

    @property
    def players_per_side(self) -> int:
        return 1

    def __init__(self):
        self._rng = np.random.default_rng()
        # Score tracking: games in current set, points in current game
        self._p1_points = 0
        self._p2_points = 0
        self._p1_games = 0
        self._p2_games = 0
        self._p1_sets = 0
        self._p2_sets = 0
        self._serving_p1 = True
        self._tiebreak = False
        self._tiebreak_points_played = 0
        self._point_names = ["0", "15", "30", "40"]

    def create_default_teams(self) -> tuple[Team, Team]:
        return _make_player_team("Player One", "P1", 1100), _make_player_team("Player Two", "P2", 1200)

    def setup_positions(self, state: GameState) -> GameState:
        if state.home_team.players:
            state.home_team.players[0].x = 2.0
            state.home_team.players[0].y = _COURT_H / 2
        if state.away_team.players:
            state.away_team.players[0].x = _COURT_W - 2.0
            state.away_team.players[0].y = _COURT_H / 2
        state.ball = Ball(x=_COURT_W / 2, y=_COURT_H / 2)
        return state

    def tick(self, state: GameState, config: SimulationConfig) -> tuple[GameState, list[GameEvent]]:
        events: list[GameEvent] = []
        rng = self._rng or np.random.default_rng()
        rng = cast(np.random.Generator, rng)

        if state.is_finished:
            return state, events

        # Process points periodically
        if rng.random() > 0.008:
            return state, events

        p1 = state.home_team.players[0] if state.home_team.players else None
        p2 = state.away_team.players[0] if state.away_team.players else None
        if not p1 or not p2:
            return state, events

        server = p1 if self._serving_p1 else p2
        returner = p2 if self._serving_p1 else p1
        server_team = state.home_team if self._serving_p1 else state.away_team
        returner_team = state.away_team if self._serving_p1 else state.home_team

        serve_quality = server.effective_skill * server.attributes.accuracy
        return_quality = returner.effective_skill * returner.attributes.speed

        # Ace check
        if rng.random() < serve_quality * 0.08:
            events.append(GameEvent(
                type=EventType.ACE, time=state.clock, period=state.period,
                team_id=server_team.id, player_id=server.id,
                description=f"ACE by {server.name}!",
            ))
            self._award_point(state, events, True)
            return state, events

        # Double fault check
        if rng.random() < (1.0 - serve_quality) * 0.06:
            events.append(GameEvent(
                type=EventType.DOUBLE_FAULT, time=state.clock, period=state.period,
                team_id=server_team.id, player_id=server.id,
                description=f"Double fault by {server.name}",
            ))
            self._award_point(state, events, False)
            return state, events

        # Rally
        events.append(GameEvent(
            type=EventType.SERVE, time=state.clock, period=state.period,
            team_id=server_team.id, player_id=server.id,
            description=f"{server.name} serves",
        ))

        rally_length = int(rng.integers(2, 12))
        for _ in range(rally_length):
            # Each rally stroke
            if rng.random() < 0.12:
                # Winner
                winner_is_server = rng.random() < serve_quality / (serve_quality + return_quality)
                if winner_is_server:
                    events.append(GameEvent(
                        type=EventType.WINNER, time=state.clock, period=state.period,
                        team_id=server_team.id, player_id=server.id,
                        description=f"Winner by {server.name}!",
                    ))
                    self._award_point(state, events, True)
                else:
                    events.append(GameEvent(
                        type=EventType.WINNER, time=state.clock, period=state.period,
                        team_id=returner_team.id, player_id=returner.id,
                        description=f"Winner by {returner.name}!",
                    ))
                    self._award_point(state, events, False)
                return state, events

            if rng.random() < 0.08:
                # Unforced error
                error_by_server = rng.random() < 0.5
                if error_by_server:
                    events.append(GameEvent(
                        type=EventType.UNFORCED_ERROR, time=state.clock, period=state.period,
                        team_id=server_team.id, player_id=server.id,
                        description=f"Unforced error by {server.name}",
                    ))
                    self._award_point(state, events, False)
                else:
                    events.append(GameEvent(
                        type=EventType.UNFORCED_ERROR, time=state.clock, period=state.period,
                        team_id=returner_team.id, player_id=returner.id,
                        description=f"Unforced error by {returner.name}",
                    ))
                    self._award_point(state, events, True)
                return state, events

        # Rally ended — server wins more often on serve
        server_wins = rng.random() < serve_quality / (serve_quality + return_quality) * 1.1
        self._award_point(state, events, server_wins)
        return state, events

    def _award_point(self, state: GameState, events: list[GameEvent], server_wins: bool):
        if server_wins == self._serving_p1:
            self._p1_points += 1
        else:
            self._p2_points += 1

        if self._tiebreak:
            self._tiebreak_points_played += 1
            # Tiebreak: first to 7, win by 2
            if self._p1_points >= 7 and self._p1_points - self._p2_points >= 2:
                self._p1_games += 1
                self._finish_tiebreak_set(state, events, is_p1=True)
            elif self._p2_points >= 7 and self._p2_points - self._p1_points >= 2:
                self._p2_games += 1
                self._finish_tiebreak_set(state, events, is_p1=False)
            # Alternate serve every 2 points in tiebreak
            if self._tiebreak_points_played % 2 == 1:
                self._serving_p1 = not self._serving_p1
        else:
            # Standard game: deuce at 40-40, need advantage + win
            if self._p1_points >= 4 and self._p1_points - self._p2_points >= 2:
                self._p1_games += 1
                self._reset_points()
                self._serving_p1 = not self._serving_p1
                self._check_set(state, events)
            elif self._p2_points >= 4 and self._p2_points - self._p1_points >= 2:
                self._p2_games += 1
                self._reset_points()
                self._serving_p1 = not self._serving_p1
                self._check_set(state, events)

        # Update scores: encode as sets won
        state.home_team.score = self._p1_sets
        state.away_team.score = self._p2_sets

    def _finish_tiebreak_set(self, state: GameState, events: list[GameEvent], is_p1: bool):
        if is_p1:
            self._p1_sets += 1
            winner_team = state.home_team
        else:
            self._p2_sets += 1
            winner_team = state.away_team
        events.append(GameEvent(
            type=EventType.SET_WON, time=state.clock, period=state.period,
            team_id=winner_team.id,
            description=f"{winner_team.name} wins tiebreak set ({self._p1_games}-{self._p2_games})",
        ))
        self._p1_games = 0
        self._p2_games = 0
        self._reset_points()
        self._tiebreak = False
        self._tiebreak_points_played = 0
        self._check_match(state, events)

    def _reset_points(self):
        self._p1_points = 0
        self._p2_points = 0

    def _check_set(self, state: GameState, events: list[GameEvent]):
        # Tiebreak at 6-6
        if self._p1_games == 6 and self._p2_games == 6:
            self._tiebreak = True
            self._tiebreak_points_played = 0
            self._reset_points()
            events.append(GameEvent(
                type=EventType.PERIOD_START, time=state.clock, period=state.period,
                description="Tiebreak! First to 7 points, win by 2.",
            ))
            return

        if self._p1_games >= 6 and self._p1_games - self._p2_games >= 2:
            self._p1_sets += 1
            events.append(GameEvent(
                type=EventType.SET_WON, time=state.clock, period=state.period,
                team_id=state.home_team.id,
                description=f"{state.home_team.name} wins set {self._p1_sets + self._p2_sets} ({self._p1_games}-{self._p2_games})",
            ))
            self._p1_games = 0
            self._p2_games = 0
            state.home_team.score = self._p1_sets
            self._check_match(state, events)
        elif self._p2_games >= 6 and self._p2_games - self._p1_games >= 2:
            self._p2_sets += 1
            events.append(GameEvent(
                type=EventType.SET_WON, time=state.clock, period=state.period,
                team_id=state.away_team.id,
                description=f"{state.away_team.name} wins set {self._p1_sets + self._p2_sets} ({self._p2_games}-{self._p1_games})",
            ))
            self._p1_games = 0
            self._p2_games = 0
            state.away_team.score = self._p2_sets
            self._check_match(state, events)

    def _check_match(self, state: GameState, events: list[GameEvent]):
        sets_to_win = (state.total_periods + 1) // 2
        if self._p1_sets >= sets_to_win or self._p2_sets >= sets_to_win:
            state.is_finished = True

    def is_valid_state(self, state: GameState) -> bool:
        return len(state.home_team.players) >= 1 and len(state.away_team.players) >= 1

    def post_event(self, state: GameState, event: GameEvent, config: SimulationConfig) -> GameState:
        if event.type == EventType.SET_WON:
            team = state.home_team if event.team_id == state.home_team.id else state.away_team
            team.momentum = min(1.0, team.momentum + 0.15)
        return state

    def get_sport_state(self, state: GameState) -> dict:
        # Build point labels with deuce/advantage support
        if self._tiebreak:
            p1_label = str(self._p1_points)
            p2_label = str(self._p2_points)
        elif self._p1_points >= 3 and self._p2_points >= 3:
            if self._p1_points == self._p2_points:
                p1_label = p2_label = "Deuce"
            elif self._p1_points > self._p2_points:
                p1_label = "Ad"
                p2_label = "40"
            else:
                p1_label = "40"
                p2_label = "Ad"
        else:
            p1_label = self._point_names[min(self._p1_points, 3)]
            p2_label = self._point_names[min(self._p2_points, 3)]

        return {
            "p1_points": self._p1_points,
            "p2_points": self._p2_points,
            "p1_point_label": p1_label,
            "p2_point_label": p2_label,
            "p1_games": self._p1_games,
            "p2_games": self._p2_games,
            "p1_sets": self._p1_sets,
            "p2_sets": self._p2_sets,
            "serving_p1": self._serving_p1,
            "is_tiebreak": self._tiebreak,
            "p1_aces": sum(1 for e in state.events if e.type == EventType.ACE and e.team_id == state.home_team.id),
            "p2_aces": sum(1 for e in state.events if e.type == EventType.ACE and e.team_id == state.away_team.id),
            "p1_double_faults": sum(1 for e in state.events if e.type == EventType.DOUBLE_FAULT and e.team_id == state.home_team.id),
            "p2_double_faults": sum(1 for e in state.events if e.type == EventType.DOUBLE_FAULT and e.team_id == state.away_team.id),
            "p1_winners": sum(1 for e in state.events if e.type == EventType.WINNER and e.team_id == state.home_team.id),
            "p2_winners": sum(1 for e in state.events if e.type == EventType.WINNER and e.team_id == state.away_team.id),
            "p1_unforced_errors": sum(1 for e in state.events if e.type == EventType.UNFORCED_ERROR and e.team_id == state.home_team.id),
            "p2_unforced_errors": sum(1 for e in state.events if e.type == EventType.UNFORCED_ERROR and e.team_id == state.away_team.id),
        }
