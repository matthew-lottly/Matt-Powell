"""Small CLI wrapper to import roster CSVs into JSON seeds.

Usage:
  python scripts/import_rosters.py

This imports all CSVs from `data/seeds_raw/` into `data/seeds/`.
"""
from __future__ import annotations

from pathlib import Path
from sports_sim.data.roster_ingest import main


if __name__ == "__main__":
    src = Path("data/seeds_raw")
    dst = Path("data/seeds")
    raise SystemExit(main(src, dst))
