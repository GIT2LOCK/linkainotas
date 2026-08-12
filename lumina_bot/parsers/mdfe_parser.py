"""MDF-e parser strategy."""

from __future__ import annotations

from lumina_bot.core.document_detector import DocumentType
from lumina_bot.models.nota import NotaFiscal
from lumina_bot.parsers.base_parser import BaseParser, ParseContext


class MdfeParser(BaseParser):
    """Parser for Manifesto Eletronico de Documentos Fiscais."""

    document_type = DocumentType.MDFE
    parser_name = "mdfe_parser"

    def _parse_specific(self, nota: NotaFiscal, context: ParseContext) -> None:
        nota.modelo = nota.modelo or "58"
        nota.outros_campos["fonte_prioritaria"] = (
            "xml" if context.xml_text else "pdf_text"
        )
