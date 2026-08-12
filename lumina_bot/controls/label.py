"""Label control adapter."""

from __future__ import annotations

from typing import ClassVar

from lumina_bot.controls.base_control import BaseControl
from lumina_bot.exceptions import ElementInteractionError, LuminaBotError


class Label(BaseControl):
    """Adapter for UIA Text controls."""

    control_type: ClassVar[str] = "Text"

    def value(self, timeout: float | None = None) -> str:
        """Return the label UIA name without using text-based location."""
        try:
            self.wait_exists(timeout=timeout)
            return str(self._wrapper().element_info.name)
        except LuminaBotError:
            raise
        except Exception as exc:
            raise ElementInteractionError(f"Could not read label {self}.") from exc
