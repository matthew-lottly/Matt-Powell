from __future__ import annotations

from fastapi import APIRouter, Query
from typing import List

from sports_sim.mc.persistence import TuningDB

router = APIRouter(prefix="/api/tuning")


@router.get("/results", response_model=List[dict])
def get_results(db_path: str = Query("tuning.db")):
    """Return all tuning results from SQLite DB (path via query param)."""
    db = TuningDB(db_path)
    try:
        rows = db.all_results()
    finally:
        db.close()
    return rows


@router.get("/best", response_model=dict)
def get_best(db_path: str = Query("tuning.db")):
    db = TuningDB(db_path)
    try:
        best = db.best() or {}
    finally:
        db.close()
    return best
