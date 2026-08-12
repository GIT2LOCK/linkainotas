"""NFS-e parser strategy."""

from __future__ import annotations

from lumina_bot.core.document_detector import DocumentType
from lumina_bot.models.nota import NotaFiscal
from lumina_bot.parsers.base_parser import BaseParser, ParseContext


class NfseParser(BaseParser):
    """Parser for Nota Fiscal de Servicos Eletronica documents."""

    document_type = DocumentType.NFSE
    parser_name = "nfse_parser"

    def _parse_specific(self, nota: NotaFiscal, context: ParseContext) -> None:
        lines = self._lines(context.text)
        nota.modelo = nota.modelo or "NFS-e"
        nota.codigo_servico = nota.codigo_servico or self._value_after_labels(
            lines,
            ("codigo do servico", "item da lista de servico"),
        )
        nota.descricao_servico = nota.descricao_servico or self._value_after_labels(
            lines,
            ("descricao do servico", "servico prestado"),
        )
        nota.discriminacao = nota.discriminacao or self._value_after_labels(
            lines,
            ("discriminacao dos servicos", "discriminacao"),
        )
        nota.outros_campos["fonte_prioritaria"] = (
            "xml" if context.xml_text else "pdf_text"
        )
