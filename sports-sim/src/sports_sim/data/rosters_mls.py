"""Minimal MLS roster samples (placeholder data)."""
from __future__ import annotations

from sports_sim.core.models import Coach, CoachStyle, Player, PlayerAttributes, Team


def _p(name: str, num: int, pos: str) -> Player:
    return Player(name=name, number=num, position=pos,
                  attributes=PlayerAttributes(speed=0.7, strength=0.6, accuracy=0.7,
                                               endurance=0.7, skill=0.7, decision_making=0.65,
                                               aggression=0.6, composure=0.65))


def _team(name: str, city: str, abbr: str, coach: str, players: list[Player]) -> Team:
    return Team(name=name, city=city, abbreviation=abbr,
                players=players, bench=[], formation="4-3-3",
                coach=Coach(name=coach, style=CoachStyle.BALANCED, play_calling=0.6, motivation=0.7))


ATL = _team("Atlanta United", "Atlanta", "ATL", "Gonzalo P.", [
    _p("Player 1", 10, "FW"), _p("Player 2", 7, "RW"), _p("Player 3", 4, "CB"),
    _p("Player 4", 1, "GK"), _p("Player 5", 11, "LW"), _p("Player 6", 8, "CM"),
])

NYC = _team("New York City FC", "New York", "NYC", "Nick C.", [
    _p("Player A", 9, "CF"), _p("Player B", 10, "AM"), _p("Player C", 3, "CB"),
    _p("Player D", 1, "GK"), _p("Player E", 14, "CM"), _p("Player F", 6, "DM"),
])

LAFC = _team("LAFC", "Los Angeles", "LAFC", "Bob B.", [
    _p("Player X", 7, "RW"), _p("Player Y", 9, "CF"), _p("Player Z", 4, "CB"),
    _p("Player W", 1, "GK"), _p("Player V", 11, "LW"), _p("Player U", 8, "CM"),
])


def get_all_mls_teams() -> dict[str, Team]:
    return {"ATL": ATL, "NYC": NYC, "LAFC": LAFC}


def get_mls_team(abbr: str) -> Team | None:
    return get_all_mls_teams().get(abbr)
"""Minimal MLS roster samples (placeholder data)."""
from __future__ import annotations

from sports_sim.core.models import Coach, CoachStyle, Player, PlayerAttributes, Team


def _p(name: str, num: int, pos: str) -> Player:
    return Player(name=name, number=num, position=pos,
                  attributes=PlayerAttributes(speed=0.65, strength=0.6, accuracy=0.7,
                                               endurance=0.7, skill=0.7, decision_making=0.65,
                                               aggression=0.6, composure=0.65))


def _team(name: str, city: str, abbr: str, coach: str, players: list[Player]) -> Team:
    return Team(name=name, city=city, abbreviation=abbr,
                players=players, bench=[], formation="4-4-2",
                coach=Coach(name=coach, style=CoachStyle.BALANCED, play_calling=0.55, motivation=0.6))


RSL = _team("Real Salt Lake", "Salt Lake City", "RSL", "Coach R", [
    _p("R1", 9, "CF"), _p("R2", 10, "AM"), _p("R3", 4, "CB"),
    _p("R4", 1, "GK"), _p("R5", 11, "LW"), _p("R6", 6, "CM"),
])

SEA = _team("Sounders", "Seattle", "SEA", "Coach S", [
    _p("S1", 7, "RW"), _p("S2", 8, "CM"), _p("S3", 5, "CB"),
    _p("S4", 1, "GK"), _p("S5", 11, "LW"), _p("S6", 2, "RB"),
])


def get_all_mls_teams() -> dict[str, Team]:
    return {"RSL": RSL, "SEA": SEA}


def get_mls_team(abbr: str) -> Team | None:
    return get_all_mls_teams().get(abbr)
