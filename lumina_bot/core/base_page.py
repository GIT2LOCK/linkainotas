"""Base page object for Lumina windows and screens.

Page objects model screens and workflows. They should compose controls instead
of calling pywinauto directly.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from pywinauto.application import WindowSpecification

from lumina_bot.config import DEFAULT_CONFIG
from lumina_bot.core.logger import get_logger
from lumina_bot.core.waits import wait_until
from lumina_bot.utils.screenshots import ScreenshotManager


class BasePage:
    """Reusable behavior shared by every Lumina page object."""

    def __init__(self, window: WindowSpecification) -> None:
        self.window = window

    @property
    def logger(self) -> logging.Logger:
        """Return a page-specific logger without storing extra state."""
        return get_logger(f"pages.{self.__class__.__name__}")

    def wait_for(
        self,
        condition: Callable[[], bool],
        description: str,
        timeout: float | None = None,
    ) -> None:
        """Wait for a page-level condition."""
        wait_until(
            condition,
            timeout=DEFAULT_CONFIG.implicit_timeout if timeout is None else timeout,
            retry_interval=DEFAULT_CONFIG.retry_interval,
            description=description,
        )

    def capture_screenshot(self, file_prefix: str) -> None:
        """Capture a page screenshot when diagnostics are enabled."""
        if DEFAULT_CONFIG.screenshot_on_error:
            ScreenshotManager(DEFAULT_CONFIG.screenshots_dir).capture_window(
                self.window,
                file_prefix,
            )
