"""Simple roster ingestion utilities.

Reads CSV roster exports (team_name, player_name, position, number, age, nationality, rating)
and writes normalized JSON team files into `data/seeds/` with structure:
{
  "teams": [ {"team": "Name", "players": [ {..}, ... ] }, ... ]
}
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Dict, Any


def read_csv_roster(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if not any(row.values()):
                continue
            yield {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}


def normalize_and_group(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    teams = defaultdict(list)
    for r in rows:
        team = r.get("team_name") or "Unknown"
        player = {
            "name": r.get("player_name") or "",
            "position": r.get("position") or "",
            "number": int(r.get("number") or 0),
            "age": int(r.get("age") or 0),
            "nationality": r.get("nationality") or "",
            "rating": float(r.get("rating") or 0.0),
        }
        teams[team].append(player)
    out = {"teams": [{"team": t, "players": p} for t, p in teams.items()]}
    return out


def write_json_seed(data: Dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def ingest_csv_to_json(src_csv: Path, dst_json: Path) -> Path:
    rows = list(read_csv_roster(src_csv))
    grouped = normalize_and_group(rows)
    write_json_seed(grouped, dst_json)
    return dst_json


def main(input_dir: str | Path = "data/seeds_raw", output_dir: str | Path = "data/seeds") -> int:
    src = Path(input_dir)
    dst = Path(output_dir)
    if not src.exists():
        print(f"Source directory {src} does not exist")
        return 1
    csv_files = list(src.glob("*.csv"))
    if not csv_files:
        print("No CSV files found")
        return 1
    for f in csv_files:
        league = f.stem
        out_file = dst / f"{league}.json"
        ingest_csv_to_json(f, out_file)
        print(f"Wrote {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
