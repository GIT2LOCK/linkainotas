"""Spreadsheet library service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lumina_bot.config import PROJECT_ROOT


class SpreadsheetService:
    """Lists generated spreadsheets for the desktop UI."""

    def __init__(self, excel_dir: Path | None = None) -> None:
        self._excel_dir = excel_dir or PROJECT_ROOT / "output" / "excel"

    def list_spreadsheets(self) -> list[dict[str, Any]]:
        """Return generated spreadsheets metadata."""
        self._excel_dir.mkdir(parents=True, exist_ok=True)
        spreadsheets: list[dict[str, Any]] = []

        for path in sorted(self._excel_dir.glob("*.xlsx")):
            stat = path.stat()
            spreadsheets.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "sizeBytes": stat.st_size,
                    "modifiedAt": stat.st_mtime,
                }
            )

        return spreadsheets
