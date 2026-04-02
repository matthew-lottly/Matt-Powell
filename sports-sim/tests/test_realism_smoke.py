from __future__ import annotations

import importlib

from sports_sim.core.models import EventType, GameEvent, GameState, Player, SimulationConfig, SportType, Team
from sports_sim.realism.fatigue import apply_fatigue
from sports_sim.realism.injuries import check_injuries
from sports_sim.realism.momentum import update_momentum
from sports_sim.realism.weather import apply_weather_effects


def make_team(name: str) -> Team:
    p1 = Player(name=f"{name} Star", number=9, position="F")
    p2 = Player(name=f"{name} Sub", number=12, position="F")
    return Team(name=name, abbreviation=name[:3].upper(), players=[p1], bench=[p2])


def test_realism_smoke_basic():
    home = make_team("HomeFC")
    away = make_team("AwayFC")
    state = GameState(sport=SportType.SOCCER, home_team=home, away_team=away)

    # apply fatigue for a small dt
    before = state.home_team.players[0].stamina
    state = apply_fatigue(state, dt=1.0, config=SimulationConfig())
    assert state.home_team.players[0].stamina <= before

    # run injury check (non-deterministic but should return state and events list)
    state, events = check_injuries(state, rng=None, config=SimulationConfig())
    assert isinstance(events, list)

    ev = GameEvent(type=EventType.GOAL, time=0.0, period=1, team_id=home.id, player_id=home.players[0].id)
    state = update_momentum(state, [ev], config=SimulationConfig())
    assert 0.0 <= state.home_team.momentum <= 1.0

    # apply weather (should not raise)
    state = apply_weather_effects(state, config=SimulationConfig())


def test_realism_modules_import():
    # Smoke test that realism modules import without runtime errors
    modules = [
        "sports_sim.realism.fatigue",
        "sports_sim.realism.injuries",
        "sports_sim.realism.momentum",
        "sports_sim.realism.weather",
        "sports_sim.realism.ratings",
        "sports_sim.realism.referee",
        "sports_sim.realism.home_advantage",
        "sports_sim.realism.surface",
        "sports_sim.realism.travel",
        "sports_sim.realism.substitutions",
    ]
    for m in modules:
        importlib.import_module(m)
