"""Tests for realism modules."""

import numpy as np
import pytest

from sports_sim.core.models import (
    Ball,
    Environment,
    EventType,
    GameEvent,
    GameState,
    Player,
    SimulationConfig,
    SportType,
    Team,
    Weather,
)
from sports_sim.realism.fatigue import apply_fatigue
from sports_sim.realism.injuries import check_injuries
from sports_sim.realism.momentum import update_momentum
from sports_sim.realism.weather import apply_weather_effects


def _make_state(**env_kwargs) -> GameState:
    players_h = [Player(name=f"H{i}", number=i, position="MF", stamina=0.8) for i in range(3)]
    players_a = [Player(name=f"A{i}", number=i, position="MF", stamina=0.8) for i in range(3)]
    h = Team(name="Home", players=players_h)
    a = Team(name="Away", players=players_a)
    env = Environment(**env_kwargs) if env_kwargs else Environment()
    return GameState(sport=SportType.SOCCER, home_team=h, away_team=a, environment=env,
                     ball=Ball(x=50, y=34))


class TestFatigue:
    def test_stamina_decreases(self):
        state = _make_state()
        original = state.home_team.players[0].stamina
        apply_fatigue(state, dt=1.0)
        assert state.home_team.players[0].stamina < original

    def test_stamina_never_negative(self):
        state = _make_state()
        for p in state.home_team.players:
            p.stamina = 0.001
        apply_fatigue(state, dt=100.0)
        for p in state.home_team.players:
            assert p.stamina >= 0.0


class TestInjuries:
    def test_no_injuries_when_disabled(self):
        state = _make_state()
        config = SimulationConfig(enable_injuries=False)
        _, events = check_injuries(state, config=config)
        assert len(events) == 0

    def test_exhausted_players_higher_risk(self):
        rng = np.random.default_rng(42)
        injuries = 0
        for _ in range(5000):
            s = _make_state()
            for t in (s.home_team, s.away_team):
                for p in t.players:
                    p.stamina = 0.01
            _, evs = check_injuries(s, rng=rng)
            injuries += len([e for e in evs if e.type == EventType.INJURY])
        # With very low stamina, we should see at least some injuries over 5000 iterations
        assert injuries > 0


class TestWeather:
    def test_rain_reduces_accuracy(self):
        state = _make_state(weather=Weather.RAIN)
        orig = state.home_team.players[0].attributes.accuracy
        apply_weather_effects(state)
        assert state.home_team.players[0].attributes.accuracy <= orig

    def test_heat_drains_stamina(self):
        state = _make_state(temperature_c=40.0)
        orig = state.home_team.players[0].stamina
        apply_weather_effects(state)
        assert state.home_team.players[0].stamina < orig

    def test_no_effects_when_disabled(self):
        state = _make_state(weather=Weather.RAIN)
        config = SimulationConfig(enable_weather=False)
        orig = state.home_team.players[0].attributes.accuracy
        apply_weather_effects(state, config=config)
        assert state.home_team.players[0].attributes.accuracy == orig


class TestMomentum:
    def test_goal_boosts_team(self):
        state = _make_state()
        state.home_team.momentum = 0.5
        ev = GameEvent(type=EventType.GOAL, team_id=state.home_team.id, description="Goal!")
        update_momentum(state, [ev])
        assert state.home_team.momentum > 0.5

    def test_natural_decay(self):
        state = _make_state()
        state.home_team.momentum = 0.9
        update_momentum(state, [])
        assert state.home_team.momentum < 0.9

    def test_disabled(self):
        state = _make_state()
        state.home_team.momentum = 0.9
        config = SimulationConfig(enable_momentum=False)
        update_momentum(state, [], config=config)
        assert state.home_team.momentum == 0.9
