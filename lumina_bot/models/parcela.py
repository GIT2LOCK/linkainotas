"""Installment data extracted from fiscal documents."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class Parcela:
    """Payment installment from a DANFE or other fiscal document."""

    numero: str | None = None
    vencimento: str | None = None
    valor: float | None = None
    raw: str | None = None
    pagina: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
