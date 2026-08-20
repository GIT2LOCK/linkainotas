"""Parser strategy manager."""

from __future__ import annotations

from pathlib import Path

from lumina_bot.core.storage import StorageService
from lumina_bot.core.document_detector import (
    DocumentDetection,
    DocumentDetector,
    DocumentType,
)
from lumina_bot.core.logger import get_logger
from lumina_bot.core.pdf_reader import PdfReadResult
from lumina_bot.models.nota import NotaFiscal
from lumina_bot.parsers import (
    BaseParser,
    BoletoParser,
    CteParser,
    DesconhecidoParser,
    MdfeParser,
    NfceParser,
    NfeParser,
    NfeDanfe55Parser,
    NfseParser,
    NfseCotiaParser,
    NfseSpParser,
    ParseContext,
)


class ParserManager:
    """Selects the right parser strategy for each detected document type."""

    def __init__(self, detector: DocumentDetector | None = None) -> None:
        self._detector = detector or DocumentDetector()
        self._logger = get_logger(self.__class__.__name__)
        self._parsers: dict[DocumentType, BaseParser] = {
            DocumentType.NFE_DANFE_55: NfeDanfe55Parser(),
            DocumentType.NFSE_SP: NfseSpParser(),
            DocumentType.NFSE_COTIA_1P: NfseCotiaParser(),
            DocumentType.NFE: NfeParser(),
            DocumentType.NFSE: NfseParser(),
            DocumentType.NFCE: NfceParser(),
            DocumentType.CTE: CteParser(),
            DocumentType.MDFE: MdfeParser(),
            DocumentType.BOLETO: BoletoParser(),
            DocumentType.DESCONHECIDO: DesconhecidoParser(),
        }

    def parse(
        self,
        pdf: PdfReadResult,
        *,
        remote_path: str | None = None,
        xml_text: str | None = None,
        xml_local_path: Path | None = None,
    ) -> NotaFiscal:
        """Detect and parse a PDF/XML result into a NotaFiscal object."""
        detection = self.detect(pdf, xml_text=xml_text)
        parser = self._parsers.get(
            detection.document_type,
            self._parsers[DocumentType.DESCONHECIDO],
        )
        self._logger.info(
            "Parser selected: %s | type=%s | confidence=%s",
            parser.parser_name,
            detection.document_type.value,
            detection.confidence,
        )
        context = ParseContext(
            text=pdf.text,
            file_name=pdf.path.name,
            detection=detection,
            pdf=pdf,
            remote_path=remote_path,
            local_path=str(pdf.path),
            xml_text=xml_text,
            xml_local_path=str(xml_local_path) if xml_local_path else None,
        )
        return parser.parse(context)

    def parse_xml(
        self,
        xml_path: Path,
        *,
        remote_path: str | None = None,
    ) -> NotaFiscal:
        """Parse an XML document directly when no PDF is available."""
        xml_text = xml_path.read_text(encoding="utf-8", errors="ignore")
        stat = xml_path.stat()
        pseudo_pdf = PdfReadResult(
            path=xml_path,
            text="",
            page_count=0,
            author=None,
            creator=None,
            producer=None,
            size_bytes=stat.st_size,
            sha256=StorageService.sha256_file(xml_path),
            metadata={"source_format": "xml"},
            ocr_required=False,
        )
        return self.parse(
            pseudo_pdf,
            remote_path=remote_path,
            xml_text=xml_text,
            xml_local_path=xml_path,
        )

    def detect(
        self,
        pdf: PdfReadResult,
        *,
        xml_text: str | None = None,
    ) -> DocumentDetection:
        """Detect document type from XML first and PDF text as fallback."""
        signal_text = f"{xml_text or ''}\n{pdf.text}"
        return self._detector.detect(signal_text, pdf.path.name)
