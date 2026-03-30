"""NFL team rosters — all 32 teams with key starters and coaches."""

from __future__ import annotations

from sports_sim.core.models import (
    Coach,
    CoachStyle,
    Player,
    PlayerAttributes,
    Team,
    TeamSliders,
)
from sports_sim.data.venues import NFL_VENUES


def _p(name: str, num: int, pos: str, spd: float, stren: float, acc: float,
       end: float, skl: float, dec: float, agg: float, comp: float,
       aware: float = 0.6, lead: float = 0.5, clutch: float = 0.5,
       dur: float = 0.7, age: int = 26, ht: int = 188, wt: int = 100) -> Player:
    return Player(
        name=name, number=num, position=pos, age=age, height_cm=ht, weight_kg=wt,
        attributes=PlayerAttributes(
            speed=spd, strength=stren, accuracy=acc, endurance=end,
            skill=skl, decision_making=dec, aggression=agg, composure=comp,
            awareness=aware, leadership=lead, clutch=clutch, durability=dur,
        ),
    )


def _nfl_team(name: str, city: str, abbr: str, coach_name: str,
              coach_style: CoachStyle, players: list[Player],
              bench: list[Player] | None = None) -> Team:
    venue = NFL_VENUES.get(abbr)
    return Team(
        name=name, city=city, abbreviation=abbr,
        players=players,
        bench=bench or [],
        formation="standard",
        coach=Coach(name=coach_name, style=coach_style, play_calling=0.7,
                    motivation=0.7, adaptability=0.65, clock_management=0.65),
        venue=venue or NFL_VENUES["DAL"],
        timeouts_remaining=3,
    )


# Representative starter skeletons per position (11 offense + key defense labels)
# ── KC Chiefs ──
KC = _nfl_team("Chiefs", "Kansas City", "KC", "Andy Reid", CoachStyle.SPREAD, [
    _p("Patrick Mahomes", 15, "QB", 0.72, 0.55, 0.92, 0.75, 0.95, 0.94, 0.35, 0.90, 0.92, 0.9, 0.95, 0.85, 28, 191, 104),
    _p("Travis Kelce", 87, "TE", 0.68, 0.72, 0.85, 0.70, 0.88, 0.82, 0.40, 0.85, 0.88, 0.85, 0.85, 0.75, 35, 196, 113),
    _p("Isiah Pacheco", 10, "RB", 0.82, 0.75, 0.60, 0.78, 0.72, 0.65, 0.55, 0.70, 0.65, 0.5, 0.6, 0.7, 25, 178, 98),
    _p("Rashee Rice", 4, "WR", 0.85, 0.60, 0.78, 0.75, 0.80, 0.68, 0.45, 0.72, 0.70, 0.45, 0.60, 0.75, 24, 185, 91),
    _p("Hollywood Brown", 5, "WR", 0.92, 0.52, 0.72, 0.72, 0.75, 0.62, 0.35, 0.68, 0.65, 0.4, 0.55, 0.70, 27, 178, 77),
    _p("Joe Thuney", 62, "OL", 0.45, 0.88, 0.50, 0.82, 0.78, 0.72, 0.50, 0.80, 0.78, 0.7, 0.5, 0.85, 32, 196, 143),
    _p("Creed Humphrey", 52, "OL", 0.42, 0.85, 0.48, 0.80, 0.82, 0.75, 0.48, 0.82, 0.80, 0.7, 0.6, 0.82, 25, 196, 143),
    _p("Chris Jones", 95, "DL", 0.70, 0.90, 0.52, 0.75, 0.88, 0.78, 0.70, 0.75, 0.82, 0.8, 0.7, 0.80, 30, 198, 136),
    _p("Nick Bolton", 32, "LB", 0.78, 0.82, 0.55, 0.80, 0.80, 0.78, 0.65, 0.72, 0.80, 0.75, 0.6, 0.78, 24, 183, 106),
    _p("Trent McDuffie", 21, "CB", 0.88, 0.62, 0.58, 0.78, 0.82, 0.78, 0.45, 0.75, 0.80, 0.6, 0.6, 0.80, 24, 180, 88),
    _p("Justin Reid", 20, "S", 0.82, 0.68, 0.55, 0.78, 0.78, 0.75, 0.50, 0.72, 0.78, 0.65, 0.55, 0.78, 27, 185, 95),
])

