"""Custom exception classes for geoprompt (item 16)."""

from __future__ import annotations


class GeoPromptError(Exception):
    """Base exception for all geoprompt errors."""


class GeometryError(GeoPromptError):
    """Raised for invalid or unsupported geometry objects."""


class ValidationError(GeoPromptError):
    """Raised when input data fails validation checks."""


class CRSError(GeoPromptError):
    """Raised for missing, mismatched, or unresolvable CRS."""


class IOError_(GeoPromptError):
    """Raised for read/write failures in geoprompt IO operations."""


class ColumnError(GeoPromptError):
    """Raised when a required column is missing from a frame."""


class AnchorError(GeoPromptError):
    """Raised when an anchor feature cannot be resolved."""


class ConfigError(GeoPromptError):
    """Raised for invalid or missing configuration."""


class PluginError(GeoPromptError):
    """Raised when a plugin hook fails or is misconfigured."""


__all__ = [
    "AnchorError",
    "CRSError",
    "ColumnError",
    "ConfigError",
    "GeoPromptError",
    "GeometryError",
    "IOError_",
    "PluginError",
    "ValidationError",
]
