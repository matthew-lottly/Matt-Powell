"""NHL team rosters — all 32 teams with key starters."""

from __future__ import annotations

from sports_sim.core.models import (
    Coach,
    CoachStyle,
    Player,
    PlayerAttributes,
    Team,
    TeamSliders,
)
from sports_sim.data.venues import NHL_VENUES


def _p(name: str, num: int, pos: str, spd: float, stren: float, acc: float,
       end: float, skl: float, dec: float, agg: float, comp: float,
       age: int = 26, ht: int = 185, wt: int = 90) -> Player:
    return Player(
        name=name, number=num, position=pos, age=age, height_cm=ht, weight_kg=wt,
        attributes=PlayerAttributes(
            speed=spd, strength=stren, accuracy=acc, endurance=end,
            skill=skl, decision_making=dec, aggression=agg, composure=comp,
        ),
    )


def _nhl_team(name: str, city: str, abbr: str, coach_name: str,
              coach_style: CoachStyle, players: list[Player],
              bench: list[Player] | None = None) -> Team:
    venue = NHL_VENUES.get(abbr)
    return Team(
        name=name, city=city, abbreviation=abbr,
        players=players, bench=bench or [],
        formation="standard",
        coach=Coach(name=coach_name, style=coach_style, play_calling=0.65,
                    motivation=0.7, adaptability=0.65),
        venue=venue or next(iter(NHL_VENUES.values()), None),
    )


# ── All 32 NHL Teams ──

_TEAMS: dict[str, Team] = {}


def _register(abbr: str, name: str, city: str, coach: str, style: CoachStyle, roster: list[Player]):
    _TEAMS[abbr] = _nhl_team(name, city, abbr, coach, style, roster)


_register("ANA", "Ducks", "Anaheim", "Greg Cronin", CoachStyle.BALANCED, [
    _p("Troy Terry", 19, "RW", 0.78, 0.55, 0.80, 0.72, 0.78, 0.72, 0.40, 0.75, 26),
    _p("Trevor Zegras", 11, "C", 0.80, 0.55, 0.78, 0.70, 0.82, 0.75, 0.38, 0.72, 23),
    _p("Mason McTavish", 37, "C", 0.72, 0.68, 0.74, 0.72, 0.75, 0.70, 0.50, 0.72, 21),
    _p("Jamie Drysdale", 6, "RD", 0.82, 0.55, 0.72, 0.72, 0.75, 0.72, 0.35, 0.72, 22),
    _p("Cam Fowler", 4, "LD", 0.75, 0.62, 0.70, 0.68, 0.72, 0.72, 0.38, 0.78, 32),
    _p("John Gibson", 36, "G", 0.50, 0.55, 0.72, 0.72, 0.82, 0.75, 0.25, 0.82, 31),
])

_register("ARI", "Coyotes", "Arizona", "André Tourigny", CoachStyle.DEFENSIVE, [
    _p("Clayton Keller", 9, "LW", 0.82, 0.55, 0.80, 0.72, 0.82, 0.75, 0.35, 0.75, 25),
    _p("Nick Schmaltz", 8, "C", 0.78, 0.55, 0.78, 0.70, 0.78, 0.75, 0.35, 0.72, 28),
    _p("Lawson Crouse", 67, "LW", 0.72, 0.72, 0.68, 0.72, 0.68, 0.65, 0.62, 0.68, 27),
    _p("Jakob Chychrun", 6, "LD", 0.78, 0.65, 0.72, 0.72, 0.75, 0.70, 0.45, 0.72, 26),
    _p("Juuso Valimaki", 4, "LD", 0.72, 0.62, 0.65, 0.70, 0.68, 0.65, 0.45, 0.68, 25),
    _p("Karel Vejmelka", 70, "G", 0.48, 0.58, 0.70, 0.72, 0.75, 0.68, 0.25, 0.75, 28),
])

_register("BOS", "Bruins", "Boston", "Jim Montgomery", CoachStyle.BALANCED, [
    _p("David Pastrnak", 88, "RW", 0.82, 0.62, 0.90, 0.75, 0.92, 0.82, 0.42, 0.82, 28),
    _p("Brad Marchand", 63, "LW", 0.78, 0.62, 0.82, 0.72, 0.85, 0.82, 0.65, 0.78, 36),
    _p("Charlie McAvoy", 73, "RD", 0.80, 0.72, 0.72, 0.78, 0.82, 0.78, 0.52, 0.80, 26),
    _p("Hampus Lindholm", 27, "LD", 0.75, 0.72, 0.68, 0.75, 0.78, 0.75, 0.48, 0.78, 30),
    _p("Pavel Zacha", 18, "C", 0.78, 0.65, 0.72, 0.72, 0.75, 0.72, 0.42, 0.72, 27),
    _p("Linus Ullmark", 35, "G", 0.48, 0.60, 0.75, 0.75, 0.88, 0.78, 0.25, 0.85, 31),
])

