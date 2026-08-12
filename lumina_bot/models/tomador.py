"""Recipient/customer model."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from lumina_bot.models.endereco import Endereco


@dataclass(slots=True)
class Tomador:
    """Recipient, customer, or payer data from a fiscal document."""

    cnpj: str | None = None
    cpf: str | None = None
    inscricao_municipal: str | None = None
    inscricao_estadual: str | None = None
    razao_social: str | None = None
    nome_fantasia: str | None = None
    telefone: str | None = None
    email: str | None = None
    endereco: Endereco = field(default_factory=Endereco)

    def to_dict(self) -> dict[str, Any]:
        """Return the recipient as a serializable dictionary."""
        return asdict(self)
