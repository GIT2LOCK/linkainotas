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

    def double_click(self, timeout: float | None = None) -> None:
        """Activate tiles whose native action is exposed as a double click.

        DevExpress tiles can expose ``InvokePattern`` while only responding to
        their legacy default action, which is a double click. ``click_input``
        still targets the element resolved by UI Automation, so this does not
        depend on fixed screen coordinates.
        """
        self._logger.info("Double-clicking %s...", self.locator.description)

        try:
            self.wait_ready(timeout=timeout)
            wrapper = self._wrapper()
            double_click = getattr(wrapper, "double_click_input", None)
            if callable(double_click):
                double_click()
            else:
                wrapper.click_input()
                wait_for_interval(0.12)
                wrapper.click_input()
            wait_for_interval(self._config.wait_after_click)
        except LuminaBotError:
            self._capture_on_error("double_click")
            raise
        except Exception as exc:
            self._capture_on_error("double_click")
            raise ElementInteractionError(f"Could not double-click {self}.") from exc
