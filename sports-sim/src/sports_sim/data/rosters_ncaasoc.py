"""Minimal NCAA soccer roster samples (placeholder data)."""
from __future__ import annotations

from sports_sim.core.models import Coach, CoachStyle, Player, PlayerAttributes, Team


def _p(name: str, num: int, pos: str) -> Player:
    return Player(name=name, number=num, position=pos,
                  attributes=PlayerAttributes(speed=0.6, strength=0.55, accuracy=0.65,
                                               endurance=0.7, skill=0.65, decision_making=0.6,
                                               aggression=0.55, composure=0.6))


def _team(name: str, city: str, abbr: str, coach: str, players: list[Player]) -> Team:
    return Team(name=name, city=city, abbreviation=abbr,
                players=players, bench=[], formation="4-4-2",
                coach=Coach(name=coach, style=CoachStyle.BALANCED, play_calling=0.5, motivation=0.6))


UCLA = _team("UCLA Bruins", "Los Angeles", "UCLA", "Coach U", [
    _p("U1", 9, "CF"), _p("U2", 10, "AM"), _p("U3", 4, "CB"),
    _p("U4", 1, "GK"), _p("U5", 11, "LW"), _p("U6", 6, "CM"),
])

UNC = _team("UNC Tar Heels", "Chapel Hill", "UNC", "Coach N", [
    _p("N1", 7, "RW"), _p("N2", 8, "CM"), _p("N3", 5, "CB"),
    _p("N4", 1, "GK"), _p("N5", 11, "LW"), _p("N6", 2, "RB"),
])


def get_all_ncaasoc_teams() -> dict[str, Team]:
    return {"UCLA": UCLA, "UNC": UNC}


def get_ncaasoc_team(abbr: str) -> Team | None:
    return get_all_ncaasoc_teams().get(abbr)
