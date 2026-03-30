# Contributing

Thanks for your interest in contributing to **Sports Sim**!

## Development Setup

```bash
# Clone the repo
git clone https://github.com/your-org/sports-sim.git
cd sports-sim

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in dev mode
pip install -e ".[dev]"

# Run tests
pytest

# Run the CLI
sports-sim run --sport soccer --seed 42 -v
```

## Frontend

```bash
cd web
npm install
npm run dev
```

## Code Quality

- **Lint:** `ruff check src/ tests/`
- **Format:** `black src/ tests/`
- **Types:** `pyright`
- **Tests:** `pytest`

## Pull Request Checklist

- [ ] Tests pass (`pytest`)
- [ ] Linting passes (`ruff check`)
- [ ] Types pass (`pyright`)
- [ ] Frontend builds (`npm run build`)
