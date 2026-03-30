"""MLB team rosters — representative starter lineups with coaches."""

from __future__ import annotations

from sports_sim.core.models import (
    Coach,
    CoachStyle,
    Player,
    PlayerAttributes,
    Team,
    TeamSliders,
)
from sports_sim.data.venues import MLB_VENUES


def _p(name: str, num: int, pos: str, spd: float, stren: float, acc: float,
       end: float, skl: float, dec: float, agg: float, comp: float,
       aware: float = 0.6, lead: float = 0.5, clutch: float = 0.5,
       dur: float = 0.7, age: int = 28, ht: int = 188, wt: int = 95) -> Player:
    return Player(
        name=name, number=num, position=pos, age=age, height_cm=ht, weight_kg=wt,
        attributes=PlayerAttributes(
            speed=spd, strength=stren, accuracy=acc, endurance=end,
            skill=skl, decision_making=dec, aggression=agg, composure=comp,
            awareness=aware, leadership=lead, clutch=clutch, durability=dur,
        ),
    )


def _mlb_team(name: str, city: str, abbr: str, coach_name: str,
              coach_style: CoachStyle, players: list[Player],
              bench: list[Player] | None = None) -> Team:
    venue = MLB_VENUES.get(abbr)
    return Team(
        name=name, city=city, abbreviation=abbr,
        players=players, bench=bench or [],
        formation="standard",
        coach=Coach(name=coach_name, style=coach_style, play_calling=0.7,
                    motivation=0.7, adaptability=0.65, clock_management=0.65),
        venue=venue or MLB_VENUES["NYY"],
    )


# ── LAD Dodgers ──
LAD = _mlb_team("Dodgers", "Los Angeles", "LAD", "Dave Roberts", CoachStyle.BALANCED, [
    _p("Clayton Kershaw", 22, "P", 0.50, 0.60, 0.90, 0.72, 0.88, 0.82, 0.38, 0.88, 0.85, 0.82, 0.82, 0.62, 36, 193, 102),
    _p("Will Smith", 16, "C", 0.62, 0.72, 0.82, 0.72, 0.82, 0.78, 0.38, 0.80, 0.78, 0.72, 0.72, 0.78, 29, 178, 88),
    _p("Freddie Freeman", 5, "1B", 0.65, 0.78, 0.88, 0.78, 0.90, 0.85, 0.35, 0.88, 0.85, 0.82, 0.85, 0.78, 35, 196, 100),
    _p("Gavin Lux", 9, "2B", 0.78, 0.60, 0.75, 0.72, 0.75, 0.72, 0.35, 0.72, 0.70, 0.62, 0.58, 0.72, 27, 188, 86),
    _p("Max Muncy", 13, "3B", 0.60, 0.78, 0.75, 0.72, 0.78, 0.75, 0.52, 0.72, 0.72, 0.65, 0.72, 0.72, 34, 183, 97),
    _p("Miguel Rojas", 11, "SS", 0.72, 0.60, 0.78, 0.72, 0.78, 0.72, 0.38, 0.78, 0.75, 0.65, 0.62, 0.78, 35, 183, 86),
    _p("Mookie Betts", 50, "LF", 0.85, 0.68, 0.88, 0.78, 0.92, 0.85, 0.42, 0.85, 0.85, 0.82, 0.82, 0.78, 31, 175, 81),
    _p("James Outman", 33, "CF", 0.85, 0.62, 0.72, 0.75, 0.72, 0.65, 0.40, 0.68, 0.65, 0.58, 0.55, 0.72, 27, 191, 95),
    _p("Shohei Ohtani", 17, "RF", 0.80, 0.82, 0.88, 0.82, 0.95, 0.82, 0.45, 0.85, 0.85, 0.78, 0.85, 0.78, 30, 193, 95),
], bench=[
    _p("Chris Taylor", 3, "PH", 0.72, 0.62, 0.72, 0.72, 0.72, 0.72, 0.42, 0.72, 0.70, 0.62, 0.62, 0.72, 33, 185, 86),
])

# ── NYY Yankees ──
NYY = _mlb_team("Yankees", "New York", "NYY", "Aaron Boone", CoachStyle.POWER_HITTING, [
    _p("Gerrit Cole", 45, "P", 0.52, 0.65, 0.90, 0.78, 0.92, 0.82, 0.42, 0.85, 0.82, 0.78, 0.78, 0.78, 34, 193, 100),
    _p("Jose Trevino", 39, "C", 0.60, 0.72, 0.75, 0.72, 0.78, 0.72, 0.38, 0.75, 0.72, 0.65, 0.58, 0.78, 31, 180, 88),
    _p("Anthony Rizzo", 48, "1B", 0.62, 0.78, 0.78, 0.72, 0.82, 0.78, 0.42, 0.82, 0.80, 0.75, 0.72, 0.68, 35, 191, 102),
    _p("Gleyber Torres", 25, "2B", 0.78, 0.65, 0.78, 0.72, 0.78, 0.72, 0.42, 0.72, 0.72, 0.62, 0.62, 0.72, 27, 185, 93),
    _p("DJ LeMahieu", 26, "3B", 0.68, 0.62, 0.82, 0.72, 0.82, 0.80, 0.35, 0.82, 0.80, 0.72, 0.68, 0.68, 36, 191, 93),
    _p("Anthony Volpe", 11, "SS", 0.82, 0.58, 0.72, 0.75, 0.75, 0.72, 0.38, 0.72, 0.72, 0.62, 0.58, 0.75, 23, 180, 81),
    _p("Juan Soto", 22, "LF", 0.72, 0.78, 0.90, 0.78, 0.92, 0.88, 0.42, 0.88, 0.88, 0.85, 0.85, 0.78, 26, 188, 100),
    _p("Aaron Judge", 99, "CF", 0.75, 0.90, 0.82, 0.75, 0.90, 0.78, 0.45, 0.82, 0.80, 0.72, 0.82, 0.72, 32, 201, 127),
    _p("Giancarlo Stanton", 27, "RF", 0.68, 0.92, 0.78, 0.65, 0.82, 0.72, 0.48, 0.72, 0.72, 0.62, 0.72, 0.55, 35, 198, 111),
])