_register("BUF", "Sabres", "Buffalo", "Lindy Ruff", CoachStyle.AGGRESSIVE, [
    _p("Tage Thompson", 72, "C", 0.80, 0.72, 0.85, 0.75, 0.85, 0.75, 0.52, 0.75, 27),
    _p("Alex Tuch", 89, "RW", 0.80, 0.68, 0.78, 0.72, 0.78, 0.72, 0.52, 0.72, 28),
    _p("Rasmus Dahlin", 26, "LD", 0.82, 0.62, 0.80, 0.75, 0.85, 0.80, 0.38, 0.78, 24),
    _p("Owen Power", 25, "LD", 0.78, 0.68, 0.70, 0.75, 0.75, 0.72, 0.38, 0.72, 21),
    _p("Dylan Cozens", 24, "C", 0.80, 0.65, 0.75, 0.75, 0.78, 0.72, 0.45, 0.72, 23),
    _p("Ukko-Pekka Luukkonen", 1, "G", 0.48, 0.58, 0.72, 0.72, 0.78, 0.70, 0.25, 0.75, 25),
])

_register("CGY", "Flames", "Calgary", "Ryan Huska", CoachStyle.BALANCED, [
    _p("Nazem Kadri", 91, "C", 0.75, 0.65, 0.78, 0.72, 0.80, 0.78, 0.58, 0.75, 33),
    _p("Jonathan Huberdeau", 10, "LW", 0.78, 0.58, 0.78, 0.72, 0.82, 0.80, 0.35, 0.78, 31),
    _p("Yegor Sharangovich", 17, "LW", 0.78, 0.62, 0.75, 0.72, 0.72, 0.68, 0.45, 0.70, 26),
    _p("Rasmus Andersson", 4, "RD", 0.75, 0.68, 0.70, 0.72, 0.75, 0.72, 0.52, 0.72, 28),
    _p("MacKenzie Weegar", 52, "LD", 0.78, 0.68, 0.68, 0.72, 0.75, 0.72, 0.48, 0.75, 30),
    _p("Jacob Markstrom", 25, "G", 0.48, 0.62, 0.72, 0.72, 0.82, 0.75, 0.25, 0.80, 34),
])

_register("CAR", "Hurricanes", "Carolina", "Rod Brind'Amour", CoachStyle.AGGRESSIVE, [
    _p("Sebastian Aho", 20, "C", 0.82, 0.62, 0.85, 0.78, 0.88, 0.82, 0.42, 0.82, 27),
    _p("Andrei Svechnikov", 37, "RW", 0.80, 0.72, 0.80, 0.75, 0.82, 0.72, 0.55, 0.75, 24),
    _p("Seth Jarvis", 24, "RW", 0.82, 0.55, 0.78, 0.72, 0.78, 0.72, 0.42, 0.72, 22),
    _p("Jaccob Slavin", 74, "LD", 0.78, 0.68, 0.68, 0.78, 0.82, 0.80, 0.35, 0.85, 30),
    _p("Brent Burns", 8, "RD", 0.72, 0.72, 0.75, 0.68, 0.78, 0.72, 0.52, 0.72, 39),
    _p("Frederik Andersen", 31, "G", 0.48, 0.60, 0.72, 0.72, 0.85, 0.75, 0.25, 0.80, 35),
])

_register("CHI", "Blackhawks", "Chicago", "Luke Richardson", CoachStyle.DEFENSIVE, [
    _p("Connor Bedard", 98, "C", 0.82, 0.52, 0.85, 0.72, 0.88, 0.78, 0.38, 0.75, 19),
    _p("Taylor Hall", 4, "LW", 0.78, 0.65, 0.75, 0.68, 0.78, 0.72, 0.48, 0.72, 33),
    _p("Philipp Kurashev", 23, "C", 0.78, 0.58, 0.72, 0.72, 0.72, 0.68, 0.38, 0.70, 24),
    _p("Seth Jones", 4, "RD", 0.78, 0.72, 0.68, 0.72, 0.78, 0.75, 0.45, 0.75, 30),
    _p("Alex Vlasic", 43, "LD", 0.72, 0.72, 0.62, 0.75, 0.72, 0.72, 0.42, 0.72, 22),
    _p("Petr Mrazek", 34, "G", 0.48, 0.58, 0.70, 0.68, 0.75, 0.70, 0.28, 0.72, 32),
])

