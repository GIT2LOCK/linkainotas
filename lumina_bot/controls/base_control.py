"""Base adapter that encapsulates pywinauto control access."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Self

from pywinauto.application import WindowSpecification
from pywinauto.controls.uiawrapper import UIAWrapper

from lumina_bot.config import AppConfig, DEFAULT_CONFIG
from lumina_bot.core.logger import get_logger
from lumina_bot.core.waits import (
    wait_enabled,
    wait_exists,
    wait_for_interval,
    wait_ready,
    wait_visible,
)
from lumina_bot.exceptions import ElementInteractionError, LuminaBotError
from lumina_bot.utils.screenshots import ScreenshotManager


@dataclass(frozen=True, slots=True)
class ControlLocator:
    """Stable UI Automation locator based on AutomationId and ControlType."""

    auto_id: str
    control_type: str

    def as_kwargs(self) -> dict[str, str]:
        """Return pywinauto child_window criteria."""
        return {
            "auto_id": self.auto_id,
            "control_type": self.control_type,
        }

    @property
    def description(self) -> str:
        """Return a log-friendly locator description."""
        return f"{self.auto_id} ({self.control_type})"


class BaseControl:
    """Common behavior for all Lumina control adapters."""

    control_type: ClassVar[str]

    def __init__(
        self,
        window: WindowSpecification,
        auto_id: str,
        config: AppConfig = DEFAULT_CONFIG,
    ) -> None:
        self._window = window
        self._config = config
        self.locator = ControlLocator(auto_id=auto_id, control_type=self.control_type)
        self._logger = get_logger(f"controls.{self.__class__.__name__}")

    @property
    def auto_id(self) -> str:
        """Return the control AutomationId."""
        return self.locator.auto_id

    def exists(self, timeout: float | None = None) -> bool:
        """Return True when the control exists within the timeout."""
        try:
            self.wait_exists(timeout=timeout)
            return True
        except LuminaBotError:
            self._logger.debug("Control not found: %s", self)
            return False

    def wait_exists(self, timeout: float | None = None) -> Self:
        """Wait until the control exists."""
        self._logger.info("Waiting %s...", self.locator.description)
        wait_exists(
            lambda: self._spec().exists(timeout=0),
            timeout=self._timeout(timeout),
            retry_interval=self._config.retry_interval,
            control_name=self.locator.description,
        )
        return self

    def wait_visible(self, timeout: float | None = None) -> Self:
        """Wait until the control is visible."""
        self._logger.info("Waiting %s to become visible...", self.locator.description)
        wait_visible(
            lambda: bool(self._wrapper().is_visible()),
            timeout=self._timeout(timeout),
            retry_interval=self._config.retry_interval,
            control_name=self.locator.description,
        )
        return self

    def wait_enabled(self, timeout: float | None = None) -> Self:
        """Wait until the control is enabled."""
        self._logger.info("Waiting %s to become enabled...", self.locator.description)
        wait_enabled(
            lambda: bool(self._wrapper().is_enabled()),
            timeout=self._timeout(timeout),
            retry_interval=self._config.retry_interval,
            control_name=self.locator.description,
        )
        return self

    def wait_ready(self, timeout: float | None = None) -> Self:
        """Wait until the control exists, is visible, and is enabled."""
        self._logger.info("Waiting %s to become ready...", self.locator.description)
        wait_ready(
            lambda: self._is_ready(),
            timeout=self._timeout(timeout),
            retry_interval=self._config.retry_interval,
            control_name=self.locator.description,
        )
        return self

    def wrapper(self, timeout: float | None = None) -> UIAWrapper:
        """Return the pywinauto wrapper after ensuring the control exists."""
        self.wait_exists(timeout=timeout)
        return self._wrapper()

    def click(self, timeout: float | None = None) -> None:
        """Click the control after it is ready."""
        self._logger.info("Clicking %s...", self.locator.description)

        try:
            self.wait_ready(timeout=timeout)
            self._wrapper().click_input()
            wait_for_interval(self._config.wait_after_click)
        except LuminaBotError:
            self._capture_on_error("click")
            raise
        except Exception as exc:
            self._capture_on_error("click")
            raise ElementInteractionError(f"Could not click {self}.") from exc

    def set_focus(self, timeout: float | None = None) -> None:
        """Move focus to the control."""
        try:
            self.wait_ready(timeout=timeout)
            self._wrapper().set_focus()
        except LuminaBotError:
            self._capture_on_error("focus")
            raise
        except Exception as exc:
            self._capture_on_error("focus")
            raise ElementInteractionError(f"Could not focus {self}.") from exc

    def _spec(self) -> WindowSpecification:
        return self._window.child_window(**self.locator.as_kwargs())

    def _wrapper(self) -> UIAWrapper:
        return self._spec().wrapper_object()

    def _is_ready(self) -> bool:
        wrapper = self._wrapper()
        return bool(wrapper.is_visible() and wrapper.is_enabled())

    def _timeout(self, timeout: float | None) -> float:
        return self._config.implicit_timeout if timeout is None else timeout

    def _capture_on_error(self, action: str) -> None:
        if not self._config.screenshot_on_error:
            return

        ScreenshotManager(self._config.screenshots_dir).capture_window(
            self._window,
            f"{self.auto_id}_{action}",
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(auto_id={self.auto_id!r}, control_type={self.control_type!r})"
        )

    def __str__(self) -> str:
        return self.__repr__()
