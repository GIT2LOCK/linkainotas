"""Page object for the Lumina tile home screen."""

from __future__ import annotations

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
        self.logger.info("Waiting for the Pedido tab controls to become visible...")

        def pedido_controls_are_visible() -> bool:
            try:
                root = self.window.wrapper_object()
                has_complete_query = False
                has_ok_button = False

                for control in root.descendants():
                    info = getattr(control, "element_info", None)
                    name = str(getattr(info, "name", "") or "")
                    automation_id = str(getattr(info, "automation_id", "") or "")

                    if name == "Consulta Completa":
                        has_complete_query = True
                    if automation_id == "btnOk":
                        has_ok_button = True

                    if has_complete_query and has_ok_button:
                        return True
            except Exception:
                return False

            return False

        wait_until(
            pedido_controls_are_visible,
            timeout=load_timeout,
            retry_interval=self._config.retry_interval,
            description="controles da aba Pedido visíveis",
        )
        self.logger.info("Pedido tab controls found; continuing with its controls.")
        return self.window
