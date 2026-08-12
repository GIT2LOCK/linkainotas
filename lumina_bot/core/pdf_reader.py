"""PDF text and metadata extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lumina_bot.core.logger import get_logger
from lumina_bot.core.storage import StorageService
from lumina_bot.exceptions import PdfReadError


@dataclass(frozen=True, slots=True)
class PdfReadResult:
    """Complete PDF extraction result."""

    path: Path
    text: str
    page_count: int
    author: str | None
    creator: str | None
    producer: str | None
    size_bytes: int
    sha256: str
    metadata: dict[str, Any] = field(default_factory=dict)
    ocr_required: bool = False


class PdfReader:
    """Extracts text and metadata using PyMuPDF with pdfplumber fallback."""

    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)

    def read(self, path: Path) -> PdfReadResult:
        """Read a PDF file and return text, metadata, and diagnostics."""
        try:
            text, page_count, metadata = self._read_with_pymupdf(path)

            if not text.strip():
                self._logger.info("No text via PyMuPDF, trying pdfplumber: %s", path)
                fallback_text = self._read_text_with_pdfplumber(path)
                text = fallback_text or text

            ocr_required = not bool(text.strip())
            sha256 = StorageService.sha256_file(path)
            stat = path.stat()

            return PdfReadResult(
                path=path,
                text=text,
                page_count=page_count,
                author=self._metadata_value(metadata, "author"),
                creator=self._metadata_value(metadata, "creator"),
                producer=self._metadata_value(metadata, "producer"),
                size_bytes=stat.st_size,
                sha256=sha256,
                metadata=metadata,
                ocr_required=ocr_required,
            )
        except Exception as exc:
            raise PdfReadError(f"Could not read PDF '{path}'.") from exc

    @staticmethod
    def _read_with_pymupdf(path: Path) -> tuple[str, int, dict[str, Any]]:
        import fitz

        parts: list[str] = []

        with fitz.open(path) as document:
            metadata = dict(document.metadata or {})
            page_count = int(document.page_count)

            for page in document:
                parts.append(page.get_text("text") or "")

        return "\n".join(parts), page_count, metadata

    @staticmethod
    def _read_text_with_pdfplumber(path: Path) -> str:
        import pdfplumber

        parts: list[str] = []

        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")

        return "\n".join(parts)

    @staticmethod
    def _metadata_value(metadata: dict[str, Any], key: str) -> str | None:
        value = metadata.get(key)
        return str(value) if value else None
