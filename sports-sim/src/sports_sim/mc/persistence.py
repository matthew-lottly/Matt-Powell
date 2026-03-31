"""Persistence helpers for tuning results (SQLite and JSONL)."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, Iterable, List, Optional


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS tuning_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  params TEXT NOT NULL,
  score REAL NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class TuningDB:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.conn = sqlite3.connect(str(self.path))
        self._init()

    def _init(self) -> None:
        cur = self.conn.cursor()
        cur.execute(CREATE_SQL)
        self.conn.commit()

    def insert_result(self, params: Dict[str, Any], score: float) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO tuning_results (params, score) VALUES (?, ?)",
            (json.dumps(params, sort_keys=True), float(score)),
        )
        self.conn.commit()

    def all_results(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT params, score, created_at FROM tuning_results ORDER BY id ASC")
        rows = cur.fetchall()
        out: List[Dict[str, Any]] = []
        for params_json, score, created_at in rows:
            try:
                params = json.loads(params_json)
            except Exception:
                params = {}
            out.append({"params": params, "score": float(score), "created_at": created_at})
        return out

    def best(self) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT params, score FROM tuning_results ORDER BY score DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return None
        params_json, score = row
        try:
            params = json.loads(params_json)
        except Exception:
            params = {}
        return {"params": params, "score": float(score)}

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass


def append_jsonl(path: str | Path, params: Dict[str, Any], score: float) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"params": params, "score": score}) + "\n")


__all__ = ["TuningDB", "append_jsonl"]
