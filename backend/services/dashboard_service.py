"""Dashboard metrics service."""

from __future__ import annotations

import os
from pathlib import Path

from lumina_bot.config import PROJECT_ROOT

from backend.models.ui import DashboardMetrics
from backend.services.processing_ui_registry import ProcessingUiRegistry


class DashboardService:
    """Builds dashboard metrics without knowing frontend details."""

    def __init__(self, project_root: Path = PROJECT_ROOT) -> None:
        self._root = project_root
        self._output = self._root / "output"
        self._registry = ProcessingUiRegistry(project_root)

    def metrics(self) -> DashboardMetrics:
        """Return current dashboard metrics."""
        registered_files = self._registry.list_files()
        spreadsheets = list((self._output / "excel").glob("*.xlsx"))
        history = self._registry.list_history()
        success = [
            record
            for record in registered_files
            if record.get("status") in {"success", "available"}
        ]
        errors = [record for record in registered_files if record.get("status") == "error"]
        elapsed_values = [
            float(record.get("elapsedSeconds") or 0)
            for record in history
            if float(record.get("elapsedSeconds") or 0) > 0
        ]

        return DashboardMetrics(
            pdf_count=len(registered_files),
            processed_count=len(success),
            error_count=len(errors),
            spreadsheet_count=len(spreadsheets),
            last_processing=history[0].get("processedAt") if history else None,
            last_sync=history[0].get("processedAt") if history else None,
            average_time_seconds=(
                sum(elapsed_values) / len(elapsed_values) if elapsed_values else None
            ),
            supabase_status=self._supabase_status(),
            used_space_bytes=self._used_space_bytes(registered_files),
        )

    @staticmethod
    def _used_space_bytes(records: list[dict[str, object]]) -> int:
        total = 0

        for record in records:
            path = record.get("path")

            if not path:
                continue

            file_path = Path(str(path))

            if file_path.is_file():
                total += file_path.stat().st_size

        return total

    @staticmethod
    def _supabase_status() -> str:
        required = ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_BUCKET")
        return "configured" if all(os.getenv(name) for name in required) else "not_configured"
