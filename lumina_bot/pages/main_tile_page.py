"""Page object for the Lumina tile home screen."""

from __future__ import annotations

from pywinauto import Desktop
from pywinauto.application import WindowSpecification

from lumina_bot.config import AppConfig, DEFAULT_CONFIG
from lumina_bot.controls import ListItem
from lumina_bot.core.base_page import BasePage
from lumina_bot.core.waits import wait_until


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
        self.logger.info("Waiting for the Pedido dialog to become visible...")

        found_handle: int | None = None

        def find_pedido_dialog() -> bool:
            nonlocal found_handle
            desktop = Desktop(backend=self._config.backend)

            for window in desktop.windows(visible_only=True):
                try:
                    if (window.window_text() or "").strip().lower() == "pedido":
                        found_handle = window.handle
                        return True
                except Exception:
                    continue

            return False

        wait_until(
            find_pedido_dialog,
            timeout=load_timeout,
            retry_interval=self._config.retry_interval,
            description="janela Pedido visível",
        )

        if found_handle is None:
            raise RuntimeError("A janela Pedido foi encontrada, mas não possui handle.")

        pedido_window = Desktop(backend=self._config.backend).window(handle=found_handle)
        self.logger.info("Pedido dialog found; continuing with its controls.")
        return pedido_window
