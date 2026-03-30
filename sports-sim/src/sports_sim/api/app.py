"""FastAPI application — REST + WebSocket API for sports-sim."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sports_sim.core.engine import Simulation
from sports_sim.core.models import (
    Environment,
    GameState,
    SimulationConfig,
    SportType,
    Weather,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory store (demo-grade; swap for Redis / DB in prod)
# ---------------------------------------------------------------------------

_simulations: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Lifespan
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
    version="0.1.0",
    description="Run and stream multi-sport simulations in real time.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class CreateSimRequest(BaseModel):
    sport: str = "soccer"
    seed: int | None = None
    fidelity: str = "medium"
    ticks_per_second: int = 10
    enable_fatigue: bool = True
    enable_injuries: bool = True
    enable_weather: bool = True
    enable_momentum: bool = True
    weather: str = "clear"
    temperature_c: float = 22.0
    wind_speed_kph: float = 0.0


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
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/api/sports")
async def list_sports():
    return {"sports": [s.value for s in SportType]}


@app.post("/api/simulations", response_model=SimSummary)
async def create_simulation(req: CreateSimRequest):
    env = Environment(
        weather=Weather(req.weather),
        temperature_c=req.temperature_c,
        wind_speed_kph=req.wind_speed_kph,
    )
    config = SimulationConfig(
        sport=SportType(req.sport),
        seed=req.seed,
        ticks_per_second=req.ticks_per_second,
        fidelity=req.fidelity,
        enable_fatigue=req.enable_fatigue,
        enable_injuries=req.enable_injuries,
        enable_weather=req.enable_weather,
        enable_momentum=req.enable_momentum,
        environment=env,
    )
    sim = Simulation(config)
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
        "events": [
            {"type": e.type.value, "time": round(e.time, 2), "period": e.period,
             "description": e.description}
            for e in state.events[-50:]  # last 50
        ],
    }


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

        env = Environment(
            weather=Weather(req.weather),
            temperature_c=req.temperature_c,
            wind_speed_kph=req.wind_speed_kph,
        )
        config = SimulationConfig(
            sport=SportType(req.sport),
            seed=req.seed,
            ticks_per_second=req.ticks_per_second,
            fidelity=req.fidelity,
            enable_fatigue=req.enable_fatigue,
            enable_injuries=req.enable_injuries,
            enable_weather=req.enable_weather,
            enable_momentum=req.enable_momentum,
            environment=env,
        )

        sim = Simulation(config)
        _simulations[sim.state.game_id] = {"sim": sim, "config": config}

        for state, events in sim.stream():
            payload = {
                "game_id": state.game_id,
                "clock": round(state.clock, 2),
                "period": state.period,
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
