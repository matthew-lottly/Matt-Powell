from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gulf_coast_inundation_lab.validation import GulfCoastValidationWorkflow

__all__ = ["GulfCoastValidationWorkflow", "build_validation_report"]


def __getattr__(name: str) -> Any:
    if name == "GulfCoastValidationWorkflow":
        from gulf_coast_inundation_lab.validation import GulfCoastValidationWorkflow

        return GulfCoastValidationWorkflow
    if name == "build_validation_report":
        from gulf_coast_inundation_lab.validation import build_validation_report

        return build_validation_report
    raise AttributeError(f"module 'gulf_coast_inundation_lab' has no attribute {name!r}")