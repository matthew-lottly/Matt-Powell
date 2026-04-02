"""Tests for weather effects module."""

import pytest
from sports_sim.core.models import (
    Ball, Environment, GameState, Player, SportType, Team, Weather, Venue,
    SurfaceType, VenueType,
)
from sports_sim.realism.weather import apply_weather_effects


def _make_state(**env_kwargs) -> GameState:
    players_h = [Player(name=f"H{i}", number=i, position="MF", stamina=0.8) for i in range(3)]
    players_a = [Player(name=f"A{i}", number=i, position="MF", stamina=0.8) for i in range(3)]
    h = Team(name="Home", players=players_h)
    a = Team(name="Away", players=players_a)
    env = Environment(**env_kwargs) if env_kwargs else Environment()
    return GameState(
        sport=SportType.SOCCER,
        home_team=h,
        away_team=a,
        environment=env,
        ball=Ball(x=50, y=34),
    )


class TestRainEffects:
    def test_rain_reduces_accuracy(self):
        state = _make_state(weather=Weather.RAIN)
        orig = state.home_team.players[0].attributes.accuracy
        for _ in range(100):
            apply_weather_effects(state)
        assert state.home_team.players[0].attributes.accuracy < orig


class TestHeatEffects:
    def test_heat_drains_stamina(self):
        state = _make_state(weather=Weather.EXTREME_HEAT, temperature_c=40.0)
        orig = state.home_team.players[0].stamina
        for _ in range(100):
            apply_weather_effects(state)
        assert state.home_team.players[0].stamina < orig


class TestSnowEffects:
    def test_snow_reduces_speed(self):
        state = _make_state(weather=Weather.SNOW)
        orig = state.home_team.players[0].attributes.speed
        for _ in range(100):
            apply_weather_effects(state)
        assert state.home_team.players[0].attributes.speed < orig


class TestFreezingEffects:
    def test_freezing_reduces_speed(self):
        state = _make_state(weather=Weather.FREEZING, temperature_c=-10.0)
        orig = state.home_team.players[0].attributes.speed
        for _ in range(100):
            apply_weather_effects(state)
        assert state.home_team.players[0].attributes.speed < orig


class TestAltitudeEffects:
    def test_altitude_drains_stamina(self):
        state = _make_state(altitude_m=3000.0)
        orig = state.home_team.players[0].stamina
        for _ in range(100):
            apply_weather_effects(state)
        assert state.home_team.players[0].stamina < orig

    def test_low_altitude_no_drain(self):
        state = _make_state(altitude_m=100.0)
        orig = state.home_team.players[0].stamina
        apply_weather_effects(state)
        # Low altitude shouldn't drain stamina significantly
        assert state.home_team.players[0].stamina >= orig - 0.001


class TestClimateControlled:
    def test_climate_controlled_skips_weather(self):
        state = _make_state(weather=Weather.RAIN)
        state.venue = Venue(
            name="Dome", city="Test", venue_type=VenueType.DOME,
            surface=SurfaceType.ARTIFICIAL_TURF, capacity=50000,
            climate_controlled=True,
        )
        orig_acc = state.home_team.players[0].attributes.accuracy
        for _ in range(100):
            apply_weather_effects(state)
        # Climate controlled — rain effect skipped, accuracy should be unchanged or minimal
        assert state.home_team.players[0].attributes.accuracy >= orig_acc - 0.01
