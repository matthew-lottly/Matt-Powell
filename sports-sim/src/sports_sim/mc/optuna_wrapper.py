"""Optional Optuna integration for Bayesian optimization of tuning.

This wrapper is lightweight and only imports Optuna when used.
"""
from __future__ import annotations

from typing import Dict, Iterable, Any


def optuna_tune(objective_callable, param_space: Dict[str, Iterable[Any]], n_trials: int = 50, seed: int = 1):
    try:
        import optuna
    except Exception as e:
        raise RuntimeError("optuna is not installed; install optuna to use this feature") from e

    def _suggest(trial: "optuna.trial.Trial"):
        params = {}
        for k, vals in param_space.items():
            # if vals is iterable of discrete options, suggest_categorical
            vals_list = list(vals)
            if all(isinstance(v, (int, float)) for v in vals_list) and len(vals_list) <= 10:
                params[k] = trial.suggest_categorical(k, vals_list)
            else:
                # fallback to uniform in min/max
                try:
                    lo = min(vals_list)
                    hi = max(vals_list)
                    params[k] = trial.suggest_float(k, float(lo), float(hi))
                except Exception:
                    params[k] = trial.suggest_categorical(k, vals_list)
        return params

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=seed))

    def _objective(trial: "optuna.trial.Trial"):
        params = _suggest(trial)
        return float(objective_callable(params))

    study.optimize(_objective, n_trials=n_trials)
    return {"best_params": study.best_params, "best_value": study.best_value}


__all__ = ["optuna_tune"]
