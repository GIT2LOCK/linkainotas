"""OCR extension point for PDFs without extractable text."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lumina_bot.core.logger import get_logger


@dataclass(frozen=True, slots=True)
class OcrResult:
    """Result returned by OCR providers."""

    text: str
    required: bool
    engine: str
    confidence: float | None = None


class OcrService:
    """Placeholder service prepared for future OCR providers."""

    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)

    def extract_text(self, path: Path) -> OcrResult:
        """Return an empty result while OCR is not configured."""
        self._logger.info("OCR required but no OCR engine is configured: %s", path)
        return OcrResult(
            text="",
            required=True,
            engine="not_configured",
            confidence=None,
        )
