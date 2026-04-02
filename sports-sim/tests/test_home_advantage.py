"""Tests for home advantage module."""

import pytest
from sports_sim.core.models import (
    Ball, Environment, GameState, Player, SimulationConfig,
    SportType, Team, Venue, SurfaceType, VenueType,
)
from sports_sim.realism.home_advantage import apply_home_advantage


def _make_state(altitude_m=0.0, crowd_intensity=0.8) -> GameState:
    players_h = [Player(name=f"H{i}", number=i, position="MF", stamina=0.8) for i in range(3)]
    players_a = [Player(name=f"A{i}", number=i, position="MF", stamina=0.8) for i in range(3)]
    h = Team(name="Home", players=players_h, momentum=0.5)
    a = Team(name="Away", players=players_a, momentum=0.5)
    env = Environment(altitude_m=altitude_m, crowd_intensity=crowd_intensity)
    state = GameState(
        sport=SportType.SOCCER,
        home_team=h,
        away_team=a,
        environment=env,
        ball=Ball(x=50, y=34),
    )
    return state


def _make_config(enable_venue=True, home_advantage=0.1):
    return SimulationConfig(
        sport=SportType.SOCCER,
        seed=42,
        fidelity="fast",
        ticks_per_second=1,
        enable_venue_effects=enable_venue,
        home_advantage=home_advantage,
    )


class TestHomeAdvantage:
    def test_home_morale_increases(self):
        state = _make_state(crowd_intensity=0.9)
        config = _make_config()
        orig = state.home_team.players[0].morale
        for _ in range(200):
            apply_home_advantage(state, config)
        assert state.home_team.players[0].morale >= orig

    def test_away_morale_decreases(self):
        state = _make_state(crowd_intensity=0.9)
        config = _make_config()
        orig = state.away_team.players[0].morale
        for _ in range(200):
            apply_home_advantage(state, config)
        assert state.away_team.players[0].morale <= orig

    def test_disabled_when_no_venue_effects(self):
        state = _make_state()
        config = _make_config(enable_venue=False)
        orig_h = state.home_team.players[0].morale
        orig_a = state.away_team.players[0].morale
        apply_home_advantage(state, config)
        assert state.home_team.players[0].morale == orig_h
        assert state.away_team.players[0].morale == orig_a

    def test_disabled_when_advantage_zero(self):
        state = _make_state()
        config = _make_config(home_advantage=0.0)
        orig_h = state.home_team.players[0].morale
        apply_home_advantage(state, config)
        assert state.home_team.players[0].morale == orig_h

    def test_high_altitude_drains_away_stamina(self):
        state = _make_state(altitude_m=3000.0)
        state.venue = Venue(
            name="High", city="Denver", venue_type=VenueType.OPEN_AIR,
            surface=SurfaceType.NATURAL_GRASS, capacity=50000,
        )
        config = _make_config()
        orig = state.away_team.players[0].stamina
        for _ in range(500):
            apply_home_advantage(state, config)
        assert state.away_team.players[0].stamina < orig
