"""CheckBox control adapter."""

from __future__ import annotations

from typing import ClassVar, Protocol, cast

from lumina_bot.controls.base_control import BaseControl
from lumina_bot.core.waits import wait_for_interval
from lumina_bot.exceptions import ElementInteractionError, LuminaBotError


class _ToggleControl(Protocol):
    """Subset of pywinauto check box behavior used by the framework."""

    def get_toggle_state(self) -> int:
        """Return 1 when checked and 0 when unchecked."""

    def toggle(self) -> None:
        """Toggle the check box state."""


class CheckBox(BaseControl):
    """Adapter for UIA CheckBox controls."""

    control_type: ClassVar[str] = "CheckBox"

    def is_checked(self, timeout: float | None = None) -> bool:
        """Return True when the check box is checked."""
        try:
            self.wait_exists(timeout=timeout)
            return bool(cast(_ToggleControl, self._wrapper()).get_toggle_state())
        except LuminaBotError:
            raise
        except Exception as exc:
            raise ElementInteractionError(f"Could not read state from {self}.") from exc

    def set_checked(self, checked: bool, timeout: float | None = None) -> None:
        """Set the check box to the requested state."""
        self._logger.info("Setting %s checked=%s...", self.locator.description, checked)

        try:
            self.wait_ready(timeout=timeout)
            wrapper = cast(_ToggleControl, self._wrapper())

            if bool(wrapper.get_toggle_state()) != checked:
                wrapper.toggle()
                wait_for_interval(self._config.wait_after_click)
        except LuminaBotError:
            self._capture_on_error("set_checked")
            raise
        except Exception as exc:
            self._capture_on_error("set_checked")
            raise ElementInteractionError(f"Could not change state on {self}.") from exc

    def check(self, timeout: float | None = None) -> None:
        """Check the control."""
        self.set_checked(True, timeout=timeout)

    def uncheck(self, timeout: float | None = None) -> None:
        """Uncheck the control."""
        self.set_checked(False, timeout=timeout)
