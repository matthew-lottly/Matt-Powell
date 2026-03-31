"""Generate production-style seeds by ingesting CSVs in data/seeds_raw."""
from __future__ import annotations

from pathlib import Path
from sports_sim.data.roster_ingest import main as ingest_main


def main():
    return ingest_main(input_dir=Path("data/seeds_raw"), output_dir=Path("data/seeds"))


if __name__ == "__main__":
    raise SystemExit(main())
