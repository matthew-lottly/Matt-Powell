from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path

import pandas as pd

LALONDE_CONFOUNDERS = [
    "age",
    "educ",
    "married",
    "nodegree",
    "re74",
    "re75",
    "race_black",
    "race_hispanic",
]

NHEFS_COMPLETE_CONFOUNDERS = [
    "sex",
    "race",
    "age",
    "school",
    "smokeintensity",
    "smokeyrs",
    "exercise",
    "active",
    "wt71",
]


@dataclass(frozen=True)
class DataSpec:
    treatment_col: str
    outcome_col: str
    confounders: list[str]


def validate_observational_frame(frame: pd.DataFrame, spec: DataSpec) -> pd.DataFrame:
    required = [spec.treatment_col, spec.outcome_col, *spec.confounders]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Missing required columns: {missing_text}")

    prepared = frame[required].copy()
    prepared = prepared.dropna(axis=0).reset_index(drop=True)
    treatment = prepared[spec.treatment_col]
    unique_values = set(treatment.unique().tolist())
    if not unique_values.issubset({0, 1}):
        raise ValueError("Treatment column must contain only 0/1 values")
    return prepared


def load_csv_dataset(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _load_packaged_dataset(filename: str) -> pd.DataFrame:
    resource = files("causal_lens.datasets").joinpath(filename)
    with as_file(resource) as resolved_path:
        return pd.read_csv(resolved_path)


def load_monitoring_intervention_sample() -> pd.DataFrame:
    frame = _load_packaged_dataset("monitoring_intervention_sample.csv")
    frame["region_category"] = frame["region"] + "_" + frame["category"]
    return frame


def load_lalonde_benchmark() -> pd.DataFrame:
    frame = _load_packaged_dataset("lalonde.csv")
    frame["race_black"] = (frame["race"] == "black").astype(int)
    frame["race_hispanic"] = (frame["race"] == "hispan").astype(int)
    frame = frame.rename(columns={"treat": "treatment", "re78": "outcome"})
    return frame


def load_nhefs_complete_benchmark() -> pd.DataFrame:
    frame = _load_packaged_dataset("nhefs_complete.csv")
    frame = frame.rename(columns={"qsmk": "treatment", "wt82_71": "outcome"})
    return frame
