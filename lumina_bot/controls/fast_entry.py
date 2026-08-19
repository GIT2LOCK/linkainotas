"""Fast-entry field control exposed as a DevExpress menu item."""

from __future__ import annotations

from typing import ClassVar

from pywinauto import Desktop

from lumina_bot.config import AppConfig, DEFAULT_CONFIG
from lumina_bot.controls.base_control import BaseControl
from lumina_bot.core.waits import wait_for_interval
from lumina_bot.exceptions import ElementInteractionError, LuminaBotError


class FastEntry(BaseControl):
    """Adapter for Lumina's ``mnuProgramFastEntry`` command field."""

    control_type: ClassVar[str] = "MenuItem"
    menu_bar_auto_id: ClassVar[str] = "1312078"

    def __init__(self, window, config: AppConfig = DEFAULT_CONFIG) -> None:
        super().__init__(
            window,
            "mnuProgramFastEntry",
            config=config,
        )

    def _resolve_wrapper(self):
        """Find the fast-entry item inside Lumina's nested Main menu bar."""
        wrapper = super()._resolve_wrapper()
        if wrapper is not None:
            return wrapper

        menu_bar_criteria = (
            {"auto_id": self.menu_bar_auto_id, "control_type": "MenuBar"},
            {"title": "Main menu", "control_type": "MenuBar"},
            {"auto_id": self.menu_bar_auto_id},
        )

        for criteria in menu_bar_criteria:
            try:
                menu_bar = self._window.child_window(**criteria).wrapper_object()
                wrapper = self._find_fast_entry(menu_bar)
                if wrapper is not None:
                    self._logger.debug(
                        "Resolved %s inside Main menu.",
                        self.locator.description,
                    )
                    return wrapper
            except Exception:
                continue

        # The menu bar is a nested WinForms window in some Lumina builds and
        # is exposed directly by Desktop instead of the main-window tree.
        try:
            desktop = Desktop(backend=self._config.backend)
            for window in desktop.windows(visible_only=True):
                info = getattr(window, "element_info", None)
                if (
                    str(getattr(info, "automation_id", "") or "")
                    != self.menu_bar_auto_id
                    and str(getattr(info, "name", "") or "") != "Main menu"
                ):
                    continue

                wrapper = self._find_fast_entry(window)
                if wrapper is not None:
                    return wrapper
        except Exception:
            pass

        return None

    def _find_fast_entry(self, menu_bar):
        """Return the exact fast-entry descendant from a menu-bar wrapper."""
        for candidate in menu_bar.descendants():
            info = getattr(candidate, "element_info", None)
            automation_id = str(getattr(info, "automation_id", "") or "")
            name = str(getattr(info, "name", "") or "")
            if automation_id == self.auto_id or name == self.auto_id:
                return candidate
        return None

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
