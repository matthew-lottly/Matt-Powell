"""Domain models: Player, Team, Ball, GameState, GameEvent, Venue, Coach, and configuration."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import numpy as np
from pydantic import BaseModel, Field, ConfigDict


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SportType(str, Enum):
    SOCCER = "soccer"
    BASKETBALL = "basketball"
    BASEBALL = "baseball"
    FOOTBALL = "football"
    HOCKEY = "hockey"
    TENNIS = "tennis"
    GOLF = "golf"
    CRICKET = "cricket"
    BOXING = "boxing"
    MMA = "mma"
    RACING = "racing"


class InjuryStatus(str, Enum):
    HEALTHY = "healthy"
    DAY_TO_DAY = "day_to_day"
    QUESTIONABLE = "questionable"
    PROBABLE = "probable"
    DOUBTFUL = "doubtful"
    OUT = "out"
    IR = "injured_reserve"
    SUSPENDED = "suspended"


class CoachStatus(str, Enum):
    ACTIVE = "active"
    SICK = "sick"
    EJECTED = "ejected"
    SUSPENDED = "suspended"


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
    # Football-specific
    TOUCHDOWN = "touchdown"
    FIELD_GOAL = "field_goal"
    EXTRA_POINT = "extra_point"
    TWO_POINT_CONVERSION = "two_point_conversion"
    SAFETY = "safety"
    SACK = "sack"
    INTERCEPTION = "interception"
    FUMBLE = "fumble"
    PUNT = "punt"
    KICKOFF = "kickoff"
    RUSH = "rush"
    RECEPTION = "reception"
    INCOMPLETE_PASS = "incomplete_pass"
    PENALTY_FLAG = "penalty_flag"
    # Hockey-specific
    POWER_PLAY = "power_play"
    PENALTY_MINUTES = "penalty_minutes"
    FACE_OFF = "face_off"
    ICING = "icing"
    SAVE = "save"
    HAT_TRICK = "hat_trick"
    EMPTY_NET = "empty_net"
    # Tennis-specific
    ACE = "ace"
    DOUBLE_FAULT = "double_fault"
    WINNER = "winner"
    UNFORCED_ERROR = "unforced_error"
    BREAK_POINT = "break_point"
    SET_WON = "set_won"
    MATCH_POINT = "match_point"
    SERVE = "serve"
    RETURN = "return"
    VOLLEY = "volley"
    # Golf-specific
    TEE_SHOT = "tee_shot"
    FAIRWAY_HIT = "fairway_hit"
    GREEN_IN_REGULATION = "green_in_regulation"
    PUTT = "putt"
    BIRDIE = "birdie"
    EAGLE = "eagle"
    BOGEY = "bogey"
    PAR = "par"
    HOLE_COMPLETE = "hole_complete"
    # Cricket-specific
    WICKET = "wicket"
    BOUNDARY_FOUR = "boundary_four"
    SIX = "six"
    OVER_COMPLETE = "over_complete"
    MAIDEN_OVER = "maiden_over"
    LBW = "lbw"
    CAUGHT = "caught"
    BOWLED = "bowled"
    RUN_OUT = "run_out"
    WIDE = "wide"
    NO_BALL = "no_ball"
    # Boxing/MMA-specific
    PUNCH = "punch"
    KNOCKOUT = "knockout"
    TKO = "tko"
    DECISION = "decision"
    ROUND_END = "round_end"
    KNOCKDOWN = "knockdown"
    CLINCH = "clinch"
    SUBMISSION = "submission"
    TAKEDOWN = "takedown"
    GROUND_STRIKE = "ground_strike"
    SPLIT_DECISION = "split_decision"
    # Racing-specific
    LAP_COMPLETE = "lap_complete"
    PIT_STOP = "pit_stop"
    OVERTAKE = "overtake"
    CRASH = "crash"
    YELLOW_FLAG = "yellow_flag"
    CHECKERED_FLAG = "checkered_flag"
    DNF = "dnf"
    FASTEST_LAP = "fastest_lap"


class Weather(str, Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    SNOW = "snow"
    WIND = "wind"
    EXTREME_HEAT = "extreme_heat"
    FOG = "fog"
    FREEZING = "freezing"
    HUMID = "humid"


class SurfaceType(str, Enum):
    NATURAL_GRASS = "natural_grass"
    ARTIFICIAL_TURF = "artificial_turf"
    FIELDTURF = "fieldturf"
    HYBRID_GRASS = "hybrid_grass"
    DIRT = "dirt"          # baseball infield
    HARDWOOD = "hardwood"  # basketball court
    ICE = "ice"            # hockey
    CLAY = "clay"          # tennis
    HARD_COURT = "hard_court"  # tennis
    GRASS_COURT = "grass_court"  # tennis (Wimbledon)
    ASPHALT = "asphalt"    # racing circuits
    CANVAS = "canvas"      # boxing/MMA ring


class VenueType(str, Enum):
    OPEN_AIR = "open_air"
    DOME = "dome"
    RETRACTABLE_ROOF = "retractable_roof"
    INDOOR_ARENA = "indoor_arena"
    RINK = "rink"          # hockey
    TENNIS_CENTER = "tennis_center"
    GOLF_COURSE = "golf_course"
    CRICKET_GROUND = "cricket_ground"
    BOXING_ARENA = "boxing_arena"
    OCTAGON = "octagon"    # MMA
    RACE_TRACK = "race_track"


# ---------------------------------------------------------------------------
# Venue / Stadium
# ---------------------------------------------------------------------------


class Venue(BaseModel):
    """Stadium or arena where the game is played."""
    name: str = "Default Stadium"
    city: str = ""
    state: str = ""
    capacity: int = 50000
    venue_type: VenueType = VenueType.OPEN_AIR
    surface: SurfaceType = SurfaceType.NATURAL_GRASS
    altitude_m: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0
    # Dimensions
    field_length_m: float = 105.0
    field_width_m: float = 68.0
    # Ballpark-specific (baseball)
    left_field_m: float = 100.0
    center_field_m: float = 122.0
    right_field_m: float = 100.0
    # Indoor climate control
    climate_controlled: bool = False
    indoor_temp_c: float = 22.0
    # Surface quality degrades over the season
    surface_quality: float = Field(default=0.9, ge=0.0, le=1.0)
    # Fan noise factor (larger/louder venues = more home advantage)
    noise_factor: float = Field(default=0.7, ge=0.0, le=1.0)
    # Difficulty ranking (0.0 = easy, 1.0 = very difficult for visitors)
    difficulty_rating: float = Field(default=0.5, ge=0.0, le=1.0)
    home_win_pct: float = Field(default=0.55, ge=0.0, le=1.0)
    visitor_fatigue_factor: float = Field(default=0.0, ge=0.0, le=0.5)

    @property
    def is_outdoor(self) -> bool:
        return self.venue_type in (VenueType.OPEN_AIR, VenueType.RETRACTABLE_ROOF)

    @property
    def weather_exposed(self) -> bool:
        """Whether weather affects gameplay (domes/arenas are climate-controlled)."""
        if self.venue_type == VenueType.DOME:
            return False
        if self.venue_type == VenueType.INDOOR_ARENA:
            return False
        return True


# ---------------------------------------------------------------------------
# Coach
# ---------------------------------------------------------------------------


class CoachStyle(str, Enum):
    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    CONSERVATIVE = "conservative"
    DEFENSIVE = "defensive"
    UP_TEMPO = "up_tempo"
    GROUND_AND_POUND = "ground_and_pound"
    SPREAD = "spread"
    SMALL_BALL = "small_ball"
    POWER_HITTING = "power_hitting"
    CONTACT_HITTING = "contact_hitting"


class Coach(BaseModel):
    """Head coach — influences tactics, substitution patterns, and team morale."""
    name: str = "Coach"
    experience_years: int = 10
    style: CoachStyle = CoachStyle.BALANCED
    status: CoachStatus = CoachStatus.ACTIVE
    # 0-1 ratings
    play_calling: float = Field(default=0.6, ge=0.0, le=1.0)
    player_development: float = Field(default=0.6, ge=0.0, le=1.0)
    clock_management: float = Field(default=0.6, ge=0.0, le=1.0)
    motivation: float = Field(default=0.6, ge=0.0, le=1.0)
    adaptability: float = Field(default=0.6, ge=0.0, le=1.0)
    challenge_tendency: float = Field(default=0.5, ge=0.0, le=1.0)

    @property
    def morale_boost(self) -> float:
        """How much the coach positively affects team morale each tick."""
        return self.motivation * 0.005

    @property
    def tactical_bonus(self) -> float:
        """Modifier applied to team event probabilities."""
        return (self.play_calling - 0.5) * 0.1


# ---------------------------------------------------------------------------
# Team Sliders (user-adjustable per-sim)
# ---------------------------------------------------------------------------


class TeamSliders(BaseModel):
    """User-adjustable strategy sliders for a team, 0.0-1.0."""
    offensive_aggression: float = Field(default=0.5, ge=0.0, le=1.0)
    defensive_intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    pace: float = Field(default=0.5, ge=0.0, le=1.0)
    pressing: float = Field(default=0.5, ge=0.0, le=1.0)
    # Sport-specific
    three_point_tendency: float = Field(default=0.5, ge=0.0, le=1.0)  # basketball
    run_pass_ratio: float = Field(default=0.5, ge=0.0, le=1.0)       # football
    steal_attempt_rate: float = Field(default=0.3, ge=0.0, le=1.0)   # baseball
    bunt_tendency: float = Field(default=0.2, ge=0.0, le=1.0)        # baseball
    blitz_frequency: float = Field(default=0.3, ge=0.0, le=1.0)      # football
    substitution_aggression: float = Field(default=0.5, ge=0.0, le=1.0)
    # Hockey
    forecheck_intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    power_play_aggression: float = Field(default=0.5, ge=0.0, le=1.0)
    line_change_frequency: float = Field(default=0.5, ge=0.0, le=1.0)
    # Tennis
    serve_aggression: float = Field(default=0.5, ge=0.0, le=1.0)
    net_approach: float = Field(default=0.3, ge=0.0, le=1.0)
    # Golf
    risk_taking: float = Field(default=0.5, ge=0.0, le=1.0)
    # Cricket
    batting_aggression: float = Field(default=0.5, ge=0.0, le=1.0)
    bowling_variation: float = Field(default=0.5, ge=0.0, le=1.0)
    # Boxing/MMA
    aggression_level: float = Field(default=0.5, ge=0.0, le=1.0)
    counter_tendency: float = Field(default=0.5, ge=0.0, le=1.0)
    clinch_tendency: float = Field(default=0.3, ge=0.0, le=1.0)
    # Racing
    tire_management: float = Field(default=0.5, ge=0.0, le=1.0)
    pit_strategy: float = Field(default=0.5, ge=0.0, le=1.0)
    overtake_aggression: float = Field(default=0.5, ge=0.0, le=1.0)


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
    # Extended attributes
    awareness: float = Field(default=0.6, ge=0.0, le=1.0)
    leadership: float = Field(default=0.5, ge=0.0, le=1.0)
    clutch: float = Field(default=0.5, ge=0.0, le=1.0)
    durability: float = Field(default=0.7, ge=0.0, le=1.0)


class PlayerStats(BaseModel):
    """Accumulated in-game statistics for a player (per simulation or career)."""
    games_played: int = 0
    minutes_played: float = 0.0
    goals: int = 0
    assists: int = 0
    shots: int = 0
    shots_on_target: int = 0
    passes_completed: int = 0
    passes_attempted: int = 0
    tackles: int = 0
    fouls_committed: int = 0
    fouls_drawn: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    saves: int = 0
    interceptions: int = 0
    turnovers: int = 0
    # Basketball / general
    points: int = 0
    rebounds: int = 0
    steals: int = 0
    blocks: int = 0
    three_pointers_made: int = 0
    free_throws_made: int = 0
    free_throws_attempted: int = 0
    # Baseball
    at_bats: int = 0
    hits: int = 0
    home_runs: int = 0
    rbis: int = 0
    strikeouts: int = 0
    walks: int = 0
    batting_average: float = 0.0
    era: float = 0.0
    # Football
    passing_yards: int = 0
    rushing_yards: int = 0
    receiving_yards: int = 0
    touchdowns: int = 0
    sacks: int = 0
    # Tennis / individual
    aces: int = 0
    double_faults: int = 0
    winners: int = 0
    unforced_errors: int = 0
    # General rating
    match_rating: float = Field(default=6.0, ge=0.0, le=10.0)


class Player(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str
    number: int
    position: str
    attributes: PlayerAttributes = Field(default_factory=PlayerAttributes)
    stats: PlayerStats = Field(default_factory=PlayerStats)
    stamina: float = Field(default=1.0, ge=0.0, le=1.0, description="Current stamina 0-1")
    morale: float = Field(default=0.7, ge=0.0, le=1.0)
    is_injured: bool = False
    injury_severity: float = 0.0
    injury_type: str = ""  # e.g. "hamstring", "concussion", "ACL"
    injury_status: str = "healthy"  # maps to InjuryStatus values
    x: float = 0.0
    y: float = 0.0
    minutes_played: float = 0.0
    # Career / season stats reference (not simulated, for display)
    age: int = 25
    height_cm: int = 183
    weight_kg: int = 84
    # Form (rolling average of recent match ratings, 0-1)
    form: float = Field(default=0.6, ge=0.0, le=1.0)

    @property
    def effective_skill(self) -> float:
        fatigue_penalty = max(0.0, 1.0 - self.stamina) * 0.3
        morale_bonus = (self.morale - 0.5) * 0.1
        return max(0.05, min(1.0, self.attributes.skill - fatigue_penalty + morale_bonus))


# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------


class TeamStats(BaseModel):
    """Accumulated team-level statistics across games."""
    wins: int = 0
    losses: int = 0
    draws: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points_for: int = 0
    points_against: int = 0
    home_wins: int = 0
    away_wins: int = 0
    streak: int = 0  # positive = win streak, negative = loss streak
    last_5: list[str] = Field(default_factory=list)  # ["W","W","L","D","W"]

    @property
    def games_played(self) -> int:
        return self.wins + self.losses + self.draws

    @property
    def win_pct(self) -> float:
        gp = self.games_played
        return self.wins / gp if gp > 0 else 0.0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against


class Team(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str
    abbreviation: str = ""
    city: str = ""
    players: list[Player] = Field(default_factory=list)
    bench: list[Player] = Field(default_factory=list)
    formation: str = ""
    tactic: str = "balanced"
    score: int = 0
    timeouts_remaining: int = 0
    momentum: float = Field(default=0.5, ge=0.0, le=1.0)
    coach: Coach = Field(default_factory=Coach)
    venue: Venue = Field(default_factory=Venue)
    sliders: TeamSliders = Field(default_factory=TeamSliders)
    stats: TeamStats = Field(default_factory=TeamStats)
    # Overall team ratings (auto-computed or set)
    overall_offense: float = Field(default=0.5, ge=0.0, le=1.0)
    overall_defense: float = Field(default=0.5, ge=0.0, le=1.0)
    overall_special_teams: float = Field(default=0.5, ge=0.0, le=1.0)
    # ELO / Glicko rating
    elo_rating: float = Field(default=1500.0, ge=0.0)
    elo_k_factor: float = Field(default=32.0, ge=1.0)
    # Form (rolling window of recent results)
    form_rating: float = Field(default=0.5, ge=0.0, le=1.0)
    # Depth rating (bench quality)
    depth_rating: float = Field(default=0.5, ge=0.0, le=1.0)

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
    # New fields derived from venue
    surface_type: SurfaceType = SurfaceType.NATURAL_GRASS
    venue_type: VenueType = VenueType.OPEN_AIR
    is_climate_controlled: bool = False
    # Precipitation/visibility
    precipitation_mm_hr: float = 0.0
    visibility_km: float = 10.0
    dew_point_c: float = 15.0
    barometric_pressure_hpa: float = 1013.0


# ---------------------------------------------------------------------------
# Game State
# ---------------------------------------------------------------------------


class GameState(BaseModel):
    game_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    sport: SportType
    league: str | None = None
    home_team: Team
    away_team: Team
    ball: Ball = Field(default_factory=Ball)
    environment: Environment = Field(default_factory=Environment)
    venue: Venue = Field(default_factory=Venue)
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
    league: str | None = None
    seed: int | None = None
    ticks_per_second: int = 10
    realtime: bool = False
    fidelity: str = Field(default="medium", pattern="^(fast|medium|high)$")
    enable_fatigue: bool = True
    enable_injuries: bool = True
    enable_weather: bool = True
    enable_momentum: bool = True
    enable_referee_errors: bool = True
    enable_venue_effects: bool = True
    enable_coach_effects: bool = True
    enable_surface_effects: bool = True
    noise_level: float = Field(default=0.1, ge=0.0, le=1.0)
    home_advantage: float = Field(default=0.05, ge=0.0, le=0.2)
    environment: Environment = Field(default_factory=Environment)
    venue: Venue | None = None
    home_sliders: TeamSliders | None = None
    away_sliders: TeamSliders | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sport": "soccer",
                "seed": 42,
                "fidelity": "medium",
                "enable_fatigue": True,
            }
        }
    )


# ---------------------------------------------------------------------------
# Home Advantage Sliders
# ---------------------------------------------------------------------------


class HomeAdvantageSliders(BaseModel):
    """Adjustable home-field advantage parameters."""
    crowd_involvement: float = Field(default=0.7, ge=0.0, le=1.0)
    elevation_factor: float = Field(default=0.0, ge=0.0, le=1.0)
    travel_fatigue: float = Field(default=0.1, ge=0.0, le=1.0)
    noise_level: float = Field(default=0.7, ge=0.0, le=1.0)
    weather_harshness: float = Field(default=0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Heatmap / Shot Chart
# ---------------------------------------------------------------------------


class HeatmapBin(BaseModel):
    """A single bin in a spatial heatmap."""
    x: float
    y: float
    count: int = 0
    success_count: int = 0
    event_type: str = ""

    @property
    def success_rate(self) -> float:
        return self.success_count / max(1, self.count)


class TradeRequest(BaseModel):
    """Request to trade a player between teams."""
    from_team_abbr: str
    to_team_abbr: str
    player_id: str
    sport: str
