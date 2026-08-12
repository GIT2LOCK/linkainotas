"""Boleto parser strategy."""

from __future__ import annotations

from lumina_bot.core.document_detector import DocumentType
from lumina_bot.models.nota import NotaFiscal
from lumina_bot.parsers.base_parser import BaseParser, ParseContext


class BoletoParser(BaseParser):
    """Parser for boleto documents."""

    document_type = DocumentType.BOLETO
    parser_name = "boleto_parser"

    def _parse_specific(self, nota: NotaFiscal, context: ParseContext) -> None:
        lines = self._lines(context.text)
        nota.valor_bruto = nota.valor_bruto or self._parse_decimal(
            self._value_after_labels(lines, ("valor documento", "valor cobrado"))
        )
        nota.outros_campos["linha_digitavel"] = self._value_after_labels(
            lines,
            ("linha digitavel",),
        )
