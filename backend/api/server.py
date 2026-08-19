"""Local FastAPI server for browser-based frontend development."""

from __future__ import annotations

import os
import shutil
import uuid
import logging
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.api.desktop_bridge import DesktopBridge
from lumina_bot.config import PROJECT_ROOT


class InvokeRequest(BaseModel):
    """Request body used by the React frontend during web development."""

    action: str
    payload: dict[str, Any] = Field(default_factory=dict)


app = FastAPI(
    title="LinkAI Local API",
    version="0.2.0",
    description="Local API used only when the frontend runs outside Tauri.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "LINKAI_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,https://linkai.2lock.app.br",
        ).split(",")
        if origin.strip()
    ],
    allow_origin_regex=os.getenv(
        "LINKAI_ALLOWED_ORIGIN_REGEX",
        r"https?://(localhost|127\.0\.0\.1|[0-9.]+)(:\d+)?|https://.*\.lovable\.app",
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_lumina_queue_worker: Any = None
_logger = logging.getLogger("linkai.api")


@app.on_event("startup")
def start_lumina_queue_worker() -> None:
    """Start one database-backed queue consumer on each Windows machine."""
    global _lumina_queue_worker

    enabled = os.getenv("LINKAI_QUEUE_WORKER_ENABLED", "true").strip().lower()
    if os.name != "nt" or enabled in {"0", "false", "no", "off"}:
        return

    try:
        from backend.automation.lumina_queue_worker import LuminaQueueWorker

        _lumina_queue_worker = LuminaQueueWorker()
        _lumina_queue_worker.start()
    except Exception:
        _logger.exception("Could not start the Lumina queue worker.")


@app.on_event("shutdown")
def stop_lumina_queue_worker() -> None:
    """Stop the queue consumer during a graceful API shutdown."""
    if _lumina_queue_worker is not None:
        _lumina_queue_worker.stop()


def require_token(request: Request, token_names: tuple[str, ...]) -> None:
    """Require one of the configured bearer tokens for protected commands."""
    expected_tokens = [
        token
        for token in (os.getenv(name) for name in token_names)
        if token
    ]

    if not expected_tokens:
        return

    authorization = request.headers.get("authorization", "")
    header_token = request.headers.get("x-linkai-bridge-token", "")

    for expected_token in expected_tokens:
        if authorization == f"Bearer {expected_token}" or header_token == expected_token:
            return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized request.",
    )


def require_processing_token(request: Request) -> None:
    """Require the processing API token when configured."""
    require_token(
        request,
        ("LINKAI_PROCESSING_TOKEN", "LINKAI_DOCUMENT_PROCESSING_TOKEN", "LINKAI_BRIDGE_TOKEN"),
    )


def require_action_token(request: Request, action: str) -> None:
    """Require the token that matches the requested command family."""
    if action == "lumina.start":
        require_token(request, ("LINKAI_LUMINA_TOKEN", "LINKAI_BRIDGE_TOKEN"))
        return

    require_token(
        request,
        ("LINKAI_PROCESSING_TOKEN", "LINKAI_DOCUMENT_PROCESSING_TOKEN", "LINKAI_BRIDGE_TOKEN"),
    )


@app.get("/health")
def health() -> dict[str, Any]:
    """Return local API health status."""
    return {
        "status": "ok",
        "busy": lumina_worker_busy(),
        "queue_worker": (
            _lumina_queue_worker.health()
            if _lumina_queue_worker is not None
            else {"enabled": False}
        ),
        "features": ["document-uploads", "construction-insights"],
    }


@app.post("/invoke")
def invoke_backend(request: InvokeRequest, http_request: Request) -> dict[str, Any]:
    """Invoke backend services using the same command bridge used by Tauri."""
    require_action_token(http_request, request.action)

    if request.action == "lumina.start" and lumina_worker_busy():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este executor Lumina ja esta atendendo outro usuario.",
        )

    result = DesktopBridge().handle(request.action, request.payload)

    if (
        request.action == "lumina.start"
        and isinstance(result.data, dict)
        and result.data.get("status") == "busy"
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(result.data.get("message", "Executor Lumina ocupado.")),
        )

    return result.to_dict()


def lumina_worker_busy() -> bool:
    """Read worker availability without importing desktop automation on Linux."""
    if os.name != "nt":
        return False

    try:
        from backend.automation import LuminaAutomationService

        return LuminaAutomationService.is_busy()
    except Exception:
        return False


@app.post("/uploads/documents", dependencies=[Depends(require_processing_token)])
async def upload_documents(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    """Receive PDF/XML documents selected in the browser as local temp files."""
    upload_dir = PROJECT_ROOT / "output" / "temp" / "uploads" / uuid.uuid4().hex
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[str] = []
    allowed_extensions = {".pdf", ".xml"}

    for uploaded_file in files:
        original_name = Path(uploaded_file.filename or "documento").name

        if Path(original_name).suffix.lower() not in allowed_extensions:
            continue

        destination = upload_dir / original_name

        with destination.open("wb") as buffer:
            shutil.copyfileobj(uploaded_file.file, buffer)

        saved_paths.append(str(destination))

    return {
        "paths": saved_paths,
        "count": len(saved_paths),
    }


@app.post("/uploads/pdfs", dependencies=[Depends(require_processing_token)])
async def upload_pdfs(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    """Backward-compatible upload endpoint for older frontend builds."""
    return await upload_documents(files)
