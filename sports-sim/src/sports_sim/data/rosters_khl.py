"""Minimal KHL roster samples (placeholder data)."""
from __future__ import annotations

from sports_sim.core.models import Coach, CoachStyle, Player, PlayerAttributes, Team


def _p(name: str, num: int, pos: str) -> Player:
    return Player(name=name, number=num, position=pos,
                  attributes=PlayerAttributes(speed=0.72, strength=0.66, accuracy=0.7,
                                               endurance=0.74, skill=0.75, decision_making=0.7,
                                               aggression=0.6, composure=0.68))


def _team(name: str, city: str, abbr: str, coach: str, players: list[Player]) -> Team:
    return Team(name=name, city=city, abbreviation=abbr,
                players=players, bench=[], formation="standard",
                coach=Coach(name=coach, style=CoachStyle.BALANCED, play_calling=0.6, motivation=0.65))


MCK = _team("Moscow Club", "Moscow", "MCK", "Coach M", [
    _p("M1", 9, "RW"), _p("M2", 10, "C"), _p("M3", 3, "LD"), _p("M4", 1, "G"), _p("M5", 11, "LW"), _p("M6", 6, "RD"),
])

SPB = _team("St Petersburg", "St Petersburg", "SPB", "Coach S", [
    _p("S1", 7, "LW"), _p("S2", 8, "C"), _p("S3", 5, "RD"), _p("S4", 1, "G"), _p("S5", 12, "RW"), _p("S6", 2, "LD"),
])


def get_all_khl_teams() -> dict[str, Team]:
    return {"MCK": MCK, "SPB": SPB}


def get_khl_team(abbr: str) -> Team | None:
    return get_all_khl_teams().get(abbr)
