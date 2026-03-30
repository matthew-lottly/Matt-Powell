"""Minimal EuroLeague roster samples (placeholder data)."""
from __future__ import annotations

from sports_sim.core.models import Coach, CoachStyle, Player, PlayerAttributes, Team


def _p(name: str, num: int, pos: str) -> Player:
    return Player(name=name, number=num, position=pos,
                  attributes=PlayerAttributes(speed=0.7, strength=0.65, accuracy=0.75,
                                               endurance=0.72, skill=0.78, decision_making=0.74,
                                               aggression=0.6, composure=0.68))


def _team(name: str, city: str, abbr: str, coach: str, players: list[Player]) -> Team:
    return Team(name=name, city=city, abbreviation=abbr,
                players=players, bench=[], formation="5-man",
                coach=Coach(name=coach, style=CoachStyle.BALANCED, play_calling=0.6, motivation=0.65))


FCS = _team("FCS Club", "City A", "FCS", "Coach F", [
    _p("B1", 7, "G"), _p("B2", 11, "F"), _p("B3", 4, "C"), _p("B4", 1, "G"), _p("B5", 15, "F"), _p("B6", 6, "G"),
])

CSK = _team("CSK Club", "City B", "CSK", "Coach C", [
    _p("C1", 9, "F"), _p("C2", 10, "G"), _p("C3", 5, "C"), _p("C4", 1, "G"), _p("C5", 12, "F"), _p("C6", 8, "G"),
])


def get_all_euro_teams() -> dict[str, Team]:
    return {"FCS": FCS, "CSK": CSK}


def get_euro_team(abbr: str) -> Team | None:
    return get_all_euro_teams().get(abbr)