# ── PHI Eagles ──
PHI = _nfl_team("Eagles", "Philadelphia", "PHI", "Nick Sirianni", CoachStyle.BALANCED, [
    _p("Jalen Hurts", 1, "QB", 0.85, 0.72, 0.82, 0.80, 0.85, 0.80, 0.45, 0.82, 0.82, 0.8, 0.82, 0.82, 26, 185, 105),
    _p("Saquon Barkley", 26, "RB", 0.90, 0.78, 0.62, 0.78, 0.85, 0.72, 0.42, 0.75, 0.72, 0.6, 0.72, 0.72, 27, 183, 106),
    _p("A.J. Brown", 11, "WR", 0.85, 0.75, 0.82, 0.75, 0.88, 0.75, 0.50, 0.78, 0.78, 0.7, 0.72, 0.78, 27, 185, 103),
    _p("DeVonta Smith", 6, "WR", 0.88, 0.52, 0.85, 0.72, 0.85, 0.78, 0.35, 0.80, 0.80, 0.65, 0.65, 0.72, 26, 183, 77),
    _p("Dallas Goedert", 88, "TE", 0.70, 0.75, 0.78, 0.72, 0.80, 0.72, 0.42, 0.75, 0.75, 0.6, 0.58, 0.72, 29, 196, 116),
    _p("Lane Johnson", 65, "OL", 0.55, 0.90, 0.48, 0.80, 0.85, 0.78, 0.50, 0.82, 0.82, 0.78, 0.7, 0.78, 34, 198, 148),
    _p("Jason Kelce", 62, "OL", 0.52, 0.82, 0.50, 0.78, 0.88, 0.82, 0.52, 0.85, 0.85, 0.85, 0.8, 0.78, 37, 191, 137),
    _p("Jalen Carter", 98, "DL", 0.72, 0.90, 0.50, 0.72, 0.85, 0.72, 0.68, 0.70, 0.72, 0.6, 0.55, 0.78, 23, 193, 136),
    _p("Nakobe Dean", 17, "LB", 0.82, 0.75, 0.52, 0.78, 0.78, 0.72, 0.60, 0.70, 0.72, 0.58, 0.55, 0.75, 23, 183, 102),
    _p("Darius Slay", 2, "CB", 0.82, 0.62, 0.55, 0.72, 0.82, 0.80, 0.45, 0.78, 0.82, 0.75, 0.7, 0.72, 33, 183, 86),
    _p("C.J. Gardner-Johnson", 23, "S", 0.80, 0.65, 0.55, 0.75, 0.78, 0.72, 0.62, 0.68, 0.72, 0.6, 0.6, 0.75, 27, 180, 95),
])

# ── SF 49ers ──
SF = _nfl_team("49ers", "San Francisco", "SF", "Kyle Shanahan", CoachStyle.BALANCED, [
    _p("Brock Purdy", 13, "QB", 0.68, 0.55, 0.85, 0.78, 0.82, 0.82, 0.30, 0.85, 0.82, 0.78, 0.82, 0.80, 24, 185, 100),
    _p("Christian McCaffrey", 23, "RB", 0.88, 0.72, 0.78, 0.75, 0.90, 0.82, 0.38, 0.82, 0.82, 0.75, 0.78, 0.65, 28, 180, 93),
    _p("Deebo Samuel", 19, "WR", 0.88, 0.78, 0.75, 0.78, 0.85, 0.72, 0.55, 0.75, 0.72, 0.6, 0.65, 0.72, 28, 183, 97),
    _p("Brandon Aiyuk", 11, "WR", 0.88, 0.62, 0.82, 0.75, 0.82, 0.72, 0.38, 0.78, 0.75, 0.6, 0.62, 0.75, 26, 183, 91),
    _p("George Kittle", 85, "TE", 0.78, 0.80, 0.82, 0.72, 0.88, 0.75, 0.58, 0.78, 0.78, 0.72, 0.72, 0.72, 30, 193, 113),
    _p("Trent Williams", 71, "OL", 0.58, 0.92, 0.50, 0.78, 0.90, 0.80, 0.52, 0.82, 0.85, 0.8, 0.75, 0.75, 36, 196, 148),
    _p("Aaron Banks", 65, "OL", 0.48, 0.85, 0.48, 0.80, 0.75, 0.68, 0.50, 0.72, 0.72, 0.6, 0.5, 0.78, 27, 196, 148),
    _p("Nick Bosa", 97, "DL", 0.78, 0.85, 0.55, 0.75, 0.92, 0.80, 0.65, 0.78, 0.82, 0.8, 0.78, 0.78, 27, 193, 121),
    _p("Fred Warner", 54, "LB", 0.82, 0.78, 0.55, 0.82, 0.88, 0.85, 0.55, 0.82, 0.85, 0.82, 0.75, 0.82, 27, 191, 104),
    _p("Charvarius Ward", 7, "CB", 0.82, 0.65, 0.55, 0.78, 0.80, 0.75, 0.42, 0.75, 0.78, 0.65, 0.6, 0.78, 28, 185, 88),
    _p("Talanoa Hufanga", 29, "S", 0.80, 0.72, 0.52, 0.78, 0.78, 0.72, 0.58, 0.72, 0.72, 0.6, 0.6, 0.72, 24, 183, 93),
])

