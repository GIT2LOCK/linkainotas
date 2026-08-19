"""Radio button control adapter."""

from __future__ import annotations

from typing import ClassVar

from lumina_bot.controls.base_control import BaseControl
from lumina_bot.core.waits import wait_for_interval
from lumina_bot.exceptions import ElementInteractionError, LuminaBotError


class RadioButton(BaseControl):
    """Adapter for a UI Automation RadioButton identified by visible name."""

    control_type: ClassVar[str] = "RadioButton"

    def __init__(self, window, name: str) -> None:
        super().__init__(window, "", name=name)

    def select(self, timeout: float | None = None) -> None:
        """Select the radio option through SelectionItemPattern."""
        self._logger.info("Selecting %s...", self.locator.description)

        try:
            self.wait_ready(timeout=timeout)
            wrapper = self._wrapper()
            select = getattr(wrapper, "select", None)
            if callable(select):
                select()
            else:
                invoke = getattr(wrapper, "invoke", None)
                if not callable(invoke):
                    raise ElementInteractionError(
                        f"UI Automation selection is unavailable for {self}."
                    )
                invoke()
            wait_for_interval(self._config.wait_after_click)
        except LuminaBotError:
            self._capture_on_error("select")
            raise
        except Exception as exc:
            self._capture_on_error("select")
            raise ElementInteractionError(f"Could not select {self}.") from exc
