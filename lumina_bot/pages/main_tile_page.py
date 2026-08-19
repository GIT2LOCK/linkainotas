"""Page object for the Lumina tile home screen."""

from __future__ import annotations

from pywinauto.application import WindowSpecification

from lumina_bot.controls import ListItem
from lumina_bot.core.base_page import BasePage


class MainTilePage(BasePage):
    """Represents the tile menu shown after Lumina login."""

    def __init__(self, window: WindowSpecification) -> None:
        super().__init__(window)
        self.lista_pedidos = ListItem(window, "Lista de Pedidos")

    def abrir_lista_pedidos(self) -> WindowSpecification:
        """Open the order list filter window using UI Automation InvokePattern."""
        self.lista_pedidos.invoke()
        pedido_window = self.window.child_window(
            title="Pedido",
            control_type="Window",
        )
        pedido_window.wait("visible enabled ready")
        return pedido_window
