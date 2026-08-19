"""List item control adapter for DevExpress tile menus."""

from __future__ import annotations

from typing import ClassVar

from lumina_bot.controls.base_control import BaseControl
from lumina_bot.config import AppConfig, DEFAULT_CONFIG
from lumina_bot.core.waits import wait_for_interval
from lumina_bot.exceptions import ElementInteractionError, LuminaBotError


class ListItem(BaseControl):
    """Adapter for a UI Automation ListItem identified by its visible name."""

    control_type: ClassVar[str] = "ListItem"

    def __init__(self, window, name: str, config: AppConfig = DEFAULT_CONFIG) -> None:
        super().__init__(window, "", config=config, name=name)

    def invoke(self, timeout: float | None = None) -> None:
        """Invoke the item's default action exposed by UI Automation."""
        self._logger.info("Invoking %s...", self.locator.description)

        try:
            self.wait_ready(timeout=timeout)
            wrapper = self._wrapper()
            invoke = getattr(wrapper, "invoke", None)
            if not callable(invoke):
                raise ElementInteractionError(
                    f"UI Automation InvokePattern is unavailable for {self}."
                )
            invoke()
            wait_for_interval(self._config.wait_after_click)
        except LuminaBotError:
            self._capture_on_error("invoke")
            raise
        except Exception as exc:
            self._capture_on_error("invoke")
            raise ElementInteractionError(f"Could not invoke {self}.") from exc