_register("COL", "Avalanche", "Colorado", "Jared Bednar", CoachStyle.AGGRESSIVE, [
    _p("Nathan MacKinnon", 29, "C", 0.92, 0.68, 0.88, 0.82, 0.95, 0.88, 0.45, 0.85, 29),
    _p("Cale Makar", 8, "RD", 0.90, 0.60, 0.88, 0.80, 0.95, 0.90, 0.35, 0.88, 25),
    _p("Mikko Rantanen", 96, "RW", 0.78, 0.72, 0.85, 0.75, 0.88, 0.80, 0.45, 0.82, 28),
    _p("Devon Toews", 7, "LD", 0.80, 0.65, 0.72, 0.78, 0.80, 0.78, 0.40, 0.80, 30),
    _p("Josh Manson", 42, "RD", 0.72, 0.75, 0.62, 0.72, 0.68, 0.68, 0.58, 0.72, 32),
    _p("Alexandar Georgiev", 40, "G", 0.48, 0.58, 0.72, 0.72, 0.80, 0.72, 0.25, 0.78, 28),
])

_register("CBJ", "Blue Jackets", "Columbus", "Pascal Vincent", CoachStyle.BALANCED, [
    _p("Johnny Gaudreau", 13, "LW", 0.82, 0.50, 0.85, 0.72, 0.85, 0.82, 0.30, 0.78, 31),
    _p("Patrik Laine", 29, "RW", 0.75, 0.65, 0.88, 0.68, 0.85, 0.72, 0.42, 0.72, 26),
    _p("Boone Jenner", 38, "C", 0.72, 0.72, 0.70, 0.75, 0.72, 0.72, 0.55, 0.75, 31),
    _p("Zach Werenski", 8, "LD", 0.78, 0.65, 0.78, 0.72, 0.80, 0.75, 0.42, 0.75, 27),
    _p("Adam Fantilli", 11, "C", 0.80, 0.58, 0.72, 0.72, 0.75, 0.70, 0.42, 0.70, 20),
    _p("Elvis Merzlikins", 90, "G", 0.48, 0.58, 0.72, 0.72, 0.78, 0.72, 0.30, 0.75, 30),
])

_register("DAL", "Stars", "Dallas", "Pete DeBoer", CoachStyle.BALANCED, [
    _p("Jason Robertson", 21, "LW", 0.78, 0.65, 0.88, 0.75, 0.88, 0.80, 0.38, 0.82, 25),
    _p("Roope Hintz", 24, "C", 0.85, 0.68, 0.78, 0.78, 0.82, 0.75, 0.48, 0.78, 27),
    _p("Joe Pavelski", 16, "C", 0.68, 0.65, 0.82, 0.68, 0.82, 0.82, 0.42, 0.85, 40),
    _p("Miro Heiskanen", 4, "LD", 0.85, 0.62, 0.78, 0.80, 0.88, 0.82, 0.35, 0.82, 25),
    _p("Esa Lindell", 23, "LD", 0.72, 0.72, 0.65, 0.75, 0.72, 0.72, 0.48, 0.78, 30),
    _p("Jake Oettinger", 29, "G", 0.48, 0.60, 0.72, 0.75, 0.85, 0.75, 0.25, 0.82, 25),
])

_register("DET", "Red Wings", "Detroit", "Derek Lalonde", CoachStyle.BALANCED, [
    _p("Dylan Larkin", 71, "C", 0.82, 0.65, 0.78, 0.78, 0.82, 0.78, 0.48, 0.78, 28),
    _p("Lucas Raymond", 23, "RW", 0.80, 0.55, 0.80, 0.72, 0.80, 0.75, 0.35, 0.75, 22),
    _p("Alex DeBrincat", 12, "LW", 0.78, 0.55, 0.82, 0.72, 0.82, 0.75, 0.38, 0.75, 26),
    _p("Moritz Seider", 53, "RD", 0.78, 0.72, 0.68, 0.78, 0.80, 0.78, 0.48, 0.78, 23),
    _p("Ben Chiarot", 8, "LD", 0.70, 0.75, 0.60, 0.72, 0.65, 0.65, 0.55, 0.70, 33),
    _p("Ville Husso", 35, "G", 0.48, 0.58, 0.70, 0.72, 0.78, 0.72, 0.25, 0.75, 29),
])

