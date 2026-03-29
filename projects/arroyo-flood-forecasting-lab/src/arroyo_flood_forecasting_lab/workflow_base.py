from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ReportWorkflow(ABC):
    report_name: str
    run_label: str
    registry_name: str

    @property
    @abstractmethod
    def output_filename(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def build_report(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def build_registry_entry(self, report: dict[str, Any], output_path: Path) -> dict[str, Any]:
        raise NotImplementedError

    def export_report(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        report = self.build_report()
        output_path = output_dir / self.output_filename
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self._update_run_registry(output_dir, self.build_registry_entry(report, output_path))
        return output_path

    def _update_run_registry(self, output_dir: Path, run_entry: dict[str, Any]) -> Path:
        registry_path = output_dir / self.registry_name
        if registry_path.exists():
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        else:
            registry = {"runs": []}
        registry.setdefault("runs", []).append(run_entry)
        registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
        return registry_path