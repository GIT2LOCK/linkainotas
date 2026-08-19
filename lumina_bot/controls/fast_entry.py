"""Fast-entry field control exposed as a DevExpress menu item."""

from __future__ import annotations

from typing import ClassVar

from lumina_bot.config import AppConfig, DEFAULT_CONFIG
from lumina_bot.controls.base_control import BaseControl
from lumina_bot.core.waits import wait_for_interval
from lumina_bot.exceptions import ElementInteractionError, LuminaBotError


class FastEntry(BaseControl):
    """Adapter for Lumina's ``mnuProgramFastEntry`` command field."""

    control_type: ClassVar[str] = "MenuItem"

    def __init__(self, window, config: AppConfig = DEFAULT_CONFIG) -> None:
        super().__init__(
            window,
            "mnuProgramFastEntry",
            config=config,
        )

    def enter_code(
        self,
        code: str,
        *,
        press_enter: bool = False,
        timeout: float | None = None,
    ) -> None:
        """Click the field, type a program code, and optionally submit it."""
        self._logger.info("Entering fast-entry code: %s", code)

        try:
            self.wait_ready(timeout=timeout)
            wrapper = self._wrapper()
            wrapper.click_input()
            wrapper.set_focus()
            wrapper.type_keys("^a")
            wrapper.type_keys(code, with_spaces=True)
            if press_enter:
                wrapper.type_keys("{ENTER}")
            wait_for_interval(self._config.wait_after_set_text)
        except LuminaBotError:
            self._capture_on_error("enter_code")
            raise
        except Exception as exc:
            self._capture_on_error("enter_code")
            raise ElementInteractionError(
                f"Could not enter fast-entry code {code!r}."
            ) from exc