_register("EDM", "Oilers", "Edmonton", "Kris Knoblauch", CoachStyle.AGGRESSIVE, [
    _p("Connor McDavid", 97, "C", 0.95, 0.62, 0.92, 0.82, 0.98, 0.92, 0.42, 0.88, 27),
    _p("Leon Draisaitl", 29, "C", 0.82, 0.72, 0.90, 0.78, 0.92, 0.85, 0.48, 0.85, 28),
    _p("Zach Hyman", 18, "LW", 0.78, 0.68, 0.78, 0.78, 0.78, 0.75, 0.55, 0.78, 32),
    _p("Darnell Nurse", 25, "LD", 0.80, 0.72, 0.65, 0.75, 0.75, 0.72, 0.55, 0.72, 29),
    _p("Evan Bouchard", 2, "RD", 0.78, 0.62, 0.80, 0.72, 0.80, 0.72, 0.38, 0.75, 24),
    _p("Stuart Skinner", 74, "G", 0.48, 0.60, 0.72, 0.75, 0.80, 0.72, 0.25, 0.78, 25),
])

_register("FLA", "Panthers", "Florida", "Paul Maurice", CoachStyle.AGGRESSIVE, [
    _p("Aleksander Barkov", 16, "C", 0.82, 0.68, 0.85, 0.80, 0.92, 0.88, 0.42, 0.88, 29),
    _p("Matthew Tkachuk", 19, "LW", 0.78, 0.72, 0.82, 0.75, 0.85, 0.78, 0.68, 0.78, 26),
    _p("Sam Reinhart", 13, "C", 0.78, 0.62, 0.82, 0.75, 0.82, 0.78, 0.38, 0.80, 28),
    _p("Aaron Ekblad", 5, "RD", 0.78, 0.72, 0.70, 0.75, 0.78, 0.75, 0.48, 0.78, 28),
    _p("Gustav Forsling", 42, "LD", 0.80, 0.62, 0.72, 0.78, 0.78, 0.75, 0.38, 0.78, 28),
    _p("Sergei Bobrovsky", 72, "G", 0.48, 0.60, 0.72, 0.72, 0.85, 0.78, 0.28, 0.82, 35),
])

_register("LA", "Kings", "Los Angeles", "Todd McLellan", CoachStyle.BALANCED, [
    _p("Anze Kopitar", 11, "C", 0.72, 0.68, 0.80, 0.72, 0.85, 0.85, 0.38, 0.85, 37),
    _p("Adrian Kempe", 9, "LW", 0.82, 0.65, 0.78, 0.75, 0.78, 0.72, 0.45, 0.75, 28),
    _p("Kevin Fiala", 22, "LW", 0.80, 0.58, 0.82, 0.72, 0.82, 0.75, 0.38, 0.72, 28),
    _p("Drew Doughty", 8, "RD", 0.72, 0.72, 0.75, 0.68, 0.80, 0.78, 0.52, 0.78, 34),
    _p("Mikey Anderson", 44, "LD", 0.75, 0.68, 0.62, 0.75, 0.72, 0.72, 0.42, 0.75, 24),
    _p("Cam Talbot", 39, "G", 0.48, 0.58, 0.70, 0.70, 0.78, 0.72, 0.25, 0.78, 37),
])

_register("MIN", "Wild", "Minnesota", "Dean Evason", CoachStyle.DEFENSIVE, [
    _p("Kirill Kaprizov", 97, "LW", 0.82, 0.62, 0.88, 0.75, 0.90, 0.80, 0.42, 0.80, 27),
    _p("Matt Boldy", 12, "LW", 0.78, 0.62, 0.80, 0.72, 0.78, 0.72, 0.38, 0.75, 23),
    _p("Joel Eriksson Ek", 14, "C", 0.78, 0.68, 0.72, 0.78, 0.78, 0.75, 0.48, 0.78, 27),
    _p("Jared Spurgeon", 46, "RD", 0.75, 0.65, 0.72, 0.72, 0.78, 0.78, 0.38, 0.80, 34),
    _p("Jonas Brodin", 25, "LD", 0.78, 0.65, 0.65, 0.78, 0.78, 0.78, 0.35, 0.82, 30),
    _p("Marc-Andre Fleury", 29, "G", 0.48, 0.58, 0.72, 0.68, 0.82, 0.75, 0.25, 0.82, 39),
])

