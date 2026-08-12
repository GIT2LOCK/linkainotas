"""Processing pipeline for fiscal documents stored in Supabase."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from tqdm import tqdm

from lumina_bot.config import PROJECT_ROOT, SupabaseConfig, get_supabase_config
from lumina_bot.core.excel_writer import ExcelWriter
from lumina_bot.core.logger import get_logger
from lumina_bot.core.ocr import OcrService
from lumina_bot.core.parser_manager import ParserManager
from lumina_bot.core.pdf_reader import PdfReader
from lumina_bot.core.storage import LocalDocument, RemoteStorageFile, StorageService
from lumina_bot.models.nota import NotaFiscal


@dataclass(slots=True)
class ProcessingRecord:
    """Persistent processing status for a remote document."""

    remote_path: str
    sha256: str | None
    processed_at: str | None
    status: str
    attempts: int = 0
    last_error: str | None = None


@dataclass(slots=True)
class ProcessingSummary:
    """Batch processing counters."""

    listed: int = 0
    processed: int = 0
    ignored: int = 0
    failed: int = 0
    duplicated: int = 0


class ProcessingRegistry:
    """JSON registry that prevents reprocessing already handled documents."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._records = self._load()

    def is_processed(self, remote_path: str, sha256: str) -> bool:
        """Return True when the same document hash was already processed."""
        record = self._records.get(remote_path)
        return bool(
            record
            and record.get("status") == "success"
            and record.get("sha256") == sha256
        )

    def mark_success(self, remote_path: str, sha256: str) -> None:
        """Persist successful processing status."""
        previous = self._records.get(remote_path, {})
        attempts = int(previous.get("attempts", 0)) + 1
        self._records[remote_path] = asdict(
            ProcessingRecord(
                remote_path=remote_path,
                sha256=sha256,
                processed_at=datetime.now().isoformat(timespec="seconds"),
                status="success",
                attempts=attempts,
                last_error=None,
            )
        )
        self.save()

    def mark_error(self, remote_path: str, error: str, sha256: str | None = None) -> None:
        """Persist failed processing status."""
        previous = self._records.get(remote_path, {})
        attempts = int(previous.get("attempts", 0)) + 1
        self._records[remote_path] = asdict(
            ProcessingRecord(
                remote_path=remote_path,
                sha256=sha256,
                processed_at=datetime.now().isoformat(timespec="seconds"),
                status="error",
                attempts=attempts,
                last_error=error,
            )
        )
        self.save()

    def save(self) -> None:
        """Persist registry to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._path.with_suffix(".tmp")
        temp_path.write_text(
            json.dumps(self._records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(self._path)

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self._path.is_file():
            return {}

        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}


class Processor:
    """Coordinates Supabase download, PDF reading, parsing, and Excel output."""

    def __init__(
        self,
        config: SupabaseConfig | None = None,
        storage: StorageService | None = None,
        pdf_reader: PdfReader | None = None,
        parser_manager: ParserManager | None = None,
        excel_writer: ExcelWriter | None = None,
        ocr_service: OcrService | None = None,
        batch_size: int = 100,
    ) -> None:
        self._config = config or get_supabase_config()
        self._storage = storage or StorageService(self._config)
        self._pdf_reader = pdf_reader or PdfReader()
        self._parser_manager = parser_manager or ParserManager()
        self._excel_writer = excel_writer or ExcelWriter(self._config.excel_output_path)
        self._ocr_service = ocr_service or OcrService()
        self._batch_size = batch_size
        self._registry = ProcessingRegistry(
            PROJECT_ROOT / "output" / "temp" / "processing_state.json"
        )
        self._logger = get_logger(self.__class__.__name__)

    def run(self) -> ProcessingSummary:
        """Run the complete processing pipeline."""
        return self.processar()

    def processar(self) -> ProcessingSummary:
        """Process every PDF from the configured private bucket."""
        summary = ProcessingSummary()
        documents = self._storage.listar_arquivos()
        pdfs = [document for document in documents if document.is_pdf]
        xml_index = self._storage.indexar_xmls(documents)
        pending_rows: list[tuple[NotaFiscal, LocalDocument]] = []
        summary.listed = len(pdfs)

        for remote_pdf in tqdm(pdfs, desc="Processando PDFs", unit="pdf"):
            start = time.perf_counter()

            try:
                local_pdf = self._storage.baixar_para_disco(remote_pdf)

                if self._registry.is_processed(remote_pdf.path, local_pdf.sha256):
                    summary.duplicated += 1
                    self._logger.info("Document already processed: %s", remote_pdf.path)
                    continue

                nota = self._process_pdf(remote_pdf, local_pdf, xml_index)
                pending_rows.append((nota, local_pdf))

                if len(pending_rows) >= self._batch_size:
                    flushed = self._safe_flush(pending_rows)
                    summary.processed += flushed
                    summary.failed += len(pending_rows) - flushed
                    pending_rows.clear()

                elapsed = time.perf_counter() - start
                self._logger.info(
                    "PDF processed: %s | hash=%s | elapsed=%.2fs",
                    remote_pdf.path,
                    local_pdf.sha256,
                    elapsed,
                )
            except Exception as exc:
                summary.failed += 1
                self._registry.mark_error(remote_pdf.path, str(exc))
                self._logger.exception("PDF failed and will be skipped: %s", remote_pdf.path)

        if pending_rows:
            flushed = self._safe_flush(pending_rows)
            summary.processed += flushed
            summary.failed += len(pending_rows) - flushed

        summary.ignored = len(documents) - len(pdfs)
        self._logger.info("Processing summary: %s", summary)
        return summary

    def _process_pdf(
        self,
        remote_pdf: RemoteStorageFile,
        local_pdf: LocalDocument,
        xml_index: dict[str, RemoteStorageFile],
    ) -> NotaFiscal:
        xml_document = None

        try:
            xml_document = self._storage.baixar_xml_correspondente(remote_pdf, xml_index)
        except Exception:
            self._logger.exception(
                "Matching XML failed and PDF text will be used: %s",
                remote_pdf.path,
            )

        xml_text = self._read_xml(xml_document.local_path) if xml_document else None
        pdf = self._pdf_reader.read(local_pdf.local_path)

        if pdf.ocr_required:
            self._ocr_service.extract_text(local_pdf.local_path)
            self._logger.info("PDF marked for future OCR: %s", local_pdf.local_path)

        nota = self._parser_manager.parse(
            pdf,
            remote_path=remote_pdf.path,
            xml_text=xml_text,
            xml_local_path=xml_document.local_path if xml_document else None,
        )
        nota.status_processamento = "success"
        return nota

    def _safe_flush(self, rows: list[tuple[NotaFiscal, LocalDocument]]) -> int:
        try:
            self._flush(rows)
            return len(rows)
        except Exception as exc:
            for nota, local_document in rows:
                if nota.caminho_remoto:
                    self._registry.mark_error(
                        nota.caminho_remoto,
                        str(exc),
                        local_document.sha256,
                    )

            self._logger.exception("Excel flush failed; batch was skipped.")
            return 0

    def _flush(self, rows: list[tuple[NotaFiscal, LocalDocument]]) -> None:
        notas = [nota for nota, _ in rows]
        self._excel_writer.append(notas)

        for nota, local_document in rows:
            if nota.caminho_remoto:
                self._registry.mark_success(
                    nota.caminho_remoto,
                    local_document.sha256,
                )

    @staticmethod
    def _read_xml(path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")
