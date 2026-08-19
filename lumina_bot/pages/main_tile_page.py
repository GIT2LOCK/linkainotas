"""Page object for the Lumina tile home screen."""

from __future__ import annotations

from pywinauto import Desktop
from pywinauto.application import WindowSpecification

from lumina_bot.config import AppConfig, DEFAULT_CONFIG
from lumina_bot.controls import ListItem
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
        self.lista_pedidos = ListItem(window, "Lista de Pedidos", config=config)

    def abrir_lista_pedidos(self, timeout: float | None = None) -> WindowSpecification:
        """Open the order list filter window through the tile's native action."""
        load_timeout = self._config.post_login_timeout if timeout is None else timeout
        self.lista_pedidos.wait_ready(timeout=load_timeout)
        self.lista_pedidos.double_click(timeout=load_timeout)
        pedido_window = Desktop(backend=self._config.backend).window(title="Pedido")
        pedido_window.wait(
            "visible enabled ready",
            timeout=load_timeout,
            retry_interval=self._config.retry_interval,
        )
        return pedido_window
