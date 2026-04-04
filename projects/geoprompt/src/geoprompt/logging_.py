"""Structured logging for geoprompt (items 17-20)."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Generator


LOGGER_NAME = "geoprompt"

logger = logging.getLogger(LOGGER_NAME)


def configure_logging(*, verbose: bool = False, trace: bool = False) -> None:
    """Configure geoprompt logging.

    Args:
        verbose: Enable DEBUG-level output.
        trace: Enable TRACE-level output (even more detail than DEBUG).
    """
    level = logging.DEBUG if verbose else logging.INFO
    if trace:
        level = logging.DEBUG

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    root_logger = logging.getLogger(LOGGER_NAME)
    root_logger.setLevel(level)
    if not root_logger.handlers:
        root_logger.addHandler(handler)


@contextmanager
def log_timing(operation: str, **kwargs: Any) -> Generator[None, None, None]:
    """Item 19: Execution timing context manager for major pipeline steps."""
    start = time.perf_counter()
    logger.info("Starting: %s", operation)
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
        logger.info("Completed: %s (%.4fs) %s", operation, elapsed, extra)


def log_trace(message: str, *args: Any) -> None:
    """Item 20: Trace-level logging for intermediate metric summaries."""
    logger.debug("[TRACE] " + message, *args)


__all__ = [
    "LOGGER_NAME",
    "configure_logging",
    "log_timing",
    "log_trace",
    "logger",
]
