"""Tests for momentum system."""

from sports_sim.core.models import (
    Ball, Environment, EventType, GameEvent, GameState, Player,
    SimulationConfig, SportType, Team,
)
from sports_sim.realism.momentum import update_momentum


def _make_state() -> GameState:
    players_h = [Player(name=f"H{i}", number=i, position="MF", stamina=0.8) for i in range(3)]
    players_a = [Player(name=f"A{i}", number=i, position="MF", stamina=0.8) for i in range(3)]
    h = Team(name="Home", players=players_h, momentum=0.5)
    a = Team(name="Away", players=players_a, momentum=0.5)
    return GameState(
        sport=SportType.SOCCER,
        home_team=h,
        away_team=a,
        environment=Environment(),
        ball=Ball(x=50, y=34),
    )


class TestMomentumDecay:
    def test_decays_toward_neutral(self):
        state = _make_state()
        state.home_team.momentum = 0.9
        for _ in range(200):
            update_momentum(state, [])
        assert state.home_team.momentum < 0.9

    def test_decays_up_from_low(self):
        state = _make_state()
        state.home_team.momentum = 0.1
        for _ in range(200):
            update_momentum(state, [])
        assert state.home_team.momentum > 0.1


class TestPositiveEvents:
    def test_goal_boosts_momentum(self):
        state = _make_state()
        initial = state.home_team.momentum
        event = GameEvent(
            type=EventType.GOAL,
            description="Goal",
            team_id=state.home_team.id,
        )
        update_momentum(state, [event])
        assert state.home_team.momentum > initial

    def test_goal_reduces_opponent(self):
        state = _make_state()
        initial = state.away_team.momentum
        event = GameEvent(
            type=EventType.GOAL,
            description="Goal",
            team_id=state.home_team.id,
        )
        update_momentum(state, [event])
        assert state.away_team.momentum < initial


class TestNegativeEvents:
    def test_foul_reduces_momentum(self):
        state = _make_state()
        initial = state.home_team.momentum
        event = GameEvent(
            type=EventType.FOUL,
            description="Foul",
            team_id=state.home_team.id,
        )
        update_momentum(state, [event])
        assert state.home_team.momentum < initial


class TestMomentumClamping:
    def test_never_exceeds_one(self):
        state = _make_state()
        state.home_team.momentum = 0.99
        for _ in range(20):
            event = GameEvent(
                type=EventType.GOAL,
                description="Goal",
                team_id=state.home_team.id,
            )
            update_momentum(state, [event])
        assert state.home_team.momentum <= 1.0

    def test_never_below_zero(self):
        state = _make_state()
        state.home_team.momentum = 0.01
        for _ in range(20):
            event = GameEvent(
                type=EventType.FOUL,
                description="Foul",
                team_id=state.home_team.id,
            )
            update_momentum(state, [event])
        assert state.home_team.momentum >= 0.0
