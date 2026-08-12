"""ComboBox control adapter."""

from __future__ import annotations

from typing import ClassVar, Protocol, cast

from lumina_bot.controls.base_control import BaseControl
from lumina_bot.core.waits import wait_for_interval
from lumina_bot.exceptions import ElementInteractionError, LuminaBotError


class _SelectableControl(Protocol):
    """Subset of pywinauto combo box behavior used by the framework."""

    def select(self, item: str) -> None:
        """Select an item by display name."""

    def selected_text(self) -> str:
        """Return the selected item text."""


class ComboBox(BaseControl):
    """Adapter for UIA ComboBox controls."""

    control_type: ClassVar[str] = "ComboBox"

    def select(self, item: str, timeout: float | None = None) -> None:
        """Select an item by its visible value."""
        self._logger.info("Selecting '%s' on %s...", item, self.locator.description)

        try:
            self.wait_ready(timeout=timeout)
            cast(_SelectableControl, self._wrapper()).select(item)
            wait_for_interval(self._config.wait_after_click)
        except LuminaBotError:
            self._capture_on_error("select")
            raise
        except Exception as exc:
            self._capture_on_error("select")
            raise ElementInteractionError(
                f"Could not select '{item}' on {self}."
            ) from exc

    def selected_value(self, timeout: float | None = None) -> str:
        """Return the selected combo box value."""
        try:
            self.wait_exists(timeout=timeout)
            return cast(_SelectableControl, self._wrapper()).selected_text()
        except LuminaBotError:
            raise
        except Exception as exc:
            raise ElementInteractionError(
                f"Could not read selected value from {self}."
            ) from exc
