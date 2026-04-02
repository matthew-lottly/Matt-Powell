"""American Football sport module — 11v11, four 15-minute quarters."""

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
from sports_sim.data.rosters_nfl import get_all_nfl_teams

_FIELD_W = 109.7   # meters (100 yards + 2 end zones)
_FIELD_H = 48.8    # meters (53⅓ yards)

# Probabilities per tick
_PLAY_FREQUENCY = 0.0033      # ~120 plays per game
_SACK_BASE_CHANCE = 0.08
_INTERCEPTION_BASE_CHANCE = 0.035
_FUMBLE_BASE_CHANCE = 0.015
_PENALTY_CHANCE = 0.04

# Scoring and completion
_COMPLETION_MAX = 0.65
_EXTRA_POINT_RATE = 0.94
_FG_DECAY_PER_YARD = 0.012
_FG_SNAP_DISTANCE = 17        # added to LOS for attempt distance

# Yardage parameters
_RUSH_MEAN_YARDS = 3.5
_RUSH_STD_YARDS = 2.5
_PUNT_MIN_YARDS = 30
_PUNT_MAX_YARDS = 55


class FootballSport(Sport):
    @property
    def name(self) -> str:
        return "football"

    @property
    def default_periods(self) -> int:
        return 4

    @property
    def default_period_length(self) -> float:
        return 15.0  # minutes per quarter

    @property
    def field_width(self) -> float:
        return _FIELD_W

    @property
    def field_height(self) -> float:
        return _FIELD_H

    @property
    def players_per_side(self) -> int:
        return 11

    def __init__(self) -> None:
        self._rng = np.random.default_rng()
        # Drive state
        self._ball_on: float = 25.0  # yards from own end zone (0-100)
        self._down: int = 1
        self._yards_to_go: float = 10.0
        self._possession_home: bool = True
        self._play_clock: float = 40.0

    def create_default_teams(self) -> tuple[Team, Team]:
        teams = get_all_nfl_teams()
        abbrs = list(teams.keys())
        if len(abbrs) >= 2:
            return teams[abbrs[0]].model_copy(deep=True), teams[abbrs[1]].model_copy(deep=True)
        # Fallback
        return self._generic_team("Home Hawks", "HHK", 700), self._generic_team("Away Lions", "ALN", 800)

    def _generic_team(self, name: str, abbr: str, seed: int) -> Team:
        rng = np.random.default_rng(seed)
        positions = ["QB", "RB", "WR", "WR", "TE", "OL", "OL", "DL", "LB", "CB", "S"]
        players = []
        for i, pos in enumerate(positions):
            attrs = PlayerAttributes(
                speed=float(rng.uniform(0.5, 0.9)),
                strength=float(rng.uniform(0.5, 0.9)),
                accuracy=float(rng.uniform(0.5, 0.9)),
                endurance=float(rng.uniform(0.5, 0.85)),
                skill=float(rng.uniform(0.5, 0.85)),
                decision_making=float(rng.uniform(0.5, 0.85)),
                aggression=float(rng.uniform(0.3, 0.7)),
                composure=float(rng.uniform(0.5, 0.85)),
            )
            players.append(Player(name=f"Player {i+1}", number=i+1, position=pos, attributes=attrs))
        return Team(name=name, abbreviation=abbr, players=players,
                    bench=[], formation="standard", timeouts_remaining=3)

    def setup_positions(self, state: GameState) -> GameState:
        # Reset field positions — offense on the left, defense right
        for i, p in enumerate(state.home_team.players):
            p.x = 25.0 + (i % 5) * 2
            p.y = 10.0 + (i % 3) * 10
        for i, p in enumerate(state.away_team.players):
            p.x = 75.0 - (i % 5) * 2
            p.y = 10.0 + (i % 3) * 10
        state.ball = Ball(x=25.0, y=_FIELD_H / 2)
        return state

    def tick(self, state: GameState, config: SimulationConfig) -> tuple[GameState, list[GameEvent]]:
        events: list[GameEvent] = []
        rng = self._rng or np.random.default_rng()
        rng = cast(np.random.Generator, rng)

        if state.is_finished:
            return state, events

        # Only run plays periodically — target ~120 plays per game
        # At 10 ticks/sec, 4 × 15 min = 36000 ticks → 120/36000 ≈ 0.0033
        if rng.random() > _PLAY_FREQUENCY:
            return state, events

        att = state.home_team if self._possession_home else state.away_team
        dfn = state.away_team if self._possession_home else state.home_team

        # Get key players
        qb = next((p for p in att.active_players if p.position == "QB"), att.active_players[0])
        rbs = [p for p in att.active_players if p.position == "RB"] or [att.active_players[0]]
        wrs = [p for p in att.active_players if p.position in ("WR", "TE")] or [att.active_players[0]]
        d_players = dfn.active_players

        # Team slider influence
        run_pass = att.sliders.run_pass_ratio  # 0 = all run, 1 = all pass
        blitz_freq = att.sliders.blitz_frequency if hasattr(att.sliders, 'blitz_frequency') else 0.3

        # Coach tactical bonus
        coach_bonus = att.coach.tactical_bonus

        # Decide play type
        play_roll = rng.random()
        is_pass_play = play_roll < (0.55 * run_pass + 0.25)

        if is_pass_play:
            # ── Passing play ──
            target = wrs[int(rng.integers(len(wrs)))]
            pass_skill = qb.effective_skill * qb.attributes.accuracy + coach_bonus
            pass_skill *= 1.0 - config.noise_level * rng.random()

            # Sack check (blitz factor)
            best_rusher = max(d_players, key=lambda p: p.attributes.speed * p.attributes.strength)
            ol_block = sum(p.attributes.strength for p in att.active_players if p.position == "OL") / max(1, sum(1 for p in att.active_players if p.position == "OL"))
            sack_chance = _SACK_BASE_CHANCE * best_rusher.effective_skill / max(0.3, ol_block) * (1 + blitz_freq * 0.3)

            if rng.random() < sack_chance:
                loss = float(rng.integers(3, 10))
                self._ball_on = max(0, self._ball_on - loss)
                self._down += 1
                self._yards_to_go = max(0.0, self._yards_to_go + loss)
                events.append(GameEvent(
                    type=EventType.SACK, time=state.clock, period=state.period,
                    team_id=dfn.id, player_id=best_rusher.id,
                    secondary_player_id=qb.id,
                    description=f"{best_rusher.name} sacks {qb.name} for a {loss:.0f}-yard loss!",
                    metadata={"yards": -loss},
                ))
            else:
                # Coverage check
                defender = d_players[int(rng.integers(len(d_players)))]
                coverage = defender.effective_skill * defender.attributes.speed

                # Interception
                int_chance = _INTERCEPTION_BASE_CHANCE * coverage / max(0.3, pass_skill)
                if rng.random() < int_chance:
                    self._turnover(state, events, dfn, defender, att, "interception")
                    return state, events

                # Completion check — NFL avg ~63%
                completion = pass_skill * 0.45 + target.attributes.speed * 0.10 - coverage * 0.25
                completion = min(_COMPLETION_MAX, completion)  # cap maximum
                if rng.random() < completion:
                    yards = float(rng.integers(1, 18)) * target.attributes.speed
                    yards = min(yards, 100 - self._ball_on)
                    self._ball_on += yards
                    self._yards_to_go -= yards

                    events.append(GameEvent(
                        type=EventType.RECEPTION, time=state.clock, period=state.period,
                        team_id=att.id, player_id=target.id,
                        secondary_player_id=qb.id,
                        description=f"{qb.name} completes to {target.name} for {yards:.0f} yards",
                        metadata={"yards": yards},
                    ))

                    # Touchdown check
                    if self._ball_on >= 100:
                        self._score_touchdown(state, events, att, target)
                        return state, events
                    self._down += 1
                else:
                    events.append(GameEvent(
                        type=EventType.INCOMPLETE_PASS, time=state.clock, period=state.period,
                        team_id=att.id, player_id=qb.id,
                        description=f"Incomplete pass from {qb.name} to {target.name}",
                    ))
                    self._down += 1
        else:
            # ── Rushing play ──
            runner = rbs[int(rng.integers(len(rbs)))]
            run_skill = runner.effective_skill * runner.attributes.speed + coach_bonus

            # Fumble check
            fumble_chance = _FUMBLE_BASE_CHANCE * (1.0 - runner.attributes.composure)
            if rng.random() < fumble_chance:
                recoverer = d_players[int(rng.integers(len(d_players)))]
                self._turnover(state, events, dfn, recoverer, att, "fumble")
                return state, events

            # Yardage — NFL avg ~4.3 ypc
            tackler = d_players[int(rng.integers(len(d_players)))]
            yards = float(rng.normal(_RUSH_MEAN_YARDS, _RUSH_STD_YARDS)) * run_skill / max(0.4, tackler.effective_skill)
            yards = max(-3, min(yards, 100 - self._ball_on))
            self._ball_on += yards
            self._yards_to_go -= yards

            events.append(GameEvent(
                type=EventType.RUSH, time=state.clock, period=state.period,
                team_id=att.id, player_id=runner.id,
                description=f"{runner.name} rushes for {yards:.0f} yards",
                metadata={"yards": yards},
            ))

            # Touchdown check
            if self._ball_on >= 100:
                self._score_touchdown(state, events, att, runner)
                return state, events
            self._down += 1

        # ── Down management ──
        if self._yards_to_go <= 0:
            # First down!
            self._down = 1
            self._yards_to_go = 10.0
        elif self._down > 4:
            # Turnover on downs or punt/FG attempt
            if self._ball_on > 60 and rng.random() < 0.6:
                # Field goal attempt
                fg_distance = 100 - self._ball_on + _FG_SNAP_DISTANCE  # add 17 yards for snap/hold
                fg_prob = max(0.1, 1.0 - fg_distance * _FG_DECAY_PER_YARD)
                kicker_skill = max(p.attributes.accuracy for p in att.active_players)
                fg_prob *= kicker_skill

                if rng.random() < fg_prob:
                    att.score += 3
                    events.append(GameEvent(
                        type=EventType.FIELD_GOAL, time=state.clock, period=state.period,
                        team_id=att.id,
                        description=f"{att.name} field goal is GOOD from {fg_distance:.0f} yards! ({state.home_team.score}-{state.away_team.score})",
                        metadata={"distance": fg_distance},
                    ))
                else:
                    events.append(GameEvent(
                        type=EventType.FIELD_GOAL, time=state.clock, period=state.period,
                        team_id=att.id,
                        description=f"{att.name} field goal MISSED from {fg_distance:.0f} yards",
                        metadata={"distance": fg_distance, "made": False},
                    ))
            else:
                # Punt
                punt_dist = float(rng.integers(_PUNT_MIN_YARDS, _PUNT_MAX_YARDS))
                events.append(GameEvent(
                    type=EventType.PUNT, time=state.clock, period=state.period,
                    team_id=att.id,
                    description=f"{att.name} punts {punt_dist:.0f} yards",
                    metadata={"distance": punt_dist},
                ))
                self._ball_on = max(1, 100 - (self._ball_on + punt_dist))

            self._change_possession()

        # Penalty check
        if rng.random() < _PENALTY_CHANCE:
            penalty_team = att if rng.random() < 0.5 else dfn
            yards_pen = float(rng.choice([5, 10, 15]))
            events.append(GameEvent(
                type=EventType.PENALTY_FLAG, time=state.clock, period=state.period,
                team_id=penalty_team.id,
                description=f"Penalty on {penalty_team.name}: {yards_pen:.0f} yards",
                metadata={"yards": yards_pen},
            ))
            if penalty_team is att:
                self._ball_on = max(0, self._ball_on - yards_pen)
                self._yards_to_go += yards_pen
            else:
                self._ball_on = min(100, self._ball_on + yards_pen)
                self._yards_to_go -= yards_pen
                if self._yards_to_go <= 0:
                    self._down = 1
                    self._yards_to_go = 10.0

        # Safety check
        if self._ball_on <= 0:
            dfn.score += 2
            events.append(GameEvent(
                type=EventType.SAFETY, time=state.clock, period=state.period,
                team_id=dfn.id,
                description=f"SAFETY! {dfn.name} scores 2 points! ({state.home_team.score}-{state.away_team.score})",
            ))
            self._ball_on = 20.0
            self._change_possession()

        return state, events

    def _score_touchdown(self, state: GameState, events: list[GameEvent],
                         team: Team, scorer: Player) -> None:
        team.score += 6
        events.append(GameEvent(
            type=EventType.TOUCHDOWN, time=state.clock, period=state.period,
            team_id=team.id, player_id=scorer.id,
            description=f"TOUCHDOWN! {scorer.name} scores for {team.name}! ({state.home_team.score}-{state.away_team.score})",
        ))
        # Extra point (automatic for now, 94% success rate)
        rng = cast(np.random.Generator, self._rng or np.random.default_rng())
        if rng.random() < _EXTRA_POINT_RATE:
            team.score += 1
            events.append(GameEvent(
                type=EventType.EXTRA_POINT, time=state.clock, period=state.period,
                team_id=team.id,
                description=f"Extra point GOOD ({state.home_team.score}-{state.away_team.score})",
            ))
        self._ball_on = 25.0
        self._down = 1
        self._yards_to_go = 10.0
        self._change_possession()

    def _turnover(self, state: GameState, events: list[GameEvent],
                  gaining_team: Team, player: Player,
                  losing_team: Team, turnover_type: str) -> None:
        if turnover_type == "interception":
            events.append(GameEvent(
                type=EventType.INTERCEPTION, time=state.clock, period=state.period,
                team_id=gaining_team.id, player_id=player.id,
                description=f"INTERCEPTION by {player.name}!",
            ))
        else:
            events.append(GameEvent(
                type=EventType.FUMBLE, time=state.clock, period=state.period,
                team_id=losing_team.id, player_id=player.id,
                description=f"FUMBLE! Recovered by {player.name} of {gaining_team.name}!",
            ))
        self._ball_on = max(1, 100 - self._ball_on)
        self._change_possession()

    def _change_possession(self) -> None:
        self._possession_home = not self._possession_home
        self._down = 1
        self._yards_to_go = 10.0
        self._ball_on = max(1, min(99, 100 - self._ball_on))

    def is_valid_state(self, state: GameState) -> bool:
        return (
            len(state.home_team.active_players) >= 11
            and len(state.away_team.active_players) >= 11
        )

    def post_event(self, state: GameState, event: GameEvent, config: SimulationConfig) -> GameState:
        if event.type == EventType.TOUCHDOWN:
            team = state.home_team if event.team_id == state.home_team.id else state.away_team
            team.momentum = min(1.0, team.momentum + 0.15)
            other = state.away_team if team is state.home_team else state.home_team
            other.momentum = max(0.0, other.momentum - 0.1)
        elif event.type == EventType.INTERCEPTION or event.type == EventType.FUMBLE:
            team = state.home_team if event.team_id == state.home_team.id else state.away_team
            team.momentum = min(1.0, team.momentum + 0.10)
        elif event.type == EventType.SACK:
            team = state.home_team if event.team_id == state.home_team.id else state.away_team
            team.momentum = min(1.0, team.momentum + 0.05)
        return state

    def get_sport_state(self, state: GameState) -> dict:
        return {
            "down": self._down,
            "yards_to_go": round(self._yards_to_go, 1),
            "ball_on": round(self._ball_on, 1),
            "possession_home": self._possession_home,
            "play_clock": round(self._play_clock, 1),
            "home_total_yards": sum(e.metadata.get("yards", 0) for e in state.events if e.team_id == state.home_team.id and e.type in (EventType.RUSH, EventType.RECEPTION)),
            "away_total_yards": sum(e.metadata.get("yards", 0) for e in state.events if e.team_id == state.away_team.id and e.type in (EventType.RUSH, EventType.RECEPTION)),
            "home_turnovers": sum(1 for e in state.events if e.type in (EventType.INTERCEPTION, EventType.FUMBLE) and e.team_id == state.away_team.id),
            "away_turnovers": sum(1 for e in state.events if e.type in (EventType.INTERCEPTION, EventType.FUMBLE) and e.team_id == state.home_team.id),
            "home_sacks": sum(1 for e in state.events if e.type == EventType.SACK and e.team_id == state.home_team.id),
            "away_sacks": sum(1 for e in state.events if e.type == EventType.SACK and e.team_id == state.away_team.id),
            "home_penalties": sum(1 for e in state.events if e.type == EventType.PENALTY_FLAG and e.team_id == state.home_team.id),
            "away_penalties": sum(1 for e in state.events if e.type == EventType.PENALTY_FLAG and e.team_id == state.away_team.id),
            "red_zone": self._ball_on >= 80,
        }
