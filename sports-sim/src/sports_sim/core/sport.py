"""Abstract Sport interface — every sport module must implement this."""

from __future__ import annotations

from abc import ABC, abstractmethod

from sports_sim.core.models import GameEvent, GameState, SimulationConfig, Team
import numpy as np
from typing import Optional


class Sport(ABC):
    """Base class that each sport plugin must implement."""

    # Optional RNG that concrete sports may use; engine will provide a seeded RNG.
    _rng: Optional[np.random.Generator] = None

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def default_periods(self) -> int: ...

    @property
    @abstractmethod
    def default_period_length(self) -> float:
        """Period length in minutes."""
        ...

    @property
    @abstractmethod
    def field_width(self) -> float: ...

    @property
    @abstractmethod
    def field_height(self) -> float: ...

    @property
    @abstractmethod
    def players_per_side(self) -> int: ...

    @abstractmethod
    def create_default_teams(self) -> tuple[Team, Team]:
        """Return a pair of teams with default rosters for this sport."""
        ...

    @abstractmethod
    def setup_positions(self, state: GameState) -> GameState:
        """Place players and ball in starting positions."""
        ...

    @abstractmethod
    def tick(self, state: GameState, config: SimulationConfig) -> tuple[GameState, list[GameEvent]]:
        """Advance the simulation by one tick. Return updated state and new events."""
        ...

    @abstractmethod
    def is_valid_state(self, state: GameState) -> bool:
        """Check if a game state is valid for this sport's rules."""
        ...

    def post_event(self, state: GameState, event: GameEvent, config: SimulationConfig) -> GameState:
        """Hook called after each event — can update momentum, morale, etc."""
        return state
