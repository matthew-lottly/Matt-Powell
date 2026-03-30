"""Minimal IPL roster samples (placeholder data)."""
from __future__ import annotations

from sports_sim.core.models import Coach, CoachStyle, Player, PlayerAttributes, Team


def _p(name: str, num: int, pos: str) -> Player:
    return Player(name=name, number=num, position=pos,
                  attributes=PlayerAttributes(speed=0.66, strength=0.6, accuracy=0.7,
                                               endurance=0.7, skill=0.74, decision_making=0.69,
                                               aggression=0.6, composure=0.67))


def _team(name: str, city: str, abbr: str, coach: str, players: list[Player]) -> Team:
    return Team(name=name, city=city, abbreviation=abbr,
                players=players, bench=[], formation="11",
                coach=Coach(name=coach, style=CoachStyle.AGGRESSIVE, play_calling=0.7, motivation=0.7))


MI = _team("Mumbai Indians", "Mumbai", "MI", "Coach M", [
    _p("P1", 1, "Batter"), _p("P2", 2, "Batter"), _p("P3", 3, "Bowler"), _p("P4", 4, "Allrounder"), _p("P5", 5, "WK"), _p("P6", 6, "Bowler"),
])

RCB = _team("Royal Challengers", "Bangalore", "RCB", "Coach R", [
    _p("R1", 7, "Batter"), _p("R2", 8, "Batter"), _p("R3", 9, "Bowler"), _p("R4", 10, "Allrounder"), _p("R5", 11, "WK"), _p("R6", 12, "Bowler"),
])


def get_all_ipl_teams() -> dict[str, Team]:
    return {"MI": MI, "RCB": RCB}


def get_ipl_team(abbr: str) -> Team | None:
    return get_all_ipl_teams().get(abbr)