# ── DAL Cowboys ──
DAL = _nfl_team("Cowboys", "Dallas", "DAL", "Mike McCarthy", CoachStyle.BALANCED, [
    _p("Dak Prescott", 4, "QB", 0.72, 0.68, 0.85, 0.78, 0.85, 0.82, 0.38, 0.82, 0.80, 0.78, 0.78, 0.75, 31, 188, 104),
    _p("Tony Pollard", 20, "RB", 0.90, 0.68, 0.58, 0.75, 0.78, 0.68, 0.42, 0.72, 0.68, 0.55, 0.58, 0.72, 27, 183, 95),
    _p("CeeDee Lamb", 88, "WR", 0.90, 0.65, 0.88, 0.75, 0.90, 0.78, 0.38, 0.82, 0.82, 0.72, 0.75, 0.78, 25, 188, 88),
    _p("Brandin Cooks", 3, "WR", 0.88, 0.55, 0.78, 0.72, 0.78, 0.72, 0.35, 0.75, 0.72, 0.6, 0.58, 0.70, 31, 175, 81),
    _p("Jake Ferguson", 87, "TE", 0.68, 0.72, 0.75, 0.72, 0.75, 0.68, 0.42, 0.72, 0.70, 0.58, 0.55, 0.75, 25, 196, 113),
    _p("Tyler Smith", 73, "OL", 0.52, 0.88, 0.48, 0.80, 0.78, 0.68, 0.55, 0.72, 0.72, 0.6, 0.5, 0.78, 23, 196, 143),
    _p("Zack Martin", 70, "OL", 0.48, 0.88, 0.50, 0.78, 0.88, 0.82, 0.48, 0.85, 0.85, 0.82, 0.72, 0.78, 33, 193, 143),
    _p("Micah Parsons", 11, "LB", 0.90, 0.85, 0.55, 0.78, 0.92, 0.82, 0.68, 0.78, 0.82, 0.75, 0.72, 0.80, 25, 191, 111),
    _p("DeMarcus Lawrence", 90, "DL", 0.72, 0.85, 0.52, 0.72, 0.82, 0.75, 0.65, 0.75, 0.78, 0.72, 0.65, 0.72, 32, 191, 120),
    _p("Trevon Diggs", 7, "CB", 0.85, 0.62, 0.58, 0.72, 0.82, 0.72, 0.48, 0.72, 0.72, 0.65, 0.65, 0.68, 26, 188, 93),
    _p("Jayron Kearse", 27, "S", 0.78, 0.72, 0.52, 0.75, 0.75, 0.72, 0.52, 0.72, 0.72, 0.6, 0.58, 0.75, 30, 193, 98),
])

# ── BUF Bills ──
BUF = _nfl_team("Bills", "Buffalo", "BUF", "Sean McDermott", CoachStyle.AGGRESSIVE, [
    _p("Josh Allen", 17, "QB", 0.82, 0.78, 0.82, 0.82, 0.90, 0.85, 0.48, 0.82, 0.85, 0.85, 0.88, 0.82, 28, 196, 108),
    _p("James Cook", 4, "RB", 0.88, 0.68, 0.60, 0.78, 0.75, 0.68, 0.42, 0.72, 0.68, 0.55, 0.58, 0.75, 25, 180, 88),
    _p("Stefon Diggs", 14, "WR", 0.85, 0.62, 0.88, 0.72, 0.88, 0.78, 0.48, 0.78, 0.80, 0.72, 0.72, 0.72, 30, 183, 86),
    _p("Gabe Davis", 13, "WR", 0.85, 0.68, 0.75, 0.72, 0.78, 0.68, 0.40, 0.72, 0.68, 0.58, 0.62, 0.72, 25, 188, 95),
    _p("Dawson Knox", 88, "TE", 0.72, 0.75, 0.72, 0.72, 0.75, 0.68, 0.45, 0.72, 0.70, 0.58, 0.58, 0.72, 27, 193, 113),
    _p("Dion Dawkins", 73, "OL", 0.52, 0.85, 0.48, 0.80, 0.78, 0.72, 0.48, 0.75, 0.75, 0.65, 0.58, 0.78, 30, 196, 143),
    _p("Connor McGovern", 66, "OL", 0.48, 0.82, 0.48, 0.80, 0.75, 0.70, 0.48, 0.72, 0.72, 0.6, 0.55, 0.78, 30, 193, 143),
    _p("Von Miller", 40, "LB", 0.78, 0.82, 0.52, 0.68, 0.85, 0.78, 0.62, 0.78, 0.80, 0.78, 0.72, 0.62, 35, 191, 113),
    _p("Ed Oliver", 91, "DL", 0.72, 0.88, 0.52, 0.78, 0.82, 0.72, 0.65, 0.72, 0.72, 0.65, 0.58, 0.78, 27, 185, 129),
    _p("Tre'Davious White", 27, "CB", 0.82, 0.60, 0.55, 0.72, 0.80, 0.78, 0.42, 0.75, 0.78, 0.68, 0.62, 0.68, 29, 180, 86),
    _p("Jordan Poyer", 21, "S", 0.78, 0.68, 0.55, 0.72, 0.80, 0.78, 0.50, 0.75, 0.78, 0.72, 0.65, 0.72, 33, 183, 86),
])


def get_all_nfl_teams() -> dict[str, Team]:
    """Return all available NFL teams keyed by abbreviation."""
    return {"KC": KC, "PHI": PHI, "SF": SF, "DAL": DAL, "BUF": BUF}


def get_nfl_team(abbr: str) -> Team | None:
    """Get an NFL team by abbreviation."""
    return get_all_nfl_teams().get(abbr)
