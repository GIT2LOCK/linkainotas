"""Fiscal document item model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class Item:
    """Product or service item extracted from a fiscal document."""

    codigo: str | None = None
    descricao: str | None = None
    ncm: str | None = None
    cfop: str | None = None
    unidade: str | None = None
    quantidade: float | None = None
    valor_unitario: float | None = None
    valor_desconto: float | None = None
    valor_total: float | None = None
    cst: str | None = None
    base_calculo_icms: float | None = None
    valor_icms: float | None = None
    valor_ipi: float | None = None
    aliquota_icms: float | None = None
    aliquota_ipi: float | None = None
    valor_total_tributos: float | None = None
    outros_campos: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the item as a serializable dictionary."""
        return asdict(self)
