"""Database-backed worker that assigns Lumina requests to one desktop machine."""

from __future__ import annotations

import os
import platform
import threading
from typing import Any

from supabase import Client, create_client

from lumina_bot.config import get_supabase_connection_config
from lumina_bot.core.application import Application
from lumina_bot.core.logger import configure_logging, get_logger

from backend.automation.lumina_service import LuminaAutomationService


class LuminaQueueWorker:
    """Poll and execute one queued Lumina job at a time on this machine."""

    def __init__(self) -> None:
        configure_logging()
        self._logger = get_logger(self.__class__.__name__)
        connection = get_supabase_connection_config()
        self._client: Client = create_client(connection.url, connection.service_role_key)
        self._worker_id = os.getenv("LINKAI_WORKER_ID") or f"{platform.node()}-lumina"
        self._poll_seconds = max(1.0, float(os.getenv("LINKAI_QUEUE_POLL_SECONDS", "3")))
        self._lease_seconds = max(60, int(os.getenv("LINKAI_QUEUE_LEASE_SECONDS", "300")))
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the polling loop once."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"linkai-lumina-queue-{self._worker_id}",
            daemon=True,
        )
        self._thread.start()
        self._logger.info("Lumina queue worker started: %s", self._worker_id)

    def stop(self) -> None:
        """Stop polling and allow the current lease to expire naturally."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def health(self) -> dict[str, Any]:
        """Return worker information for the local health endpoint."""
        return {
            "enabled": True,
            "worker_id": self._worker_id,
            "running": bool(self._thread and self._thread.is_alive()),
        }

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                job = self._claim_job()
                if job:
                    self._execute_job(job)
                    continue
            except Exception:
                self._logger.exception("Lumina queue polling failed.")

            self._stop_event.wait(self._poll_seconds)

    def _claim_job(self) -> dict[str, Any] | None:
        response = self._client.rpc(
            "claim_lumina_job",
            {
                "p_worker_id": self._worker_id,
                "p_lease_seconds": self._lease_seconds,
            },
        ).execute()
        rows = response.data or []
        return dict(rows[0]) if rows else None

    def _execute_job(self, job: dict[str, Any]) -> None:
        job_id = str(job["id"])
        self._logger.info("Claimed Lumina job %s", job_id)

        try:
            result = LuminaAutomationService().iniciar_lancamento()
            if result.get("status") == "busy":
                self._release_job(job_id, result.get("message", "Executor ocupado."))
                return

            if result.get("status") != "started":
                self._finish_job(
                    job_id,
                    "failed",
                    result.get("message", "Não foi possível iniciar o Lumina."),
                )
                return

            self._wait_until_lumina_is_released(job_id)
        except Exception as exc:
            self._logger.exception("Lumina job %s failed.", job_id)
            self._finish_job(job_id, "failed", str(exc))

    def _wait_until_lumina_is_released(self, job_id: str) -> None:
        while not self._stop_event.is_set():
            if not self._renew_job(job_id):
                return

            if not Application.has_lumina_window():
                self._finish_job(job_id, "succeeded", "Atendimento Lumina concluído.")
                return

            self._stop_event.wait(5)

    def _renew_job(self, job_id: str) -> bool:
        response = self._client.rpc(
            "renew_lumina_job",
            {
                "p_job_id": job_id,
                "p_worker_id": self._worker_id,
                "p_lease_seconds": self._lease_seconds,
            },
        ).execute()
        return bool(response.data)

    def _release_job(self, job_id: str, message: str) -> None:
        self._client.rpc(
            "release_lumina_job",
            {
                "p_job_id": job_id,
                "p_worker_id": self._worker_id,
                "p_message": message,
            },
        ).execute()

    def _finish_job(self, job_id: str, status: str, message: str) -> None:
        self._client.rpc(
            "finish_lumina_job",
            {
                "p_job_id": job_id,
                "p_worker_id": self._worker_id,
                "p_status": status,
                "p_message": message,
            },
        ).execute()
