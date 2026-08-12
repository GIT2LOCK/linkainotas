"""Local FastAPI server for browser-based frontend development."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, UploadFile
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
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|[0-9.]+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, Any]:
    """Return local API health status."""
    return {
        "status": "ok",
        "features": ["document-uploads", "construction-insights"],
    }


@app.post("/invoke")
def invoke_backend(request: InvokeRequest) -> dict[str, Any]:
    """Invoke backend services using the same command bridge used by Tauri."""
    result = DesktopBridge().handle(request.action, request.payload)
    return result.to_dict()


@app.post("/uploads/documents")
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


@app.post("/uploads/pdfs")
async def upload_pdfs(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    """Backward-compatible upload endpoint for older frontend builds."""
    return await upload_documents(files)
