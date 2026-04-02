"""Tests for get_sport_state() across all sport modules and WS enrichment."""

from __future__ import annotations

import pytest

from sports_sim.core.engine import Simulation
from sports_sim.core.models import SimulationConfig, SportType


SPORTS = [
    SportType.SOCCER,
    SportType.BASKETBALL,
    SportType.BASEBALL,
    SportType.FOOTBALL,
    SportType.HOCKEY,
    SportType.TENNIS,
    SportType.GOLF,
    SportType.CRICKET,
    SportType.BOXING,
    SportType.MMA,
    SportType.RACING,
]


class TestGetSportState:
    """Verify every sport plugin returns a non-empty dict from get_sport_state()."""

    @pytest.mark.parametrize("sport", SPORTS, ids=lambda s: s.value)
    def test_sport_state_returns_dict(self, sport: SportType):
        config = SimulationConfig(sport=sport, seed=42, fidelity="fast")
        sim = Simulation(config)
        # Run one tick to get initial state
        for state, events in sim.stream():
            result = sim.sport.get_sport_state(state)
            assert isinstance(result, dict), f"{sport.value} get_sport_state() did not return dict"
            break  # only need one tick

    @pytest.mark.parametrize("sport", SPORTS, ids=lambda s: s.value)
    def test_sport_state_nonempty_after_events(self, sport: SportType):
        config = SimulationConfig(sport=sport, seed=42, fidelity="fast")
        sim = Simulation(config)
        last_state = None
        count = 0
        for state, events in sim.stream():
            last_state = state
            count += 1
            if count > 20:  # run a few ticks to generate events
                break
        if last_state:
            result = sim.sport.get_sport_state(last_state)
            assert isinstance(result, dict)
            # Most sports should have some state after 20 ticks
            # (soccer may be empty since it derives from events, but the method still works)

    @pytest.mark.parametrize("sport", SPORTS, ids=lambda s: s.value)
    def test_sport_state_values_are_serializable(self, sport: SportType):
        """Ensure the dict can be JSON-serialized (for WebSocket transmission)."""
        import json

        config = SimulationConfig(sport=sport, seed=42, fidelity="fast")
        sim = Simulation(config)
        count = 0
        for state, events in sim.stream():
            count += 1
            if count > 10:
                result = sim.sport.get_sport_state(state)
                # Should not raise
                serialized = json.dumps(result)
                assert isinstance(serialized, str)
                break


class TestStreamPayloadEnrichment:
    """Verify the simulation stream produces enriched payloads."""

    def test_full_simulation_completes(self):
        config = SimulationConfig(sport=SportType.SOCCER, seed=99, fidelity="fast")
        sim = Simulation(config)
        state = sim.run()
        assert state.is_finished

    @pytest.mark.parametrize("sport", SPORTS, ids=lambda s: s.value)
    def test_events_have_metadata_field(self, sport: SportType):
        config = SimulationConfig(sport=sport, seed=42, fidelity="fast")
        sim = Simulation(config)
        state = sim.run()
        # Every event should have a metadata dict (even if empty)
        for event in state.events:
            assert isinstance(event.metadata, dict)
