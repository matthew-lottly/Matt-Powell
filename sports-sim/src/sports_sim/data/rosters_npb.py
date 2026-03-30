"""Minimal NPB (Japan) roster samples (placeholder data)."""
from __future__ import annotations

from sports_sim.core.models import Coach, CoachStyle, Player, PlayerAttributes, Team


def _p(name: str, num: int, pos: str) -> Player:
    return Player(name=name, number=num, position=pos,
                  attributes=PlayerAttributes(speed=0.68, strength=0.62, accuracy=0.72,
                                               endurance=0.7, skill=0.75, decision_making=0.7,
                                               aggression=0.55, composure=0.68))


def _team(name: str, city: str, abbr: str, coach: str, players: list[Player]) -> Team:
    return Team(name=name, city=city, abbreviation=abbr,
                players=players, bench=[], formation="standard",
                coach=Coach(name=coach, style=CoachStyle.BALANCED, play_calling=0.6, motivation=0.65))


TOK = _team("Tokyo Giants", "Tokyo", "TOK", "Coach T", [
    _p("T1", 3, "1B"), _p("T2", 4, "CF"), _p("T3", 5, "P"), _p("T4", 1, "C"), _p("T5", 11, "SS"), _p("T6", 2, "2B"),
])

OSK = _team("Osaka Tigers", "Osaka", "OSK", "Coach O", [
    _p("O1", 7, "RF"), _p("O2", 8, "3B"), _p("O3", 9, "P"), _p("O4", 1, "C"), _p("O5", 14, "LF"), _p("O6", 6, "2B"),
])


def get_all_npb_teams() -> dict[str, Team]:
    return {"TOK": TOK, "OSK": OSK}


def get_npb_team(abbr: str) -> Team | None:
    return get_all_npb_teams().get(abbr)