# ── HOU Astros ──
HOU = _mlb_team("Astros", "Houston", "HOU", "Joe Espada", CoachStyle.BALANCED, [
    _p("Framber Valdez", 59, "P", 0.55, 0.68, 0.85, 0.80, 0.85, 0.75, 0.42, 0.78, 0.78, 0.68, 0.68, 0.78, 30, 180, 102),
    _p("Martin Maldonado", 15, "C", 0.55, 0.72, 0.68, 0.72, 0.75, 0.78, 0.38, 0.78, 0.78, 0.72, 0.58, 0.78, 37, 183, 104),
    _p("Jose Abreu", 79, "1B", 0.58, 0.82, 0.78, 0.72, 0.78, 0.75, 0.42, 0.78, 0.75, 0.68, 0.68, 0.72, 37, 191, 113),
    _p("Jose Altuve", 27, "2B", 0.82, 0.60, 0.88, 0.78, 0.90, 0.85, 0.42, 0.85, 0.85, 0.82, 0.85, 0.78, 34, 168, 74),
    _p("Alex Bregman", 2, "3B", 0.72, 0.72, 0.85, 0.78, 0.85, 0.82, 0.45, 0.82, 0.82, 0.78, 0.78, 0.78, 30, 183, 88),
    _p("Jeremy Pena", 3, "SS", 0.82, 0.62, 0.78, 0.78, 0.80, 0.75, 0.38, 0.78, 0.78, 0.68, 0.72, 0.78, 26, 183, 81),
    _p("Yordan Alvarez", 44, "LF", 0.62, 0.88, 0.85, 0.72, 0.88, 0.78, 0.42, 0.82, 0.80, 0.72, 0.82, 0.68, 27, 196, 100),
    _p("Chas McCormick", 20, "CF", 0.80, 0.65, 0.72, 0.75, 0.72, 0.68, 0.42, 0.72, 0.68, 0.58, 0.58, 0.75, 29, 183, 93),
    _p("Kyle Tucker", 30, "RF", 0.82, 0.72, 0.85, 0.78, 0.88, 0.78, 0.38, 0.82, 0.80, 0.72, 0.75, 0.78, 27, 193, 88),
])

# ── ATL Braves ──
ATL = _mlb_team("Braves", "Atlanta", "ATL", "Brian Snitker", CoachStyle.POWER_HITTING, [
    _p("Max Fried", 54, "P", 0.55, 0.62, 0.88, 0.78, 0.88, 0.78, 0.38, 0.82, 0.80, 0.72, 0.72, 0.78, 30, 193, 86),
    _p("Sean Murphy", 12, "C", 0.58, 0.75, 0.78, 0.72, 0.80, 0.75, 0.42, 0.78, 0.75, 0.68, 0.65, 0.72, 29, 191, 100),
    _p("Matt Olson", 28, "1B", 0.60, 0.82, 0.78, 0.72, 0.82, 0.75, 0.42, 0.78, 0.75, 0.68, 0.72, 0.78, 30, 196, 104),
    _p("Ozzie Albies", 1, "2B", 0.88, 0.65, 0.78, 0.78, 0.82, 0.75, 0.45, 0.75, 0.72, 0.65, 0.65, 0.72, 27, 173, 74),
    _p("Austin Riley", 27, "3B", 0.68, 0.82, 0.82, 0.75, 0.85, 0.75, 0.45, 0.78, 0.78, 0.68, 0.72, 0.78, 27, 191, 108),
    _p("Orlando Arcia", 11, "SS", 0.72, 0.60, 0.72, 0.72, 0.72, 0.68, 0.38, 0.72, 0.70, 0.62, 0.55, 0.72, 30, 183, 81),
    _p("Ronald Acuña Jr.", 13, "LF", 0.92, 0.78, 0.85, 0.82, 0.92, 0.78, 0.48, 0.82, 0.82, 0.72, 0.78, 0.72, 27, 183, 93),
    _p("Michael Harris II", 23, "CF", 0.90, 0.65, 0.78, 0.80, 0.82, 0.72, 0.38, 0.78, 0.75, 0.65, 0.62, 0.78, 23, 183, 88),
    _p("Marcell Ozuna", 20, "RF", 0.62, 0.82, 0.78, 0.68, 0.78, 0.68, 0.50, 0.68, 0.68, 0.58, 0.65, 0.68, 33, 185, 100),
])


def get_all_mlb_teams() -> dict[str, Team]:
    return {"LAD": LAD, "NYY": NYY, "HOU": HOU, "ATL": ATL}


def get_mlb_team(abbr: str) -> Team | None:
    return get_all_mlb_teams().get(abbr)
