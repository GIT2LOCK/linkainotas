"""Command bridge used by Tauri IPC to call Python backend services."""

from __future__ import annotations

import json
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.automation import LuminaAutomationService
from backend.core.log_stream import LogStream
from backend.core.result import CommandResult, failure, success
from backend.models.ui import ProcessingOptions
from backend.services import (
    ConstructionInsightsService,
    DashboardService,
    DocumentProcessingService,
    OperatorService,
    SpreadsheetService,
)
from lumina_bot.config import get_supabase_config
from lumina_bot.core.supabase_client import SupabaseStorageClient


class DesktopBridge:
    """Dispatches frontend commands to backend services."""

    def handle(self, action: str, payload: dict[str, Any]) -> CommandResult:
        """Execute a backend command and return a serializable result."""
        try:
            if action == "dashboard.metrics":
                return success(DashboardService().metrics().to_dict())

            if action == "operator.profile":
                return success(OperatorService().profile().to_dict())

            if action == "noticias.recentes":
                limit = int(payload.get("limite", 6))
                force = bool(payload.get("force", False))
                return success(
                    ConstructionInsightsService().recent_news(limit, force=force)
                )

            if action == "indicadores.painel":
                force = bool(payload.get("force", False))
                return success(
                    ConstructionInsightsService().indicator_panel(force=force)
                )

            if action == "documents.process":
                options = ProcessingOptions.from_payload(payload)
                return success(DocumentProcessingService().process(options))

            if action == "documents.last":
                return success(DocumentProcessingService().last_processing())

            if action == "downloads.default_path":
                return success(DocumentProcessingService().default_download_path())

            if action == "files.list":
                return success(DocumentProcessingService().list_files())

            if action == "history.list":
                return success(DocumentProcessingService().list_history())

            if action == "lumina.start":
                return success(LuminaAutomationService().iniciar_lancamento())

            if action == "spreadsheets.list":
                return success(SpreadsheetService().list_spreadsheets())

            if action == "logs.latest":
                lines = int(payload.get("lines", 300))
                stream = LogStream()
                return success({"path": stream.export_path(), "lines": stream.latest(lines)})

            if action in {"cloud.test", "supabase.test"}:
                config = get_supabase_config()
                client = SupabaseStorageClient(config)
                files = client.listar(config.folder)
                if action == "cloud.test":
                    return success(
                        {
                            "status": "connected",
                            "space": config.bucket,
                            "folder": config.folder,
                            "items": len(files),
                        }
                    )

                return success(
                    {
                        "status": "connected",
                        "bucket": config.bucket,
                        "folder": config.folder,
                        "items": len(files),
                    }
                )

            return failure(f"Unknown action: {action}")
        except Exception as exc:
            return failure(str(exc))


def main() -> None:
    """CLI entry point used by the Tauri Rust shell command."""
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    payload_text = sys.argv[2] if len(sys.argv) > 2 else "{}"

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError:
        payload = {}

    with redirect_stdout(sys.stderr):
        result = DesktopBridge().handle(action, payload)

    print(json.dumps(result.to_dict(), ensure_ascii=False))


if __name__ == "__main__":
    main()
