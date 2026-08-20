"""Optional OCR support for scanned fiscal PDFs.

The parser remains usable when Tesseract is not installed. In that case the
result explicitly says that OCR was not configured instead of pretending that
an empty text layer was successfully processed.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
from typing import Any

from lumina_bot.core.logger import get_logger
from lumina_bot.core.pdf_reader import PdfWord


@dataclass(frozen=True, slots=True)
class OcrResult:
    """Result returned by OCR providers."""

    text: str
    required: bool
    engine: str
    confidence: float | None = None
    pages: tuple[str, ...] = ()
    words: tuple[PdfWord, ...] = ()


class OcrService:
    """Run Tesseract OCR when the optional local dependencies are available."""

    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)

    def extract_text(self, path: Path) -> OcrResult:
        """Render each page and extract Portuguese text with coordinates."""
        try:
            import fitz
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            self._logger.warning("OCR dependencies are unavailable: %s", exc)
            return OcrResult(text="", required=True, engine="not_configured")

        if not self._configure_tesseract(pytesseract):
            self._logger.warning(
                "Tesseract executable was not found. Set TESSERACT_CMD or install it."
            )
            return OcrResult(text="", required=True, engine="not_configured")

        try:
            pages: list[str] = []
            words: list[PdfWord] = []
            confidences: list[float] = []
            language = self._language(pytesseract)

            with fitz.open(path) as document:
                for page_number, page in enumerate(document, start=1):
                    # Scanned DANFEs contain small fiscal columns. Four times
                    # keeps digits and column boundaries readable while OCR
                    # remains limited to documents without a text layer.
                    requested_scale = float(os.getenv("LINKAI_OCR_SCALE", "4.0"))
                    scale = requested_scale
                    try:
                        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                    except Exception:
                        # A large scanned page can exceed the available memory
                        # on smaller workers. Retry the same page at a safer
                        # resolution instead of discarding the whole document.
                        scale = min(requested_scale, 2.0)
                        self._logger.warning(
                            "OCR render fallback at scale %s for page %s: %s",
                            scale,
                            page_number,
                            path.name,
                        )
                        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                    data: dict[str, Any] = pytesseract.image_to_data(
                        image,
                        lang=language,
                        config=os.getenv("LINKAI_OCR_CONFIG", "--psm 3"),
                        output_type=pytesseract.Output.DICT,
                    )
                    page_lines = self._lines_from_data(data)
                    primary_text = "\n".join(page_lines)
                    # PSM 3 preserves the product columns better; PSM 6 is
                    # useful for the compact totals row in scanned DANFEs.
                    supplement = pytesseract.image_to_string(
                        image,
                        lang=language,
                        config=os.getenv("LINKAI_OCR_SUPPLEMENT_CONFIG", "--psm 6"),
                    ).strip()
                    pages.append("\n".join(part for part in (primary_text, supplement) if part))
                    for index, value in enumerate(data.get("text", [])):
                        token = str(value).strip()
                        if not token:
                            continue
                        confidence = self._confidence(data.get("conf", [])[index])
                        if confidence is not None:
                            confidences.append(confidence)
                        words.append(
                            PdfWord(
                                text=token,
                                page=page_number,
                                x0=float(data["left"][index]) / scale,
                                y0=float(data["top"][index]) / scale,
                                x1=float(data["left"][index] + data["width"][index]) / scale,
                                y1=float(data["top"][index] + data["height"][index]) / scale,
                            )
                        )

            text = "\n\n".join(pages).strip()
            confidence = round(sum(confidences) / len(confidences) / 100, 3) if confidences else None
            return OcrResult(
                text=text,
                required=True,
                engine=f"tesseract:{language}",
                confidence=confidence,
                pages=tuple(pages),
                words=tuple(words),
            )
        except Exception:
            self._logger.exception("OCR failed for %s", path)
            return OcrResult(text="", required=True, engine="failed")

    @staticmethod
    def _configure_tesseract(pytesseract: Any) -> bool:
        """Find Tesseract without requiring a machine-specific PATH entry."""
        configured = os.getenv("TESSERACT_CMD") or os.getenv("LINKAI_TESSERACT_CMD")
        candidates = [configured] if configured else []
        candidates.extend(
            [
                shutil.which("tesseract"),
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                "/usr/bin/tesseract",
                "/usr/local/bin/tesseract",
            ]
        )

        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate)
            if path.is_file():
                pytesseract.pytesseract.tesseract_cmd = str(path)
                return True
        return False

    @staticmethod
    def _language(pytesseract: Any) -> str:
        try:
            languages = set(pytesseract.get_languages(config=""))
        except Exception:
            languages = set()
        return "por+eng" if {"por", "eng"}.issubset(languages) else ("por" if "por" in languages else "eng")

    @staticmethod
    def _confidence(value: Any) -> float | None:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None

    @staticmethod
    def _lines_from_data(data: dict[str, Any]) -> list[str]:
        grouped: dict[tuple[int, int, int], list[tuple[int, str]]] = {}
        for index, value in enumerate(data.get("text", [])):
            token = str(value).strip()
            if not token:
                continue
            key = (
                int(data.get("block_num", [0])[index]),
                int(data.get("par_num", [0])[index]),
                int(data.get("line_num", [0])[index]),
            )
            grouped.setdefault(key, []).append((int(data.get("left", [0])[index]), token))
        return [" ".join(token for _, token in sorted(tokens)) for _, tokens in sorted(grouped.items())]
