"""Lumina automation service executed on user request."""

from __future__ import annotations

from threading import Lock

from lumina_bot.config import LoginCredentials
from lumina_bot.core.application import Application
from lumina_bot.core.logger import configure_logging, get_logger
from lumina_bot.pages.login_page import LoginPage
from lumina_bot.pages.main_tile_page import MainTilePage
from lumina_bot.pages.pedido_page import PedidoPage


class LuminaAutomationService:
    """Runs the existing Lumina login automation as a backend feature."""

    _operation_lock = Lock()

    def __init__(self) -> None:
        configure_logging()
        self._logger = get_logger(self.__class__.__name__)

    @classmethod
    def is_busy(cls) -> bool:
        """Return True when this desktop worker is unavailable."""
        return cls._operation_lock.locked() or Application.has_lumina_window()

    def iniciar_lancamento(self) -> dict[str, str]:
        """Open Lumina, log in, and return execution status."""
        if not self._operation_lock.acquire(blocking=False):
            return {
                "status": "busy",
                "message": "Este executor Lumina ja esta atendendo outro usuario.",
            }

        try:
            if Application.has_lumina_window():
                return {
                    "status": "busy",
                    "message": "Este executor Lumina ja esta atendendo outro usuario.",
                }

            return self._run_login()
        finally:
            self._operation_lock.release()

    def _run_login(self) -> dict[str, str]:
        """Start Lumina and submit the configured login credentials."""
        credentials = LoginCredentials.from_env()
        app = Application()

        self._logger.info("Launching Lumina from desktop action...")
        main_window = app.launch_or_connect()

        login_page = LoginPage(main_window)
        login_page.login(credentials.username, credentials.password)

        main_window = app.wait_for_authenticated_window()
        pedido_window = MainTilePage(main_window).abrir_lista_pedidos()
        pedido_page = PedidoPage(pedido_window)
        pedido_page.selecionar_consulta_completa()
        pedido_page.confirmar()

        self._logger.info("Lumina order list opened with complete query.")
        return {
            "status": "started",
            "message": "Lista de pedidos aberta com consulta completa",
        }
