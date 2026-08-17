"""Validation results for normalized fiscal documents."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class ValidationResult:
    """Result of a consistency rule applied after extraction."""

    regra: str
    status: str
    valor_extraido: Any = None
    valor_calculado: Any = None
    mensagem: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
