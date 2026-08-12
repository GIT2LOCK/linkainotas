"""JSON serialization helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def dumps(value: Any) -> str:
    """Serialize a Python object to JSON."""
    return json.dumps(value, ensure_ascii=False, default=_default)


def _default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)

    if is_dataclass(value):
        return asdict(value)

    return str(value)
