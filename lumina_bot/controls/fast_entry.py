"""Fast-entry field control exposed as a DevExpress menu item."""

from __future__ import annotations

from typing import ClassVar

from pywinauto import Desktop
from pywinauto.keyboard import send_keys

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
            self._logger.info(
                "%s is ready; waiting %.1f seconds before typing...",
                self.locator.description,
                self._config.action_delay,
            )
            wait_for_interval(self._config.action_delay)
            wrapper = self._wrapper()
            double_click = getattr(wrapper, "double_click_input", None)
            if callable(double_click):
                double_click()
            else:
                wrapper.click_input()
                wait_for_interval(0.12)
                wrapper.click_input()
            # The double click activates an inline editor. Calling
            # set_focus() on the original MenuItem closes that editor, so
            # send keystrokes to the focus that Lumina just established.
            send_keys("^a")
            send_keys(code, pause=0.01, with_spaces=True)
            if press_enter:
                send_keys("{ENTER}")
            wait_for_interval(self._config.wait_after_set_text)
        except LuminaBotError:
            self._capture_on_error("enter_code")
            raise
        except Exception as exc:
            self._capture_on_error("enter_code")
            raise ElementInteractionError(
                f"Could not enter fast-entry code {code!r}."
            ) from exc
