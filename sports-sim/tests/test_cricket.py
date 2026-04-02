"""Tests for cricket sport — innings, wickets, overs."""

import pytest
from sports_sim.core.engine import Simulation
from sports_sim.core.models import SimulationConfig, SportType


class TestCricketIntegration:
    def test_runs_to_completion(self):
        config = SimulationConfig(sport=SportType.CRICKET, seed=42, fidelity="fast", ticks_per_second=1)
        sim = Simulation(config)
        final = sim.run()
        assert final.is_finished

    def test_deterministic(self):
        config = SimulationConfig(sport=SportType.CRICKET, seed=99, fidelity="fast", ticks_per_second=1)
        a = Simulation(config).run()
        b = Simulation(config).run()
        assert a.home_team.score == b.home_team.score
        assert a.away_team.score == b.away_team.score

    def test_scores_non_negative(self):
        config = SimulationConfig(sport=SportType.CRICKET, seed=42, fidelity="fast", ticks_per_second=1)
        final = Simulation(config).run()
        assert final.home_team.score >= 0
        assert final.away_team.score >= 0

    def test_events_generated(self):
        config = SimulationConfig(sport=SportType.CRICKET, seed=42, fidelity="fast", ticks_per_second=1)
        final = Simulation(config).run()
        assert len(final.events) > 0

    def test_sport_state_has_overs(self):
        config = SimulationConfig(sport=SportType.CRICKET, seed=42, fidelity="fast", ticks_per_second=1)
        sim = Simulation(config)
        final = sim.run()
        sport_state = sim.sport.get_sport_state(final)
        assert "overs" in sport_state or "current_over" in sport_state

    def test_multiple_seeds_vary(self):
        results = []
        for seed in [1, 2, 3, 4, 5]:
            config = SimulationConfig(sport=SportType.CRICKET, seed=seed, fidelity="fast", ticks_per_second=1)
            final = Simulation(config).run()
            results.append((final.home_team.score, final.away_team.score))
        # At least some variation across seeds
        assert len(set(results)) > 1
