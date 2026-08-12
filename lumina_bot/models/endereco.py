"""Address model used by fiscal document parties."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class Endereco:
    """Address data extracted from a fiscal document."""

    logradouro: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    municipio: str | None = None
    uf: str | None = None
    cep: str | None = None
    codigo_municipio: str | None = None
    pais: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the address as a serializable dictionary."""
        return asdict(self)
