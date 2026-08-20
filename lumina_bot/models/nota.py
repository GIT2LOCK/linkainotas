"""Fiscal document aggregate model."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from lumina_bot.models.emitente import Emitente
from lumina_bot.models.item import Item
from lumina_bot.models.tomador import Tomador
from lumina_bot.models.tributos import Tributos
from lumina_bot.models.parcela import Parcela
from lumina_bot.models.validation import ValidationResult


@dataclass(slots=True)
class NotaFiscal:
    """Normalized representation of a fiscal document."""

    tipo_documento: str | None = None
    layout: str | None = None
    parser: str | None = None
    arquivo: str | None = None
    caminho_remoto: str | None = None
    caminho_local: str | None = None
    caminho_xml_local: str | None = None
    sha256: str | None = None
    tamanho_bytes: int | None = None
    quantidade_paginas: int | None = None
    ocr_required: bool = False
    ocr_used: bool = False
    sub_layout: str | None = None

    numero: str | None = None
    serie: str | None = None
    modelo: str | None = None
    chave: str | None = None
    protocolo: str | None = None
    autorizacao: str | None = None
    data_emissao: str | None = None
    hora_emissao: str | None = None
    competencia: str | None = None
    chave_acesso_raw: str | None = None
    rps_numero: str | None = None
    municipio_emissor_nfse: str | None = None
    municipio_incidencia_iss: str | None = None
    codigo_nbs: str | None = None
    cnae: str | None = None
    codigo_obra: str | None = None
    codigo_cei_cno: str | None = None
    sfo_bras: str | None = None
    valor_aproximado_tributos_raw: str | None = None

    prestador: Emitente = field(default_factory=Emitente)
    tomador: Tomador = field(default_factory=Tomador)
    intermediario: str | None = None

    municipio: str | None = None
    uf: str | None = None
    codigo_municipio: str | None = None
    codigo_servico: str | None = None
    descricao_servico: str | None = None
    discriminacao: str | None = None
    observacoes: str | None = None

    valor_bruto: float | None = None
    valor_liquido: float | None = None
    valor_total: float | None = None
    tributos: Tributos = field(default_factory=Tributos)
    itens: list[Item] = field(default_factory=list)
    parcelas: list[Parcela] = field(default_factory=list)
    validacoes: list[ValidationResult] = field(default_factory=list)

    autor_pdf: str | None = None
    criador_pdf: str | None = None
    producer_pdf: str | None = None
    metadados_pdf: dict[str, Any] = field(default_factory=dict)

    outros_campos: dict[str, Any] = field(default_factory=dict)
    status_processamento: str | None = None
    erro_processamento: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return the full nested representation."""
        return asdict(self)

    def to_flat_dict(self) -> dict[str, Any]:
        """Return a single-row representation for Excel output."""
        row: dict[str, Any] = {
            "tipo_documento": self.tipo_documento,
            "layout": self.layout,
            "parser": self.parser,
            "arquivo": self.arquivo,
            "caminho_remoto": self.caminho_remoto,
            "caminho_local": self.caminho_local,
            "caminho_xml_local": self.caminho_xml_local,
            "sha256": self.sha256,
            "tamanho_bytes": self.tamanho_bytes,
            "quantidade_paginas": self.quantidade_paginas,
            "ocr_required": self.ocr_required,
            "ocr_used": self.ocr_used,
            "sub_layout": self.sub_layout,
            "numero": self.numero,
            "serie": self.serie,
            "modelo": self.modelo,
            "chave": self.chave,
            "protocolo": self.protocolo,
            "autorizacao": self.autorizacao,
            "data_emissao": self.data_emissao,
            "hora_emissao": self.hora_emissao,
            "competencia": self.competencia,
            "chave_acesso_raw": self.chave_acesso_raw,
            "rps_numero": self.rps_numero,
            "municipio_emissor_nfse": self.municipio_emissor_nfse,
            "municipio_incidencia_iss": self.municipio_incidencia_iss,
            "codigo_nbs": self.codigo_nbs,
            "cnae": self.cnae,
            "codigo_obra": self.codigo_obra,
            "codigo_cei_cno": self.codigo_cei_cno,
            "sfo_bras": self.sfo_bras,
            "valor_aproximado_tributos_raw": self.valor_aproximado_tributos_raw,
            "municipio": self.municipio,
            "uf": self.uf,
            "codigo_municipio": self.codigo_municipio,
            "codigo_servico": self.codigo_servico,
            "descricao_servico": self.descricao_servico,
            "discriminacao": self.discriminacao,
            "observacoes": self.observacoes,
            "valor_bruto": self.valor_bruto,
            "valor_liquido": self.valor_liquido,
            "valor_total": self.valor_total,
            "intermediario": self.intermediario,
            "autor_pdf": self.autor_pdf,
            "criador_pdf": self.criador_pdf,
            "producer_pdf": self.producer_pdf,
            "status_processamento": self.status_processamento,
            "erro_processamento": self.erro_processamento,
        }
        row.update(self._prefixed_dict("prestador", self.prestador.to_dict()))
        row.update(self._prefixed_dict("tomador", self.tomador.to_dict()))
        row.update(self._prefixed_dict("tributos", self.tributos.to_dict()))
        row["itens_quantidade"] = len(self.itens)
        row["parcelas_quantidade"] = len(self.parcelas)
        row["validacoes_quantidade"] = len(self.validacoes)
        row["itens_json"] = self._json([item.to_dict() for item in self.itens])
        row["metadados_pdf_json"] = self._json(self.metadados_pdf)
        row["outros_campos_json"] = self._json(self.outros_campos)
        return row

    @classmethod
    def _prefixed_dict(cls, prefix: str, data: dict[str, Any]) -> dict[str, Any]:
        flattened: dict[str, Any] = {}

        for key, value in data.items():
            if isinstance(value, dict):
                flattened.update(cls._prefixed_dict(f"{prefix}_{key}", value))
            else:
                flattened[f"{prefix}_{key}"] = value

        return flattened

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)


Nota = NotaFiscal
