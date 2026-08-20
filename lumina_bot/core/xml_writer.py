"""XML export for normalized fiscal documents extracted from PDFs."""

from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from lumina_bot.models.nota import NotaFiscal


class XmlWriter:
    """Write a portable LinkAI XML representation of a fiscal document."""

    schema = "linkai.documento-fiscal.v1"

    def write(
        self,
        nota: NotaFiscal,
        output_dir: Path,
        *,
        source_format: str = "pdf",
    ) -> Path:
        """Serialize a normalized document and return the generated path."""
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._unique_path(output_dir, nota.arquivo, nota.sha256)
        root = ET.Element(
            "documentoFiscal",
            {
                "schema": self.schema,
                "tipo": nota.layout or nota.tipo_documento or "UNKNOWN_LAYOUT",
                "sub_layout": nota.sub_layout or "",
                "ocr_used": str(nota.ocr_used).lower(),
                "source_format": source_format,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        self._append_canonical(root, nota)
        self._append_value(root, "documento", nota.to_dict())

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        return output_path

    @classmethod
    def _append_canonical(cls, root: ET.Element, nota: NotaFiscal) -> None:
        """Write stable top-level blocks while retaining the full nested object."""
        cls._append_value(root, "origem", {
            "arquivo": nota.arquivo,
            "hash": nota.sha256,
            "paginas": nota.quantidade_paginas,
            "layout": nota.layout,
            "sub_layout": nota.sub_layout,
            "ocr_used": nota.ocr_used,
        })
        cls._append_value(root, "identificacao", {
            "numero": nota.numero,
            "serie": nota.serie,
            "modelo": nota.modelo,
            "dataEmissao": nota.data_emissao,
            "horaEmissao": nota.hora_emissao,
            "competencia": nota.competencia,
            "chaveAcesso": nota.chave,
            "chaveAcessoRaw": nota.chave_acesso_raw,
            "codigoVerificacao": nota.autorizacao,
            "rpsNumero": nota.rps_numero,
        })
        cls._append_value(root, "emitente", nota.prestador.to_dict())
        cls._append_value(root, "destinatario", nota.tomador.to_dict())
        cls._append_value(root, "totais", {
            "valorBruto": nota.valor_bruto,
            "valorLiquido": nota.valor_liquido,
            "valorTotal": nota.valor_total,
        })
        cls._append_value(root, "tributos", nota.tributos.to_dict())
        cls._append_value(root, "itens", [item.to_dict() for item in nota.itens])
        cls._append_value(root, "parcelas", [parcela.to_dict() for parcela in nota.parcelas])
        cls._append_value(root, "dadosAdicionais", {
            "municipioEmissorNfse": nota.municipio_emissor_nfse,
            "municipioIncidenciaIss": nota.municipio_incidencia_iss,
            "codigoNbs": nota.codigo_nbs,
            "cnae": nota.cnae,
            "codigoObra": nota.codigo_obra,
            "codigoCeiCno": nota.codigo_cei_cno,
            "sfoBras": nota.sfo_bras,
            "valorAproximadoTributosRaw": nota.valor_aproximado_tributos_raw,
            "observacoes": nota.observacoes,
        })
        if nota.layout == "NFSE_COTIA_1P":
            cls._append_value(root, "nfseCotia", nota.outros_campos.get("nfse", {}))
        elif nota.layout == "NFSE_SP":
            cls._append_value(root, "nfse", nota.outros_campos.get("nfse", {}))
        elif nota.layout == "NFE_DANFE_55":
            cls._append_value(root, "nfe", nota.outros_campos.get("nfe", {}))
        cls._append_value(root, "validacao", [validation.to_dict() for validation in nota.validacoes])

    @classmethod
    def _append_value(cls, parent: ET.Element, name: str, value: Any) -> None:
        if value is None:
            return

        element = ET.SubElement(parent, cls._safe_tag(name))

        if isinstance(value, Mapping):
            for key, child_value in value.items():
                cls._append_value(element, str(key), child_value)
            return

        if isinstance(value, (list, tuple)):
            for item in value:
                cls._append_value(element, "item", item)
            return

        element.text = str(value)

    @classmethod
    def _unique_path(
        cls,
        output_dir: Path,
        source_name: str | None,
        source_hash: str | None,
    ) -> Path:
        source_stem = Path(source_name or "documento").stem
        stem = cls._safe_file_name(source_stem) or "documento"
        candidate = output_dir / f"{stem}.xml"

        if not candidate.exists():
            return candidate

        suffix = (source_hash or "documento")[:8]
        candidate = output_dir / f"{stem}_{suffix}.xml"
        counter = 2

        while candidate.exists():
            candidate = output_dir / f"{stem}_{suffix}_{counter}.xml"
            counter += 1

        return candidate

    @staticmethod
    def _safe_file_name(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_value).strip("._-")

    @staticmethod
    def _safe_tag(value: str) -> str:
        tag = XmlWriter._safe_file_name(value).replace(".", "_").replace("-", "_")

        if not tag:
            return "field"

        if not re.match(r"[A-Za-z_]", tag[0]):
            return f"field_{tag}"

        return tag
