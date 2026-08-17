"""TextBox control adapter."""

from __future__ import annotations

from typing import ClassVar, Protocol, cast

from lumina_bot.controls.base_control import BaseControl
from lumina_bot.core.waits import wait_for_interval
from lumina_bot.exceptions import ElementInteractionError, LuminaBotError


class _EditableControl(Protocol):
    """Subset of pywinauto edit wrapper behavior used by the framework."""

    def set_edit_text(self, text: str) -> None:
        """Set the edit control value."""

    def get_value(self) -> str:
        """Return the edit control value."""


class TextBox(BaseControl):
    """Adapter for UIA Edit controls."""

    control_type: ClassVar[str] = "Edit"

    def set(
        self,
        value: str,
        *,
        timeout: float | None = None,
        sensitive: bool = False,
    ) -> None:
        """Set the text box value."""
        log_value = "<hidden>" if sensitive else value
        self._logger.info("Typing into %s: %s", self.locator.description, log_value)

        try:
            self.wait_ready(timeout=timeout)
            wrapper = self._wrapper()
            wrapper.set_focus()
            setter = getattr(wrapper, "set_edit_text", None)
            if callable(setter):
                setter(value)
            else:
                wrapper.click_input()
                wrapper.type_keys("^a")
                wrapper.type_keys(value, with_spaces=True)
            wait_for_interval(self._config.wait_after_set_text)
        except LuminaBotError:
            self._capture_on_error("set_text")
            raise
        except Exception as exc:
            self._capture_on_error("set_text")
            raise ElementInteractionError(f"Could not set text on {self}.") from exc

    def clear(self, timeout: float | None = None) -> None:
        """Clear the text box value."""
        self.set("", timeout=timeout)

    def value(self, timeout: float | None = None) -> str:
        """Return the current text box value."""
        try:
            self.wait_exists(timeout=timeout)
            return cast(_EditableControl, self._wrapper()).get_value()
        except LuminaBotError:
            raise
        except Exception as exc:
            raise ElementInteractionError(f"Could not read text from {self}.") from exc
