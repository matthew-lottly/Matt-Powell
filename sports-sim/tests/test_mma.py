"""Tests for MMA sport — KO, submission, decision."""

from typing import cast

from sports_sim.core.engine import Simulation
from sports_sim.core.models import SimulationConfig, SportType
from sports_sim.sports.mma import MMASport


class TestMMAIntegration:
    def test_runs_to_completion(self):
        config = SimulationConfig(sport=SportType.MMA, seed=42, fidelity="fast", ticks_per_second=1)
        sim = Simulation(config)
        final = sim.run()
        assert final.is_finished

    def test_deterministic(self):
        config = SimulationConfig(sport=SportType.MMA, seed=42, fidelity="fast", ticks_per_second=1)
        a = Simulation(config).run()
        b = Simulation(config).run()
        assert a.home_team.score == b.home_team.score

    def test_scores_non_negative(self):
        config = SimulationConfig(sport=SportType.MMA, seed=42, fidelity="fast", ticks_per_second=1)
        final = Simulation(config).run()
        assert final.home_team.score >= 0
        assert final.away_team.score >= 0

    def test_events_generated(self):
        config = SimulationConfig(sport=SportType.MMA, seed=42, fidelity="fast", ticks_per_second=1)
        final = Simulation(config).run()
        assert len(final.events) > 0


class TestMMAUnit:
    def test_health_never_negative(self):
        config = SimulationConfig(sport=SportType.MMA, seed=42, fidelity="fast", ticks_per_second=1)
        sim = Simulation(config)
        sim.run()
        mma_sport = cast(MMASport, sim.sport)
        assert mma_sport._p1_health >= 0.0
        assert mma_sport._p2_health >= 0.0

    def test_on_ground_resets_between_rounds(self):
        sport = MMASport()
        sport._on_ground = True
        from sports_sim.core.models import GameState, Team, Player, Ball
        h = Team(name="P1", players=[Player(name="P1", number=1, position="MMA")])
        a = Team(name="P2", players=[Player(name="P2", number=1, position="MMA")])
        state = GameState(sport=SportType.MMA, home_team=h, away_team=a, ball=Ball(x=0, y=0))
        sport._end_round(state)
        assert sport._on_ground is False

    def test_round_recovery(self):
        sport = MMASport()
        sport._p1_health = 60.0
        sport._p2_health = 70.0
        from sports_sim.core.models import GameState, Team, Player, Ball
        h = Team(name="P1", players=[Player(name="P1", number=1, position="MMA")])
        a = Team(name="P2", players=[Player(name="P2", number=1, position="MMA")])
        state = GameState(sport=SportType.MMA, home_team=h, away_team=a, ball=Ball(x=0, y=0))
        sport._end_round(state)
        assert sport._p1_health == 70.0  # +10
        assert sport._p2_health == 80.0  # +10
