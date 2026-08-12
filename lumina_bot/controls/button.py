"""Button control adapter."""

from __future__ import annotations

from typing import ClassVar

from lumina_bot.controls.base_control import BaseControl


class Button(BaseControl):
    """Adapter for UIA Button controls."""

    control_type: ClassVar[str] = "Button"
