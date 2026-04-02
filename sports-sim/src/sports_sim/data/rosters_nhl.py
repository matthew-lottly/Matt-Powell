"""NHL team rosters — all 32 teams with core starters plus real depth snapshots.

The source data in this module focuses on key NHL contributors. Bench depth is
filled from an offline snapshot of current NHL rosters when available, with a
synthesized fallback to keep the simulation resilient if that snapshot is
missing or incomplete.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from sports_sim.core.models import (
    Coach,
    CoachStyle,
    Player,
    PlayerAttributes,
    Team,
    TeamSliders,
    Venue,
)
from sports_sim.data.venues import NHL_VENUES

_DEPTH_FIRST = [
    "Tyler",
    "Mason",
    "Dylan",
    "Cole",
    "Brandon",
    "Noah",
    "Evan",
    "Logan",
    "Luke",
    "Ryan",
    "Parker",
    "Jake",
    "Nolan",
    "Owen",
    "Carter",
    "Wyatt",
]

_DEPTH_LAST = [
    "Bennett",
    "Mercer",
    "Lowry",
    "Foote",
    "Greene",
    "Lund",
    "Borgen",
    "Hayes",
    "Walker",
    "Pinto",
    "Zary",
    "Krebs",
    "Sillinger",
    "Schneider",
    "Holm",
    "Faber",
]

_DEPTH_BLUEPRINTS: list[tuple[str, str, float]] = [
    ("C", "two-way center", 0.92),
    ("LW", "middle-six wing", 0.91),
    ("RW", "middle-six wing", 0.91),
    ("LW", "forechecking wing", 0.88),
    ("RW", "scoring wing", 0.89),
    ("C", "energy center", 0.87),
    ("LD", "second-pair defense", 0.91),
    ("RD", "second-pair defense", 0.91),
    ("LD", "shutdown defense", 0.88),
    ("RD", "puck-moving defense", 0.89),
    ("LW", "checking wing", 0.86),
    ("G", "backup goalie", 0.93),
]

_DEPTH_SNAPSHOT_PATH = Path(__file__).with_name("nhl_depth_snapshot.json")
_REAL_DEPTH_SNAPSHOT: dict[str, list[dict[str, object]]] | None = None


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return round(max(lo, min(hi, value)), 3)


def _avg(values: list[float]) -> float:
    return float(mean(values)) if values else 0.5


def _load_real_depth_snapshot() -> dict[str, list[dict[str, object]]]:
    global _REAL_DEPTH_SNAPSHOT

    if _REAL_DEPTH_SNAPSHOT is None:
        try:
            raw = json.loads(_DEPTH_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}

        _REAL_DEPTH_SNAPSHOT = raw if isinstance(raw, dict) else {}

    return _REAL_DEPTH_SNAPSHOT


def _snapshot_int(entry: dict[str, object], key: str, default: int) -> int:
    value = entry.get(key)
    return value if isinstance(value, int) else default


def _slug(seed: str) -> int:
    return sum(ord(char) for char in seed)


def _style_sliders(style: CoachStyle) -> TeamSliders:
    if style == CoachStyle.AGGRESSIVE:
        return TeamSliders(
            offensive_aggression=0.7,
            defensive_intensity=0.63,
            pace=0.66,
            forecheck_intensity=0.72,
            power_play_aggression=0.7,
            line_change_frequency=0.58,
        )
    if style == CoachStyle.DEFENSIVE:
        return TeamSliders(
            offensive_aggression=0.48,
            defensive_intensity=0.75,
            pace=0.46,
            forecheck_intensity=0.55,
            power_play_aggression=0.52,
            line_change_frequency=0.62,
        )
    if style == CoachStyle.UP_TEMPO:
        return TeamSliders(
            offensive_aggression=0.64,
            defensive_intensity=0.56,
            pace=0.74,
            forecheck_intensity=0.66,
            power_play_aggression=0.67,
            line_change_frequency=0.68,
        )
    return TeamSliders(
        offensive_aggression=0.58,
        defensive_intensity=0.6,
        pace=0.57,
        forecheck_intensity=0.6,
        power_play_aggression=0.6,
        line_change_frequency=0.6,
    )


def _player_value(player: Player) -> float:
    attrs = player.attributes
    if player.position == "G":
        return _clamp(
            attrs.skill * 0.28
            + attrs.decision_making * 0.18
            + attrs.composure * 0.18
            + attrs.endurance * 0.1
            + attrs.awareness * 0.12
            + attrs.clutch * 0.08
            + attrs.durability * 0.06,
        )

    return _clamp(
        attrs.speed * 0.12
        + attrs.strength * 0.1
        + attrs.accuracy * 0.16
        + attrs.endurance * 0.1
        + attrs.skill * 0.18
        + attrs.decision_making * 0.14
        + attrs.composure * 0.08
        + attrs.awareness * 0.06
        + attrs.clutch * 0.04
        + attrs.durability * 0.02,
    )


def _template_for_position(roster: list[Player], position: str) -> Player:
    candidates = [player for player in roster if player.position == position]
    if not candidates and position in {"LW", "RW"}:
        candidates = [player for player in roster if player.position in {"LW", "RW"}]
    if not candidates and position in {"LD", "RD"}:
        candidates = [player for player in roster if player.position in {"LD", "RD"}]
    if not candidates:
        candidates = roster
    return max(candidates, key=_player_value)


def _bench_name(abbr: str, index: int) -> str:
    seed = _slug(abbr) + index * 11
    first = _DEPTH_FIRST[seed % len(_DEPTH_FIRST)]
    last = _DEPTH_LAST[(seed // 3) % len(_DEPTH_LAST)]
    return f"{first} {last}"


def _depth_player(
    abbr: str,
    roster: list[Player],
    index: int,
    position: str,
    role: str,
    factor: float,
    *,
    name: str | None = None,
    number: int | None = None,
    age: int | None = None,
    height_cm: int | None = None,
    weight_kg: int | None = None,
) -> Player:
    template = _template_for_position(roster, position)
    attrs = template.attributes
    age_offset = ((index + _slug(abbr)) % 6) - 2
    height_offset = ((index * 3) % 7) - 3
    weight_offset = ((index * 5) % 9) - 4
    role_boost = 0.02 if "scoring" in role or "puck-moving" in role else 0.0
    defense_boost = 0.02 if "shutdown" in role or "two-way" in role else 0.0

    adjusted = PlayerAttributes(
        speed=_clamp(attrs.speed * factor + (0.01 if position in {"LW", "RW"} else 0.0)),
        strength=_clamp(attrs.strength * factor + defense_boost),
        accuracy=_clamp(attrs.accuracy * factor + role_boost),
        endurance=_clamp(attrs.endurance * min(1.0, factor + 0.02)),
        skill=_clamp(attrs.skill * factor + role_boost),
        decision_making=_clamp(attrs.decision_making * factor + defense_boost),
        aggression=_clamp(attrs.aggression * factor + (0.03 if "checking" in role else 0.0)),
        composure=_clamp(attrs.composure * factor),
        awareness=_clamp(attrs.awareness * factor + defense_boost),
        leadership=_clamp(attrs.leadership * factor),
        clutch=_clamp(attrs.clutch * factor + role_boost),
        durability=_clamp(attrs.durability * min(1.0, factor + 0.04)),
    )

    return Player(
        name=name or _bench_name(abbr, index),
        number=number if number is not None else 40 + index,
        position=position,
        age=max(20, age if age is not None else template.age + age_offset),
        height_cm=max(173, height_cm if height_cm is not None else template.height_cm + height_offset),
        weight_kg=max(74, weight_kg if weight_kg is not None else template.weight_kg + weight_offset),
        attributes=adjusted,
    )


def _build_real_bench(abbr: str, roster: list[Player]) -> list[Player]:
    snapshot = _load_real_depth_snapshot().get(abbr, [])
    if not snapshot:
        return []

    starters = {player.name for player in roster}
    used_names = set(starters)
    bench: list[Player] = []

    for entry in snapshot:
        name = str(entry.get("name") or "").strip()
        position = str(entry.get("position") or "").strip().upper()
        if not name or name in used_names or position not in {"C", "LW", "RW", "LD", "RD", "G"}:
            continue

        blueprint_index = min(len(bench), len(_DEPTH_BLUEPRINTS) - 1)
        _, role, factor = _DEPTH_BLUEPRINTS[blueprint_index]
        if position == "G":
            role = "backup goalie"
            factor = max(factor, 0.93)

        bench.append(
            _depth_player(
                abbr,
                roster + bench,
                len(bench) + 1,
                position,
                role,
                factor,
                name=name,
                number=_snapshot_int(entry, "number", 0) or 40 + len(bench) + 1,
                age=_snapshot_int(entry, "age", 25),
                height_cm=_snapshot_int(entry, "height_cm", 185),
                weight_kg=_snapshot_int(entry, "weight_kg", 88),
            )
        )
        used_names.add(name)

        if len(bench) == len(_DEPTH_BLUEPRINTS):
            break

    return bench


def _build_bench(abbr: str, roster: list[Player]) -> list[Player]:
    bench = _build_real_bench(abbr, roster)
    if len(bench) >= len(_DEPTH_BLUEPRINTS):
        bench = bench[: len(_DEPTH_BLUEPRINTS)]
    else:
        for index, (position, role, factor) in enumerate(_DEPTH_BLUEPRINTS[len(bench) :], start=len(bench) + 1):
            bench.append(_depth_player(abbr, roster + bench, index, position, role, factor))

    if not any(player.position == "G" for player in bench):
        goalie_position, goalie_role, goalie_factor = _DEPTH_BLUEPRINTS[-1]
        goalie = _depth_player(abbr, roster + bench, len(bench) + 1, goalie_position, goalie_role, goalie_factor)
        if len(bench) == len(_DEPTH_BLUEPRINTS):
            bench[-1] = goalie
        else:
            bench.append(goalie)

    return bench


def _team_strengths(players: list[Player], bench: list[Player]) -> tuple[float, float, float, float]:
    skaters = [player for player in players if player.position != "G"]
    forwards = [player for player in skaters if player.position in {"C", "LW", "RW"}]
    defenders = [player for player in skaters if player.position in {"LD", "RD"}]
    goalies = [player for player in players + bench if player.position == "G"]

    offense = _clamp(
        _avg(
            [
                _player_value(player) * 0.55 + player.attributes.accuracy * 0.25 + player.attributes.skill * 0.2
                for player in forwards
            ]
        )
    )
    defense = _clamp(
        _avg(
            [
                _player_value(player) * 0.45
                + player.attributes.awareness * 0.25
                + player.attributes.strength * 0.15
                + player.attributes.composure * 0.15
                for player in defenders
            ]
        )
        * 0.7
        + _avg([_player_value(goalie) for goalie in goalies]) * 0.3
    )
    special = _clamp(
        _avg(
            [
                player.attributes.skill * 0.3
                + player.attributes.decision_making * 0.25
                + player.attributes.clutch * 0.2
                + player.attributes.accuracy * 0.25
                for player in skaters[:5]
            ]
        )
    )
    depth = _clamp(_avg([_player_value(player) for player in bench]))
    return offense, defense, special, depth


def _p(
    name: str,
    num: int,
    pos: str,
    spd: float,
    stren: float,
    acc: float,
    end: float,
    skl: float,
    dec: float,
    agg: float,
    comp: float,
    age: int = 26,
    ht: int = 185,
    wt: int = 90,
    aware: float | None = None,
    lead: float | None = None,
    clutch: float | None = None,
    dur: float | None = None,
) -> Player:
    awareness = aware if aware is not None else _clamp(dec * 0.55 + comp * 0.25 + skl * 0.2)
    leadership = lead if lead is not None else _clamp(comp * 0.35 + dec * 0.25 + min(age / 40, 1.0) * 0.2 + skl * 0.2)
    clutch_rating = clutch if clutch is not None else _clamp(acc * 0.35 + comp * 0.35 + skl * 0.3)
    durability = (
        dur if dur is not None else _clamp(end * 0.55 + stren * 0.25 + max(0.0, 0.22 - abs(age - 27) * 0.012) + 0.38)
    )

    return Player(
        name=name,
        number=num,
        position=pos,
        age=age,
        height_cm=ht,
        weight_kg=wt,
        attributes=PlayerAttributes(
            speed=spd,
            strength=stren,
            accuracy=acc,
            endurance=end,
            skill=skl,
            decision_making=dec,
            aggression=agg,
            composure=comp,
            awareness=awareness,
            leadership=leadership,
            clutch=clutch_rating,
            durability=durability,
        ),
    )


def _nhl_team(
    name: str,
    city: str,
    abbr: str,
    coach_name: str,
    coach_style: CoachStyle,
    players: list[Player],
    bench: list[Player] | None = None,
) -> Team:
    # Ensure `venue` is a Venue instance (not None) to satisfy strict typing
    venue = NHL_VENUES.get(abbr) or next(iter(NHL_VENUES.values()), None)
    if venue is None:
        venue = Venue()

    full_bench = bench or _build_bench(abbr, players)
    offense, defense, special, depth = _team_strengths(players, full_bench)

    return Team(
        name=name,
        city=city,
        abbreviation=abbr,
        players=players,
        bench=full_bench,
        formation="standard",
        coach=Coach(name=coach_name, style=coach_style, play_calling=0.65, motivation=0.7, adaptability=0.65),
        venue=venue,
        sliders=_style_sliders(coach_style),
        overall_offense=offense,
        overall_defense=defense,
        overall_special_teams=special,
        depth_rating=depth,
    )


# ── All 32 NHL Teams ──

_TEAMS: dict[str, Team] = {}


def _register(
    abbr: str,
    name: str,
    city: str,
    coach: str,
    style: CoachStyle,
    roster: list[Player],
    bench: list[Player] | None = None,
):
    _TEAMS[abbr] = _nhl_team(name, city, abbr, coach, style, roster, bench=bench)


_register(
    "ANA",
    "Ducks",
    "Anaheim",
    "Greg Cronin",
    CoachStyle.BALANCED,
    [
        _p("Troy Terry", 19, "RW", 0.78, 0.55, 0.80, 0.72, 0.78, 0.72, 0.40, 0.75, 26),
        _p("Trevor Zegras", 11, "C", 0.80, 0.55, 0.78, 0.70, 0.82, 0.75, 0.38, 0.72, 23),
        _p("Mason McTavish", 37, "C", 0.72, 0.68, 0.74, 0.72, 0.75, 0.70, 0.50, 0.72, 21),
        _p("Jamie Drysdale", 6, "RD", 0.82, 0.55, 0.72, 0.72, 0.75, 0.72, 0.35, 0.72, 22),
        _p("Cam Fowler", 4, "LD", 0.75, 0.62, 0.70, 0.68, 0.72, 0.72, 0.38, 0.78, 32),
        _p("John Gibson", 36, "G", 0.50, 0.55, 0.72, 0.72, 0.82, 0.75, 0.25, 0.82, 31),
    ],
)

_register(
    "ARI",
    "Coyotes",
    "Arizona",
    "André Tourigny",
    CoachStyle.DEFENSIVE,
    [
        _p("Clayton Keller", 9, "LW", 0.82, 0.55, 0.80, 0.72, 0.82, 0.75, 0.35, 0.75, 25),
        _p("Nick Schmaltz", 8, "C", 0.78, 0.55, 0.78, 0.70, 0.78, 0.75, 0.35, 0.72, 28),
        _p("Lawson Crouse", 67, "LW", 0.72, 0.72, 0.68, 0.72, 0.68, 0.65, 0.62, 0.68, 27),
        _p("Jakob Chychrun", 6, "LD", 0.78, 0.65, 0.72, 0.72, 0.75, 0.70, 0.45, 0.72, 26),
        _p("Juuso Valimaki", 4, "LD", 0.72, 0.62, 0.65, 0.70, 0.68, 0.65, 0.45, 0.68, 25),
        _p("Karel Vejmelka", 70, "G", 0.48, 0.58, 0.70, 0.72, 0.75, 0.68, 0.25, 0.75, 28),
    ],
)

_register(
    "BOS",
    "Bruins",
    "Boston",
    "Jim Montgomery",
    CoachStyle.BALANCED,
    [
        _p("David Pastrnak", 88, "RW", 0.82, 0.62, 0.90, 0.75, 0.92, 0.82, 0.42, 0.82, 28),
        _p("Brad Marchand", 63, "LW", 0.78, 0.62, 0.82, 0.72, 0.85, 0.82, 0.65, 0.78, 36),
        _p("Charlie McAvoy", 73, "RD", 0.80, 0.72, 0.72, 0.78, 0.82, 0.78, 0.52, 0.80, 26),
        _p("Hampus Lindholm", 27, "LD", 0.75, 0.72, 0.68, 0.75, 0.78, 0.75, 0.48, 0.78, 30),
        _p("Pavel Zacha", 18, "C", 0.78, 0.65, 0.72, 0.72, 0.75, 0.72, 0.42, 0.72, 27),
        _p("Linus Ullmark", 35, "G", 0.48, 0.60, 0.75, 0.75, 0.88, 0.78, 0.25, 0.85, 31),
    ],
)

_register(
    "BUF",
    "Sabres",
    "Buffalo",
    "Lindy Ruff",
    CoachStyle.AGGRESSIVE,
    [
        _p("Tage Thompson", 72, "C", 0.80, 0.72, 0.85, 0.75, 0.85, 0.75, 0.52, 0.75, 27),
        _p("Alex Tuch", 89, "RW", 0.80, 0.68, 0.78, 0.72, 0.78, 0.72, 0.52, 0.72, 28),
        _p("Rasmus Dahlin", 26, "LD", 0.82, 0.62, 0.80, 0.75, 0.85, 0.80, 0.38, 0.78, 24),
        _p("Owen Power", 25, "LD", 0.78, 0.68, 0.70, 0.75, 0.75, 0.72, 0.38, 0.72, 21),
        _p("Dylan Cozens", 24, "C", 0.80, 0.65, 0.75, 0.75, 0.78, 0.72, 0.45, 0.72, 23),
        _p("Ukko-Pekka Luukkonen", 1, "G", 0.48, 0.58, 0.72, 0.72, 0.78, 0.70, 0.25, 0.75, 25),
    ],
)

_register(
    "CGY",
    "Flames",
    "Calgary",
    "Ryan Huska",
    CoachStyle.BALANCED,
    [
        _p("Nazem Kadri", 91, "C", 0.75, 0.65, 0.78, 0.72, 0.80, 0.78, 0.58, 0.75, 33),
        _p("Jonathan Huberdeau", 10, "LW", 0.78, 0.58, 0.78, 0.72, 0.82, 0.80, 0.35, 0.78, 31),
        _p("Yegor Sharangovich", 17, "LW", 0.78, 0.62, 0.75, 0.72, 0.72, 0.68, 0.45, 0.70, 26),
        _p("Rasmus Andersson", 4, "RD", 0.75, 0.68, 0.70, 0.72, 0.75, 0.72, 0.52, 0.72, 28),
        _p("MacKenzie Weegar", 52, "LD", 0.78, 0.68, 0.68, 0.72, 0.75, 0.72, 0.48, 0.75, 30),
        _p("Jacob Markstrom", 25, "G", 0.48, 0.62, 0.72, 0.72, 0.82, 0.75, 0.25, 0.80, 34),
    ],
)

_register(
    "CAR",
    "Hurricanes",
    "Carolina",
    "Rod Brind'Amour",
    CoachStyle.AGGRESSIVE,
    [
        _p("Sebastian Aho", 20, "C", 0.82, 0.62, 0.85, 0.78, 0.88, 0.82, 0.42, 0.82, 27),
        _p("Andrei Svechnikov", 37, "RW", 0.80, 0.72, 0.80, 0.75, 0.82, 0.72, 0.55, 0.75, 24),
        _p("Seth Jarvis", 24, "RW", 0.82, 0.55, 0.78, 0.72, 0.78, 0.72, 0.42, 0.72, 22),
        _p("Jaccob Slavin", 74, "LD", 0.78, 0.68, 0.68, 0.78, 0.82, 0.80, 0.35, 0.85, 30),
        _p("Brent Burns", 8, "RD", 0.72, 0.72, 0.75, 0.68, 0.78, 0.72, 0.52, 0.72, 39),
        _p("Frederik Andersen", 31, "G", 0.48, 0.60, 0.72, 0.72, 0.85, 0.75, 0.25, 0.80, 35),
    ],
)

_register(
    "CHI",
    "Blackhawks",
    "Chicago",
    "Luke Richardson",
    CoachStyle.DEFENSIVE,
    [
        _p("Connor Bedard", 98, "C", 0.82, 0.52, 0.85, 0.72, 0.88, 0.78, 0.38, 0.75, 19),
        _p("Taylor Hall", 4, "LW", 0.78, 0.65, 0.75, 0.68, 0.78, 0.72, 0.48, 0.72, 33),
        _p("Philipp Kurashev", 23, "C", 0.78, 0.58, 0.72, 0.72, 0.72, 0.68, 0.38, 0.70, 24),
        _p("Seth Jones", 4, "RD", 0.78, 0.72, 0.68, 0.72, 0.78, 0.75, 0.45, 0.75, 30),
        _p("Alex Vlasic", 43, "LD", 0.72, 0.72, 0.62, 0.75, 0.72, 0.72, 0.42, 0.72, 22),
        _p("Petr Mrazek", 34, "G", 0.48, 0.58, 0.70, 0.68, 0.75, 0.70, 0.28, 0.72, 32),
    ],
)

_register(
    "COL",
    "Avalanche",
    "Colorado",
    "Jared Bednar",
    CoachStyle.AGGRESSIVE,
    [
        _p("Nathan MacKinnon", 29, "C", 0.92, 0.68, 0.88, 0.82, 0.95, 0.88, 0.45, 0.85, 29),
        _p("Cale Makar", 8, "RD", 0.90, 0.60, 0.88, 0.80, 0.95, 0.90, 0.35, 0.88, 25),
        _p("Mikko Rantanen", 96, "RW", 0.78, 0.72, 0.85, 0.75, 0.88, 0.80, 0.45, 0.82, 28),
        _p("Devon Toews", 7, "LD", 0.80, 0.65, 0.72, 0.78, 0.80, 0.78, 0.40, 0.80, 30),
        _p("Josh Manson", 42, "RD", 0.72, 0.75, 0.62, 0.72, 0.68, 0.68, 0.58, 0.72, 32),
        _p("Alexandar Georgiev", 40, "G", 0.48, 0.58, 0.72, 0.72, 0.80, 0.72, 0.25, 0.78, 28),
    ],
)

_register(
    "CBJ",
    "Blue Jackets",
    "Columbus",
    "Pascal Vincent",
    CoachStyle.BALANCED,
    [
        _p("Johnny Gaudreau", 13, "LW", 0.82, 0.50, 0.85, 0.72, 0.85, 0.82, 0.30, 0.78, 31),
        _p("Patrik Laine", 29, "RW", 0.75, 0.65, 0.88, 0.68, 0.85, 0.72, 0.42, 0.72, 26),
        _p("Boone Jenner", 38, "C", 0.72, 0.72, 0.70, 0.75, 0.72, 0.72, 0.55, 0.75, 31),
        _p("Zach Werenski", 8, "LD", 0.78, 0.65, 0.78, 0.72, 0.80, 0.75, 0.42, 0.75, 27),
        _p("Adam Fantilli", 11, "C", 0.80, 0.58, 0.72, 0.72, 0.75, 0.70, 0.42, 0.70, 20),
        _p("Elvis Merzlikins", 90, "G", 0.48, 0.58, 0.72, 0.72, 0.78, 0.72, 0.30, 0.75, 30),
    ],
)

_register(
    "DAL",
    "Stars",
    "Dallas",
    "Pete DeBoer",
    CoachStyle.BALANCED,
    [
        _p("Jason Robertson", 21, "LW", 0.78, 0.65, 0.88, 0.75, 0.88, 0.80, 0.38, 0.82, 25),
        _p("Roope Hintz", 24, "C", 0.85, 0.68, 0.78, 0.78, 0.82, 0.75, 0.48, 0.78, 27),
        _p("Joe Pavelski", 16, "C", 0.68, 0.65, 0.82, 0.68, 0.82, 0.82, 0.42, 0.85, 40),
        _p("Miro Heiskanen", 4, "LD", 0.85, 0.62, 0.78, 0.80, 0.88, 0.82, 0.35, 0.82, 25),
        _p("Esa Lindell", 23, "LD", 0.72, 0.72, 0.65, 0.75, 0.72, 0.72, 0.48, 0.78, 30),
        _p("Jake Oettinger", 29, "G", 0.48, 0.60, 0.72, 0.75, 0.85, 0.75, 0.25, 0.82, 25),
    ],
)

_register(
    "DET",
    "Red Wings",
    "Detroit",
    "Derek Lalonde",
    CoachStyle.BALANCED,
    [
        _p("Dylan Larkin", 71, "C", 0.82, 0.65, 0.78, 0.78, 0.82, 0.78, 0.48, 0.78, 28),
        _p("Lucas Raymond", 23, "RW", 0.80, 0.55, 0.80, 0.72, 0.80, 0.75, 0.35, 0.75, 22),
        _p("Alex DeBrincat", 12, "LW", 0.78, 0.55, 0.82, 0.72, 0.82, 0.75, 0.38, 0.75, 26),
        _p("Moritz Seider", 53, "RD", 0.78, 0.72, 0.68, 0.78, 0.80, 0.78, 0.48, 0.78, 23),
        _p("Ben Chiarot", 8, "LD", 0.70, 0.75, 0.60, 0.72, 0.65, 0.65, 0.55, 0.70, 33),
        _p("Ville Husso", 35, "G", 0.48, 0.58, 0.70, 0.72, 0.78, 0.72, 0.25, 0.75, 29),
    ],
)

_register(
    "EDM",
    "Oilers",
    "Edmonton",
    "Kris Knoblauch",
    CoachStyle.AGGRESSIVE,
    [
        _p("Connor McDavid", 97, "C", 0.95, 0.62, 0.92, 0.82, 0.98, 0.92, 0.42, 0.88, 27),
        _p("Leon Draisaitl", 29, "C", 0.82, 0.72, 0.90, 0.78, 0.92, 0.85, 0.48, 0.85, 28),
        _p("Zach Hyman", 18, "LW", 0.78, 0.68, 0.78, 0.78, 0.78, 0.75, 0.55, 0.78, 32),
        _p("Darnell Nurse", 25, "LD", 0.80, 0.72, 0.65, 0.75, 0.75, 0.72, 0.55, 0.72, 29),
        _p("Evan Bouchard", 2, "RD", 0.78, 0.62, 0.80, 0.72, 0.80, 0.72, 0.38, 0.75, 24),
        _p("Stuart Skinner", 74, "G", 0.48, 0.60, 0.72, 0.75, 0.80, 0.72, 0.25, 0.78, 25),
    ],
)

_register(
    "FLA",
    "Panthers",
    "Florida",
    "Paul Maurice",
    CoachStyle.AGGRESSIVE,
    [
        _p("Aleksander Barkov", 16, "C", 0.82, 0.68, 0.85, 0.80, 0.92, 0.88, 0.42, 0.88, 29),
        _p("Matthew Tkachuk", 19, "LW", 0.78, 0.72, 0.82, 0.75, 0.85, 0.78, 0.68, 0.78, 26),
        _p("Sam Reinhart", 13, "C", 0.78, 0.62, 0.82, 0.75, 0.82, 0.78, 0.38, 0.80, 28),
        _p("Aaron Ekblad", 5, "RD", 0.78, 0.72, 0.70, 0.75, 0.78, 0.75, 0.48, 0.78, 28),
        _p("Gustav Forsling", 42, "LD", 0.80, 0.62, 0.72, 0.78, 0.78, 0.75, 0.38, 0.78, 28),
        _p("Sergei Bobrovsky", 72, "G", 0.48, 0.60, 0.72, 0.72, 0.85, 0.78, 0.28, 0.82, 35),
    ],
)

_register(
    "LA",
    "Kings",
    "Los Angeles",
    "Todd McLellan",
    CoachStyle.BALANCED,
    [
        _p("Anze Kopitar", 11, "C", 0.72, 0.68, 0.80, 0.72, 0.85, 0.85, 0.38, 0.85, 37),
        _p("Adrian Kempe", 9, "LW", 0.82, 0.65, 0.78, 0.75, 0.78, 0.72, 0.45, 0.75, 28),
        _p("Kevin Fiala", 22, "LW", 0.80, 0.58, 0.82, 0.72, 0.82, 0.75, 0.38, 0.72, 28),
        _p("Drew Doughty", 8, "RD", 0.72, 0.72, 0.75, 0.68, 0.80, 0.78, 0.52, 0.78, 34),
        _p("Mikey Anderson", 44, "LD", 0.75, 0.68, 0.62, 0.75, 0.72, 0.72, 0.42, 0.75, 24),
        _p("Cam Talbot", 39, "G", 0.48, 0.58, 0.70, 0.70, 0.78, 0.72, 0.25, 0.78, 37),
    ],
)

_register(
    "MIN",
    "Wild",
    "Minnesota",
    "Dean Evason",
    CoachStyle.DEFENSIVE,
    [
        _p("Kirill Kaprizov", 97, "LW", 0.82, 0.62, 0.88, 0.75, 0.90, 0.80, 0.42, 0.80, 27),
        _p("Matt Boldy", 12, "LW", 0.78, 0.62, 0.80, 0.72, 0.78, 0.72, 0.38, 0.75, 23),
        _p("Joel Eriksson Ek", 14, "C", 0.78, 0.68, 0.72, 0.78, 0.78, 0.75, 0.48, 0.78, 27),
        _p("Jared Spurgeon", 46, "RD", 0.75, 0.65, 0.72, 0.72, 0.78, 0.78, 0.38, 0.80, 34),
        _p("Jonas Brodin", 25, "LD", 0.78, 0.65, 0.65, 0.78, 0.78, 0.78, 0.35, 0.82, 30),
        _p("Marc-Andre Fleury", 29, "G", 0.48, 0.58, 0.72, 0.68, 0.82, 0.75, 0.25, 0.82, 39),
    ],
)

_register(
    "MTL",
    "Canadiens",
    "Montreal",
    "Martin St. Louis",
    CoachStyle.UP_TEMPO,
    [
        _p("Nick Suzuki", 14, "C", 0.80, 0.58, 0.80, 0.75, 0.82, 0.80, 0.38, 0.78, 24),
        _p("Cole Caufield", 22, "RW", 0.80, 0.50, 0.85, 0.72, 0.82, 0.75, 0.38, 0.75, 23),
        _p("Juraj Slafkovsky", 20, "LW", 0.75, 0.72, 0.68, 0.72, 0.72, 0.68, 0.48, 0.70, 20),
        _p("Mike Matheson", 8, "LD", 0.80, 0.65, 0.72, 0.72, 0.75, 0.72, 0.42, 0.72, 30),
        _p("David Savard", 58, "RD", 0.68, 0.72, 0.60, 0.72, 0.65, 0.68, 0.52, 0.72, 33),
        _p("Samuel Montembeault", 35, "G", 0.48, 0.58, 0.70, 0.72, 0.75, 0.70, 0.25, 0.72, 27),
    ],
)

_register(
    "NSH",
    "Predators",
    "Nashville",
    "Andrew Brunette",
    CoachStyle.DEFENSIVE,
    [
        _p("Filip Forsberg", 9, "LW", 0.80, 0.65, 0.85, 0.75, 0.85, 0.78, 0.42, 0.80, 30),
        _p("Ryan O'Reilly", 90, "C", 0.72, 0.68, 0.78, 0.75, 0.82, 0.82, 0.42, 0.82, 33),
        _p("Gustav Nyquist", 14, "RW", 0.75, 0.55, 0.75, 0.72, 0.75, 0.75, 0.35, 0.78, 34),
        _p("Roman Josi", 59, "LD", 0.80, 0.65, 0.82, 0.78, 0.88, 0.82, 0.42, 0.82, 34),
        _p("Alexandre Carrier", 45, "RD", 0.78, 0.65, 0.65, 0.75, 0.72, 0.70, 0.45, 0.72, 27),
        _p("Juuse Saros", 74, "G", 0.48, 0.55, 0.72, 0.78, 0.88, 0.78, 0.25, 0.85, 29),
    ],
)

_register(
    "NJ",
    "Devils",
    "New Jersey",
    "Lindy Ruff",
    CoachStyle.AGGRESSIVE,
    [
        _p("Jack Hughes", 86, "C", 0.90, 0.55, 0.85, 0.75, 0.90, 0.82, 0.42, 0.78, 23),
        _p("Nico Hischier", 13, "C", 0.80, 0.65, 0.78, 0.78, 0.82, 0.78, 0.42, 0.80, 25),
        _p("Jesper Bratt", 63, "LW", 0.82, 0.55, 0.82, 0.72, 0.82, 0.78, 0.35, 0.78, 25),
        _p("Dougie Hamilton", 7, "RD", 0.75, 0.68, 0.80, 0.72, 0.82, 0.78, 0.42, 0.78, 31),
        _p("Jonas Siegenthaler", 71, "LD", 0.75, 0.72, 0.60, 0.75, 0.72, 0.72, 0.42, 0.78, 27),
        _p("Vitek Vanecek", 41, "G", 0.48, 0.58, 0.70, 0.72, 0.78, 0.72, 0.25, 0.75, 28),
    ],
)

_register(
    "NYI",
    "Islanders",
    "New York",
    "Patrick Roy",
    CoachStyle.DEFENSIVE,
    [
        _p("Mathew Barzal", 13, "C", 0.88, 0.58, 0.80, 0.72, 0.85, 0.80, 0.42, 0.78, 27),
        _p("Brock Nelson", 29, "C", 0.75, 0.68, 0.78, 0.72, 0.78, 0.75, 0.42, 0.78, 32),
        _p("Bo Horvat", 14, "C", 0.78, 0.68, 0.78, 0.75, 0.80, 0.78, 0.48, 0.78, 29),
        _p("Ryan Pulock", 6, "RD", 0.72, 0.72, 0.72, 0.72, 0.75, 0.72, 0.45, 0.75, 29),
        _p("Adam Pelech", 3, "LD", 0.75, 0.72, 0.62, 0.78, 0.75, 0.75, 0.42, 0.80, 29),
        _p("Ilya Sorokin", 30, "G", 0.48, 0.60, 0.72, 0.75, 0.88, 0.78, 0.25, 0.85, 29),
    ],
)

_register(
    "NYR",
    "Rangers",
    "New York",
    "Peter Laviolette",
    CoachStyle.AGGRESSIVE,
    [
        _p("Artemi Panarin", 10, "LW", 0.80, 0.58, 0.88, 0.72, 0.90, 0.85, 0.38, 0.82, 32),
        _p("Mika Zibanejad", 93, "C", 0.78, 0.68, 0.85, 0.72, 0.85, 0.80, 0.42, 0.78, 31),
        _p("Chris Kreider", 20, "LW", 0.82, 0.72, 0.78, 0.75, 0.78, 0.72, 0.52, 0.75, 33),
        _p("Adam Fox", 23, "RD", 0.78, 0.60, 0.85, 0.75, 0.90, 0.88, 0.35, 0.85, 26),
        _p("K'Andre Miller", 79, "LD", 0.82, 0.72, 0.65, 0.78, 0.78, 0.72, 0.42, 0.75, 24),
        _p("Igor Shesterkin", 31, "G", 0.50, 0.58, 0.75, 0.78, 0.92, 0.82, 0.25, 0.88, 28),
    ],
)

_register(
    "OTT",
    "Senators",
    "Ottawa",
    "Travis Green",
    CoachStyle.UP_TEMPO,
    [
        _p("Brady Tkachuk", 7, "LW", 0.78, 0.72, 0.78, 0.78, 0.82, 0.75, 0.65, 0.75, 25),
        _p("Tim Stutzle", 18, "C", 0.85, 0.55, 0.82, 0.72, 0.85, 0.78, 0.38, 0.75, 22),
        _p("Claude Giroux", 28, "RW", 0.72, 0.58, 0.80, 0.68, 0.80, 0.82, 0.42, 0.82, 36),
        _p("Thomas Chabot", 72, "LD", 0.82, 0.65, 0.78, 0.72, 0.82, 0.78, 0.42, 0.78, 27),
        _p("Jakob Chychrun", 6, "LD", 0.78, 0.68, 0.72, 0.72, 0.78, 0.72, 0.42, 0.72, 26),
        _p("Joonas Korpisalo", 70, "G", 0.48, 0.58, 0.70, 0.72, 0.75, 0.70, 0.25, 0.72, 30),
    ],
)

_register(
    "PHI",
    "Flyers",
    "Philadelphia",
    "John Tortorella",
    CoachStyle.DEFENSIVE,
    [
        _p("Travis Konecny", 11, "RW", 0.82, 0.62, 0.82, 0.75, 0.82, 0.75, 0.52, 0.75, 27),
        _p("Sean Couturier", 14, "C", 0.72, 0.68, 0.75, 0.72, 0.80, 0.80, 0.42, 0.80, 31),
        _p("Owen Tippett", 74, "RW", 0.80, 0.62, 0.75, 0.72, 0.75, 0.70, 0.45, 0.72, 25),
        _p("Ivan Provorov", 9, "LD", 0.78, 0.68, 0.68, 0.72, 0.75, 0.72, 0.42, 0.72, 27),
        _p("Travis Sanheim", 6, "LD", 0.78, 0.65, 0.70, 0.75, 0.75, 0.72, 0.42, 0.75, 28),
        _p("Carter Hart", 79, "G", 0.48, 0.58, 0.72, 0.72, 0.80, 0.72, 0.25, 0.78, 25),
    ],
)

_register(
    "PIT",
    "Penguins",
    "Pittsburgh",
    "Mike Sullivan",
    CoachStyle.BALANCED,
    [
        _p("Sidney Crosby", 87, "C", 0.78, 0.72, 0.90, 0.75, 0.95, 0.92, 0.42, 0.90, 37),
        _p("Evgeni Malkin", 71, "C", 0.72, 0.72, 0.85, 0.68, 0.88, 0.82, 0.48, 0.78, 38),
        _p("Bryan Rust", 17, "RW", 0.80, 0.65, 0.78, 0.72, 0.78, 0.72, 0.45, 0.75, 32),
        _p("Kris Letang", 58, "RD", 0.78, 0.68, 0.78, 0.68, 0.82, 0.78, 0.45, 0.78, 37),
        _p("Marcus Pettersson", 28, "LD", 0.75, 0.68, 0.65, 0.72, 0.72, 0.72, 0.38, 0.75, 28),
        _p("Tristan Jarry", 35, "G", 0.48, 0.60, 0.72, 0.72, 0.80, 0.72, 0.25, 0.78, 29),
    ],
)

_register(
    "SJ",
    "Sharks",
    "San Jose",
    "David Quinn",
    CoachStyle.BALANCED,
    [
        _p("Tomas Hertl", 48, "C", 0.78, 0.68, 0.78, 0.75, 0.80, 0.75, 0.42, 0.78, 30),
        _p("Logan Couture", 39, "C", 0.72, 0.62, 0.78, 0.68, 0.78, 0.78, 0.42, 0.80, 35),
        _p("Erik Karlsson", 65, "RD", 0.80, 0.58, 0.85, 0.68, 0.88, 0.82, 0.38, 0.78, 34),
        _p("Mario Ferraro", 38, "LD", 0.80, 0.65, 0.62, 0.75, 0.72, 0.72, 0.48, 0.72, 25),
        _p("Fabian Zetterlund", 20, "RW", 0.78, 0.62, 0.72, 0.72, 0.72, 0.68, 0.42, 0.70, 24),
        _p("Mackenzie Blackwood", 29, "G", 0.48, 0.62, 0.72, 0.72, 0.80, 0.72, 0.25, 0.78, 27),
    ],
)

_register(
    "SEA",
    "Kraken",
    "Seattle",
    "Dave Hakstol",
    CoachStyle.BALANCED,
    [
        _p("Matty Beniers", 10, "C", 0.80, 0.58, 0.75, 0.75, 0.78, 0.75, 0.38, 0.72, 21),
        _p("Jared McCann", 19, "C", 0.78, 0.62, 0.80, 0.72, 0.78, 0.72, 0.45, 0.75, 28),
        _p("Jordan Eberle", 7, "RW", 0.75, 0.58, 0.78, 0.68, 0.78, 0.75, 0.35, 0.78, 34),
        _p("Vince Dunn", 29, "LD", 0.80, 0.60, 0.75, 0.72, 0.78, 0.75, 0.38, 0.75, 27),
        _p("Adam Larsson", 6, "RD", 0.72, 0.72, 0.62, 0.72, 0.72, 0.72, 0.48, 0.78, 31),
        _p("Philipp Grubauer", 31, "G", 0.48, 0.58, 0.70, 0.72, 0.78, 0.72, 0.25, 0.75, 32),
    ],
)

_register(
    "STL",
    "Blues",
    "St. Louis",
    "Drew Bannister",
    CoachStyle.BALANCED,
    [
        _p("Robert Thomas", 18, "C", 0.82, 0.58, 0.82, 0.75, 0.85, 0.82, 0.38, 0.78, 25),
        _p("Jordan Kyrou", 25, "RW", 0.85, 0.55, 0.80, 0.72, 0.82, 0.72, 0.38, 0.72, 26),
        _p("Pavel Buchnevich", 89, "LW", 0.78, 0.62, 0.80, 0.72, 0.80, 0.78, 0.38, 0.78, 29),
        _p("Colton Parayko", 55, "RD", 0.78, 0.75, 0.72, 0.72, 0.75, 0.72, 0.45, 0.72, 31),
        _p("Torey Krug", 47, "LD", 0.75, 0.58, 0.78, 0.68, 0.78, 0.78, 0.38, 0.75, 33),
        _p("Jordan Binnington", 50, "G", 0.48, 0.60, 0.72, 0.72, 0.80, 0.72, 0.42, 0.75, 31),
    ],
)

_register(
    "TB",
    "Lightning",
    "Tampa Bay",
    "Jon Cooper",
    CoachStyle.AGGRESSIVE,
    [
        _p("Nikita Kucherov", 86, "RW", 0.80, 0.60, 0.92, 0.72, 0.92, 0.88, 0.38, 0.85, 31),
        _p("Brayden Point", 21, "C", 0.82, 0.62, 0.85, 0.75, 0.88, 0.82, 0.45, 0.82, 28),
        _p("Steven Stamkos", 91, "C", 0.75, 0.68, 0.85, 0.68, 0.85, 0.80, 0.42, 0.82, 34),
        _p("Victor Hedman", 77, "LD", 0.78, 0.75, 0.78, 0.75, 0.88, 0.82, 0.42, 0.82, 33),
        _p("Erik Cernak", 81, "RD", 0.75, 0.75, 0.62, 0.75, 0.72, 0.72, 0.52, 0.75, 27),
        _p("Andrei Vasilevskiy", 88, "G", 0.48, 0.62, 0.75, 0.78, 0.90, 0.82, 0.25, 0.88, 30),
    ],
)

_register(
    "TOR",
    "Maple Leafs",
    "Toronto",
    "Sheldon Keefe",
    CoachStyle.UP_TEMPO,
    [
        _p("Auston Matthews", 34, "C", 0.85, 0.72, 0.92, 0.78, 0.95, 0.85, 0.42, 0.82, 27),
        _p("Mitch Marner", 16, "RW", 0.82, 0.55, 0.85, 0.75, 0.90, 0.88, 0.32, 0.82, 27),
        _p("William Nylander", 88, "RW", 0.82, 0.58, 0.82, 0.72, 0.85, 0.78, 0.35, 0.78, 28),
        _p("Morgan Rielly", 44, "LD", 0.80, 0.60, 0.78, 0.72, 0.82, 0.78, 0.38, 0.78, 30),
        _p("TJ Brodie", 78, "RD", 0.72, 0.65, 0.68, 0.72, 0.75, 0.78, 0.35, 0.80, 34),
        _p("Ilya Samsonov", 35, "G", 0.48, 0.60, 0.72, 0.72, 0.78, 0.72, 0.25, 0.75, 27),
    ],
)

_register(
    "VAN",
    "Canucks",
    "Vancouver",
    "Rick Tocchet",
    CoachStyle.AGGRESSIVE,
    [
        _p("Elias Pettersson", 40, "C", 0.82, 0.62, 0.88, 0.75, 0.90, 0.85, 0.38, 0.82, 25),
        _p("J.T. Miller", 9, "C", 0.78, 0.68, 0.80, 0.72, 0.82, 0.78, 0.52, 0.75, 31),
        _p("Brock Boeser", 6, "RW", 0.75, 0.62, 0.82, 0.70, 0.78, 0.72, 0.38, 0.75, 27),
        _p("Quinn Hughes", 43, "LD", 0.85, 0.55, 0.85, 0.75, 0.90, 0.88, 0.32, 0.82, 24),
        _p("Filip Hronek", 17, "RD", 0.78, 0.65, 0.72, 0.72, 0.78, 0.72, 0.42, 0.75, 27),
        _p("Thatcher Demko", 35, "G", 0.48, 0.60, 0.72, 0.75, 0.85, 0.78, 0.25, 0.82, 28),
    ],
)

_register(
    "VGK",
    "Golden Knights",
    "Vegas",
    "Bruce Cassidy",
    CoachStyle.AGGRESSIVE,
    [
        _p("Jack Eichel", 9, "C", 0.82, 0.68, 0.88, 0.75, 0.88, 0.82, 0.45, 0.80, 27),
        _p("Mark Stone", 61, "RW", 0.75, 0.65, 0.82, 0.72, 0.85, 0.85, 0.48, 0.82, 32),
        _p("Jonathan Marchessault", 81, "LW", 0.78, 0.58, 0.80, 0.72, 0.78, 0.75, 0.42, 0.78, 33),
        _p("Alex Pietrangelo", 7, "RD", 0.75, 0.72, 0.75, 0.72, 0.82, 0.80, 0.42, 0.82, 34),
        _p("Shea Theodore", 27, "LD", 0.80, 0.62, 0.78, 0.72, 0.80, 0.78, 0.38, 0.78, 29),
        _p("Logan Thompson", 36, "G", 0.48, 0.60, 0.72, 0.72, 0.82, 0.75, 0.25, 0.80, 27),
    ],
)

_register(
    "WSH",
    "Capitals",
    "Washington",
    "Spencer Carbery",
    CoachStyle.BALANCED,
    [
        _p("Alex Ovechkin", 8, "LW", 0.70, 0.78, 0.90, 0.65, 0.88, 0.75, 0.55, 0.80, 38),
        _p("Dylan Strome", 17, "C", 0.78, 0.60, 0.80, 0.72, 0.80, 0.78, 0.38, 0.75, 27),
        _p("Tom Wilson", 43, "RW", 0.78, 0.78, 0.68, 0.75, 0.72, 0.65, 0.72, 0.72, 30),
        _p("John Carlson", 74, "RD", 0.72, 0.65, 0.80, 0.68, 0.80, 0.78, 0.38, 0.78, 34),
        _p("Dmitry Orlov", 9, "LD", 0.75, 0.68, 0.68, 0.72, 0.75, 0.72, 0.45, 0.75, 32),
        _p("Charlie Lindgren", 79, "G", 0.48, 0.58, 0.70, 0.72, 0.78, 0.72, 0.25, 0.75, 30),
    ],
)

_register(
    "WPG",
    "Jets",
    "Winnipeg",
    "Rick Bowness",
    CoachStyle.BALANCED,
    [
        _p("Kyle Connor", 81, "LW", 0.82, 0.62, 0.85, 0.75, 0.85, 0.78, 0.38, 0.78, 27),
        _p("Mark Scheifele", 55, "C", 0.78, 0.68, 0.82, 0.72, 0.85, 0.80, 0.42, 0.78, 31),
        _p("Nikolaj Ehlers", 27, "LW", 0.85, 0.55, 0.82, 0.72, 0.82, 0.75, 0.35, 0.75, 28),
        _p("Josh Morrissey", 44, "LD", 0.78, 0.68, 0.78, 0.75, 0.82, 0.78, 0.42, 0.78, 29),
        _p("Neal Pionk", 4, "RD", 0.75, 0.65, 0.72, 0.72, 0.72, 0.72, 0.45, 0.72, 28),
        _p("Connor Hellebuyck", 37, "G", 0.48, 0.62, 0.75, 0.78, 0.90, 0.80, 0.25, 0.88, 31),
    ],
)


def get_nhl_team(abbr: str) -> Team | None:
    return _TEAMS.get(abbr.upper())


def get_all_nhl_teams() -> dict[str, Team]:
    return dict(_TEAMS)
