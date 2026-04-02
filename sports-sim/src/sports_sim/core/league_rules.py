"""League-specific rules — overtime formats, substitution limits, and other
rule variations that differ across leagues within the same sport.

Usage:
    rules = get_league_rules("soccer", "epl")
    if rules.max_substitutions is not None:
        enforce_sub_limit(rules.max_substitutions)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LeagueRules:
    """Immutable rule set for a league."""

    league: str
    sport: str

    # Period / game structure
    periods: int | None = None
    period_length_minutes: float | None = None
    overtime_format: str | None = None        # "golden_goal", "full_period", "shootout", "sudden_death", etc.
    overtime_periods: int | None = None
    overtime_length_minutes: float | None = None

    # Substitutions
    max_substitutions: int | None = None
    sub_windows: int | None = None            # e.g. 3 windows in soccer (excl. halftime)
    concussion_sub: bool = False              # extra sub for head injuries

    # Cards / fouls
    yellow_card_suspension_threshold: int | None = None  # accumulation for suspension
    technical_foul_ejection: int | None = None

    # Roster
    max_roster_size: int | None = None
    max_active_roster: int | None = None

    # Timing
    has_stoppage_time: bool = False
    has_shot_clock: bool = False
    shot_clock_seconds: float | None = None
    has_play_clock: bool = False
    play_clock_seconds: float | None = None

    # Tie-breaking
    allows_draws: bool = True
    has_shootout: bool = False
    has_penalty_kicks: bool = False

    # Misc
    dh_rule: bool = False                     # baseball designated hitter
    two_line_pass: bool = False               # hockey
    three_point_line: bool = True             # basketball


# ---------------------------------------------------------------------------
# Built-in league rule sets
# ---------------------------------------------------------------------------

_RULES: dict[tuple[str, str], LeagueRules] = {}


def _register(rules: LeagueRules) -> None:
    _RULES[(rules.sport, rules.league.lower())] = rules


# ── Soccer ──
_register(LeagueRules(
    league="EPL", sport="soccer",
    periods=2, period_length_minutes=45.0,
    max_substitutions=5, sub_windows=3, concussion_sub=True,
    overtime_format="full_period", overtime_periods=2, overtime_length_minutes=15.0,
    has_stoppage_time=True, allows_draws=True,
    yellow_card_suspension_threshold=5,
    max_roster_size=25, max_active_roster=18,
))

_register(LeagueRules(
    league="MLS", sport="soccer",
    periods=2, period_length_minutes=45.0,
    max_substitutions=5, sub_windows=3, concussion_sub=True,
    overtime_format="shootout", has_shootout=True,
    has_stoppage_time=True, allows_draws=True,
    max_roster_size=30, max_active_roster=18,
))

_register(LeagueRules(
    league="LaLiga", sport="soccer",
    periods=2, period_length_minutes=45.0,
    max_substitutions=5, sub_windows=3, concussion_sub=True,
    overtime_format="full_period", overtime_periods=2, overtime_length_minutes=15.0,
    has_stoppage_time=True, allows_draws=True,
    yellow_card_suspension_threshold=5,
))

# ── Basketball ──
_register(LeagueRules(
    league="NBA", sport="basketball",
    periods=4, period_length_minutes=12.0,
    overtime_format="full_period", overtime_length_minutes=5.0,
    allows_draws=False, has_shot_clock=True, shot_clock_seconds=24.0,
    max_roster_size=17, max_active_roster=13,
    technical_foul_ejection=2,
))

_register(LeagueRules(
    league="NCAA", sport="basketball",
    periods=2, period_length_minutes=20.0,
    overtime_format="full_period", overtime_length_minutes=5.0,
    allows_draws=False, has_shot_clock=True, shot_clock_seconds=30.0,
))

# ── Football ──
_register(LeagueRules(
    league="NFL", sport="football",
    periods=4, period_length_minutes=15.0,
    overtime_format="sudden_death", overtime_length_minutes=10.0,
    allows_draws=True,  # regular season can end in tie
    has_play_clock=True, play_clock_seconds=40.0,
    max_roster_size=53, max_active_roster=46,
))

# ── Hockey ──
_register(LeagueRules(
    league="NHL", sport="hockey",
    periods=3, period_length_minutes=20.0,
    overtime_format="sudden_death", overtime_length_minutes=5.0,
    has_shootout=True, allows_draws=False,
    max_roster_size=23, max_active_roster=20,
))

# ── Baseball ──
_register(LeagueRules(
    league="MLB", sport="baseball",
    periods=9, period_length_minutes=0,  # innings, not timed
    overtime_format="extra_innings",
    allows_draws=False, dh_rule=True,
    max_roster_size=40, max_active_roster=26,
))

# ── Cricket ──
_register(LeagueRules(
    league="IPL", sport="cricket",
    periods=2, period_length_minutes=0,  # over-based
    max_substitutions=0,  # no subs in cricket
    allows_draws=False,
))

# ── Tennis ──
_register(LeagueRules(
    league="ATP", sport="tennis",
    periods=5,  # sets (Grand Slam)
    allows_draws=False,
    max_substitutions=0,
))

_register(LeagueRules(
    league="WTA", sport="tennis",
    periods=3,  # sets
    allows_draws=False,
    max_substitutions=0,
))

# ── Boxing ──
_register(LeagueRules(
    league="WBC", sport="boxing",
    periods=12,  # rounds
    period_length_minutes=3.0,
    allows_draws=True,
    max_substitutions=0,
))

# ── MMA ──
_register(LeagueRules(
    league="UFC", sport="mma",
    periods=3,  # rounds (5 for title fights)
    period_length_minutes=5.0,
    allows_draws=True,
    max_substitutions=0,
))

# ── Racing ──
_register(LeagueRules(
    league="F1", sport="racing",
    allows_draws=False,
    max_substitutions=0,
))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_league_rules(sport: str, league: str | None) -> LeagueRules | None:
    """Look up rules for a sport/league combination. Returns None if not found."""
    if not league:
        return None
    return _RULES.get((sport, league.lower()))


def list_leagues(sport: str | None = None) -> list[str]:
    """Return known league names, optionally filtered by sport."""
    if sport:
        return [r.league for k, r in _RULES.items() if k[0] == sport]
    return [r.league for r in _RULES.values()]


def all_rules() -> dict[tuple[str, str], LeagueRules]:
    """Return the full rules registry (read-only view)."""
    return dict(_RULES)
