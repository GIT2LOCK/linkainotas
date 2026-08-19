"""Button control adapter."""

from __future__ import annotations

from typing import ClassVar

from lumina_bot.controls.base_control import BaseControl
from lumina_bot.core.waits import wait_for_interval
from lumina_bot.exceptions import ElementInteractionError, LuminaBotError


class Button(BaseControl):
    """Adapter for UIA Button controls."""

    control_type: ClassVar[str] = "Button"

    def click_with_invoke_fallback(self, timeout: float | None = None) -> None:
        """Click physically and invoke only if the same button remains.

        This is reserved for dialogs such as ``Pedido``. The login button
        keeps the base physical-click behavior because its window can remain
        briefly while Lumina transitions to the authenticated screen.
        """
        self._logger.info("Clicking %s...", self.locator.description)

        try:
            self.wait_ready(timeout=timeout)
            self._logger.info(
                "%s is ready; waiting %.1f seconds before clicking...",
                self.locator.description,
                self._config.action_delay,
            )
            wait_for_interval(self._config.action_delay)
            self._wrapper().click_input()
            wait_for_interval(self._config.wait_after_click)

            # Some DevExpress SimpleButton wrappers accept the mouse event but
            # do not execute the command. If the same button is still present,
            # retry through its UI Automation InvokePattern.
            if self._resolve_wrapper() is not None:
                wrapper = self._wrapper()
                invoke = getattr(wrapper, "invoke", None)
                if callable(invoke):
                    self._logger.info(
                        "Button %s is still present; invoking its UIA action...",
                        self.locator.description,
                    )
                    invoke()
                    wait_for_interval(self._config.wait_after_click)
        except LuminaBotError:
            self._capture_on_error("click_with_invoke_fallback")
            raise
        except Exception as exc:
            self._capture_on_error("click_with_invoke_fallback")
            raise ElementInteractionError(
                f"Could not click {self} with fallback."
            ) from exc
