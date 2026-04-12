from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable, Sequence


Record = dict[str, Any]


class PromptTable:
    """Lightweight non-spatial table for model outputs and comparisons."""

    def __init__(self, rows: Sequence[Record]) -> None:
        self._rows = [dict(row) for row in rows]

    @classmethod
    def from_records(cls, records: Iterable[Record]) -> "PromptTable":
        return cls(list(records))

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self):
        return iter(self._rows)

    @property
    def columns(self) -> list[str]:
        return list(self._rows[0].keys()) if self._rows else []

    def head(self, count: int = 5) -> list[Record]:
        return [dict(row) for row in self._rows[:count]]

    def to_records(self) -> list[Record]:
        return [dict(row) for row in self._rows]

    def sort_values(self, by: str, descending: bool = False) -> "PromptTable":
        if by not in self.columns:
            raise KeyError(f"column '{by}' is not present")
        return PromptTable(
            sorted(self._rows, key=lambda row: (row[by] is None, row[by]), reverse=descending)
        )

    def select_columns(self, columns: Sequence[str]) -> "PromptTable":
        for column in columns:
            if column not in self.columns:
                raise KeyError(f"column '{column}' is not present")
        return PromptTable([{column: row[column] for column in columns} for row in self._rows])

    def to_markdown(self) -> str:
        if not self._rows:
            return "| |\n| --- |\n"
        columns = self.columns
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join("---" for _ in columns) + " |"
        body = ["| " + " | ".join(str(row.get(column, "")) for column in columns) + " |" for row in self._rows]
        return "\n".join([header, separator, *body]) + "\n"

    def to_csv(self, output_path: str | Path) -> str:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.columns)
            writer.writeheader()
            writer.writerows(self._rows)
        return str(path)


__all__ = ["PromptTable"]