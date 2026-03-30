"""NBA team rosters — representative starter lineups with coaches."""

from __future__ import annotations

from sports_sim.core.models import (
    Coach,
    CoachStyle,
    Player,
    PlayerAttributes,
    Team,
    TeamSliders,
)
from sports_sim.data.venues import NBA_VENUES


def _p(name: str, num: int, pos: str, spd: float, stren: float, acc: float,
       end: float, skl: float, dec: float, agg: float, comp: float,
       aware: float = 0.6, lead: float = 0.5, clutch: float = 0.5,
       dur: float = 0.7, age: int = 26, ht: int = 198, wt: int = 100) -> Player:
    return Player(
        name=name, number=num, position=pos, age=age, height_cm=ht, weight_kg=wt,
        attributes=PlayerAttributes(
            speed=spd, strength=stren, accuracy=acc, endurance=end,
            skill=skl, decision_making=dec, aggression=agg, composure=comp,
            awareness=aware, leadership=lead, clutch=clutch, durability=dur,
        ),
    )


def _nba_team(name: str, city: str, abbr: str, coach_name: str,
              coach_style: CoachStyle, players: list[Player],
              bench: list[Player] | None = None) -> Team:
    venue = NBA_VENUES.get(abbr)
    return Team(
        name=name, city=city, abbreviation=abbr,
        players=players, bench=bench or [],
        formation="standard",
        coach=Coach(name=coach_name, style=coach_style, play_calling=0.7,
                    motivation=0.7, adaptability=0.65, clock_management=0.65),
        venue=venue or NBA_VENUES["LAL"],
        timeouts_remaining=7,
    )


# ── BOS Celtics ──
BOS = _nba_team("Celtics", "Boston", "BOS", "Joe Mazzulla", CoachStyle.BALANCED, [
    _p("Jrue Holiday", 4, "PG", 0.78, 0.68, 0.78, 0.75, 0.85, 0.85, 0.45, 0.82, 0.82, 0.8, 0.78, 0.78, 34, 191, 93),
    _p("Derrick White", 9, "SG", 0.80, 0.65, 0.78, 0.78, 0.82, 0.80, 0.42, 0.80, 0.80, 0.72, 0.72, 0.78, 30, 193, 86),
    _p("Jayson Tatum", 0, "SF", 0.82, 0.75, 0.85, 0.78, 0.92, 0.82, 0.42, 0.82, 0.82, 0.82, 0.85, 0.78, 26, 203, 95),
    _p("Jaylen Brown", 7, "PF", 0.85, 0.78, 0.78, 0.80, 0.88, 0.78, 0.48, 0.78, 0.78, 0.72, 0.75, 0.78, 28, 198, 100),
    _p("Kristaps Porzingis", 8, "C", 0.68, 0.75, 0.82, 0.65, 0.85, 0.72, 0.38, 0.75, 0.72, 0.65, 0.68, 0.55, 28, 221, 109),
], bench=[
    _p("Al Horford", 42, "C", 0.60, 0.72, 0.72, 0.68, 0.78, 0.80, 0.35, 0.82, 0.82, 0.82, 0.78, 0.72, 38, 206, 109),
    _p("Payton Pritchard", 11, "PG", 0.78, 0.55, 0.80, 0.72, 0.75, 0.72, 0.42, 0.75, 0.72, 0.6, 0.65, 0.75, 26, 185, 86),
])

# ── DEN Nuggets ──
DEN = _nba_team("Nuggets", "Denver", "DEN", "Michael Malone", CoachStyle.BALANCED, [
    _p("Jamal Murray", 27, "PG", 0.80, 0.62, 0.82, 0.72, 0.85, 0.80, 0.40, 0.80, 0.78, 0.72, 0.88, 0.68, 27, 193, 97),
    _p("Kentavious Caldwell-Pope", 5, "SG", 0.78, 0.62, 0.78, 0.75, 0.78, 0.75, 0.42, 0.78, 0.78, 0.68, 0.65, 0.78, 31, 196, 93),
    _p("Michael Porter Jr.", 1, "SF", 0.75, 0.68, 0.85, 0.70, 0.82, 0.68, 0.35, 0.72, 0.68, 0.58, 0.62, 0.62, 26, 208, 97),
    _p("Aaron Gordon", 50, "PF", 0.82, 0.82, 0.68, 0.78, 0.78, 0.72, 0.50, 0.75, 0.72, 0.62, 0.58, 0.78, 28, 203, 100),
    _p("Nikola Jokic", 15, "C", 0.55, 0.80, 0.88, 0.72, 0.95, 0.95, 0.35, 0.92, 0.92, 0.92, 0.88, 0.78, 29, 211, 129),
])

