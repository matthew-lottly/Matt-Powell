"""NBA team rosters — representative cores with fuller rotation depth."""

from __future__ import annotations

from statistics import mean

from sports_sim.core.models import Coach, CoachStyle, Player, PlayerAttributes, Team
from sports_sim.data.venues import NBA_VENUES

_DEPTH_FIRST = [
    "Malik",
    "Tyus",
    "Immanuel",
    "Payton",
    "DeAndre",
    "Cam",
    "Dorian",
    "Tari",
    "Jalen",
    "Nickeil",
    "Sam",
    "Naz",
    "Cole",
    "Terance",
    "Royce",
    "Caris",
]

_DEPTH_LAST = [
    "Reed",
    "Martin",
    "Walker",
    "Daniels",
    "Mann",
    "Porter",
    "Jones",
    "Murphy",
    "Smith",
    "Brooks",
    "House",
    "Ellis",
    "O'Neal",
    "Braun",
    "Hardy",
    "Watford",
]

_DEPTH_BLUEPRINTS: list[tuple[str, str, float]] = [
    ("PG", "second-unit organizer", 0.93),
    ("SG", "bench scorer", 0.92),
    ("SF", "3-and-D wing", 0.92),
    ("PF", "stretch forward", 0.9),
    ("C", "backup rim protector", 0.91),
    ("SG", "microwave guard", 0.9),
    ("SF", "slashing wing", 0.89),
    ("PF", "glass-cleaning big", 0.88),
]


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return round(max(lo, min(hi, value)), 3)


def _avg(values: list[float]) -> float:
    return float(mean(values)) if values else 0.5


def _slug(seed: str) -> int:
    return sum(ord(char) for char in seed)


def _player_value(player: Player) -> float:
    attrs = player.attributes
    return _clamp(
        attrs.skill * 0.24
        + attrs.accuracy * 0.2
        + attrs.decision_making * 0.16
        + attrs.awareness * 0.12
        + attrs.composure * 0.1
        + attrs.clutch * 0.1
        + attrs.speed * 0.05
        + attrs.strength * 0.03,
    )


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
    aware: float = 0.6,
    lead: float = 0.5,
    clutch: float = 0.5,
    dur: float = 0.7,
    age: int = 26,
    ht: int = 198,
    wt: int = 100,
) -> Player:
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
            awareness=aware,
            leadership=lead,
            clutch=clutch,
            durability=dur,
        ),
    )


def _template_for_position(roster: list[Player], position: str) -> Player:
    candidates = [player for player in roster if player.position == position]
    if not candidates and position in {"PG", "SG"}:
        candidates = [player for player in roster if player.position in {"PG", "SG"}]
    if not candidates and position in {"SF", "PF"}:
        candidates = [player for player in roster if player.position in {"SF", "PF"}]
    if not candidates and position == "C":
        candidates = [player for player in roster if player.position in {"PF", "C"}]
    if not candidates:
        candidates = roster
    return max(candidates, key=_player_value)


