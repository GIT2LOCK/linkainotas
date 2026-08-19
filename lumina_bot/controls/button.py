"""Button control adapter."""

from __future__ import annotations

from typing import ClassVar

from lumina_bot.controls.base_control import BaseControl
from lumina_bot.core.waits import wait_for_interval
from lumina_bot.exceptions import ElementInteractionError, LuminaBotError


class Button(BaseControl):
    """Adapter for UIA Button controls."""

    control_type: ClassVar[str] = "Button"

    def click(self, timeout: float | None = None) -> None:
        """Click the button physically, then use InvokePattern if needed."""
        self._logger.info("Clicking %s...", self.locator.description)

        try:
            self.wait_ready(timeout=timeout)
            wrapper = self._wrapper()
            set_focus = getattr(wrapper, "set_focus", None)
            if callable(set_focus):
                set_focus()

            click_input = getattr(wrapper, "click_input", None)
            if not callable(click_input):
                raise ElementInteractionError(f"Physical click is unavailable for {self}.")
            click_input()
            wait_for_interval(self._config.wait_after_click)

            # Some DevExpress SimpleButton wrappers accept the mouse event but
            # do not execute the command. If the same button is still present,
            # retry through its UI Automation InvokePattern.
            if self._resolve_wrapper() is not None:
                invoke = getattr(wrapper, "invoke", None)
                if callable(invoke):
                    self._logger.info(
                        "Button %s is still present; invoking its UIA action...",
                        self.locator.description,
                    )
                    invoke()
                    wait_for_interval(self._config.wait_after_click)
        except LuminaBotError:
            self._capture_on_error("click")
            raise
        except Exception as exc:
            self._capture_on_error("click")
            raise ElementInteractionError(f"Could not click {self}.") from exc
