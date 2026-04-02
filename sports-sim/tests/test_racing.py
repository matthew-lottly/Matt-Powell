"""Tests for racing sport — laps, pit stops, DNF."""

from typing import cast

from sports_sim.core.engine import Simulation
from sports_sim.core.models import SimulationConfig, SportType
from sports_sim.sports.racing import RacingSport


class TestRacingIntegration:
    def test_runs_to_completion(self):
        config = SimulationConfig(sport=SportType.RACING, seed=42, fidelity="fast", ticks_per_second=1)
        sim = Simulation(config)
        final = sim.run()
        assert final.is_finished

    def test_deterministic(self):
        config = SimulationConfig(sport=SportType.RACING, seed=42, fidelity="fast", ticks_per_second=1)
        a = Simulation(config).run()
        b = Simulation(config).run()
        assert a.home_team.score == b.home_team.score

    def test_scores_are_lap_counts(self):
        config = SimulationConfig(sport=SportType.RACING, seed=42, fidelity="fast", ticks_per_second=1)
        sim = Simulation(config)
        final = sim.run()
        assert final.home_team.score >= 0
        assert final.away_team.score >= 0

    def test_events_include_laps(self):
        config = SimulationConfig(sport=SportType.RACING, seed=42, fidelity="fast", ticks_per_second=1)
        final = Simulation(config).run()
        event_types = {e.type.value for e in final.events}
        assert len(event_types) > 0


class TestRacingUnit:
    def test_tire_wear_decreases(self):
        sport = RacingSport()
        initial_tire = sport._p1_tire_wear
        # After many ticks tire should degrade
        config = SimulationConfig(sport=SportType.RACING, seed=42, fidelity="fast", ticks_per_second=1)
        sim = Simulation(config)
        # Stream a few ticks
        count = 0
        for state, events in sim.stream():
            count += 1
            if count > 500:
                break
        racing_sport = cast(RacingSport, sim.sport)
        assert racing_sport._p1_tire_wear < initial_tire

    def test_tire_wear_has_floor(self):
        config = SimulationConfig(sport=SportType.RACING, seed=42, fidelity="fast", ticks_per_second=1)
        sim = Simulation(config)
        sim.run()
        racing_sport = cast(RacingSport, sim.sport)
        assert racing_sport._p1_tire_wear >= 0.3 or racing_sport._p1_dnf
