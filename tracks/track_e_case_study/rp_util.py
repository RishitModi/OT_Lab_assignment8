"""Utility functions for Track E: CSV export and GitHub-flavored Markdown rendering.

Provides lightweight table serialization and rendering routines without third-party
tabular dependencies (such as pandas).
"""

from __future__ import annotations

import csv
from pathlib import Path
import sys
from typing import Any, Sequence

# Ensure repository root and current track directory are present on sys.path
_TRACK_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in [str(_REPO_ROOT), str(_TRACK_ROOT)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)


def write_csv(
    path: str | Path,
    rows: Sequence[dict[str, Any] | Sequence[Any]],
    columns: Sequence[str],
) -> None:
    """Write tabular data to a CSV file.

    Parameters
    ----------
    path : str | Path
        Target filesystem location for the CSV file.
    rows : Sequence[dict[str, Any] | Sequence[Any]]
        Records formatted as dictionaries keyed by column name or tuples matching column order.
    columns : Sequence[str]
        Ordered sequence of column header names.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(list(columns))

        # Explicit loop iteration cap to guard against unbounded data structures
        max_rows = len(rows) + 10
        step = 0
        for row in rows:
            step += 1
            if step > max_rows:
                break
            if isinstance(row, dict):
                writer.writerow([row.get(col, "") for col in columns])
            else:
                writer.writerow(list(row))


def to_markdown(
    rows: Sequence[dict[str, Any] | Sequence[Any]],
    columns: Sequence[str],
    float_fmt: str = "{:.4g}",
) -> str:
    """Format tabular records into a GitHub-flavored Markdown table string.

    Parameters
    ----------
    rows : Sequence[dict[str, Any] | Sequence[Any]]
        Records formatted as dictionaries keyed by column name or ordered sequences.
    columns : Sequence[str]
        Ordered sequence of column header names.
    float_fmt : str, default="{:.4g}"
        Format string specification for floating point numbers.

    Returns
    -------
    str
        Markdown formatted table including headers, separators, and rows.
    """
    headers = [str(c) for c in columns]
    divider = ["---"] * len(headers)
    table_lines: list[str] = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(divider) + " |",
    ]

    # Explicit loop iteration cap to guard against non-terminating loops
    max_rows = len(rows) + 10
    step = 0
    for row in rows:
        step += 1
        if step > max_rows:
            break
        cells: list[str] = []
        if isinstance(row, dict):
            raw_vals = [row.get(col, "") for col in columns]
        else:
            raw_vals = list(row)

        for val in raw_vals:
            if isinstance(val, (float, int)) and not isinstance(val, bool):
                if isinstance(val, float):
                    cells.append(float_fmt.format(val))
                else:
                    cells.append(str(val))
            elif val is None:
                cells.append("N/A")
            else:
                cells.append(str(val))

        table_lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(table_lines)

