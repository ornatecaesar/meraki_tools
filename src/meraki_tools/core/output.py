"""Write tool results as tables on screen or as CSV files."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

from meraki_tools.core.paths import output_dir

Row = Mapping[str, Any]


def format_table(rows: Sequence[Row], columns: Sequence[str]) -> str:
    """Return rows as a plain-text table with aligned columns.

    Args:
        rows: One mapping per row.
        columns: Column names, in display order. Missing values show as blank.

    Returns:
        The table as a string, with a header row and an underline.

    Example:
        >>> print(format_table([{"a": 1, "b": "xy"}], ["a", "b"]))
        a  b
        -  --
        1  xy
    """
    cells = [["" if row.get(col) is None else str(row[col]) for col in columns] for row in rows]
    widths = [max([len(col), *(len(r[i]) for r in cells)]) for i, col in enumerate(columns)]
    lines = [
        "  ".join(col.ljust(w) for col, w in zip(columns, widths, strict=True)).rstrip(),
        "  ".join("-" * w for w in widths),
    ]
    lines += ["  ".join(c.ljust(w) for c, w in zip(r, widths, strict=True)).rstrip() for r in cells]
    return "\n".join(lines)


def write_csv(rows: Sequence[Row], columns: Sequence[str], path: Path) -> Path:
    """Write rows to a CSV file, creating its folder if needed.

    Args:
        rows: One mapping per row.
        columns: Column names, in file order.
        path: Destination file.

    Returns:
        ``path``, for convenience.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def dated_output_path(tool_name: str, stem: str, suffix: str) -> Path:
    """Return ``output/<tool_name>/<stem>_<YYYY-MM-DD><suffix>``.

    Args:
        tool_name: The tool's short name, which is also its output folder.
        stem: Start of the file name.
        suffix: File extension including the dot, for example ``".csv"``.
    """
    return output_dir(tool_name) / f"{stem}_{date.today().isoformat()}{suffix}"
