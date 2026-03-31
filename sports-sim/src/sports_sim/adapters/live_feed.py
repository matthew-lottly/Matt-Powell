"""Skeleton for live data adapters (WebSocket/Kafka/HTTP) for ingesting match updates."""
from __future__ import annotations

from typing import Callable, Any


class LiveAdapter:
    """Abstract base for a live feed adapter."""

    def __init__(self):
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []

    def register_callback(self, cb: Callable[[dict], None]) -> None:
        self._callbacks.append(cb)

    def _emit(self, message: dict) -> None:
        for cb in list(self._callbacks):
            try:
                cb(message)
            except Exception:
                # swallow errors in callbacks
                pass

    def start(self) -> None:
        raise NotImplementedError()

    def stop(self) -> None:
        raise NotImplementedError()


class WebSocketAdapter(LiveAdapter):
    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def start(self) -> None:
        # placeholder: an async implementation would open a ws and forward messages
        raise NotImplementedError("WebSocketAdapter.start() must be implemented by the application")

    def stop(self) -> None:
        pass


class KafkaAdapter(LiveAdapter):
    def __init__(self, bootstrap_servers: str, topic: str):
        super().__init__()
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic

    def start(self) -> None:
        raise NotImplementedError("KafkaAdapter.start() must be implemented by the application")

    def stop(self) -> None:
        pass


__all__ = ["LiveAdapter", "WebSocketAdapter", "KafkaAdapter"]
