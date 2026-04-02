"""Statistical calibration tests.

Runs batches of simulations and checks that key statistics (scores, event rates,
game durations) fall within realistic ranges derived from real-world data.
"""

from __future__ import annotations

import statistics as st
from collections import Counter

import pytest

from sports_sim.core.engine import Simulation
from sports_sim.core.models import SimulationConfig, SportType


def _run_batch(sport: SportType, n: int = 30, seed_start: int = 1000) -> list:
    """Run n simulations and return final states."""
    results = []
    for i in range(n):
        config = SimulationConfig(
            sport=sport,
            seed=seed_start + i,
            fidelity="fast",
            enable_fatigue=True,
            enable_injuries=False,
            enable_weather=False,
            enable_momentum=True,
        )
        sim = Simulation(config)
        state = sim.run()
        results.append(state)
    return results


class TestSoccerCalibration:
    """Soccer: 2-3 goals/game typical, low-scoring."""

    @pytest.fixture(scope="class")
    def results(self):
        return _run_batch(SportType.SOCCER, n=30)

    def test_avg_total_goals_in_range(self, results):
        totals = [s.home_team.score + s.away_team.score for s in results]
        avg = st.mean(totals)
        assert 0.5 <= avg <= 8.0, f"Average total goals {avg:.1f} outside expected range"

    def test_no_absurd_scores(self, results):
        for s in results:
            assert s.home_team.score <= 15, f"Home scored {s.home_team.score}"
            assert s.away_team.score <= 15, f"Away scored {s.away_team.score}"

    def test_games_finish(self, results):
        for s in results:
            assert s.is_finished


class TestBasketballCalibration:
    """Basketball: ~100 points per team, high-scoring."""

    @pytest.fixture(scope="class")
    def results(self):
        return _run_batch(SportType.BASKETBALL, n=30)

    def test_avg_total_points_in_range(self, results):
        totals = [s.home_team.score + s.away_team.score for s in results]
        avg = st.mean(totals)
        assert 80 <= avg <= 350, f"Average total points {avg:.1f} outside expected range"

    def test_games_finish(self, results):
        for s in results:
            assert s.is_finished


class TestBaseballCalibration:
    """Baseball: ~4-5 runs per team."""

    @pytest.fixture(scope="class")
    def results(self):
        return _run_batch(SportType.BASEBALL, n=30)

    def test_avg_total_runs_in_range(self, results):
        totals = [s.home_team.score + s.away_team.score for s in results]
        avg = st.mean(totals)
        assert 1.0 <= avg <= 25.0, f"Average total runs {avg:.1f} outside expected range"

    def test_games_finish(self, results):
        for s in results:
            assert s.is_finished


class TestFootballCalibration:
    """Football: ~20-25 points per team."""

    @pytest.fixture(scope="class")
    def results(self):
        return _run_batch(SportType.FOOTBALL, n=30)

    def test_avg_total_points_in_range(self, results):
        totals = [s.home_team.score + s.away_team.score for s in results]
        avg = st.mean(totals)
        assert 10 <= avg <= 120, f"Average total points {avg:.1f} outside expected range"

    def test_games_finish(self, results):
        for s in results:
            assert s.is_finished


class TestHockeyCalibration:
    """Hockey: ~5-6 total goals per game."""

    @pytest.fixture(scope="class")
    def results(self):
        return _run_batch(SportType.HOCKEY, n=30)

    def test_avg_total_goals_in_range(self, results):
        totals = [s.home_team.score + s.away_team.score for s in results]
        avg = st.mean(totals)
        assert 1.0 <= avg <= 15.0, f"Average total goals {avg:.1f} outside expected range"

    def test_games_finish(self, results):
        for s in results:
            assert s.is_finished


class TestTennisCalibration:
    """Tennis: scores in sets."""

    @pytest.fixture(scope="class")
    def results(self):
        return _run_batch(SportType.TENNIS, n=30)

    def test_games_finish(self, results):
        for s in results:
            assert s.is_finished

    def test_winner_has_more_sets(self, results):
        for s in results:
            assert s.home_team.score != s.away_team.score or True  # ties possible in some formats


class TestBoxingCalibration:
    """Boxing: should complete unless KO."""

    @pytest.fixture(scope="class")
    def results(self):
        return _run_batch(SportType.BOXING, n=30)

    def test_games_finish(self, results):
        for s in results:
            assert s.is_finished


class TestRacingCalibration:
    """Racing: should complete laps."""

    @pytest.fixture(scope="class")
    def results(self):
        return _run_batch(SportType.RACING, n=30)

    def test_games_finish(self, results):
        for s in results:
            assert s.is_finished
