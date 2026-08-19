"""Page object for the Lumina tile home screen."""

from __future__ import annotations

from pywinauto.application import WindowSpecification

from lumina_bot.config import AppConfig, DEFAULT_CONFIG
from lumina_bot.controls import FastEntry
from lumina_bot.core.base_page import BasePage


class MainTilePage(BasePage):
    """Represents the tile menu shown after Lumina login."""

    def __init__(
        self,
        window: WindowSpecification,
        config: AppConfig = DEFAULT_CONFIG,
    ) -> None:
        super().__init__(window)
        self._config = config
        self.fast_entry = FastEntry(window, config=config)

    def digitar_codigo_programa(
        self,
        code: str,
        *,
        press_enter: bool = False,
        timeout: float | None = None,
    ) -> None:
        """Enter a Lumina program code in the authenticated main window."""
        load_timeout = self._config.post_login_timeout if timeout is None else timeout
        self.fast_entry.enter_code(
            code,
            press_enter=press_enter,
            timeout=load_timeout,
        )
