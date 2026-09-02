"""Persistent UI registry for processed documents, files, and history."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from lumina_bot.config import PROJECT_ROOT
from lumina_bot.core.logger import get_logger
from lumina_bot.core.storage import StorageService


class ProcessingUiRegistry:
    """Stores desktop UI processing state without coupling it to React."""

    def __init__(self, project_root: Path = PROJECT_ROOT) -> None:
        self._root = project_root
        self._state_path = self._root / "output" / "temp" / "ui_processing_state.json"
        self._default_download_path = self._root / "output" / "pdfs"
        self._logger = get_logger(self.__class__.__name__)

    @property
    def default_download_path(self) -> Path:
        """Return the default local folder used for downloaded PDFs."""
        self._default_download_path.mkdir(parents=True, exist_ok=True)
        return self._default_download_path

    def processing_progress(self) -> dict[str, Any]:
        """Return the current document-processing progress for the UI."""
        state = self._load()
        progress = state.get("processing")
        return deepcopy(progress) if isinstance(progress, dict) else self._empty_progress()

    def start_processing(self, *, source: str, total: int | None = None) -> None:
        """Start a progress record before the potentially long processing call."""
        state = self._load()
        state["processing"] = self._progress_record(
            source=source,
            total=max(int(total or 0), 0),
            status="running",
            phase="Preparando processamento",
        )
        self._save(state)

    def set_processing_total(self, total: int) -> None:
        """Set the total after the selected source has been enumerated."""
        state = self._load()
        progress = state.get("processing")
        if not isinstance(progress, dict) or progress.get("status") != "running":
            return

        progress["total"] = max(int(total), 0)
        progress["updatedAt"] = self._now()
        self._save(state)

    def update_processing(
        self,
        *,
        completed: int,
        total: int,
        current_file: str | None,
        phase: str,
        stage_progress: float = 0.0,
    ) -> None:
        """Persist a lightweight progress snapshot without blocking processing."""
        state = self._load()
        progress = state.get("processing")
        if not isinstance(progress, dict) or progress.get("status") != "running":
            return

        normalized_total = max(int(total), 0)
        normalized_completed = min(max(int(completed), 0), normalized_total)
        normalized_stage = min(max(float(stage_progress), 0.0), 1.0)
        percentage = 0

        if normalized_total:
            percentage = round(
                min(96.0, ((normalized_completed + normalized_stage) / normalized_total) * 96)
            )
        else:
            percentage = max(int(progress.get("progress") or 0), 4)

        progress.update(
            {
                "total": normalized_total,
                "completed": normalized_completed,
                "progress": percentage,
                "currentFile": current_file,
                "phase": phase,
                "error": None,
                "updatedAt": self._now(),
            }
        )
        self._save(state)

    def complete_processing(self) -> None:
        """Mark the current processing run as complete."""
        state = self._load()
        progress = state.get("processing")
        if not isinstance(progress, dict):
            return

        progress.update(
            {
                "status": "completed",
                "completed": int(progress.get("total") or 0),
                "progress": 100,
                "currentFile": None,
                "phase": "Processamento concluído",
                "error": None,
                "updatedAt": self._now(),
            }
        )
        self._save(state)

    def fail_processing(self, error: str) -> None:
        """Keep the last progress snapshot available when processing fails."""
        state = self._load()
        progress = state.get("processing")
        if not isinstance(progress, dict):
            progress = self._progress_record(
                source="unknown",
                total=0,
                status="error",
                phase="Falha",
            )
            state["processing"] = progress

        progress.update(
            {
                "status": "error",
                "phase": "Falha no processamento",
                "error": error,
                "updatedAt": self._now(),
            }
        )
        self._save(state)

    def last_processing(self) -> dict[str, Any] | None:
        """Return the most recent processing response shown in the UI."""
        state = self._load()
        last = state.get("lastProcessing")
        return deepcopy(last) if isinstance(last, dict) else None

    def list_history(self) -> list[dict[str, Any]]:
        """Return processing sessions from newest to oldest."""
        state = self._load()
        history = state.get("history", [])
        return history if isinstance(history, list) else []

    def list_files(self) -> list[dict[str, Any]]:
        """Return registered PDFs and PDFs discovered in the default output folder."""
        state = self._load()
        files = state.get("files", [])
        indexed: dict[str, dict[str, Any]] = {}

        if isinstance(files, list):
            for record in files:
                if not isinstance(record, dict):
                    continue

                key = self._file_key(record)
                if key:
                    indexed[key] = record

        for document_path in self._local_documents_from_disk():
            record = self._record_from_disk(document_path)
            key = self._file_key(record)

            if key and key not in indexed:
                indexed[key] = record

        return sorted(
            indexed.values(),
            key=lambda record: str(record.get("processedAt") or record.get("modifiedAt") or ""),
            reverse=True,
        )

    def has_success_hash(self, sha256: str | None) -> bool:
        """Return True when a successful registered file with this hash still exists."""
        if not sha256:
            return False

        for record in self.list_files():
            if record.get("hash") != sha256 or record.get("status") != "success":
                continue

            path = record.get("path")
            if path and Path(str(path)).is_file():
                return True

        return False

    def save_processing(
        self,
        *,
        response: dict[str, Any],
        file_records: list[dict[str, Any]],
        source: str,
        download_path: Path | None,
        download_label: str | None = None,
    ) -> dict[str, Any]:
        """Persist a completed processing response and return the enriched response."""
        state = self._load()
        processed_at = datetime.now().isoformat(timespec="seconds")
        session_id = uuid4().hex
        summary = dict(response.get("summary") or {})
        status = self._session_status(summary)
        shown_download_path = download_label or (str(download_path) if download_path else None)
        enriched_response = deepcopy(response)
        enriched_response["sessionId"] = session_id
        enriched_response["processedAt"] = processed_at
        enriched_response["downloadPath"] = shown_download_path

        session = {
            "sessionId": session_id,
            "processedAt": processed_at,
            "source": source,
            "downloadPath": shown_download_path,
            "listed": int(summary.get("listed") or 0),
            "processed": int(summary.get("processed") or 0),
            "ignored": int(summary.get("ignored") or 0),
            "failed": int(summary.get("failed") or 0),
            "duplicated": int(summary.get("duplicated") or 0),
            "elapsedSeconds": float(summary.get("elapsedSeconds") or 0),
            "status": status,
        }

        persisted_response = deepcopy(enriched_response)
        persisted_response.pop("excelFiles", None)
        state["lastProcessing"] = persisted_response
        state["history"] = self._limited([session, *self.list_history()], limit=500)
        state["files"] = self._merge_files(file_records, self.list_files(), processed_at)
        self._save(state)
        return enriched_response

    def _record_from_disk(self, path: Path) -> dict[str, Any]:
        stat = path.stat()

        try:
            sha256 = StorageService.sha256_file(path)
        except OSError:
            sha256 = None

        return {
            "id": sha256 or str(path),
            "name": path.name,
            "type": self._file_type(path),
            "path": str(path),
            "originPath": None,
            "sizeBytes": stat.st_size,
            "hash": sha256,
            "source": "local",
            "documentType": None,
            "parser": None,
            "pageCount": None,
            "status": "available",
            "error": None,
            "processedAt": None,
            "modifiedAt": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        }

    def _local_documents_from_disk(self) -> list[Path]:
        documents: list[Path] = []

        for extension in ("*.pdf", "*.xml"):
            documents.extend(sorted(self.default_download_path.rglob(extension)))

        return sorted(documents)

    def _merge_files(
        self,
        new_records: list[dict[str, Any]],
        existing_records: list[dict[str, Any]],
        processed_at: str,
    ) -> list[dict[str, Any]]:
        indexed: dict[str, dict[str, Any]] = {}

        for record in existing_records:
            key = self._file_key(record)

            if key:
                indexed[key] = dict(record)

        for record in new_records:
            prepared = dict(record)
            prepared["processedAt"] = processed_at
            key = self._file_key(prepared)

            if key:
                indexed[key] = prepared

        return self._limited(
            sorted(
                indexed.values(),
                key=lambda record: str(record.get("processedAt") or record.get("modifiedAt") or ""),
                reverse=True,
            ),
            limit=10000,
        )

    def _load(self) -> dict[str, Any]:
        if not self._state_path.is_file():
            return self._empty_state()

        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self._logger.exception("Invalid UI processing state was ignored: %s", self._state_path)
            return self._empty_state()

        if not isinstance(data, dict):
            return self._empty_state()

        data.setdefault("lastProcessing", None)
        data.setdefault("history", [])
        data.setdefault("files", [])
        data.setdefault("processing", self._empty_progress())
        return data

    def _save(self, state: dict[str, Any]) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._state_path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self._state_path)

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return {
            "lastProcessing": None,
            "history": [],
            "files": [],
            "processing": ProcessingUiRegistry._empty_progress(),
        }

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    @classmethod
    def _progress_record(
        cls,
        *,
        source: str,
        total: int,
        status: str,
        phase: str,
    ) -> dict[str, Any]:
        return {
            "status": status,
            "source": source,
            "total": total,
            "completed": 0,
            "progress": 0,
            "currentFile": None,
            "phase": phase,
            "error": None,
            "updatedAt": cls._now(),
        }

    @classmethod
    def _empty_progress(cls) -> dict[str, Any]:
        return cls._progress_record(
            source="unknown",
            total=0,
            status="idle",
            phase="Aguardando processamento",
        )

    @staticmethod
    def _file_key(record: dict[str, Any]) -> str | None:
        sha256 = record.get("hash")

        if sha256:
            return f"hash:{sha256}"

        path = record.get("path")
        return f"path:{path}" if path else None

    @staticmethod
    def _limited(records: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
        return records[:limit]

    @staticmethod
    def _session_status(summary: dict[str, Any]) -> str:
        failed = int(summary.get("failed") or 0)
        processed = int(summary.get("processed") or 0)
        duplicated = int(summary.get("duplicated") or 0)

        if failed and not processed and not duplicated:
            return "error"

        if failed:
            return "partial"

        return "success"

    @staticmethod
    def _file_type(path: Path) -> str:
        extension = path.suffix.lower()

        if extension == ".xml":
            return "XML"

        if extension == ".pdf":
            return "PDF"

        return "DOCUMENTO"
