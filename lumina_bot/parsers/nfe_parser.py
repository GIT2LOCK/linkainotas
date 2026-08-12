"""NF-e parser strategy."""

from __future__ import annotations

from lumina_bot.core.document_detector import DocumentType
from lumina_bot.models.nota import NotaFiscal
from lumina_bot.parsers.base_parser import BaseParser, ParseContext


class NfeParser(BaseParser):
    """Parser for Nota Fiscal Eletronica documents."""

    document_type = DocumentType.NFE
    parser_name = "nfe_parser"

    def _parse_specific(self, nota: NotaFiscal, context: ParseContext) -> None:
        nota.modelo = nota.modelo or "55"
        nota.numero = nota.numero or self._value_after_labels(
            self._lines(context.text),
            ("nf-e", "numero da nota", "danfe"),
        )
        nota.outros_campos["fonte_prioritaria"] = (
            "xml" if context.xml_text else "pdf_text"
        )
