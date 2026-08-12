"""Page object for the Lumina login screen."""

from __future__ import annotations

from pywinauto.application import WindowSpecification

from lumina_bot.controls import Button, ComboBox, TextBox
from lumina_bot.core.base_page import BasePage


class LoginPage(BasePage):
    """Represents the login screen and its controls."""

    def __init__(self, window: WindowSpecification) -> None:
        super().__init__(window)

        self.usuario = TextBox(window, "txtLogin")
        self.senha = TextBox(window, "txtPassword")
        self.base = ComboBox(window, "ComboBoxEditDatabase")
        self.idioma = ComboBox(window, "ComboBoxEditLanguages")
        self.ok = Button(window, "btnOk")
        self.cancelar = Button(window, "btnCancel")
        self.conexao = Button(window, "btnConnection")

    def login(self, usuario: str, senha: str) -> None:
        """Fill credentials and submit the login form."""
        self.logger.info("Starting login flow...")
        self.logger.info("Typing username...")
        self.usuario.set(usuario)
        self.logger.info("Typing password...")
        self.senha.set(senha, sensitive=True)
        self.clicar_ok()

    def selecionar_base(self, nome: str) -> None:
        """Select the target database/base."""
        self.logger.info("Selecting database...")
        self.base.select(nome)

    def selecionar_idioma(self, nome: str) -> None:
        """Select the target language."""
        self.logger.info("Selecting language...")
        self.idioma.select(nome)

    def clicar_ok(self) -> None:
        """Click the OK button."""
        self.logger.info("Clicking OK...")
        self.ok.click()

    def clicar_cancelar(self) -> None:
        """Click the Cancel button."""
        self.logger.info("Clicking Cancel...")
        self.cancelar.click()

    def is_loaded(self, timeout: float = 2.0) -> bool:
        """Return True when the known login controls are present."""
        return (
            self.usuario.exists(timeout=timeout)
            and self.senha.exists(timeout=timeout)
            and self.base.exists(timeout=timeout)
            and self.idioma.exists(timeout=timeout)
            and self.ok.exists(timeout=timeout)
            and self.cancelar.exists(timeout=timeout)
        )
