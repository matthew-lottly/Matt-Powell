"""FastAPI application — REST + WebSocket API for sports-sim."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from sports_sim.core.engine import Simulation
from sports_sim.core.models import (
    Coach,
    CoachStyle,
    Environment,
    GameState,
    SimulationConfig,
    SportType,
    SurfaceType,
    VenueType,
    Weather,
    Venue,
    TeamSliders,
)

# Module logger and in-memory simulation registry
logger = logging.getLogger(__name__)
_simulations: dict[str, dict[str, object]] = {}
# Simple registry cache to avoid repeated imports/merges
_registry_cache: dict[tuple[str, str | None], dict[str, object]] = {}

# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Sports-sim API starting")
    yield
    _simulations.clear()
    logger.info("Sports-sim API shut down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Sports Simulation API",
    version="0.2.0",
    description="Run and stream multi-sport simulations with full team/player/venue/coach customization.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class SlidersRequest(BaseModel):
    offensive_aggression: float = 0.5
    defensive_intensity: float = 0.5
    pace: float = 0.5
    pressing: float = 0.5
    three_point_tendency: float = 0.5
    run_pass_ratio: float = 0.5
    steal_attempt_rate: float = 0.3
    bunt_tendency: float = 0.2
    blitz_frequency: float = 0.3
    substitution_aggression: float = 0.5
    # Hockey
    forecheck_intensity: float = 0.5
    power_play_aggression: float = 0.5
    line_change_frequency: float = 0.5
    # Tennis
    serve_aggression: float = 0.5
    net_approach: float = 0.3
    # Golf / Cricket / Racing
    risk_taking: float = 0.5
    batting_aggression: float = 0.5
    bowling_variation: float = 0.5
    # Boxing / MMA
    aggression_level: float = 0.5
    counter_tendency: float = 0.3
    clinch_tendency: float = 0.3
    # Racing
    tire_management: float = 0.5
    pit_strategy: float = 0.5
    overtake_aggression: float = 0.5


class CreateSimRequest(BaseModel):
    sport: str = "soccer"
    seed: int | None = None
    fidelity: str = "medium"
    ticks_per_second: int = 10
    enable_fatigue: bool = True
    enable_injuries: bool = True
    enable_weather: bool = True
    enable_momentum: bool = True
    enable_venue_effects: bool = True
    enable_coach_effects: bool = True
    enable_surface_effects: bool = True
    weather: str = "clear"
    temperature_c: float = 22.0
    wind_speed_kph: float = 0.0
    humidity: float = 0.5
    # Team selection
    home_team: str | None = None  # team abbreviation
    away_team: str | None = None
    # League selection (optional)
    league: str | None = None
    # Venue override
    venue_name: str | None = None
    venue_type: str | None = None
    surface_type: str | None = None
    altitude_m: float | None = None
    # Sliders
    home_sliders: SlidersRequest | None = None
    away_sliders: SlidersRequest | None = None


class SubstitutionRequest(BaseModel):
    team: str  # "home" or "away"
    player_out_id: str
    player_in_id: str


class PlayerUpdateRequest(BaseModel):
    team: str  # "home" or "away"
    player_id: str
    name: str | None = None
    number: int | None = None
    position: str | None = None
    speed: float | None = None
    strength: float | None = None
    accuracy: float | None = None
    endurance: float | None = None
    skill: float | None = None
    decision_making: float | None = None
    aggression: float | None = None
    composure: float | None = None


class SimSummary(BaseModel):
    game_id: str
    sport: str
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    is_finished: bool
    total_events: int


# ---------------------------------------------------------------------------
# Helpers — team/venue loading
# ---------------------------------------------------------------------------

def _load_teams(sport: str, home_abbr: str | None, away_abbr: str | None, league: str | None = None):
    """Load real teams by abbreviation, or return None to use sport defaults."""
    if not home_abbr and not away_abbr:
        return None, None

    loaders: dict[str, Any] = {}
    # Choose loader based on sport and optional league
    if sport == "football":
        if league is None or league == "nfl":
            from sports_sim.data.rosters_nfl import get_nfl_team
            loaders["get"] = get_nfl_team
        else:
            return None, None
    elif sport == "basketball":
        if league is None or league == "nba":
            from sports_sim.data.rosters_nba import get_nba_team
            loaders["get"] = get_nba_team
        else:
            return None, None
    elif sport == "baseball":
        if league is None or league == "mlb":
            from sports_sim.data.rosters_mlb import get_mlb_team
            loaders["get"] = get_mlb_team
        else:
            return None, None
    elif sport == "hockey":
        if league is None or league == "nhl":
            from sports_sim.data.rosters_nhl import get_nhl_team
            loaders["get"] = get_nhl_team
        else:
            return None, None
    else:
        # Individual sports (tennis, golf, boxing, MMA, racing, cricket) use defaults
        return None, None

    getter = loaders["get"]
    h = getter(home_abbr) if home_abbr else None
    a = getter(away_abbr) if away_abbr else None

    # Deep-copy so mutations don't bleed across sims
    if h:
        h = h.model_copy(deep=True)
    if a:
        a = a.model_copy(deep=True)
    return h, a


def _available_teams(sport: str, league: str | None = None) -> list[dict[str, str]]:
    """List available team abbreviations and names for a sport optionally filtered by league."""
    teams: dict[str, Any] = {}
    if sport == "football":
        if league is None or league == "nfl":
            from sports_sim.data.rosters_nfl import get_all_nfl_teams
            teams = get_all_nfl_teams()
        else:
            return []
    elif sport == "soccer":
        # support MLS and EPL sample rosters
        if league is None or league == "mls":
            try:
                from sports_sim.data.rosters_mls import get_all_mls_teams
                teams = get_all_mls_teams()
            except Exception:
                teams = {}
        elif league == "epl":
            try:
                from sports_sim.data.rosters_epl import get_all_epl_teams
                teams = get_all_epl_teams()
            except Exception:
                teams = {}
        elif league == "ncaasoc":
            try:
                from sports_sim.data.rosters_ncaasoc import get_all_ncaasoc_teams
                teams = get_all_ncaasoc_teams()
            except Exception:
                teams = {}
        else:
            return []
    elif sport == "basketball":
        if league is None or league == "nba":
            from sports_sim.data.rosters_nba import get_all_nba_teams
            teams = get_all_nba_teams()
        else:
            return []
            if league == "euro":
                try:
                    from sports_sim.data.rosters_eurobasket import get_all_euro_teams
                    teams = get_all_euro_teams()
                except Exception:
                    return []
            else:
                return []
    elif sport == "baseball":
        if league is None or league == "mlb":
            from sports_sim.data.rosters_mlb import get_all_mlb_teams
            teams = get_all_mlb_teams()
        else:
            return []
            if league == "npb":
                try:
                    from sports_sim.data.rosters_npb import get_all_npb_teams
                    teams = get_all_npb_teams()
                except Exception:
                    return []
            else:
                return []
    elif sport == "hockey":
        if league is None or league == "nhl":
            from sports_sim.data.rosters_nhl import get_all_nhl_teams
            teams = get_all_nhl_teams()
        else:
            return []
            if league == "khl":
                try:
                    from sports_sim.data.rosters_khl import get_all_khl_teams
                    teams = get_all_khl_teams()
                except Exception:
                    return []
            else:
                return []
    else:
        if league is None or league == "ipl":
            try:
                from sports_sim.data.rosters_ipl import get_all_ipl_teams
                teams = get_all_ipl_teams()
            except Exception:
                return []
        else:
            return []
    return [{"abbreviation": k, "name": t.name, "city": t.city} for k, t in teams.items()]


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/api/sports")
async def list_sports():
    return {"sports": [s.value for s in SportType]}


@app.get("/api/leagues")
async def list_leagues(sport: str | None = None):
    """List known leagues for a given sport (or all leagues if sport omitted)."""
    from sports_sim.data.leagues import get_leagues_for_sport, LEAGUES
    if sport:
        return {"sport": sport, "leagues": get_leagues_for_sport(sport)}
    return {"leagues": LEAGUES}


@app.get("/api/teams/{sport}")
async def list_teams(sport: str, league: str | None = None, page: int = 1, per_page: int = 200):
    """List all available real teams for a given sport, optionally filtered by league."""
    teams = _available_teams(sport, league)
    # pagination
    total = len(teams)
    if per_page <= 0:
        per_page = 200
    start = (max(1, page) - 1) * per_page
    end = start + per_page
    paged = teams[start:end]
    return {"sport": sport, "league": league, "total": total, "page": page, "per_page": per_page, "teams": paged}


@app.get("/api/teams/{sport}/{abbr}")
async def get_team_detail(sport: str, abbr: str, league: str | None = None):
    """Get full roster and venue info for a specific team."""
    h, _ = _load_teams(sport, abbr, None, league)
    if not h:
        raise HTTPException(404, f"Team {abbr} not found for {sport}")
    return {
        "abbreviation": abbr,
        "name": h.name,
        "city": h.city,
        "coach": {"name": h.coach.name, "style": h.coach.style.value},
        "venue": {
            "name": h.venue.name, "city": h.venue.city,
            "venue_type": h.venue.venue_type.value,
            "surface": h.venue.surface.value,
            "capacity": h.venue.capacity,
            "altitude_m": h.venue.altitude_m,
            "weather_exposed": h.venue.weather_exposed,
        } if h.venue else None,
        "players": [
            {"id": p.id, "name": p.name, "number": p.number, "position": p.position,
             "age": p.age, "height_cm": p.height_cm, "weight_kg": p.weight_kg,
             "attributes": p.attributes.model_dump()}
            for p in h.players
        ],
        "bench": [
            {"id": p.id, "name": p.name, "number": p.number, "position": p.position,
             "attributes": p.attributes.model_dump()}
            for p in h.bench
        ],
    }


@app.get("/api/venues/{sport}")
async def list_venues(sport: str, league: str | None = None, page: int = 1, per_page: int = 200):
    """List known venues for a sport. If `league` is provided, return venues for that league when available."""
    # Import base registries
    from sports_sim.data.venues import NFL_VENUES, NBA_VENUES, MLB_VENUES, NHL_VENUES

    registries: dict[str, dict[str, object]] = {
        "football": NFL_VENUES,
        "basketball": NBA_VENUES,
        "baseball": MLB_VENUES,
        "hockey": NHL_VENUES,
    }

    # Include soccer/base registries if any (merge per-league below)
    registries.setdefault("soccer", {})
    registries.setdefault("cricket", {})

    # Attach known per-league collections
    try:
        from sports_sim.data.venues_epl import EPL_VENUES
        registries.setdefault("soccer", {}).update(EPL_VENUES)
    except Exception:
        pass
    try:
        from sports_sim.data.venues_npb import NPB_VENUES
        registries.setdefault("baseball", {}).update(NPB_VENUES)
    except Exception:
        pass
    try:
        from sports_sim.data.venues_ipl import IPL_VENUES
        registries.setdefault("cricket", {}).update(IPL_VENUES)
    except Exception:
        pass
    try:
        from sports_sim.data.venues_khl import KHL_VENUES
        registries.setdefault("hockey", {}).update(KHL_VENUES)
    except Exception:
        pass

    # If a league is requested, try to return only that league's venue set
    if league:
        league = league.lower()
        try:
            if league == "epl":
                from sports_sim.data.venues_epl import EPL_VENUES as _lv
                reg = _lv
            elif league == "npb":
                from sports_sim.data.venues_npb import NPB_VENUES as _lv
                reg = _lv
            elif league == "ipl":
                from sports_sim.data.venues_ipl import IPL_VENUES as _lv
                reg = _lv
            elif league == "khl":
                from sports_sim.data.venues_khl import KHL_VENUES as _lv
                reg = _lv
            else:
                # Unknown league: fall back to sport-wide registry
                reg = registries.get(sport, {})
        except Exception:
            reg = registries.get(sport, {})
    else:
        reg = registries.get(sport, {})

    items = [
            {"abbreviation": k, "name": v.name, "city": v.city,
             "venue_type": v.venue_type.value, "surface": v.surface.value,
             "capacity": v.capacity, "altitude_m": v.altitude_m,
             "weather_exposed": v.weather_exposed}
            for k, v in reg.items()
        ]
    total = len(items)
    if per_page <= 0:
        per_page = 200
    start = (max(1, page) - 1) * per_page
    end = start + per_page
    paged = items[start:end]
    return {"sport": sport, "league": league, "total": total, "page": page, "per_page": per_page, "venues": paged}


@app.post("/api/simulations", response_model=SimSummary)
async def create_simulation(req: CreateSimRequest):
    # Load teams (pass requested league if provided)
    home_team, away_team = _load_teams(req.sport, req.home_team, req.away_team, req.league)

    # Build environment
    env = Environment(
        weather=Weather(req.weather),
        temperature_c=req.temperature_c,
        wind_speed_kph=req.wind_speed_kph,
        humidity=req.humidity,
    )

    # Venue override
    venue = None
    if req.venue_type:
        venue = Venue(
            venue_type=VenueType(req.venue_type),
            surface=SurfaceType(req.surface_type) if req.surface_type else SurfaceType.NATURAL_GRASS,
            altitude_m=req.altitude_m or 0.0,
            name=req.venue_name or "Custom Venue",
        )

    # Sliders
    home_sliders = TeamSliders(**req.home_sliders.model_dump()) if req.home_sliders else None
    away_sliders = TeamSliders(**req.away_sliders.model_dump()) if req.away_sliders else None

    config = SimulationConfig(
        sport=SportType(req.sport),
        seed=req.seed,
        ticks_per_second=req.ticks_per_second,
        fidelity=req.fidelity,
        enable_fatigue=req.enable_fatigue,
        enable_injuries=req.enable_injuries,
        enable_weather=req.enable_weather,
        enable_momentum=req.enable_momentum,
        enable_venue_effects=req.enable_venue_effects,
        enable_coach_effects=req.enable_coach_effects,
        enable_surface_effects=req.enable_surface_effects,
        environment=env,
        venue=venue,
        home_sliders=home_sliders,
        away_sliders=away_sliders,
    )
    sim = Simulation(config, home_team=home_team, away_team=away_team)
    gid = sim.state.game_id

    _simulations[gid] = {"sim": sim, "config": config}

    return SimSummary(
        game_id=gid,
        sport=req.sport,
        home_team=sim.state.home_team.name,
        away_team=sim.state.away_team.name,
        home_score=0,
        away_score=0,
        is_finished=False,
        total_events=0,
    )


@app.post("/api/simulations/{game_id}/run", response_model=SimSummary)
async def run_simulation(game_id: str):
    entry = _simulations.get(game_id)
    if not entry:
        raise HTTPException(404, "Simulation not found")
    sim: Simulation = entry["sim"]
    final = sim.run()
    return SimSummary(
        game_id=game_id,
        sport=final.sport.value,
        home_team=final.home_team.name,
        away_team=final.away_team.name,
        home_score=final.home_team.score,
        away_score=final.away_team.score,
        is_finished=True,
        total_events=len(final.events),
    )


@app.get("/api/simulations/{game_id}")
async def get_simulation(game_id: str):
    entry = _simulations.get(game_id)
    if not entry:
        raise HTTPException(404, "Simulation not found")
    sim: Simulation = entry["sim"]
    state = sim.state
    return {
        "game_id": game_id,
        "sport": state.sport.value,
        "score": {"home": state.home_team.score, "away": state.away_team.score},
        "home_team": state.home_team.name,
        "away_team": state.away_team.name,
        "period": state.period,
        "clock": round(state.clock, 2),
        "is_finished": state.is_finished,
        "total_events": len(state.events),
        "venue": {
            "name": state.venue.name,
            "venue_type": state.venue.venue_type.value,
            "surface": state.venue.surface.value,
            "weather_exposed": state.venue.weather_exposed,
        } if state.venue else None,
        "environment": {
            "weather": state.environment.weather.value,
            "temperature_c": state.environment.temperature_c,
            "wind_speed_kph": state.environment.wind_speed_kph,
            "humidity": state.environment.humidity,
            "surface_type": state.environment.surface_type.value,
            "altitude_m": state.environment.altitude_m,
        },
        "home_roster": [
            {"id": p.id, "name": p.name, "number": p.number, "position": p.position,
             "stamina": round(p.stamina, 2), "morale": round(p.morale, 2),
             "is_injured": p.is_injured}
            for p in state.home_team.players
        ],
        "away_roster": [
            {"id": p.id, "name": p.name, "number": p.number, "position": p.position,
             "stamina": round(p.stamina, 2), "morale": round(p.morale, 2),
             "is_injured": p.is_injured}
            for p in state.away_team.players
        ],
        "events": [
            {"type": e.type.value, "time": round(e.time, 2), "period": e.period,
             "description": e.description}
            for e in state.events[-50:]
        ],
    }


@app.get("/api/simulations/{game_id}/roster/{team}")
async def get_roster(game_id: str, team: str):
    """Get full roster details for home or away team in a simulation."""
    entry = _simulations.get(game_id)
    if not entry:
        raise HTTPException(404, "Simulation not found")
    sim: Simulation = entry["sim"]
    t = sim.state.home_team if team == "home" else sim.state.away_team
    return {
        "team": t.name,
        "coach": {"name": t.coach.name, "style": t.coach.style.value,
                  "play_calling": t.coach.play_calling, "motivation": t.coach.motivation},
        "venue": {"name": t.venue.name, "venue_type": t.venue.venue_type.value,
                  "surface": t.venue.surface.value} if t.venue else None,
        "sliders": t.sliders.model_dump(),
        "players": [
            {"id": p.id, "name": p.name, "number": p.number, "position": p.position,
             "age": p.age, "stamina": round(p.stamina, 2), "morale": round(p.morale, 2),
             "is_injured": p.is_injured, "minutes_played": round(p.minutes_played, 1),
             "attributes": p.attributes.model_dump()}
            for p in t.players
        ],
        "bench": [
            {"id": p.id, "name": p.name, "number": p.number, "position": p.position,
             "attributes": p.attributes.model_dump()}
            for p in t.bench
        ],
    }


@app.post("/api/simulations/{game_id}/substitute")
async def substitute_player(game_id: str, req: SubstitutionRequest):
    """Substitute a player from bench into the active roster."""
    entry = _simulations.get(game_id)
    if not entry:
        raise HTTPException(404, "Simulation not found")
    sim: Simulation = entry["sim"]
    team = sim.state.home_team if req.team == "home" else sim.state.away_team

    out_idx = next((i for i, p in enumerate(team.players) if p.id == req.player_out_id), None)
    in_idx = next((i for i, p in enumerate(team.bench) if p.id == req.player_in_id), None)

    if out_idx is None:
        raise HTTPException(400, "Player to substitute out not found in active roster")
    if in_idx is None:
        raise HTTPException(400, "Player to substitute in not found on bench")

    out_player = team.players[out_idx]
    in_player = team.bench.pop(in_idx)
    in_player.x = out_player.x
    in_player.y = out_player.y
    team.players[out_idx] = in_player
    team.bench.append(out_player)

    return {"substituted": True, "player_in": in_player.name, "player_out": out_player.name}


@app.put("/api/simulations/{game_id}/player")
async def update_player(game_id: str, req: PlayerUpdateRequest):
    """Update individual player attributes before or during a game."""
    entry = _simulations.get(game_id)
    if not entry:
        raise HTTPException(404, "Simulation not found")
    sim: Simulation = entry["sim"]
    team = sim.state.home_team if req.team == "home" else sim.state.away_team

    player = next((p for p in team.players + team.bench if p.id == req.player_id), None)
    if not player:
        raise HTTPException(404, "Player not found")

    if req.name is not None:
        player.name = req.name
    if req.number is not None:
        player.number = req.number
    if req.position is not None:
        player.position = req.position
    if req.speed is not None:
        player.attributes.speed = max(0.0, min(1.0, req.speed))
    if req.strength is not None:
        player.attributes.strength = max(0.0, min(1.0, req.strength))
    if req.accuracy is not None:
        player.attributes.accuracy = max(0.0, min(1.0, req.accuracy))
    if req.endurance is not None:
        player.attributes.endurance = max(0.0, min(1.0, req.endurance))
    if req.skill is not None:
        player.attributes.skill = max(0.0, min(1.0, req.skill))
    if req.decision_making is not None:
        player.attributes.decision_making = max(0.0, min(1.0, req.decision_making))
    if req.aggression is not None:
        player.attributes.aggression = max(0.0, min(1.0, req.aggression))
    if req.composure is not None:
        player.attributes.composure = max(0.0, min(1.0, req.composure))

    return {"updated": True, "player": player.name}


@app.put("/api/simulations/{game_id}/sliders/{team}")
async def update_sliders(game_id: str, team: str, sliders: SlidersRequest):
    """Update team strategy sliders during a simulation."""
    entry = _simulations.get(game_id)
    if not entry:
        raise HTTPException(404, "Simulation not found")
    sim: Simulation = entry["sim"]
    t = sim.state.home_team if team == "home" else sim.state.away_team
    t.sliders = TeamSliders(**sliders.model_dump())
    return {"updated": True, "team": t.name}


@app.get("/api/simulations")
async def list_simulations():
    results = []
    for gid, entry in _simulations.items():
        s = entry["sim"].state
        results.append({
            "game_id": gid,
            "sport": s.sport.value,
            "home_team": s.home_team.name,
            "away_team": s.away_team.name,
            "home_score": s.home_team.score,
            "away_score": s.away_team.score,
            "is_finished": s.is_finished,
        })
    return {"simulations": results}


@app.delete("/api/simulations/{game_id}")
async def delete_simulation(game_id: str):
    if game_id not in _simulations:
        raise HTTPException(404, "Simulation not found")
    del _simulations[game_id]
    return {"deleted": True}


# ---------------------------------------------------------------------------
# WebSocket — stream simulation in real time
# ---------------------------------------------------------------------------

@app.websocket("/ws/simulate")
async def ws_simulate(ws: WebSocket):
    await ws.accept()
    try:
        raw = await ws.receive_text()
        data = json.loads(raw)
        req = CreateSimRequest(**data)

        # Load teams
        home_team, away_team = _load_teams(req.sport, req.home_team, req.away_team)

        env = Environment(
            weather=Weather(req.weather),
            temperature_c=req.temperature_c,
            wind_speed_kph=req.wind_speed_kph,
            humidity=req.humidity,
        )

        venue = None
        if req.venue_type:
            venue = Venue(
                venue_type=VenueType(req.venue_type),
                surface=SurfaceType(req.surface_type) if req.surface_type else SurfaceType.NATURAL_GRASS,
                altitude_m=req.altitude_m or 0.0,
                name=req.venue_name or "Custom Venue",
            )

        home_sliders = TeamSliders(**req.home_sliders.model_dump()) if req.home_sliders else None
        away_sliders = TeamSliders(**req.away_sliders.model_dump()) if req.away_sliders else None

        config = SimulationConfig(
            sport=SportType(req.sport),
            seed=req.seed,
            ticks_per_second=req.ticks_per_second,
            fidelity=req.fidelity,
            enable_fatigue=req.enable_fatigue,
            enable_injuries=req.enable_injuries,
            enable_weather=req.enable_weather,
            enable_momentum=req.enable_momentum,
            enable_venue_effects=req.enable_venue_effects,
            enable_coach_effects=req.enable_coach_effects,
            enable_surface_effects=req.enable_surface_effects,
            environment=env,
            venue=venue,
            home_sliders=home_sliders,
            away_sliders=away_sliders,
        )

        sim = Simulation(config, home_team=home_team, away_team=away_team)
        _simulations[sim.state.game_id] = {"sim": sim, "config": config}

        for state, events in sim.stream():
            payload = {
                "game_id": state.game_id,
                "clock": round(state.clock, 2),
                "period": state.period,
                "home_team": state.home_team.name,
                "away_team": state.away_team.name,
                "home_score": state.home_team.score,
                "away_score": state.away_team.score,
                "home_momentum": round(state.home_team.momentum, 3),
                "away_momentum": round(state.away_team.momentum, 3),
                "is_finished": state.is_finished,
                "events": [
                    {"type": e.type.value, "time": round(e.time, 2), "description": e.description}
                    for e in events
                ],
            }
            await ws.send_text(json.dumps(payload))
            if config.realtime:
                await asyncio.sleep(1.0 / config.ticks_per_second)
            else:
                await asyncio.sleep(0)  # yield to event loop

        await ws.close()
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as exc:
        logger.exception("WebSocket error")
        await ws.close(code=1011, reason=str(exc)[:120])


# ---------------------------------------------------------------------------
# Heatmap endpoint
# ---------------------------------------------------------------------------

@app.get("/api/simulations/{game_id}/heatmap")
async def get_heatmap(game_id: str, event_type: str | None = None, team: str | None = None):
    """Aggregate spatial event data into heatmap bins."""
    entry = _simulations.get(game_id)
    if not entry:
        raise HTTPException(404, "Simulation not found")
    sim: Simulation = entry["sim"]
    events = sim.state.events

    # Filter by team if requested
    if team:
        tid = sim.state.home_team.id if team == "home" else sim.state.away_team.id
        events = [e for e in events if e.team_id == tid]

    # Filter by event type
    if event_type:
        events = [e for e in events if e.type.value == event_type]

    # Only events with spatial data
    spatial = [e for e in events if e.x is not None and e.y is not None]

    # Bin into grid (10x10)
    bins: dict[tuple[int, int], dict] = {}
    num_x, num_y = 10, 10
    for ev in spatial:
        bx = min(int(ev.x / 10), num_x - 1) if ev.x is not None else 0
        by = min(int(ev.y / 10), num_y - 1) if ev.y is not None else 0
        key = (bx, by)
        if key not in bins:
            bins[key] = {"x": bx * 10 + 5, "y": by * 10 + 5, "count": 0,
                         "success_count": 0, "event_type": event_type or "all"}
        bins[key]["count"] += 1
        if ev.type.value in ("goal", "three_pointer", "home_run", "touchdown", "ace", "winner", "birdie", "eagle"):
            bins[key]["success_count"] += 1

    return {"game_id": game_id, "bins": list(bins.values()), "total_events": len(spatial)}


# ---------------------------------------------------------------------------
# Trade endpoint
# ---------------------------------------------------------------------------

@app.post("/api/trade")
async def trade_player(req_body: dict):
    """Trade a player between two teams in an active simulation."""
    game_id = req_body.get("game_id")
    from_team = req_body.get("from_team")  # "home" or "away"
    to_team = req_body.get("to_team")  # "home" or "away"
    player_id = req_body.get("player_id")

    if not all([game_id, from_team, to_team, player_id]):
        raise HTTPException(400, "Missing required fields: game_id, from_team, to_team, player_id")

    entry = _simulations.get(game_id)
    if not entry:
        raise HTTPException(404, "Simulation not found")

    sim: Simulation = entry["sim"]
    src = sim.state.home_team if from_team == "home" else sim.state.away_team
    dst = sim.state.home_team if to_team == "home" else sim.state.away_team

    # Find player in source (active + bench)
    player = None
    for i, p in enumerate(src.players):
        if p.id == player_id:
            player = src.players.pop(i)
            break
    if not player:
        for i, p in enumerate(src.bench):
            if p.id == player_id:
                player = src.bench.pop(i)
                break

    if not player:
        raise HTTPException(404, "Player not found on source team")

    dst.bench.append(player)
    return {"traded": True, "player": player.name, "from": src.name, "to": dst.name}
