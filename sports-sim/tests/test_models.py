"""Unit tests for core models."""

import pytest
from sports_sim.core.models import (
    Ball,
    Environment,
    EventType,
    GameEvent,
    GameState,
    Player,
    PlayerAttributes,
    SimulationConfig,
    SportType,
    Team,
    Weather,
)


class TestPlayerAttributes:
    def test_defaults(self):
        a = PlayerAttributes()
        assert 0.0 <= a.speed <= 1.0
        assert 0.0 <= a.strength <= 1.0

    def test_clamped(self):
        with pytest.raises(Exception):
            PlayerAttributes(speed=1.5)


class TestPlayer:
    def test_effective_skill_full_stamina(self):
        p = Player(name="Test", number=1, position="FW")
        assert 0.0 < p.effective_skill <= 1.0

    def test_effective_skill_decreases_with_fatigue(self):
        p = Player(name="Test", number=1, position="FW", stamina=1.0)
        high = p.effective_skill
        p.stamina = 0.2
        low = p.effective_skill
        assert low < high

    def test_morale_affects_skill(self):
        p = Player(name="Test", number=1, position="FW", morale=1.0)
        high = p.effective_skill
        p.morale = 0.0
        low = p.effective_skill
        assert low < high


class TestTeam:
    def _make_team(self, n=3):
        players = [Player(name=f"P{i}", number=i, position="MF") for i in range(n)]
        return Team(name="Test", players=players)

    def test_active_players(self):
        t = self._make_team(5)
        assert len(t.active_players) == 5
        t.players[0].is_injured = True
        assert len(t.active_players) == 4

    def test_avg_stamina(self):
        t = self._make_team(2)
        t.players[0].stamina = 1.0
        t.players[1].stamina = 0.5
        assert t.avg_stamina == pytest.approx(0.75)


class TestBall:
    def test_defaults(self):
        b = Ball()
        assert b.x == 0.0
        assert b.possessed_by is None


class TestGameEvent:
    def test_creation(self):
        ev = GameEvent(type=EventType.GOAL, time=45.0, period=1, description="Goal!")
        assert ev.type == EventType.GOAL
        assert len(ev.id) == 8


class TestEnvironment:
    def test_defaults(self):
        e = Environment()
        assert e.weather == Weather.CLEAR
        assert e.temperature_c == 22.0


class TestGameState:
    def test_score_summary(self):
        h = Team(name="Home", players=[])
        a = Team(name="Away", players=[])
        h.score = 2
        a.score = 1
        state = GameState(sport=SportType.SOCCER, home_team=h, away_team=a)
        assert "2" in state.score_summary
        assert "1" in state.score_summary


class TestSimulationConfig:
    def test_defaults(self):
        c = SimulationConfig()
        assert c.sport == SportType.SOCCER
        assert c.enable_fatigue is True

    def test_fidelity_validation(self):
        with pytest.raises(Exception):
            SimulationConfig(fidelity="ultra")
