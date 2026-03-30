"""Main simulation engine — runs the game loop using a Sport plugin."""

from __future__ import annotations

import logging
from typing import Generator

import numpy as np

from sports_sim.core.models import (
    EventType,
    GameEvent,
    GameState,
    SimulationConfig,
    SportType,
    SurfaceType,
    VenueType,
)
from sports_sim.core.sport import Sport
from sports_sim.core.sport_capabilities import get_capabilities
from sports_sim.realism.fatigue import apply_fatigue
from sports_sim.realism.injuries import check_injuries
from sports_sim.realism.momentum import update_momentum
from sports_sim.realism.weather import apply_weather_effects
from sports_sim.realism.ratings import update_elo_from_state, update_team_stats_from_state
from sports_sim.realism.referee import RefereeProfile, apply_referee_variability, create_referee
from sports_sim.realism.home_advantage import apply_home_advantage
from sports_sim.realism.surface import apply_surface_effects
from sports_sim.realism.travel import apply_travel_fatigue
from sports_sim.realism.substitutions import (
    create_sub_tracker,
    check_auto_substitutions,
    check_hockey_line_changes,
)

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
    # Optional sport imports
    try:
        from sports_sim.sports.football import FootballSport
        registry[SportType.FOOTBALL] = FootballSport
    except ImportError:
        pass
    try:
        from sports_sim.sports.hockey import HockeySport
        registry[SportType.HOCKEY] = HockeySport
    except ImportError:
        pass
    try:
        from sports_sim.sports.tennis import TennisSport
        registry[SportType.TENNIS] = TennisSport
    except ImportError:
        pass
    try:
        from sports_sim.sports.golf import GolfSport
        registry[SportType.GOLF] = GolfSport
    except ImportError:
        pass
    try:
        from sports_sim.sports.cricket import CricketSport
        registry[SportType.CRICKET] = CricketSport
    except ImportError:
        pass
    try:
        from sports_sim.sports.boxing import BoxingSport
        registry[SportType.BOXING] = BoxingSport
    except ImportError:
        pass
    try:
        from sports_sim.sports.mma import MMASport
        registry[SportType.MMA] = MMASport
    except ImportError:
        pass
    try:
        from sports_sim.sports.racing import RacingSport
        registry[SportType.RACING] = RacingSport
    except ImportError:
        pass

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
        self.caps = get_capabilities(config.sport)

        # Create referee for this game
        self.referee = create_referee(self.rng)

        # Create substitution tracker
        self.sub_tracker = create_sub_tracker(config.sport)

        if home_team and away_team:
            h, a = home_team, away_team
        else:
            h, a = self.sport.create_default_teams()

        # Apply user sliders if provided
        if config.home_sliders:
            h.sliders = config.home_sliders
        if config.away_sliders:
            a.sliders = config.away_sliders

        # Determine venue (from config, or home team, or default)
        venue = config.venue or h.venue

        # Sync environment with venue properties
        env = config.environment.model_copy()
        if venue:
            env.altitude_m = venue.altitude_m
            env.surface_quality = venue.surface_quality
            env.surface_type = venue.surface
            env.venue_type = venue.venue_type
            env.is_climate_controlled = venue.climate_controlled
            # If dome/arena, override crowd from venue noise
            env.crowd_intensity = venue.noise_factor

        self.state = GameState(
            sport=config.sport,
            home_team=h,
            away_team=a,
            environment=env,
            venue=venue,
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

        # Apply pre-game travel fatigue to away team
        self.state = apply_travel_fatigue(self.state, self.config)

        # Apply home-field advantage via crowd intensity
        home_adv = self.config.home_advantage
        if self.state.environment.is_home_game and home_adv > 0:
            crowd = self.state.environment.crowd_intensity
            self.state.home_team.momentum = min(1.0, 0.5 + home_adv * crowd)

        # Coach morale boost at game start
        if self.config.enable_coach_effects:
            for team in (self.state.home_team, self.state.away_team):
                boost = team.coach.morale_boost
                for p in team.active_players:
                    p.morale = min(1.0, p.morale + boost)

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

                # --- referee variability ---
                if self.config.enable_referee_errors:
                    events = apply_referee_variability(
                        self.state, events, self.referee, self.rng, self.config
                    )

                # --- realism layers ---
                if self.config.enable_fatigue:
                    self.state = apply_fatigue(self.state, dt)
                if self.config.enable_injuries:
                    self.state, inj_events = check_injuries(self.state, self.rng)
                    events.extend(inj_events)
                if self.config.enable_weather and self.caps.weather_affected:
                    self.state = apply_weather_effects(self.state, self.config)
                if self.config.enable_momentum:
                    self.state = update_momentum(self.state, events)

                # --- surface & altitude effects ---
                if self.config.enable_surface_effects:
                    self.state = apply_surface_effects(self.state, self.config)

                # --- home advantage (continuous) ---
                if self.config.enable_venue_effects:
                    self.state = apply_home_advantage(self.state, self.config)

                # --- auto-substitutions ---
                sub_events = check_auto_substitutions(
                    self.state, self.sub_tracker, self.rng, self.config
                )
                if self.config.sport == SportType.HOCKEY:
                    sub_events.extend(
                        check_hockey_line_changes(self.state, self.sub_tracker, self.rng)
                    )
                events.extend(sub_events)

                # --- coach tactical adjustments (periodic) ---
                if self.config.enable_coach_effects and self.state.tick % 100 == 0:
                    self._apply_coach_effects()

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

        # Post-game: update ELO ratings and team stats
        update_elo_from_state(self.state)
        update_team_stats_from_state(self.state)

        yield self.state, self.state.events[-1:]
        logger.info("Simulation complete: %s", self.state.score_summary)

    def _apply_coach_effects(self) -> None:
        """Periodic coach influence — motivation pushes player morale toward team momentum."""
        for team in (self.state.home_team, self.state.away_team):
            motivation = team.coach.motivation
            for p in team.active_players:
                diff = team.momentum - p.morale
                p.morale = min(1.0, max(0.0, p.morale + diff * motivation * 0.02))
