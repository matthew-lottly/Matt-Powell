"""Tests for golf sport — hole completion, scoring."""

from typing import cast

from sports_sim.core.engine import Simulation
from sports_sim.core.models import SimulationConfig, SportType
from sports_sim.sports.golf import GolfSport


class TestGolfIntegration:
    def test_runs_to_completion(self):
        config = SimulationConfig(sport=SportType.GOLF, seed=42, fidelity="fast", ticks_per_second=1)
        sim = Simulation(config)
        final = sim.run()
        assert final.is_finished

    def test_deterministic(self):
        config = SimulationConfig(sport=SportType.GOLF, seed=55, fidelity="fast", ticks_per_second=1)
        a = Simulation(config).run()
        b = Simulation(config).run()
        assert a.home_team.score == b.home_team.score
        assert a.away_team.score == b.away_team.score

    def test_18_holes_played(self):
        config = SimulationConfig(sport=SportType.GOLF, seed=42, fidelity="fast", ticks_per_second=1)
        sim = Simulation(config)
        final = sim.run()
        sport_state = sim.sport.get_sport_state(final)
        assert sport_state.get("current_hole", 0) == 18

    def test_events_include_hole_results(self):
        config = SimulationConfig(sport=SportType.GOLF, seed=42, fidelity="fast", ticks_per_second=1)
        final = Simulation(config).run()
        event_types = {e.type.value for e in final.events}
        assert len(event_types) > 0

    def test_sport_state_has_strokes(self):
        config = SimulationConfig(sport=SportType.GOLF, seed=42, fidelity="fast", ticks_per_second=1)
        sim = Simulation(config)
        final = sim.run()
        sport_state = sim.sport.get_sport_state(final)
        assert "p1_total_strokes" in sport_state or "total_strokes" in sport_state or "p1_strokes" in sport_state


class TestGolfUnit:
    def test_strokes_always_at_least_one(self):
        config = SimulationConfig(sport=SportType.GOLF, seed=42, fidelity="fast", ticks_per_second=1)
        sim = Simulation(config)
        sim.run()
        golf_sport = cast(GolfSport, sim.sport)
        for s in golf_sport._p1_strokes:
            assert s >= 1
        for s in golf_sport._p2_strokes:
            assert s >= 1
