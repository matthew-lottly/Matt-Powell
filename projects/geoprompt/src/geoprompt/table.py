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

    def where(
        self,
        predicate: Any | None = None,
        **equals: Any,
    ) -> "PromptTable":
        if predicate is not None and not callable(predicate):
            raise TypeError("predicate must be callable when provided")

        rows: list[Record] = []
        for row in self._rows:
            if any(row.get(key) != value for key, value in equals.items()):
                continue
            if predicate is not None and not bool(predicate(row)):
                continue
            rows.append(dict(row))
        return PromptTable(rows)

    def join(
        self,
        other: "PromptTable",
        on: str,
        how: str = "inner",
        rsuffix: str = "right",
    ) -> "PromptTable":
        if on not in self.columns:
            raise KeyError(f"column '{on}' is not present in left table")
        if on not in other.columns:
            raise KeyError(f"column '{on}' is not present in right table")
        if how not in {"inner", "left"}:
            raise ValueError("how must be 'inner' or 'left'")

        right_index: dict[Any, list[Record]] = {}
        for row in other:
            right_index.setdefault(row[on], []).append(dict(row))

        right_columns = [column for column in other.columns if column != on]
        rows: list[Record] = []
        for left_row in self._rows:
            right_rows = right_index.get(left_row.get(on), [])
            if not right_rows and how == "left":
                merged = dict(left_row)
                for column in right_columns:
                    target = column if column not in merged else f"{column}_{rsuffix}"
                    merged[target] = None
                rows.append(merged)
                continue

            for right_row in right_rows:
                merged = dict(left_row)
                for column in right_columns:
                    target = column if column not in merged else f"{column}_{rsuffix}"
                    merged[target] = right_row[column]
                rows.append(merged)

        return PromptTable(rows)

    def pivot(
        self,
        index: str,
        columns: str,
        values: str,
        agg: str = "sum",
    ) -> "PromptTable":
        for column in [index, columns, values]:
            if column not in self.columns:
                raise KeyError(f"column '{column}' is not present")

        grouped: dict[Any, dict[Any, list[Any]]] = {}
        column_values: set[Any] = set()
        for row in self._rows:
            grouped.setdefault(row[index], {}).setdefault(row[columns], []).append(row[values])
            column_values.add(row[columns])

        sorted_columns = sorted(column_values, key=str)
        rows: list[Record] = []
        for index_value, bucket in grouped.items():
            pivot_row: Record = {index: index_value}
            for column_value in sorted_columns:
                values_bucket = bucket.get(column_value, [])
                if not values_bucket:
                    pivot_row[str(column_value)] = None
                elif agg == "sum":
                    pivot_row[str(column_value)] = sum(float(value) for value in values_bucket)
                elif agg == "mean":
                    pivot_row[str(column_value)] = sum(float(value) for value in values_bucket) / len(values_bucket)
                elif agg == "min":
                    pivot_row[str(column_value)] = min(values_bucket)
                elif agg == "max":
                    pivot_row[str(column_value)] = max(values_bucket)
                elif agg == "first":
                    pivot_row[str(column_value)] = values_bucket[0]
                elif agg == "count":
                    pivot_row[str(column_value)] = len(values_bucket)
                else:
                    raise ValueError(f"unsupported aggregation: {agg}")
            rows.append(pivot_row)

        return PromptTable(rows)

    def summarize(self, by: str, aggregations: dict[str, str] | None = None) -> "PromptTable":
        if by not in self.columns:
            raise KeyError(f"column '{by}' is not present")

        grouped_rows: dict[Any, list[Record]] = {}
        for row in self._rows:
            grouped_rows.setdefault(row[by], []).append(row)

        summary_rows: list[Record] = []
        for group_value, rows in grouped_rows.items():
            summary_row: Record = {by: group_value, "row_count": len(rows)}
            for column, operation in (aggregations or {}).items():
                values = [row[column] for row in rows if column in row and row[column] is not None]
                if not values:
                    summary_row[f"{column}_{operation}"] = None
                    continue
                if operation == "sum":
                    summary_row[f"{column}_{operation}"] = sum(float(value) for value in values)
                elif operation == "mean":
                    summary_row[f"{column}_{operation}"] = sum(float(value) for value in values) / len(values)
                elif operation == "min":
                    summary_row[f"{column}_{operation}"] = min(values)
                elif operation == "max":
                    summary_row[f"{column}_{operation}"] = max(values)
                elif operation == "first":
                    summary_row[f"{column}_{operation}"] = values[0]
                elif operation == "count":
                    summary_row[f"{column}_{operation}"] = len(values)
                else:
                    raise ValueError(f"unsupported aggregation: {operation}")
            summary_rows.append(summary_row)

        return PromptTable(summary_rows)

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