_register("MTL", "Canadiens", "Montreal", "Martin St. Louis", CoachStyle.UP_TEMPO, [
    _p("Nick Suzuki", 14, "C", 0.80, 0.58, 0.80, 0.75, 0.82, 0.80, 0.38, 0.78, 24),
    _p("Cole Caufield", 22, "RW", 0.80, 0.50, 0.85, 0.72, 0.82, 0.75, 0.38, 0.75, 23),
    _p("Juraj Slafkovsky", 20, "LW", 0.75, 0.72, 0.68, 0.72, 0.72, 0.68, 0.48, 0.70, 20),
    _p("Mike Matheson", 8, "LD", 0.80, 0.65, 0.72, 0.72, 0.75, 0.72, 0.42, 0.72, 30),
    _p("David Savard", 58, "RD", 0.68, 0.72, 0.60, 0.72, 0.65, 0.68, 0.52, 0.72, 33),
    _p("Samuel Montembeault", 35, "G", 0.48, 0.58, 0.70, 0.72, 0.75, 0.70, 0.25, 0.72, 27),
])

_register("NSH", "Predators", "Nashville", "Andrew Brunette", CoachStyle.DEFENSIVE, [
    _p("Filip Forsberg", 9, "LW", 0.80, 0.65, 0.85, 0.75, 0.85, 0.78, 0.42, 0.80, 30),
    _p("Ryan O'Reilly", 90, "C", 0.72, 0.68, 0.78, 0.75, 0.82, 0.82, 0.42, 0.82, 33),
    _p("Gustav Nyquist", 14, "RW", 0.75, 0.55, 0.75, 0.72, 0.75, 0.75, 0.35, 0.78, 34),
    _p("Roman Josi", 59, "LD", 0.80, 0.65, 0.82, 0.78, 0.88, 0.82, 0.42, 0.82, 34),
    _p("Alexandre Carrier", 45, "RD", 0.78, 0.65, 0.65, 0.75, 0.72, 0.70, 0.45, 0.72, 27),
    _p("Juuse Saros", 74, "G", 0.48, 0.55, 0.72, 0.78, 0.88, 0.78, 0.25, 0.85, 29),
])

_register("NJ", "Devils", "New Jersey", "Lindy Ruff", CoachStyle.AGGRESSIVE, [
    _p("Jack Hughes", 86, "C", 0.90, 0.55, 0.85, 0.75, 0.90, 0.82, 0.42, 0.78, 23),
    _p("Nico Hischier", 13, "C", 0.80, 0.65, 0.78, 0.78, 0.82, 0.78, 0.42, 0.80, 25),
    _p("Jesper Bratt", 63, "LW", 0.82, 0.55, 0.82, 0.72, 0.82, 0.78, 0.35, 0.78, 25),
    _p("Dougie Hamilton", 7, "RD", 0.75, 0.68, 0.80, 0.72, 0.82, 0.78, 0.42, 0.78, 31),
    _p("Jonas Siegenthaler", 71, "LD", 0.75, 0.72, 0.60, 0.75, 0.72, 0.72, 0.42, 0.78, 27),
    _p("Vitek Vanecek", 41, "G", 0.48, 0.58, 0.70, 0.72, 0.78, 0.72, 0.25, 0.75, 28),
])

_register("NYI", "Islanders", "New York", "Patrick Roy", CoachStyle.DEFENSIVE, [
    _p("Mathew Barzal", 13, "C", 0.88, 0.58, 0.80, 0.72, 0.85, 0.80, 0.42, 0.78, 27),
    _p("Brock Nelson", 29, "C", 0.75, 0.68, 0.78, 0.72, 0.78, 0.75, 0.42, 0.78, 32),
    _p("Bo Horvat", 14, "C", 0.78, 0.68, 0.78, 0.75, 0.80, 0.78, 0.48, 0.78, 29),
    _p("Ryan Pulock", 6, "RD", 0.72, 0.72, 0.72, 0.72, 0.75, 0.72, 0.45, 0.75, 29),
    _p("Adam Pelech", 3, "LD", 0.75, 0.72, 0.62, 0.78, 0.75, 0.75, 0.42, 0.80, 29),
    _p("Ilya Sorokin", 30, "G", 0.48, 0.60, 0.72, 0.75, 0.88, 0.78, 0.25, 0.85, 29),
])

