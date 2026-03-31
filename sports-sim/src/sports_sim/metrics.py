"""Prometheus metrics helpers for tuning jobs."""
from __future__ import annotations

try:
	from prometheus_client import Counter, Gauge, Summary

	# Total number of tuning runs attempted
	tuning_runs_total = Counter("tuning_runs_total", "Total tuning runs executed")

	# Duration of last tuning run (seconds)
	tuning_last_duration_seconds = Summary("tuning_last_duration_seconds", "Duration of last tuning run in seconds")

	# Best score observed
	tuning_best_score = Gauge("tuning_best_score", "Best tuning score observed")
except Exception:
	# Provide no-op stand-ins when prometheus_client is not installed
	class _NoOp:
		def inc(self, *_, **__):
			return None

		def observe(self, *_, **__):
			return None

		def set(self, *_, **__):
			return None

	tuning_runs_total = _NoOp()
	tuning_last_duration_seconds = _NoOp()
	tuning_best_score = _NoOp()

__all__ = ["tuning_runs_total", "tuning_last_duration_seconds", "tuning_best_score"]