# ── MIL Bucks ──
MIL = _nba_team("Bucks", "Milwaukee", "MIL", "Doc Rivers", CoachStyle.AGGRESSIVE, [
    _p("Damian Lillard", 0, "PG", 0.82, 0.60, 0.88, 0.75, 0.90, 0.85, 0.42, 0.85, 0.82, 0.82, 0.92, 0.72, 34, 188, 88),
    _p("Khris Middleton", 22, "SG", 0.72, 0.65, 0.85, 0.68, 0.85, 0.78, 0.38, 0.82, 0.80, 0.72, 0.78, 0.62, 33, 201, 100),
    _p("Bobby Portis", 9, "SF", 0.72, 0.78, 0.72, 0.72, 0.75, 0.68, 0.62, 0.68, 0.68, 0.58, 0.62, 0.72, 29, 208, 113),
    _p("Giannis Antetokounmpo", 34, "PF", 0.90, 0.92, 0.68, 0.85, 0.92, 0.78, 0.55, 0.78, 0.78, 0.78, 0.82, 0.75, 29, 211, 110),
    _p("Brook Lopez", 11, "C", 0.55, 0.80, 0.78, 0.68, 0.82, 0.72, 0.42, 0.78, 0.75, 0.72, 0.65, 0.72, 36, 213, 127),
])

# ── GSW Warriors ──
GSW = _nba_team("Warriors", "Golden State", "GSW", "Steve Kerr", CoachStyle.UP_TEMPO, [
    _p("Stephen Curry", 30, "PG", 0.80, 0.55, 0.95, 0.75, 0.95, 0.90, 0.35, 0.88, 0.88, 0.88, 0.95, 0.72, 36, 188, 84),
    _p("Klay Thompson", 11, "SG", 0.72, 0.62, 0.90, 0.68, 0.85, 0.75, 0.38, 0.82, 0.80, 0.72, 0.82, 0.62, 34, 198, 97),
    _p("Andrew Wiggins", 22, "SF", 0.82, 0.72, 0.75, 0.72, 0.78, 0.68, 0.42, 0.72, 0.68, 0.58, 0.62, 0.72, 29, 201, 88),
    _p("Draymond Green", 23, "PF", 0.72, 0.78, 0.55, 0.72, 0.82, 0.88, 0.72, 0.68, 0.85, 0.88, 0.78, 0.72, 34, 198, 104),
    _p("Kevon Looney", 5, "C", 0.60, 0.75, 0.52, 0.72, 0.72, 0.72, 0.42, 0.75, 0.72, 0.65, 0.55, 0.78, 28, 206, 100),
])

# ── LAL Lakers ──
LAL = _nba_team("Lakers", "Los Angeles", "LAL", "JJ Redick", CoachStyle.BALANCED, [
    _p("D'Angelo Russell", 1, "PG", 0.75, 0.55, 0.80, 0.68, 0.80, 0.75, 0.38, 0.72, 0.72, 0.68, 0.68, 0.72, 28, 193, 88),
    _p("Austin Reaves", 15, "SG", 0.78, 0.62, 0.78, 0.75, 0.78, 0.75, 0.42, 0.78, 0.75, 0.65, 0.68, 0.75, 26, 196, 88),
    _p("LeBron James", 23, "SF", 0.80, 0.85, 0.82, 0.78, 0.92, 0.92, 0.48, 0.88, 0.90, 0.92, 0.90, 0.72, 39, 206, 113),
    _p("Rui Hachimura", 28, "PF", 0.75, 0.78, 0.72, 0.72, 0.75, 0.68, 0.42, 0.72, 0.68, 0.58, 0.55, 0.72, 26, 203, 104),
    _p("Anthony Davis", 3, "C", 0.78, 0.82, 0.78, 0.72, 0.90, 0.78, 0.45, 0.78, 0.78, 0.75, 0.78, 0.58, 31, 208, 116),
])


def get_all_nba_teams() -> dict[str, Team]:
    return {"BOS": BOS, "DEN": DEN, "MIL": MIL, "GSW": GSW, "LAL": LAL}


def get_nba_team(abbr: str) -> Team | None:
    return get_all_nba_teams().get(abbr)
