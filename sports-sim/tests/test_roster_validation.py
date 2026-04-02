"""Tests for roster validation module."""

from __future__ import annotations

import pytest

from sports_sim.core.models import Player, PlayerAttributes, SportType, Team
from sports_sim.core.roster_validation import validate_roster, validate_matchup


def _player(name: str = "Test Player", number: int = 10, position: str = "GK", **kwargs) -> Player:
    return Player(name=name, number=number, position=position, **kwargs)


def _team(name: str = "Test FC", players: list[Player] | None = None, bench: list[Player] | None = None) -> Team:
    return Team(
        name=name,
        abbreviation="TST",
        city="Test City",
        players=players or [],
        bench=bench or [],
    )


class TestSoccerValidation:
    def test_valid_11_player_roster(self):
        players = [
            _player("GK", 1, "GK"),
            *[_player(f"P{i}", i + 1, "CM") for i in range(10)],
        ]
        team = _team(players=players)
        issues = validate_roster(team, SportType.SOCCER)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_wrong_roster_size_warns(self):
        players = [_player(f"P{i}", i + 1, "CM") for i in range(5)]
        team = _team(players=players)
        issues = validate_roster(team, SportType.SOCCER)
        size_issues = [i for i in issues if "starters" in i.message.lower()]
        assert len(size_issues) > 0

    def test_missing_goalkeeper_errors(self):
        players = [_player(f"P{i}", i + 1, "CM") for i in range(11)]
        team = _team(players=players)
        issues = validate_roster(team, SportType.SOCCER)
        gk_issues = [i for i in issues if "GK" in i.message]
        assert len(gk_issues) > 0

    def test_duplicate_numbers_warn(self):
        players = [
            _player("GK", 1, "GK"),
            _player("P1", 1, "CM"),  # duplicate
            *[_player(f"P{i}", i + 2, "CM") for i in range(9)],
        ]
        team = _team(players=players)
        issues = validate_roster(team, SportType.SOCCER)
        dup_issues = [i for i in issues if "Duplicate" in i.message]
        assert len(dup_issues) > 0

    def test_invalid_position_warns(self):
        players = [
            _player("GK", 1, "GK"),
            _player("P1", 2, "ZZZZ"),  # invalid
            *[_player(f"P{i}", i + 3, "CM") for i in range(9)],
        ]
        team = _team(players=players)
        issues = validate_roster(team, SportType.SOCCER)
        pos_issues = [i for i in issues if "Unknown position" in i.message]
        assert len(pos_issues) > 0


class TestHockeyValidation:
    def test_needs_goalie(self):
        players = [_player(f"P{i}", i + 1, "C") for i in range(6)]
        team = _team(players=players)
        issues = validate_roster(team, SportType.HOCKEY)
        g_issues = [i for i in issues if i.severity == "error" and "G" in i.message]
        assert len(g_issues) > 0

    def test_needs_defensemen(self):
        players = [
            _player("G", 1, "G"),
            _player("C", 2, "C"),
            *[_player(f"W{i}", i + 3, "LW") for i in range(4)],
        ]
        team = _team(players=players)
        issues = validate_roster(team, SportType.HOCKEY)
        d_issues = [i for i in issues if i.severity == "error" and ("LD" in i.message or "RD" in i.message)]
        assert len(d_issues) > 0


class TestAttributeValidation:
    def test_out_of_range_attribute_rejected_by_pydantic(self):
        """Pydantic enforces attribute bounds, so out-of-range values raise ValidationError."""
        import pydantic

        with pytest.raises(pydantic.ValidationError):
            PlayerAttributes(speed=1.5)

    def test_unrealistic_age_warns(self):
        p = _player("Old Player", 99, "CM", age=55)
        team = _team(players=[p])
        issues = validate_roster(team, SportType.SOCCER)
        age_issues = [i for i in issues if "age" in i.message.lower()]
        assert len(age_issues) > 0

    def test_unrealistic_jersey_number_warns(self):
        p = _player("High Number", 999, "CM")
        team = _team(players=[p])
        issues = validate_roster(team, SportType.SOCCER)
        num_issues = [i for i in issues if "jersey number" in i.message.lower()]
        assert len(num_issues) > 0


class TestMatchupValidation:
    def test_validates_both_teams(self):
        home = _team("Home FC", players=[_player("P1", 1, "CM")])
        away = _team("Away FC", players=[_player("P1", 1, "CM")])
        issues = validate_matchup(home, away, SportType.SOCCER)
        # Both teams should have roster size warnings
        home_issues = [i for i in issues if i.team == "Home FC"]
        away_issues = [i for i in issues if i.team == "Away FC"]
        assert len(home_issues) > 0
        assert len(away_issues) > 0
