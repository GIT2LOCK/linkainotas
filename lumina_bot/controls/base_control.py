"""Base adapter that encapsulates pywinauto control access."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Self

from pywinauto.application import WindowSpecification

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
    """Stable UI Automation locator based on id/name and ControlType."""

    control_type: str
    auto_id: str = ""
    name: str = ""
    fallback_names: tuple[str, ...] = ()

    def as_kwargs(self) -> dict[str, str]:
        """Return pywinauto child_window criteria."""
        criteria = {"control_type": self.control_type}
        if self.auto_id:
            criteria["auto_id"] = self.auto_id
        if self.name:
            criteria["title"] = self.name
        return criteria

    def fallback_kwargs(self) -> tuple[dict[str, str], ...]:
        """Return progressively broader criteria for vendor-specific controls."""
        criteria: list[dict[str, str]] = [self.as_kwargs()]
        if self.auto_id:
            criteria.append({"auto_id": self.auto_id})
        if self.name:
            criteria.append({"title": self.name})
        criteria.extend({"title": name} for name in self.fallback_names)
        return tuple(criteria)

    @property
    def description(self) -> str:
        """Return a log-friendly locator description."""
        identifier = self.auto_id or self.name or "unnamed"
        return f"{identifier} ({self.control_type})"


class BaseControl:
    """Common behavior for all Lumina control adapters."""

    control_type: ClassVar[str]

    def __init__(
        self,
        window: WindowSpecification,
        auto_id: str,
        config: AppConfig = DEFAULT_CONFIG,
        *,
        name: str = "",
        fallback_names: tuple[str, ...] = (),
    ) -> None:
        self._window = window
        self._config = config
        self.locator = ControlLocator(
            auto_id=auto_id,
            control_type=self.control_type,
            name=name,
            fallback_names=fallback_names,
        )
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
            lambda: self._resolve_wrapper() is not None,
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

    def wrapper(self, timeout: float | None = None) -> Any:
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
        primary = self._window.child_window(**self.locator.as_kwargs())
        try:
            if primary.exists(timeout=0):
                return primary
        except Exception:
            pass

        for criteria in self.locator.fallback_kwargs():
            try:
                candidate = self._window.child_window(**criteria)
                if candidate.exists(timeout=0):
                    self._logger.debug(
                        "Using fallback locator for %s: %s",
                        self.locator.description,
                        criteria,
                    )
                    return candidate
            except Exception:
                continue

        return primary

    def _wrapper(self) -> Any:
        wrapper = self._resolve_wrapper()
        if wrapper is None:
            return self._spec().wrapper_object()
        return wrapper

    def _resolve_wrapper(self) -> Any | None:
        """Resolve the actual descendant wrapper by AutomationId."""
        try:
            root = self._window.wrapper_object()
            descendants = root.descendants()
        except Exception as exc:
            self._logger.debug(
                "Could not enumerate descendants for %s: %s",
                self.locator.description,
                exc,
            )
            return None

        matches: list[Any] = []
        for candidate in descendants:
            info = getattr(candidate, "element_info", None)
            candidate_id = str(getattr(info, "automation_id", "") or "")
            candidate_name = str(getattr(info, "name", "") or "")
            try:
                candidate_title = str(candidate.window_text() or "")
            except Exception:
                candidate_title = ""

            id_matches = not self.locator.auto_id or candidate_id == self.locator.auto_id
            name_matches = (
                not self.locator.name
                or candidate_name == self.locator.name
                or candidate_title == self.locator.name
            )
            if id_matches and name_matches:
                matches.append(candidate)

        if not matches:
            return None

        for candidate in matches:
            info = getattr(candidate, "element_info", None)
            candidate_type = str(getattr(info, "control_type", "") or "")
            if candidate_type == self.locator.control_type:
                return candidate

        self._logger.debug(
            "Resolved %s by AutomationId with vendor-specific control type.",
            self.locator.description,
        )
        return matches[0]

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
