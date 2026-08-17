"""Tax model for fiscal documents."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Tributos:
    """Tax and withholding values extracted from a fiscal document."""

    iss: float | None = None
    inss: float | None = None
    pis: float | None = None
    cofins: float | None = None
    csll: float | None = None
    irrf: float | None = None
    retencoes: float | None = None
    descontos: float | None = None
    base_calculo: float | None = None
    aliquota: float | None = None
    valor_aproximado: float | None = None
    icms: float | None = None
    ipi: float | None = None
    pis_cofins: float | None = None
    ibs: float | None = None
    cbs: float | None = None
    outros: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return taxes as a serializable dictionary."""
        return asdict(self)
