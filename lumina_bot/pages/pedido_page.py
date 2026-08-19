"""Page object for the Lumina order-list filter dialog."""

from __future__ import annotations

from pywinauto.application import WindowSpecification

from lumina_bot.controls import Button, RadioButton
from lumina_bot.core.base_page import BasePage


class PedidoPage(BasePage):
    """Represents the Pedido query options dialog."""

    def __init__(self, window: WindowSpecification) -> None:
        super().__init__(window)
        self.consulta_completa = RadioButton(window, "Consulta Completa")
        self.ok = Button(window, "btnOk")

    def selecionar_consulta_completa(self) -> None:
        """Select the complete order-list query."""
        self.consulta_completa.select()

    def confirmar(self) -> None:
        """Confirm the selected order-list query."""
        self.ok.click_with_invoke_fallback()