_register("NYR", "Rangers", "New York", "Peter Laviolette", CoachStyle.AGGRESSIVE, [
    _p("Artemi Panarin", 10, "LW", 0.80, 0.58, 0.88, 0.72, 0.90, 0.85, 0.38, 0.82, 32),
    _p("Mika Zibanejad", 93, "C", 0.78, 0.68, 0.85, 0.72, 0.85, 0.80, 0.42, 0.78, 31),
    _p("Chris Kreider", 20, "LW", 0.82, 0.72, 0.78, 0.75, 0.78, 0.72, 0.52, 0.75, 33),
    _p("Adam Fox", 23, "RD", 0.78, 0.60, 0.85, 0.75, 0.90, 0.88, 0.35, 0.85, 26),
    _p("K'Andre Miller", 79, "LD", 0.82, 0.72, 0.65, 0.78, 0.78, 0.72, 0.42, 0.75, 24),
    _p("Igor Shesterkin", 31, "G", 0.50, 0.58, 0.75, 0.78, 0.92, 0.82, 0.25, 0.88, 28),
])

_register("OTT", "Senators", "Ottawa", "Travis Green", CoachStyle.UP_TEMPO, [
    _p("Brady Tkachuk", 7, "LW", 0.78, 0.72, 0.78, 0.78, 0.82, 0.75, 0.65, 0.75, 25),
    _p("Tim Stutzle", 18, "C", 0.85, 0.55, 0.82, 0.72, 0.85, 0.78, 0.38, 0.75, 22),
    _p("Claude Giroux", 28, "RW", 0.72, 0.58, 0.80, 0.68, 0.80, 0.82, 0.42, 0.82, 36),
    _p("Thomas Chabot", 72, "LD", 0.82, 0.65, 0.78, 0.72, 0.82, 0.78, 0.42, 0.78, 27),
    _p("Jakob Chychrun", 6, "LD", 0.78, 0.68, 0.72, 0.72, 0.78, 0.72, 0.42, 0.72, 26),
    _p("Joonas Korpisalo", 70, "G", 0.48, 0.58, 0.70, 0.72, 0.75, 0.70, 0.25, 0.72, 30),
])

_register("PHI", "Flyers", "Philadelphia", "John Tortorella", CoachStyle.DEFENSIVE, [
    _p("Travis Konecny", 11, "RW", 0.82, 0.62, 0.82, 0.75, 0.82, 0.75, 0.52, 0.75, 27),
    _p("Sean Couturier", 14, "C", 0.72, 0.68, 0.75, 0.72, 0.80, 0.80, 0.42, 0.80, 31),
    _p("Owen Tippett", 74, "RW", 0.80, 0.62, 0.75, 0.72, 0.75, 0.70, 0.45, 0.72, 25),
    _p("Ivan Provorov", 9, "LD", 0.78, 0.68, 0.68, 0.72, 0.75, 0.72, 0.42, 0.72, 27),
    _p("Travis Sanheim", 6, "LD", 0.78, 0.65, 0.70, 0.75, 0.75, 0.72, 0.42, 0.75, 28),
    _p("Carter Hart", 79, "G", 0.48, 0.58, 0.72, 0.72, 0.80, 0.72, 0.25, 0.78, 25),
])

_register("PIT", "Penguins", "Pittsburgh", "Mike Sullivan", CoachStyle.BALANCED, [
    _p("Sidney Crosby", 87, "C", 0.78, 0.72, 0.90, 0.75, 0.95, 0.92, 0.42, 0.90, 37),
    _p("Evgeni Malkin", 71, "C", 0.72, 0.72, 0.85, 0.68, 0.88, 0.82, 0.48, 0.78, 38),
    _p("Bryan Rust", 17, "RW", 0.80, 0.65, 0.78, 0.72, 0.78, 0.72, 0.45, 0.75, 32),
    _p("Kris Letang", 58, "RD", 0.78, 0.68, 0.78, 0.68, 0.82, 0.78, 0.45, 0.78, 37),
    _p("Marcus Pettersson", 28, "LD", 0.75, 0.68, 0.65, 0.72, 0.72, 0.72, 0.38, 0.75, 28),
    _p("Tristan Jarry", 35, "G", 0.48, 0.60, 0.72, 0.72, 0.80, 0.72, 0.25, 0.78, 29),
])

_register("SJ", "Sharks", "San Jose", "David Quinn", CoachStyle.BALANCED, [
    _p("Tomas Hertl", 48, "C", 0.78, 0.68, 0.78, 0.75, 0.80, 0.75, 0.42, 0.78, 30),
    _p("Logan Couture", 39, "C", 0.72, 0.62, 0.78, 0.68, 0.78, 0.78, 0.42, 0.80, 35),
    _p("Erik Karlsson", 65, "RD", 0.80, 0.58, 0.85, 0.68, 0.88, 0.82, 0.38, 0.78, 34),
    _p("Mario Ferraro", 38, "LD", 0.80, 0.65, 0.62, 0.75, 0.72, 0.72, 0.48, 0.72, 25),
    _p("Fabian Zetterlund", 20, "RW", 0.78, 0.62, 0.72, 0.72, 0.72, 0.68, 0.42, 0.70, 24),
    _p("Mackenzie Blackwood", 29, "G", 0.48, 0.62, 0.72, 0.72, 0.80, 0.72, 0.25, 0.78, 27),
])

