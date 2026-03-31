"""Streamlit dashboard to inspect tuning results from SQLite or JSONL."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import streamlit as st

from sports_sim.mc.persistence import TuningDB


def load_entries(db_path: str | None, jsonl_path: str | None):
    entries = []
    if db_path:
        try:
            db = TuningDB(db_path)
            entries = db.all_results()
            db.close()
        except Exception:
            entries = []
    if jsonl_path:
        p = Path(jsonl_path)
        if p.exists():
            with p.open(encoding="utf-8") as fh:
                for line in fh:
                    try:
                        j = json.loads(line)
                        entries.append(j)
                    except Exception:
                        continue
    return entries


def main():
    st.title("Tuning Dashboard")
    st.write("Inspect tuning runs stored in SQLite DB or JSONL file.")

    db_path = st.text_input("SQLite DB path", value="tuning.db")
    jsonl_path = st.text_input("JSONL path", value="tuning.jsonl")

    if st.button("Load"):
        entries = load_entries(db_path if db_path else None, jsonl_path if jsonl_path else None)
        if not entries:
            st.warning("No entries found")
            return

        entries_sorted = sorted(entries, key=lambda r: r.get("score", 0.0), reverse=True)
        st.subheader("Top candidates")
        for idx, row in enumerate(entries_sorted[:50], start=1):
            st.write(f"#{idx}: score={row.get('score')}, params={row.get('params')}")

        # simple histogram of scores
        scores = [r.get("score", 0.0) for r in entries]
        st.subheader("Score distribution")
        st.bar_chart(scores)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=str, default="tuning.db")
    parser.add_argument("--jsonl", type=str, default="tuning.jsonl")
    args = parser.parse_args()
    # Launch Streamlit when invoked directly
    print("Run with: streamlit run scripts/tune_dashboard.py")
