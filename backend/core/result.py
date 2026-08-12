"""Common response helpers for desktop IPC commands."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class CommandResult:
    """Serializable command result returned to the Tauri frontend."""

    ok: bool
    data: dict[str, Any] | list[Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""
        return asdict(self)


def success(data: dict[str, Any] | list[Any] | None = None) -> CommandResult:
    """Create a successful command result."""
    return CommandResult(ok=True, data=data, error=None)


def failure(error: str) -> CommandResult:
    """Create a failed command result."""
    return CommandResult(ok=False, data=None, error=error)
