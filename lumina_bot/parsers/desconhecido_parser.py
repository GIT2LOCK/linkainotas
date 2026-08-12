"""Fallback parser for unknown documents."""

from __future__ import annotations

from lumina_bot.core.document_detector import DocumentType
from lumina_bot.models.nota import NotaFiscal
from lumina_bot.parsers.base_parser import BaseParser, ParseContext


class DesconhecidoParser(BaseParser):
    """Parser used when the document type cannot be identified."""

    document_type = DocumentType.DESCONHECIDO
    parser_name = "desconhecido_parser"

    def _parse_specific(self, nota: NotaFiscal, context: ParseContext) -> None:
        nota.outros_campos["motivo_detector"] = context.detection.reason
        nota.outros_campos["confianca_detector"] = context.detection.confidence
