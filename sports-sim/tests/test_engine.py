"""Unit tests for the simulation engine."""

import pytest
from sports_sim.core.engine import Simulation
from sports_sim.core.models import SimulationConfig, SportType


@pytest.fixture(params=["soccer", "basketball", "baseball"])
def sport(request):
    return request.param


class TestSimulation:
    def test_runs_to_completion(self, sport):
        config = SimulationConfig(
            sport=SportType(sport),
            seed=42,
            fidelity="fast",
            ticks_per_second=1,
        )
        sim = Simulation(config)
        final = sim.run()
        assert final.is_finished
        assert final.home_team.score >= 0
        assert final.away_team.score >= 0
        assert len(final.events) > 0

    def test_stream_yields_tuples(self, sport):
        config = SimulationConfig(
            sport=SportType(sport),
            seed=123,
            fidelity="fast",
            ticks_per_second=1,
        )
        sim = Simulation(config)
        count = 0
        for state, events in sim.stream():
            assert state is not None
            assert isinstance(events, list)
            count += 1
        assert count > 0

    def test_deterministic_with_seed(self):
        config = SimulationConfig(sport=SportType.SOCCER, seed=99, fidelity="fast", ticks_per_second=1)
        s1 = Simulation(config).run()
        s2 = Simulation(config).run()
        assert s1.home_team.score == s2.home_team.score
        assert s1.away_team.score == s2.away_team.score

    def test_disabling_realism(self):
        config = SimulationConfig(
            sport=SportType.BASKETBALL,
            seed=42,
            fidelity="fast",
            ticks_per_second=1,
            enable_fatigue=False,
            enable_injuries=False,
            enable_weather=False,
            enable_momentum=False,
        )
        sim = Simulation(config)
        final = sim.run()
        assert final.is_finished
        # With no fatigue, all stamina should remain 1.0
        for p in final.home_team.players:
            assert p.stamina == 1.0
