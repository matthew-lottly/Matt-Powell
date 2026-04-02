"""Ice Hockey sport module — 5v5 (+ goalie), three 20-minute periods."""

from __future__ import annotations

from typing import cast

import numpy as np

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
    ("G", 3, 13),
    ("LD", 12, 8),
    ("RD", 12, 18),
    ("LW", 25, 6),
    ("C", 25, 13),
    ("RW", 25, 20),
]


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _goalie_for(team: Team) -> Player:
    return next((player for player in team.active_players if player.position == "G"), team.active_players[0])


def _attack_profile(team: Team) -> float:
    return _clamp(
        team.overall_offense * 0.42
        + team.depth_rating * 0.15
        + team.overall_special_teams * 0.08
        + team.avg_stamina * 0.13
        + team.momentum * 0.08
        + team.sliders.offensive_aggression * 0.08
        + team.sliders.pace * 0.06,
        0.1,
        1.0,
    )


def _defense_profile(team: Team) -> float:
    goalie = _goalie_for(team)
    return _clamp(
        team.overall_defense * 0.4
        + team.depth_rating * 0.08
        + team.avg_stamina * 0.1
        + team.sliders.defensive_intensity * 0.12
        + goalie.attributes.awareness * 0.1
        + goalie.attributes.composure * 0.08
        + goalie.attributes.skill * 0.12,
        0.1,
        1.0,
    )


def _power_play_multiplier(team: Team) -> float:
    return 1.02 + team.overall_special_teams * 0.16 + team.sliders.power_play_aggression * 0.05


def _rand_attrs(rng: np.random.Generator, pos: str) -> PlayerAttributes:
    base = rng.uniform(0.5, 0.88, size=8)
    if pos == "G":
        base[4] = rng.uniform(0.75, 0.96)  # skill (reflexes)
        base[0] = rng.uniform(0.4, 0.6)  # speed (lower)
    elif pos == "C":
        base[5] = rng.uniform(0.65, 0.90)  # decision making
        base[0] = rng.uniform(0.7, 0.92)  # speed
    elif pos in ("LW", "RW"):
        base[2] = rng.uniform(0.6, 0.92)  # accuracy (shooting)
        base[0] = rng.uniform(0.7, 0.92)  # speed
    elif pos in ("LD", "RD"):
        base[1] = rng.uniform(0.6, 0.88)  # strength
    return PlayerAttributes(
        speed=float(base[0]),
        strength=float(base[1]),
        accuracy=float(base[2]),
        endurance=float(base[3]),
        skill=float(base[4]),
        decision_making=float(base[5]),
        aggression=float(base[6]),
        composure=float(base[7]),
    )


