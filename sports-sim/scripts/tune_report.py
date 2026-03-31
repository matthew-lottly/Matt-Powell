"""Simple tuning report script: read SQLite or JSONL checkpoints and print top candidates."""
from __future__ import annotations

import argparse
import json
from sports_sim.mc.persistence import TuningDB


def main():
    parser = argparse.ArgumentParser(description="Tuning report")
    parser.add_argument("--db", type=str, default=None, help="Path to tuning SQLite DB")
    parser.add_argument("--jsonl", type=str, default=None, help="Path to JSONL checkpoint")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    entries = []
    if args.db:
        db = TuningDB(args.db)
        entries = db.all_results()
        db.close()
    if args.jsonl:
        with open(args.jsonl, encoding="utf-8") as fh:
            for line in fh:
                try:
                    j = json.loads(line)
                    entries.append(j)
                except Exception:
                    continue

    entries_sorted = sorted(entries, key=lambda r: r.get("score", 0.0), reverse=True)
    for idx, row in enumerate(entries_sorted[: args.top], start=1):
        print(f"#{idx}: score={row.get('score')}, params={row.get('params')}")


if __name__ == "__main__":
    main()
