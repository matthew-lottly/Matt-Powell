"""FastAPI app for lightweight STRATA inference and diagnostics."""

from __future__ import annotations

from typing import Any


def create_app():
    try:
        from fastapi import FastAPI
        from pydantic import BaseModel, Field
    except ImportError as exc:
        raise RuntimeError("Install API extras first: pip install -e .[api]") from exc

    from .experiment import ExperimentConfig, run_experiment

    app = FastAPI(title="STRATA API", version="0.1.0")

    class ExperimentRequest(BaseModel):
        seed: int = 42
        alpha: float = Field(default=0.1, gt=0.0, lt=1.0)
        epochs: int = Field(default=30, ge=1)
        patience: int = Field(default=10, ge=1)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/datasets")
    def datasets() -> dict[str, list[str]]:
        return {"datasets": ["synthetic", "ACTIVSg200", "IEEE118"]}

    @app.post("/run-experiment")
    def run_experiment_endpoint(request: ExperimentRequest) -> dict[str, Any]:
        result = run_experiment(
            ExperimentConfig(seed=request.seed, alpha=request.alpha, epochs=request.epochs, patience=request.patience),
            verbose=False,
        )
        return {
            "marginal_coverage": result.marginal_cov,
            "type_coverage": result.type_cov,
            "mean_width": result.mean_width,
            "ece": result.ece,
        }

    return app
