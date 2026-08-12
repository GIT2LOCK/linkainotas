"""Centralized wait helpers for UI Automation controls."""

from __future__ import annotations

import time
from collections.abc import Callable

from lumina_bot.exceptions import TimeoutWaitingControl


def wait_until(
    condition: Callable[[], bool],
    *,
    timeout: float,
    retry_interval: float,
    description: str,
) -> None:
    """Wait until condition returns True or raise a framework timeout.

    This is the only place where polling sleeps are performed. Other modules
    should call these helpers instead of scattering time.sleep calls.
    """
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None

    while time.monotonic() <= deadline:
        try:
            if condition():
                return
        except Exception as exc:
            last_error = exc

        time.sleep(retry_interval)

    raise TimeoutWaitingControl(
        f"Timed out after {timeout} seconds waiting for {description}."
    ) from last_error


def wait_exists(
    condition: Callable[[], bool],
    *,
    timeout: float,
    retry_interval: float,
    control_name: str,
) -> None:
    """Wait until a control exists."""
    wait_until(
        condition,
        timeout=timeout,
        retry_interval=retry_interval,
        description=f"{control_name} to exist",
    )


def wait_visible(
    condition: Callable[[], bool],
    *,
    timeout: float,
    retry_interval: float,
    control_name: str,
) -> None:
    """Wait until a control is visible."""
    wait_until(
        condition,
        timeout=timeout,
        retry_interval=retry_interval,
        description=f"{control_name} to become visible",
    )


def wait_enabled(
    condition: Callable[[], bool],
    *,
    timeout: float,
    retry_interval: float,
    control_name: str,
) -> None:
    """Wait until a control is enabled."""
    wait_until(
        condition,
        timeout=timeout,
        retry_interval=retry_interval,
        description=f"{control_name} to become enabled",
    )


def wait_ready(
    condition: Callable[[], bool],
    *,
    timeout: float,
    retry_interval: float,
    control_name: str,
) -> None:
    """Wait until a control is visible and enabled."""
    wait_until(
        condition,
        timeout=timeout,
        retry_interval=retry_interval,
        description=f"{control_name} to become ready",
    )


def wait_for_interval(seconds: float) -> None:
    """Wait for a configured post-action interval."""
    if seconds > 0:
        time.sleep(seconds)