def _depth_name(abbr: str, index: int) -> str:
    seed = _slug(abbr) + index * 13
    first = _DEPTH_FIRST[seed % len(_DEPTH_FIRST)]
    last = _DEPTH_LAST[(seed // 5) % len(_DEPTH_LAST)]
    return f"{first} {last}"


def _depth_player(abbr: str, roster: list[Player], index: int, position: str, role: str, factor: float) -> Player:
    template = _template_for_position(roster, position)
    attrs = template.attributes
    role_boost = 0.02 if "scorer" in role or "stretch" in role else 0.0
    defense_boost = 0.02 if "3-and-D" in role or "rim" in role or "glass" in role else 0.0
    playmaking_boost = 0.02 if "organizer" in role else 0.0

    adjusted = PlayerAttributes(
        speed=_clamp(attrs.speed * factor + (0.01 if position in {"PG", "SG"} else 0.0)),
        strength=_clamp(attrs.strength * factor + defense_boost),
        accuracy=_clamp(attrs.accuracy * factor + role_boost),
        endurance=_clamp(attrs.endurance * min(1.0, factor + 0.03)),
        skill=_clamp(attrs.skill * factor + role_boost),
        decision_making=_clamp(attrs.decision_making * factor + playmaking_boost),
        aggression=_clamp(attrs.aggression * factor),
        composure=_clamp(attrs.composure * factor + role_boost * 0.5),
        awareness=_clamp(attrs.awareness * factor + defense_boost),
        leadership=_clamp(attrs.leadership * factor),
        clutch=_clamp(attrs.clutch * factor + role_boost),
        durability=_clamp(attrs.durability * min(1.0, factor + 0.04)),
    )

    age_offset = ((index + _slug(abbr)) % 5) - 2
    height_offset = ((index * 2) % 7) - 3
    weight_offset = ((index * 4) % 9) - 4
    return Player(
        name=_depth_name(abbr, index),
        number=20 + index,
        position=position,
        age=max(21, template.age + age_offset),
        height_cm=template.height_cm + height_offset,
        weight_kg=max(82, template.weight_kg + weight_offset),
        attributes=adjusted,
    )


def _build_bench(abbr: str, players: list[Player], existing: list[Player] | None) -> list[Player]:
    bench = list(existing or [])
    for index, (position, role, factor) in enumerate(_DEPTH_BLUEPRINTS[len(bench) :], start=len(bench) + 1):
        bench.append(_depth_player(abbr, players + bench, index, position, role, factor))
    return bench


def _team_strengths(players: list[Player], bench: list[Player]) -> tuple[float, float, float, float]:
    offense = _clamp(
        _avg(
            [
                _player_value(player) * 0.45
                + player.attributes.accuracy * 0.22
                + player.attributes.skill * 0.18
                + player.attributes.decision_making * 0.1
                + player.attributes.clutch * 0.05
                for player in players
            ]
        )
    )
    defense = _clamp(
        _avg(
            [
                _player_value(player) * 0.32
                + player.attributes.awareness * 0.22
                + player.attributes.strength * 0.16
                + player.attributes.decision_making * 0.14
                + player.attributes.durability * 0.08
                + min(player.height_cm / 230.0, 1.0) * 0.08
                for player in players
            ]
        )
    )
    late_game = _clamp(
        _avg(
            [
                player.attributes.clutch * 0.34
                + player.attributes.decision_making * 0.24
                + player.attributes.leadership * 0.22
                + player.attributes.composure * 0.2
                for player in players
            ]
        )
    )
    depth = _clamp(_avg([_player_value(player) for player in bench]))
    return offense, defense, late_game, depth


def _nba_team(
    name: str,
    city: str,
    abbr: str,
    coach_name: str,
    coach_style: CoachStyle,
    players: list[Player],
    bench: list[Player] | None = None,
) -> Team:
    venue = NBA_VENUES.get(abbr)
    full_bench = _build_bench(abbr, players, bench)
    offense, defense, late_game, depth = _team_strengths(players, full_bench)
    return Team(
        name=name,
        city=city,
        abbreviation=abbr,
        players=players,
        bench=full_bench,
        formation="standard",
        coach=Coach(
            name=coach_name,
            style=coach_style,
            play_calling=0.7,
            motivation=0.7,
            adaptability=0.65,
            clock_management=0.65,
        ),
        venue=venue or NBA_VENUES["LAL"],
        timeouts_remaining=7,
        overall_offense=offense,
        overall_defense=defense,
        overall_special_teams=late_game,
        depth_rating=depth,
    )


# ── BOS Celtics ──
BOS = _nba_team(
    "Celtics",
    "Boston",
    "BOS",
    "Joe Mazzulla",
    CoachStyle.BALANCED,
    [
        _p("Jrue Holiday", 4, "PG", 0.78, 0.68, 0.78, 0.75, 0.85, 0.85, 0.45, 0.82, 0.82, 0.8, 0.78, 0.78, 34, 191, 93),
        _p(
            "Derrick White",
            9,
            "SG",
            0.80,
            0.65,
            0.78,
            0.78,
            0.82,
            0.80,
            0.42,
            0.80,
            0.80,
            0.72,
            0.72,
            0.78,
            30,
            193,
            86,
        ),
        _p(
            "Jayson Tatum", 0, "SF", 0.82, 0.75, 0.85, 0.78, 0.92, 0.82, 0.42, 0.82, 0.82, 0.82, 0.85, 0.78, 26, 203, 95
        ),
        _p(
            "Jaylen Brown",
            7,
            "PF",
            0.85,
            0.78,
            0.78,
            0.80,
            0.88,
            0.78,
            0.48,
            0.78,
            0.78,
            0.72,
            0.75,
            0.78,
            28,
            198,
            100,
        ),
        _p(
            "Kristaps Porzingis",
            8,
            "C",
            0.68,
            0.75,
            0.82,
            0.65,
            0.85,
            0.72,
            0.38,
            0.75,
            0.72,
            0.65,
            0.68,
            0.55,
            28,
            221,
            109,
        ),
    ],
    bench=[
        _p("Al Horford", 42, "C", 0.60, 0.72, 0.72, 0.68, 0.78, 0.80, 0.35, 0.82, 0.82, 0.82, 0.78, 0.72, 38, 206, 109),
        _p(
            "Payton Pritchard",
            11,
            "PG",
            0.78,
            0.55,
            0.80,
            0.72,
            0.75,
            0.72,
            0.42,
            0.75,
            0.72,
            0.6,
            0.65,
            0.75,
            26,
            185,
            86,
        ),
    ],
)

# ── DEN Nuggets ──
DEN = _nba_team(
    "Nuggets",
    "Denver",
    "DEN",
    "Michael Malone",
    CoachStyle.BALANCED,
    [
        _p(
            "Jamal Murray",
            27,
            "PG",
            0.80,
            0.62,
            0.82,
            0.72,
            0.85,
            0.80,
            0.40,
            0.80,
            0.78,
            0.72,
            0.88,
            0.68,
            27,
            193,
            97,
        ),
        _p(
            "Kentavious Caldwell-Pope",
            5,
            "SG",
            0.78,
            0.62,
            0.78,
            0.75,
            0.78,
            0.75,
            0.42,
            0.78,
            0.78,
            0.68,
            0.65,
            0.78,
            31,
            196,
            93,
        ),
        _p(
            "Michael Porter Jr.",
            1,
            "SF",
            0.75,
            0.68,
            0.85,
            0.70,
            0.82,
            0.68,
            0.35,
            0.72,
            0.68,
            0.58,
            0.62,
            0.62,
            26,
            208,
            97,
        ),
        _p(
            "Aaron Gordon",
            50,
            "PF",
            0.82,
            0.82,
            0.68,
            0.78,
            0.78,
            0.72,
            0.50,
            0.75,
            0.72,
            0.62,
            0.58,
            0.78,
            28,
            203,
            100,
        ),
        _p(
            "Nikola Jokic",
            15,
            "C",
            0.55,
            0.80,
            0.88,
            0.72,
            0.95,
            0.95,
            0.35,
            0.92,
            0.92,
            0.92,
            0.88,
            0.78,
            29,
            211,
            129,
        ),
    ],
)

# ── MIL Bucks ──
MIL = _nba_team(
    "Bucks",
    "Milwaukee",
    "MIL",
    "Doc Rivers",
    CoachStyle.AGGRESSIVE,
    [
        _p(
            "Damian Lillard",
            0,
            "PG",
            0.82,
            0.60,
            0.88,
            0.75,
            0.90,
            0.85,
            0.42,
            0.85,
            0.82,
            0.82,
            0.92,
            0.72,
            34,
            188,
            88,
        ),
        _p(
            "Khris Middleton",
            22,
            "SG",
            0.72,
            0.65,
            0.85,
            0.68,
            0.85,
            0.78,
            0.38,
            0.82,
            0.80,
            0.72,
            0.78,
            0.62,
            33,
            201,
            100,
        ),
        _p(
            "Bobby Portis",
            9,
            "SF",
            0.72,
            0.78,
            0.72,
            0.72,
            0.75,
            0.68,
            0.62,
            0.68,
            0.68,
            0.58,
            0.62,
            0.72,
            29,
            208,
            113,
        ),
        _p(
            "Giannis Antetokounmpo",
            34,
            "PF",
            0.90,
            0.92,
            0.68,
            0.85,
            0.92,
            0.78,
            0.55,
            0.78,
            0.78,
            0.78,
            0.82,
            0.75,
            29,
            211,
            110,
        ),
        _p(
            "Brook Lopez", 11, "C", 0.55, 0.80, 0.78, 0.68, 0.82, 0.72, 0.42, 0.78, 0.75, 0.72, 0.65, 0.72, 36, 213, 127
        ),
    ],
)

# ── GSW Warriors ──
GSW = _nba_team(
    "Warriors",
    "Golden State",
    "GSW",
    "Steve Kerr",
    CoachStyle.UP_TEMPO,
    [
        _p(
            "Stephen Curry",
            30,
            "PG",
            0.80,
            0.55,
            0.95,
            0.75,
            0.95,
            0.90,
            0.35,
            0.88,
            0.88,
            0.88,
            0.95,
            0.72,
            36,
            188,
            84,
        ),
        _p(
            "Klay Thompson",
            11,
            "SG",
            0.72,
            0.62,
            0.90,
            0.68,
            0.85,
            0.75,
            0.38,
            0.82,
            0.80,
            0.72,
            0.82,
            0.62,
            34,
            198,
            97,
        ),
        _p(
            "Andrew Wiggins",
            22,
            "SF",
            0.82,
            0.72,
            0.75,
            0.72,
            0.78,
            0.68,
            0.42,
            0.72,
            0.68,
            0.58,
            0.62,
            0.72,
            29,
            201,
            88,
        ),
        _p(
            "Draymond Green",
            23,
            "PF",
            0.72,
            0.78,
            0.55,
            0.72,
            0.82,
            0.88,
            0.72,
            0.68,
            0.85,
            0.88,
            0.78,
            0.72,
            34,
            198,
            104,
        ),
        _p(
            "Kevon Looney", 5, "C", 0.60, 0.75, 0.52, 0.72, 0.72, 0.72, 0.42, 0.75, 0.72, 0.65, 0.55, 0.78, 28, 206, 100
        ),
    ],
)

# ── LAL Lakers ──
LAL = _nba_team(
    "Lakers",
    "Los Angeles",
    "LAL",
    "JJ Redick",
    CoachStyle.BALANCED,
    [
        _p(
            "D'Angelo Russell",
            1,
            "PG",
            0.75,
            0.55,
            0.80,
            0.68,
            0.80,
            0.75,
            0.38,
            0.72,
            0.72,
            0.68,
            0.68,
            0.72,
            28,
            193,
            88,
        ),
        _p(
            "Austin Reaves",
            15,
            "SG",
            0.78,
            0.62,
            0.78,
            0.75,
            0.78,
            0.75,
            0.42,
            0.78,
            0.75,
            0.65,
            0.68,
            0.75,
            26,
            196,
            88,
        ),
        _p(
            "LeBron James",
            23,
            "SF",
            0.80,
            0.85,
            0.82,
            0.78,
            0.92,
            0.92,
            0.48,
            0.88,
            0.90,
            0.92,
            0.90,
            0.72,
            39,
            206,
            113,
        ),
        _p(
            "Rui Hachimura",
            28,
            "PF",
            0.75,
            0.78,
            0.72,
            0.72,
            0.75,
            0.68,
            0.42,
            0.72,
            0.68,
            0.58,
            0.55,
            0.72,
            26,
            203,
            104,
        ),
        _p(
            "Anthony Davis",
            3,
            "C",
            0.78,
            0.82,
            0.78,
            0.72,
            0.90,
            0.78,
            0.45,
            0.78,
            0.78,
            0.75,
            0.78,
            0.58,
            31,
            208,
            116,
        ),
    ],
)


def get_all_nba_teams() -> dict[str, Team]:
    return {"BOS": BOS, "DEN": DEN, "MIL": MIL, "GSW": GSW, "LAL": LAL}


def get_nba_team(abbr: str) -> Team | None:
    return get_all_nba_teams().get(abbr)
