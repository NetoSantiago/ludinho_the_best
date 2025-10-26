from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List


@dataclass
class TableData:
    """Utility container to mimic a subset of pandas.DataFrame features."""

    rows: List[Dict[str, Any]]

    @classmethod
    def from_records(cls, records: Iterable[Dict[str, Any]] | None) -> "TableData":
        return cls([dict(row) for row in records or []])

    @property
    def empty(self) -> bool:
        return len(self.rows) == 0

    def to_csv(self) -> str:
        if self.empty:
            return ""

        # Preserve insertion order of columns based on their first appearance.
        columns: List[str] = []
        for row in self.rows:
            for key in row.keys():
                if key not in columns:
                    columns.append(key)

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=columns)
        writer.writeheader()
        for row in self.rows:
            writer.writerow({column: row.get(column, "") for column in columns})

        return buffer.getvalue()

    def as_streamlit_data(self) -> List[Dict[str, Any]]:
        """Return the raw data to be used with Streamlit widgets."""

        return self.rows