def _make_team(name: str, abbr: str, seed: int) -> Team:
    rng = np.random.default_rng(seed)
    first = ["Connor", "Auston", "Nathan", "Leon", "Cale", "Sidney", "Alex", "David", "Nikita", "Mika", "Jack"]
    last = [
        "McDavid",
        "Matthews",
        "MacKinnon",
        "Draisaitl",
        "Makar",
        "Crosby",
        "Ovechkin",
        "Pastrnak",
        "Kucherov",
        "Zibanejad",
        "Hughes",
    ]
    players = []
    for i, (pos, x, y) in enumerate(POSITIONS_6):
        players.append(
            Player(
                name=f"{rng.choice(first)} {rng.choice(last)}",
                number=i + 1,
                position=pos,
                attributes=_rand_attrs(rng, pos),
                x=x,
                y=y,
            )
        )
    bench = [
        Player(name=f"Bench {j}", number=7 + j, position="SUB", attributes=_rand_attrs(rng, "C")) for j in range(12)
    ]
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
        for i, (_pos, x, y) in enumerate(POSITIONS_6):
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
        att_profile = _attack_profile(att)
        dfn_profile = _defense_profile(dfn)

        goal_x = _RINK_W if att is state.home_team else 0.0
        puck_drive = 0.018 + att.sliders.pace * 0.006 + att.depth_rating * 0.004

        # Move puck toward goal
        state.ball.x += (goal_x - state.ball.x) * puck_drive
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
        shot_window = max(0.0, 1.0 - dist_to_goal / 13.5)
        shot_chance = (0.0014 + shot_window * 0.0026) * (0.8 + att_profile * 0.55) * (1.06 - dfn_profile * 0.18)
        if dist_to_goal < 13.0 and rng.random() < shot_chance:
            shooters = [p for p in att.active_players if p.position in ("LW", "RW", "C")] or att.active_players
            shooter = shooters[int(rng.integers(len(shooters)))]
            shot_quality = (
                shooter.effective_skill * 0.36
                + shooter.attributes.accuracy * 0.22
                + shooter.attributes.skill * 0.14
                + shooter.attributes.decision_making * 0.08
                + shooter.attributes.composure * 0.06
                + att.overall_offense * 0.1
                + att.depth_rating * 0.04
            )
            shot_quality *= 1.0 + max(0.0, att_profile - dfn_profile) * 0.18
            shot_quality *= 1.0 - config.noise_level * rng.random()

            # Power play bonus
            if att.id in self._power_play_ticks:
                shot_quality *= _power_play_multiplier(att)

            events.append(
                GameEvent(
                    type=EventType.SHOT,
                    time=state.clock,
                    period=state.period,
                    team_id=att.id,
                    player_id=shooter.id,
                    x=state.ball.x,
                    y=state.ball.y,
                    description=f"{shooter.name} shoots!",
                )
            )

            # Goalie save check
            goalie = _goalie_for(dfn)
            save_quality = (
                goalie.effective_skill * 0.34
                + goalie.attributes.skill * 0.22
                + goalie.attributes.awareness * 0.12
                + goalie.attributes.composure * 0.08
                + dfn.overall_defense * 0.16
                + dfn.depth_rating * 0.03
                + dfn.sliders.defensive_intensity * 0.05
            )

            if att.id in self._power_play_ticks:
                save_quality *= 1.0 - max(0.02, (att.overall_special_teams - dfn.overall_special_teams) * 0.08)

            if shot_quality > save_quality * rng.uniform(0.96, 1.08):
                att.score += 1
                events.append(
                    GameEvent(
                        type=EventType.GOAL,
                        time=state.clock,
                        period=state.period,
                        team_id=att.id,
                        player_id=shooter.id,
                        description=(
                            f"GOAL! {shooter.name} scores for {att.name}! "
                            f"({state.home_team.score}-{state.away_team.score})"
                        ),
                    )
                )
                state.ball = Ball(x=_RINK_W / 2, y=_RINK_H / 2)
                state.possession_team_id = dfn.id
            else:
                events.append(
                    GameEvent(
                        type=EventType.SAVE,
                        time=state.clock,
                        period=state.period,
                        team_id=dfn.id,
                        player_id=goalie.id,
                        description=f"Save by {goalie.name}!",
                    )
                )

        # Face-off
        if rng.random() < 0.0005:
            events.append(
                GameEvent(
                    type=EventType.FACE_OFF,
                    time=state.clock,
                    period=state.period,
                    description="Face-off",
                )
            )
            if rng.random() < 0.5:
                state.possession_team_id = dfn.id

        # Penalty
        if rng.random() < 0.0004:
            fouler_team = att if rng.random() < 0.5 else dfn
            other_team = dfn if fouler_team is att else att
            foulers = fouler_team.active_players
            fouler = foulers[int(rng.integers(len(foulers)))]
            minutes = int(rng.choice([2, 2, 2, 5]))
            events.append(
                GameEvent(
                    type=EventType.PENALTY_MINUTES,
                    time=state.clock,
                    period=state.period,
                    team_id=fouler_team.id,
                    player_id=fouler.id,
                    description=f"{minutes}-minute penalty on {fouler.name}",
                    metadata={"minutes": minutes},
                )
            )
            # Power play for other team
            pp_ticks = minutes * 60 * config.ticks_per_second
            self._power_play_ticks[other_team.id] = pp_ticks
            events.append(
                GameEvent(
                    type=EventType.POWER_PLAY,
                    time=state.clock,
                    period=state.period,
                    team_id=other_team.id,
                    description=f"Power play for {other_team.name}",
                )
            )

        # Icing
        if rng.random() < 0.0003:
            events.append(
                GameEvent(
                    type=EventType.ICING,
                    time=state.clock,
                    period=state.period,
                    team_id=att.id,
                    description=f"Icing called on {att.name}",
                )
            )
            state.possession_team_id = dfn.id

        # Possession change
        turnover_chance = 0.0012 + dfn_profile * 0.0014 - att_profile * 0.0008
        if rng.random() < max(0.0005, turnover_chance):
            state.possession_team_id = dfn.id
            events.append(
                GameEvent(
                    type=EventType.POSSESSION_CHANGE,
                    time=state.clock,
                    period=state.period,
                    team_id=dfn.id,
                    description="Possession change",
                )
            )

        return state, events

    def is_valid_state(self, state: GameState) -> bool:
        return len(state.home_team.active_players) >= 4 and len(state.away_team.active_players) >= 4

    def post_event(self, state: GameState, event: GameEvent, config: SimulationConfig) -> GameState:
        if event.type == EventType.GOAL:
            team = state.home_team if event.team_id == state.home_team.id else state.away_team
            team.momentum = min(1.0, team.momentum + 0.12)
            other = state.away_team if team is state.home_team else state.home_team
            other.momentum = max(0.0, other.momentum - 0.08)
        return state

    def get_sport_state(self, state: GameState) -> dict:
        home_pp = self._power_play_ticks.get(state.home_team.id, 0)
        away_pp = self._power_play_ticks.get(state.away_team.id, 0)
        return {
            "home_power_play": home_pp > 0,
            "away_power_play": away_pp > 0,
            "home_pp_ticks_remaining": home_pp,
            "away_pp_ticks_remaining": away_pp,
            "home_shots": sum(1 for e in state.events if e.type == EventType.SHOT and e.team_id == state.home_team.id),
            "away_shots": sum(1 for e in state.events if e.type == EventType.SHOT and e.team_id == state.away_team.id),
            "home_saves": sum(1 for e in state.events if e.type == EventType.SAVE and e.team_id == state.home_team.id),
            "away_saves": sum(1 for e in state.events if e.type == EventType.SAVE and e.team_id == state.away_team.id),
            "home_penalties": sum(1 for e in state.events if e.type == EventType.PENALTY_MINUTES and e.team_id == state.home_team.id),
            "away_penalties": sum(1 for e in state.events if e.type == EventType.PENALTY_MINUTES and e.team_id == state.away_team.id),
            "home_faceoff_wins": sum(1 for e in state.events if e.type == EventType.FACE_OFF and e.team_id == state.home_team.id),
            "away_faceoff_wins": sum(1 for e in state.events if e.type == EventType.FACE_OFF and e.team_id == state.away_team.id),
        }
