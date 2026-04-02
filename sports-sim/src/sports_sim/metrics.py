"""Prometheus metrics helpers for Sports Sim."""
from __future__ import annotations

try:
	from prometheus_client import Counter, Gauge, Summary, Histogram

	# Tuning metrics
	tuning_runs_total = Counter("tuning_runs_total", "Total tuning runs executed")
	tuning_last_duration_seconds = Summary("tuning_last_duration_seconds", "Duration of last tuning run in seconds")
	tuning_best_score = Gauge("tuning_best_score", "Best tuning score observed")

	# Simulation metrics
	simulations_created_total = Counter("simulations_created_total", "Total simulations created", ["sport"])
	simulations_completed_total = Counter("simulations_completed_total", "Total simulations completed", ["sport"])
	simulation_duration_seconds = Histogram(
		"simulation_duration_seconds",
		"Time to run a simulation",
		["sport"],
		buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
	)
	active_simulations = Gauge("active_simulations", "Currently active simulations")
	batch_simulations_total = Counter("batch_simulations_total", "Total batch simulation requests")

	# API metrics
	websocket_connections = Gauge("websocket_connections", "Active WebSocket connections")
	api_errors_total = Counter("api_errors_total", "Total API errors", ["endpoint", "status"])

except Exception:
	class _NoOp:
		def inc(self, *_, **__):
			return None

		def observe(self, *_, **__):
			return None

		def set(self, *_, **__):
			return None

		def dec(self, *_, **__):
			return None

		def labels(self, *_, **__):
			return _NoOp()

	tuning_runs_total = _NoOp()
	tuning_last_duration_seconds = _NoOp()
	tuning_best_score = _NoOp()
	simulations_created_total = _NoOp()
	simulations_completed_total = _NoOp()
	simulation_duration_seconds = _NoOp()
	active_simulations = _NoOp()
	batch_simulations_total = _NoOp()
	websocket_connections = _NoOp()
	api_errors_total = _NoOp()

__all__ = [
	"tuning_runs_total",
	"tuning_last_duration_seconds",
	"tuning_best_score",
	"simulations_created_total",
	"simulations_completed_total",
	"simulation_duration_seconds",
	"active_simulations",
	"batch_simulations_total",
	"websocket_connections",
	"api_errors_total",
]