_register("SEA", "Kraken", "Seattle", "Dave Hakstol", CoachStyle.BALANCED, [
    _p("Matty Beniers", 10, "C", 0.80, 0.58, 0.75, 0.75, 0.78, 0.75, 0.38, 0.72, 21),
    _p("Jared McCann", 19, "C", 0.78, 0.62, 0.80, 0.72, 0.78, 0.72, 0.45, 0.75, 28),
    _p("Jordan Eberle", 7, "RW", 0.75, 0.58, 0.78, 0.68, 0.78, 0.75, 0.35, 0.78, 34),
    _p("Vince Dunn", 29, "LD", 0.80, 0.60, 0.75, 0.72, 0.78, 0.75, 0.38, 0.75, 27),
    _p("Adam Larsson", 6, "RD", 0.72, 0.72, 0.62, 0.72, 0.72, 0.72, 0.48, 0.78, 31),
    _p("Philipp Grubauer", 31, "G", 0.48, 0.58, 0.70, 0.72, 0.78, 0.72, 0.25, 0.75, 32),
])

_register("STL", "Blues", "St. Louis", "Drew Bannister", CoachStyle.BALANCED, [
    _p("Robert Thomas", 18, "C", 0.82, 0.58, 0.82, 0.75, 0.85, 0.82, 0.38, 0.78, 25),
    _p("Jordan Kyrou", 25, "RW", 0.85, 0.55, 0.80, 0.72, 0.82, 0.72, 0.38, 0.72, 26),
    _p("Pavel Buchnevich", 89, "LW", 0.78, 0.62, 0.80, 0.72, 0.80, 0.78, 0.38, 0.78, 29),
    _p("Colton Parayko", 55, "RD", 0.78, 0.75, 0.72, 0.72, 0.75, 0.72, 0.45, 0.72, 31),
    _p("Torey Krug", 47, "LD", 0.75, 0.58, 0.78, 0.68, 0.78, 0.78, 0.38, 0.75, 33),
    _p("Jordan Binnington", 50, "G", 0.48, 0.60, 0.72, 0.72, 0.80, 0.72, 0.42, 0.75, 31),
])

_register("TB", "Lightning", "Tampa Bay", "Jon Cooper", CoachStyle.AGGRESSIVE, [
    _p("Nikita Kucherov", 86, "RW", 0.80, 0.60, 0.92, 0.72, 0.92, 0.88, 0.38, 0.85, 31),
    _p("Brayden Point", 21, "C", 0.82, 0.62, 0.85, 0.75, 0.88, 0.82, 0.45, 0.82, 28),
    _p("Steven Stamkos", 91, "C", 0.75, 0.68, 0.85, 0.68, 0.85, 0.80, 0.42, 0.82, 34),
    _p("Victor Hedman", 77, "LD", 0.78, 0.75, 0.78, 0.75, 0.88, 0.82, 0.42, 0.82, 33),
    _p("Erik Cernak", 81, "RD", 0.75, 0.75, 0.62, 0.75, 0.72, 0.72, 0.52, 0.75, 27),
    _p("Andrei Vasilevskiy", 88, "G", 0.48, 0.62, 0.75, 0.78, 0.90, 0.82, 0.25, 0.88, 30),
])

_register("TOR", "Maple Leafs", "Toronto", "Sheldon Keefe", CoachStyle.UP_TEMPO, [
    _p("Auston Matthews", 34, "C", 0.85, 0.72, 0.92, 0.78, 0.95, 0.85, 0.42, 0.82, 27),
    _p("Mitch Marner", 16, "RW", 0.82, 0.55, 0.85, 0.75, 0.90, 0.88, 0.32, 0.82, 27),
    _p("William Nylander", 88, "RW", 0.82, 0.58, 0.82, 0.72, 0.85, 0.78, 0.35, 0.78, 28),
    _p("Morgan Rielly", 44, "LD", 0.80, 0.60, 0.78, 0.72, 0.82, 0.78, 0.38, 0.78, 30),
    _p("TJ Brodie", 78, "RD", 0.72, 0.65, 0.68, 0.72, 0.75, 0.78, 0.35, 0.80, 34),
    _p("Ilya Samsonov", 35, "G", 0.48, 0.60, 0.72, 0.72, 0.78, 0.72, 0.25, 0.75, 27),
])

