"""Screenshot utilities prepared for future diagnostics."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from re import sub

from pywinauto.application import WindowSpecification

from lumina_bot.config import DEFAULT_CONFIG
from lumina_bot.core.logger import get_logger


class ScreenshotManager:
    """Captures screenshots from the active Lumina window when enabled."""

    def __init__(self, screenshots_dir: Path = DEFAULT_CONFIG.screenshots_dir) -> None:
        self._screenshots_dir = screenshots_dir
        self._logger = get_logger(self.__class__.__name__)

    def capture_window(
        self,
        window: WindowSpecification,
        file_prefix: str,
    ) -> Path | None:
        """Capture a screenshot from a pywinauto window wrapper."""
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._screenshots_dir / self._build_file_name(file_prefix)

        try:
            image = window.wrapper_object().capture_as_image()
            image.save(output_path)
            self._logger.info("Screenshot saved: %s", output_path)
            return output_path
        except Exception:
            self._logger.warning("Could not capture screenshot.", exc_info=True)
            return None

    @staticmethod
    def _build_file_name(file_prefix: str) -> str:
        safe_prefix = sub(r"[^A-Za-z0-9_.-]+", "_", file_prefix).strip("_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{safe_prefix}_{timestamp}.png"
