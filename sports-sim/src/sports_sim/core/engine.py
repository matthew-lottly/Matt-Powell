"""Main simulation engine — runs the game loop using a Sport plugin."""

from __future__ import annotations

import logging
from typing import Generator

import numpy as np

from sports_sim.core.models import EventType, GameEvent, GameState, SimulationConfig, SportType
from sports_sim.core.sport import Sport
from sports_sim.realism.fatigue import apply_fatigue
from sports_sim.realism.injuries import check_injuries
from sports_sim.realism.momentum import update_momentum
from sports_sim.realism.weather import apply_weather_effects

logger = logging.getLogger(__name__)


def _get_sport(sport_type: SportType) -> Sport:
    from sports_sim.sports.baseball import BaseballSport
    from sports_sim.sports.basketball import BasketballSport
    from sports_sim.sports.soccer import SoccerSport

    registry: dict[SportType, type[Sport]] = {
        SportType.SOCCER: SoccerSport,
        SportType.BASKETBALL: BasketballSport,
        SportType.BASEBALL: BaseballSport,
    }
    cls = registry.get(sport_type)
    if cls is None:
        raise ValueError(f"Unknown sport: {sport_type}")
    return cls()


class Simulation:
    """Runs a full game simulation for any registered sport."""

    def __init__(self, config: SimulationConfig, home_team=None, away_team=None):
        self.config = config
        self.sport = _get_sport(config.sport)
        self.rng = np.random.default_rng(config.seed)
        self.sport._rng = self.rng

        if home_team and away_team:
            h, a = home_team, away_team
        else:
            h, a = self.sport.create_default_teams()

        self.state = GameState(
            sport=config.sport,
            home_team=h,
            away_team=a,
            environment=config.environment,
            total_periods=self.sport.default_periods,
            period_length=self.sport.default_period_length,
            seed=config.seed or int(self.rng.integers(0, 2**31)),
        )
        self.state = self.sport.setup_positions(self.state)

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self) -> GameState:
        """Run the entire game and return the final state."""
        for _ in self.stream():
            pass
        return self.state

    def stream(self) -> Generator[tuple[GameState, list[GameEvent]], None, None]:
        """Yield (state, events) after each tick — useful for realtime / WebSocket streaming."""
        self.state.is_running = True
        self.state.events.append(
            GameEvent(type=EventType.GAME_START, time=0.0, period=1, description="Game started")
        )
        yield self.state, self.state.events[-1:]

        for period in range(1, self.state.total_periods + 1):
            self.state.period = period
            self.state.events.append(
                GameEvent(type=EventType.PERIOD_START, time=self.state.clock, period=period,
                          description=f"Period {period} started")
            )
            yield self.state, self.state.events[-1:]
            self.state = self.sport.setup_positions(self.state)

            ticks_in_period = int(self.state.period_length * 60 * self.config.ticks_per_second)
            dt = 1.0 / self.config.ticks_per_second

            for t in range(ticks_in_period):
                self.state.tick += 1
                self.state.clock = (period - 1) * self.state.period_length + t * dt / 60.0

                # --- sport-specific tick ---
                self.state, events = self.sport.tick(self.state, self.config)

                # --- realism layers ---
                if self.config.enable_fatigue:
                    self.state = apply_fatigue(self.state, dt)
                if self.config.enable_injuries:
                    self.state, inj_events = check_injuries(self.state, self.rng)
                    events.extend(inj_events)
                if self.config.enable_weather:
                    self.state = apply_weather_effects(self.state)
                if self.config.enable_momentum:
                    self.state = update_momentum(self.state, events)

                # --- post-event hooks ---
                for ev in events:
                    self.state = self.sport.post_event(self.state, ev, self.config)
                    self.state.events.append(ev)

                if events:
                    yield self.state, events

            self.state.events.append(
                GameEvent(type=EventType.PERIOD_END, time=self.state.clock, period=period,
                          description=f"Period {period} ended")
            )
            yield self.state, self.state.events[-1:]

        self.state.is_running = False
        self.state.is_finished = True
        self.state.events.append(
            GameEvent(type=EventType.GAME_END, time=self.state.clock,
                      period=self.state.total_periods,
                      description=f"Final: {self.state.score_summary}")
        )
        yield self.state, self.state.events[-1:]
        logger.info("Simulation complete: %s", self.state.score_summary)
