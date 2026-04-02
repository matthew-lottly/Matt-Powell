"""Roster validation utilities.

Validates team rosters against sport-specific rules before simulation starts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sports_sim.core.models import Player, SportType, Team
from sports_sim.core.sport_capabilities import SPORT_CAPABILITIES

logger = logging.getLogger(__name__)


@dataclass
class RosterIssue:
    """A single roster validation finding."""

    team: str
    severity: str  # "error" | "warning"
    message: str


# ---------------------------------------------------------------------------
# Position requirements per sport (minimum counts)
# ---------------------------------------------------------------------------

POSITION_REQUIREMENTS: dict[SportType, dict[str, int]] = {
    SportType.HOCKEY: {"G": 1, "LD": 1, "RD": 1, "C": 1},
    SportType.SOCCER: {"GK": 1},
    SportType.BASEBALL: {"P": 1, "C": 1},
    SportType.FOOTBALL: {"QB": 1},
    SportType.BASKETBALL: {},  # no strict position minimums
    SportType.TENNIS: {},
    SportType.GOLF: {},
    SportType.CRICKET: {},
    SportType.BOXING: {},
    SportType.MMA: {},
    SportType.RACING: {},
}

# Valid positions per sport
VALID_POSITIONS: dict[SportType, set[str]] = {
    SportType.SOCCER: {"GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LW", "RW", "LM", "RM", "CF", "ST", "DEF", "MID", "FWD", "SUB"},
    SportType.BASKETBALL: {"PG", "SG", "SF", "PF", "C", "G", "F", "SUB"},
    SportType.BASEBALL: {"P", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH", "SP", "RP", "CL", "PH"},
    SportType.FOOTBALL: {"QB", "RB", "WR", "TE", "OL", "OT", "OG", "C", "DL", "DE", "DT", "LB", "ILB", "OLB", "CB", "S", "FS", "SS", "K", "P", "KR", "PR", "SUB"},
    SportType.HOCKEY: {"G", "D", "C", "LW", "RW", "LD", "RD", "F", "SUB"},
    SportType.TENNIS: {"P", "SNG", "DBL"},
    SportType.GOLF: {"P", "G"},
    SportType.CRICKET: {"BAT", "BOWL", "AR", "WK", "ALL", "FIELD", "SUB"},
    SportType.BOXING: {"F", "BOX"},
    SportType.MMA: {"F", "MMA"},
    SportType.RACING: {"D", "DRV"},
}


def validate_roster(team: Team, sport: SportType) -> list[RosterIssue]:
    """Validate a team's roster for a given sport.

    Returns a list of issues found (empty = valid).
    """
    issues: list[RosterIssue] = []
    caps = SPORT_CAPABILITIES.get(sport)

    # --- Roster size ---
    if caps:
        expected = caps.players_per_side
        actual = len(team.players)
        if actual != expected:
            issues.append(RosterIssue(
                team=team.name,
                severity="warning",
                message=f"Expected {expected} starters, found {actual}",
            ))

    # --- Duplicate jersey numbers ---
    all_players = team.players + team.bench
    numbers = [p.number for p in all_players]
    seen_numbers: set[int] = set()
    for n in numbers:
        if n in seen_numbers:
            issues.append(RosterIssue(
                team=team.name,
                severity="warning",
                message=f"Duplicate jersey number: {n}",
            ))
        seen_numbers.add(n)

    # --- Position validation ---
    valid_pos = VALID_POSITIONS.get(sport, set())
    if valid_pos:
        for p in all_players:
            pos = p.position.upper().strip()
            if pos and pos not in valid_pos:
                issues.append(RosterIssue(
                    team=team.name,
                    severity="warning",
                    message=f"Unknown position '{p.position}' for {p.name} in {sport.value}",
                ))

    # --- Position composition requirements ---
    reqs = POSITION_REQUIREMENTS.get(sport, {})
    for pos_needed, min_count in reqs.items():
        count = sum(1 for p in team.players if p.position.upper().strip() == pos_needed)
        if count < min_count:
            issues.append(RosterIssue(
                team=team.name,
                severity="error",
                message=f"Need at least {min_count} {pos_needed} in starters, found {count}",
            ))

    # --- Attribute range sanity ---
    for p in all_players:
        attrs = p.attributes
        for attr_name in ["speed", "strength", "accuracy", "endurance", "skill",
                          "decision_making", "aggression", "composure", "awareness",
                          "leadership", "clutch", "durability"]:
            val = getattr(attrs, attr_name, None)
            if val is not None and (val < 0.0 or val > 1.0):
                issues.append(RosterIssue(
                    team=team.name,
                    severity="error",
                    message=f"{p.name} has {attr_name}={val:.2f} (must be 0.0-1.0)",
                ))

    # --- Player number range ---
    for p in all_players:
        if p.number < 0 or p.number > 99:
            issues.append(RosterIssue(
                team=team.name,
                severity="warning",
                message=f"{p.name} has jersey number {p.number} (expected 0-99)",
            ))

    # --- Age sanity ---
    for p in all_players:
        if p.age < 16 or p.age > 50:
            issues.append(RosterIssue(
                team=team.name,
                severity="warning",
                message=f"{p.name} has age {p.age} (expected 16-50)",
            ))

    return issues


def validate_matchup(home: Team, away: Team, sport: SportType) -> list[RosterIssue]:
    """Validate both teams' rosters for a simulation matchup."""
    issues = validate_roster(home, sport)
    issues.extend(validate_roster(away, sport))
    return issues


def log_roster_issues(issues: list[RosterIssue]) -> None:
    """Log any roster validation issues."""
    for issue in issues:
        if issue.severity == "error":
            logger.error("Roster [%s]: %s", issue.team, issue.message)
        else:
            logger.warning("Roster [%s]: %s", issue.team, issue.message)