_register("VAN", "Canucks", "Vancouver", "Rick Tocchet", CoachStyle.AGGRESSIVE, [
    _p("Elias Pettersson", 40, "C", 0.82, 0.62, 0.88, 0.75, 0.90, 0.85, 0.38, 0.82, 25),
    _p("J.T. Miller", 9, "C", 0.78, 0.68, 0.80, 0.72, 0.82, 0.78, 0.52, 0.75, 31),
    _p("Brock Boeser", 6, "RW", 0.75, 0.62, 0.82, 0.70, 0.78, 0.72, 0.38, 0.75, 27),
    _p("Quinn Hughes", 43, "LD", 0.85, 0.55, 0.85, 0.75, 0.90, 0.88, 0.32, 0.82, 24),
    _p("Filip Hronek", 17, "RD", 0.78, 0.65, 0.72, 0.72, 0.78, 0.72, 0.42, 0.75, 27),
    _p("Thatcher Demko", 35, "G", 0.48, 0.60, 0.72, 0.75, 0.85, 0.78, 0.25, 0.82, 28),
])

_register("VGK", "Golden Knights", "Vegas", "Bruce Cassidy", CoachStyle.AGGRESSIVE, [
    _p("Jack Eichel", 9, "C", 0.82, 0.68, 0.88, 0.75, 0.88, 0.82, 0.45, 0.80, 27),
    _p("Mark Stone", 61, "RW", 0.75, 0.65, 0.82, 0.72, 0.85, 0.85, 0.48, 0.82, 32),
    _p("Jonathan Marchessault", 81, "LW", 0.78, 0.58, 0.80, 0.72, 0.78, 0.75, 0.42, 0.78, 33),
    _p("Alex Pietrangelo", 7, "RD", 0.75, 0.72, 0.75, 0.72, 0.82, 0.80, 0.42, 0.82, 34),
    _p("Shea Theodore", 27, "LD", 0.80, 0.62, 0.78, 0.72, 0.80, 0.78, 0.38, 0.78, 29),
    _p("Logan Thompson", 36, "G", 0.48, 0.60, 0.72, 0.72, 0.82, 0.75, 0.25, 0.80, 27),
])

_register("WSH", "Capitals", "Washington", "Spencer Carbery", CoachStyle.BALANCED, [
    _p("Alex Ovechkin", 8, "LW", 0.70, 0.78, 0.90, 0.65, 0.88, 0.75, 0.55, 0.80, 38),
    _p("Dylan Strome", 17, "C", 0.78, 0.60, 0.80, 0.72, 0.80, 0.78, 0.38, 0.75, 27),
    _p("Tom Wilson", 43, "RW", 0.78, 0.78, 0.68, 0.75, 0.72, 0.65, 0.72, 0.72, 30),
    _p("John Carlson", 74, "RD", 0.72, 0.65, 0.80, 0.68, 0.80, 0.78, 0.38, 0.78, 34),
    _p("Dmitry Orlov", 9, "LD", 0.75, 0.68, 0.68, 0.72, 0.75, 0.72, 0.45, 0.75, 32),
    _p("Charlie Lindgren", 79, "G", 0.48, 0.58, 0.70, 0.72, 0.78, 0.72, 0.25, 0.75, 30),
])

_register("WPG", "Jets", "Winnipeg", "Rick Bowness", CoachStyle.BALANCED, [
    _p("Kyle Connor", 81, "LW", 0.82, 0.62, 0.85, 0.75, 0.85, 0.78, 0.38, 0.78, 27),
    _p("Mark Scheifele", 55, "C", 0.78, 0.68, 0.82, 0.72, 0.85, 0.80, 0.42, 0.78, 31),
    _p("Nikolaj Ehlers", 27, "LW", 0.85, 0.55, 0.82, 0.72, 0.82, 0.75, 0.35, 0.75, 28),
    _p("Josh Morrissey", 44, "LD", 0.78, 0.68, 0.78, 0.75, 0.82, 0.78, 0.42, 0.78, 29),
    _p("Neal Pionk", 4, "RD", 0.75, 0.65, 0.72, 0.72, 0.72, 0.72, 0.45, 0.72, 28),
    _p("Connor Hellebuyck", 37, "G", 0.48, 0.62, 0.75, 0.78, 0.90, 0.80, 0.25, 0.88, 31),
])


def get_nhl_team(abbr: str) -> Team | None:
    return _TEAMS.get(abbr.upper())


def get_all_nhl_teams() -> dict[str, Team]:
    return dict(_TEAMS)
