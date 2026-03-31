# Sports Sim

A multi-sport simulation engine with realistic fatigue, injury, weather, and momentum models — powered by Python, FastAPI, and React.

## Sports

| Sport | Players | Periods | Key Features |
|---|---|---|---|
| **Soccer** | 11 v 11 | 2 × 45 min | Passing, shots, goals, fouls, cards, offsides |
| **Basketball** | 5 v 5 | 4 × 12 min | Shot clock, 2pt/3pt, free throws, rebounds, steals |
| **Baseball** | 9 v 9 | 9 innings | At-bats, pitching, hits, home runs, strikeouts |

## Realism Models

- **Fatigue** — stamina drains based on activity/distance and endurance rating
- **Injuries** — probabilistic injury model scaled by fatigue and aggression
- **Weather** — rain reduces accuracy, wind moves the ball, heat accelerates fatigue
- **Momentum** — team morale shifts with goals, turnovers, and key events

## Quick Start

### CLI

```bash
pip install -e ".[dev]"

# Single game
sports-sim run --sport soccer --seed 42 -v

# Batch of 100 games
sports-sim batch --sport basketball -n 100 --seed 1

# With weather
sports-sim run --sport baseball --weather rain --temperature 30 --wind 15 -v
```

### API

```bash
uvicorn sports_sim.api.app:app --reload
```

Then visit `http://localhost:8000/docs` for the OpenAPI explorer.

### Frontend

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:5173` — select a sport, configure, and stream a simulation in real time.

## Architecture

```
sports-sim/
├── src/sports_sim/
│   ├── core/           # Models, engine, sport interface
│   ├── sports/         # Soccer, basketball, baseball
│   ├── realism/        # Fatigue, injuries, weather, momentum
│   ├── api/            # FastAPI + WebSocket
│   └── cli.py          # Click CLI
├── web/                # React + Vite + TypeScript frontend
├── tests/              # pytest suite
├── Dockerfile
└── pyproject.toml
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/sports` | List available sports |
| `POST` | `/api/simulations` | Create a simulation |
| `POST` | `/api/simulations/{id}/run` | Run to completion |
| `GET` | `/api/simulations/{id}` | Get state + events |
| `GET` | `/api/simulations` | List all simulations |
| `DELETE` | `/api/simulations/{id}` | Delete a simulation |
| `WS` | `/ws/simulate` | Stream simulation in real time |

## Testing

```bash
pytest --tb=short -q
```

## Dashboard & Profiling

Start the tuning dashboard (Streamlit):

```bash
# from project root
python -m streamlit run scripts/tune_dashboard.py --server.port 8501
```

Generate a short profiler run and convert to HTML:

```bash
python scripts/profile_tuner.py
python scripts/convert_profile.py  # writes outputs/tuner_profile.html
# or view interactively with SnakeViz:
python -m pip install snakeviz
python -m snakeviz -s tuner_profile.prof
```

If you only need a quick preview, serve the `outputs/` folder and open the HTML:

```bash
python -m http.server 8000 --directory outputs
# then open http://localhost:8000/tuner_profile.html
```


## License

MIT
