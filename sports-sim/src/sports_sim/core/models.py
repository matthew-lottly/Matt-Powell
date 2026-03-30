"""Domain models: Player, Team, Ball, GameState, GameEvent, and configuration."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SportType(str, Enum):
    SOCCER = "soccer"
    BASKETBALL = "basketball"
    BASEBALL = "baseball"


class EventType(str, Enum):
    GOAL = "goal"
    SHOT = "shot"
    PASS = "pass"
    FOUL = "foul"
    TURNOVER = "turnover"
    SUBSTITUTION = "substitution"
    INJURY = "injury"
    TIMEOUT = "timeout"
    PERIOD_START = "period_start"
    PERIOD_END = "period_end"
    GAME_START = "game_start"
    GAME_END = "game_end"
    POSSESSION_CHANGE = "possession_change"
    FREE_THROW = "free_throw"
    PENALTY = "penalty"
    STRIKEOUT = "strikeout"
    HIT = "hit"
    HOME_RUN = "home_run"
    OUT = "out"
    RUN = "run"
    WALK = "walk"
    STEAL = "steal"
    REBOUND = "rebound"
    BLOCK = "block"
    ASSIST = "assist"
    CARD = "card"
    YELLOW_CARD = "yellow_card"
    RED_CARD = "red_card"
    THREE_POINTER = "three_pointer"
    CORNER = "corner"
    OFFSIDE = "offside"


class Weather(str, Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    SNOW = "snow"
    WIND = "wind"
    EXTREME_HEAT = "extreme_heat"


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------


class PlayerAttributes(BaseModel):
    speed: float = Field(default=0.7, ge=0.0, le=1.0, description="0-1 normalized speed rating")
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    accuracy: float = Field(default=0.6, ge=0.0, le=1.0)
    endurance: float = Field(default=0.6, ge=0.0, le=1.0)
    skill: float = Field(default=0.6, ge=0.0, le=1.0)
    decision_making: float = Field(default=0.6, ge=0.0, le=1.0)
    aggression: float = Field(default=0.4, ge=0.0, le=1.0)
    composure: float = Field(default=0.6, ge=0.0, le=1.0)


class Player(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str
    number: int
    position: str
    attributes: PlayerAttributes = Field(default_factory=PlayerAttributes)
    stamina: float = Field(default=1.0, ge=0.0, le=1.0, description="Current stamina 0-1")
    morale: float = Field(default=0.7, ge=0.0, le=1.0)
    is_injured: bool = False
    injury_severity: float = 0.0
    x: float = 0.0
    y: float = 0.0
    minutes_played: float = 0.0

    @property
    def effective_skill(self) -> float:
        fatigue_penalty = max(0.0, 1.0 - self.stamina) * 0.3
        morale_bonus = (self.morale - 0.5) * 0.1
        return max(0.05, min(1.0, self.attributes.skill - fatigue_penalty + morale_bonus))


# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------


class Team(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str
    abbreviation: str = ""
    players: list[Player] = Field(default_factory=list)
    bench: list[Player] = Field(default_factory=list)
    formation: str = ""
    tactic: str = "balanced"
    score: int = 0
    timeouts_remaining: int = 0
    momentum: float = Field(default=0.5, ge=0.0, le=1.0)

    @property
    def active_players(self) -> list[Player]:
        return [p for p in self.players if not p.is_injured]

    @property
    def avg_stamina(self) -> float:
        active = self.active_players
        if not active:
            return 0.0
        return sum(p.stamina for p in active) / len(active)


# ---------------------------------------------------------------------------
# Ball / Game Object
# ---------------------------------------------------------------------------


class Ball(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    spin: float = 0.0
    possessed_by: str | None = None


# ---------------------------------------------------------------------------
# Game Event
# ---------------------------------------------------------------------------


class GameEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    type: EventType
    time: float = 0.0
    period: int = 1
    team_id: str | None = None
    player_id: str | None = None
    secondary_player_id: str | None = None
    x: float | None = None
    y: float | None = None
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------


class Environment(BaseModel):
    weather: Weather = Weather.CLEAR
    temperature_c: float = 22.0
    humidity: float = 0.5
    wind_speed_kph: float = 0.0
    wind_direction_deg: float = 0.0
    altitude_m: float = 0.0
    surface_quality: float = Field(default=0.9, ge=0.0, le=1.0)
    is_home_game: bool = True
    crowd_intensity: float = Field(default=0.7, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Game State
# ---------------------------------------------------------------------------


class GameState(BaseModel):
    game_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    sport: SportType
    home_team: Team
    away_team: Team
    ball: Ball = Field(default_factory=Ball)
    environment: Environment = Field(default_factory=Environment)
    clock: float = 0.0
    period: int = 1
    total_periods: int = 2
    period_length: float = 45.0
    is_running: bool = False
    is_finished: bool = False
    possession_team_id: str | None = None
    events: list[GameEvent] = Field(default_factory=list)
    tick: int = 0
    seed: int = Field(default_factory=lambda: int(np.random.default_rng().integers(0, 2**31)))

    @property
    def score_summary(self) -> str:
        return f"{self.home_team.name} {self.home_team.score} - {self.away_team.score} {self.away_team.name}"


# ---------------------------------------------------------------------------
# Simulation Config
# ---------------------------------------------------------------------------


class SimulationConfig(BaseModel):
    sport: SportType = SportType.SOCCER
    seed: int | None = None
    ticks_per_second: int = 10
    realtime: bool = False
    fidelity: str = Field(default="medium", pattern="^(fast|medium|high)$")
    enable_fatigue: bool = True
    enable_injuries: bool = True
    enable_weather: bool = True
    enable_momentum: bool = True
    enable_referee_errors: bool = True
    noise_level: float = Field(default=0.1, ge=0.0, le=1.0)
    home_advantage: float = Field(default=0.05, ge=0.0, le=0.2)
    environment: Environment = Field(default_factory=Environment)

    class Config:
        json_schema_extra = {
            "example": {
                "sport": "soccer",
                "seed": 42,
                "fidelity": "medium",
                "enable_fatigue": True,
            }
        }
