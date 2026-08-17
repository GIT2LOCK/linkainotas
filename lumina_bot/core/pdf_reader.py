"""PDF text and metadata extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lumina_bot.core.logger import get_logger
from lumina_bot.core.storage import StorageService
from lumina_bot.exceptions import PdfReadError


@dataclass(frozen=True, slots=True)
class PdfWord:
    """Word extracted from a PDF with page and bounding-box information."""

    text: str
    page: int
    x0: float
    y0: float
    x1: float
    y1: float
    block: int | None = None
    line: int | None = None
    word: int | None = None

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """Return the word bounding box."""
        return (self.x0, self.y0, self.x1, self.y1)


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
    pages: tuple[str, ...] = ()
    words: tuple[PdfWord, ...] = ()


class PdfReader:
    """Extracts text and metadata using PyMuPDF with pdfplumber fallback."""

    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)

    def read(self, path: Path) -> PdfReadResult:
        """Read a PDF file and return text, metadata, and diagnostics."""
        try:
            text, page_count, metadata, pages, words = self._read_with_pymupdf(path)

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
                pages=tuple(pages),
                words=tuple(words),
            )
        except Exception as exc:
            raise PdfReadError(f"Could not read PDF '{path}'.") from exc

    @staticmethod
    def _read_with_pymupdf(
        path: Path,
    ) -> tuple[str, int, dict[str, Any], list[str], list[PdfWord]]:
        import fitz

        parts: list[str] = []
        pages: list[str] = []
        words: list[PdfWord] = []

        with fitz.open(path) as document:
            metadata = dict(document.metadata or {})
            page_count = int(document.page_count)

            for page in document:
                page_text = page.get_text("text") or ""
                parts.append(page_text)
                pages.append(page_text)

                for raw_word in page.get_text("words") or []:
                    if len(raw_word) < 8 or not str(raw_word[4]).strip():
                        continue

                    words.append(
                        PdfWord(
                            text=str(raw_word[4]),
                            page=page.number + 1,
                            x0=float(raw_word[0]),
                            y0=float(raw_word[1]),
                            x1=float(raw_word[2]),
                            y1=float(raw_word[3]),
                            block=int(raw_word[5]),
                            line=int(raw_word[6]),
                            word=int(raw_word[7]),
                        )
                    )

        return "\n".join(parts), page_count, metadata, pages, words

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
