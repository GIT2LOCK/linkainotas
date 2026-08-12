"""Lumina automation service executed on user request."""

from __future__ import annotations

from lumina_bot.config import LoginCredentials
from lumina_bot.core.application import Application
from lumina_bot.core.logger import configure_logging, get_logger
from lumina_bot.core.waits import wait_for_interval
from lumina_bot.pages.login_page import LoginPage


class LuminaAutomationService:
    """Runs the existing Lumina login automation as a backend feature."""

    def __init__(self) -> None:
        configure_logging()
        self._logger = get_logger(self.__class__.__name__)

    def iniciar_lancamento(self) -> dict[str, str]:
        """Open Lumina, log in, and return execution status."""
        credentials = LoginCredentials.from_env()
        app = Application()

        self._logger.info("Launching Lumina from desktop action...")
        main_window = app.launch_or_connect()
        wait_for_interval(10)

        login_page = LoginPage(main_window)
        login_page.login(credentials.username, credentials.password)

        self._logger.info("Lumina login submitted from desktop action.")
        return {"status": "started", "message": "Lumina login submitted"}
