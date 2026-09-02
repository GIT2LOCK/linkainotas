"""Processing pipeline for fiscal documents stored in Supabase."""

from __future__ import annotations

from dataclasses import replace
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from tqdm import tqdm

from lumina_bot.config import PROJECT_ROOT, SupabaseConfig, get_supabase_config
from lumina_bot.core.excel_writer import ExcelWriter
from lumina_bot.core.logger import get_logger
from lumina_bot.core.ocr import OcrService
from lumina_bot.core.parser_manager import ParserManager
from lumina_bot.core.pdf_reader import PdfReader
from lumina_bot.core.storage import LocalDocument, RemoteStorageFile, StorageService
from lumina_bot.models.nota import NotaFiscal
from lumina_bot.core.xml_writer import XmlWriter


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
    """JSON registry that records processing attempts and outcomes."""

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
    """Coordinates Supabase download, PDF reading, XML output, and Excel export."""

    def __init__(
        self,
        config: SupabaseConfig | None = None,
        storage: StorageService | None = None,
        pdf_reader: PdfReader | None = None,
        parser_manager: ParserManager | None = None,
        excel_writer: ExcelWriter | None = None,
        xml_writer: XmlWriter | None = None,
        ocr_service: OcrService | None = None,
        progress_callback: Callable[[int, int, str | None, str, float], None] | None = None,
        batch_size: int = 100,
    ) -> None:
        self._config = config or get_supabase_config()
        self._storage = storage or StorageService(self._config)
        self._pdf_reader = pdf_reader or PdfReader()
        self._parser_manager = parser_manager or ParserManager()
        self._excel_writer = excel_writer or ExcelWriter(self._config.excel_output_path)
        self._xml_writer = xml_writer or XmlWriter()
        self._ocr_service = ocr_service or OcrService()
        self._progress_callback = progress_callback
        self._batch_size = batch_size
        self._xml_output_dir = PROJECT_ROOT / "output" / "xml"
        self._generated_xml_paths: list[Path] = []
        self._registry = ProcessingRegistry(
            PROJECT_ROOT / "output" / "temp" / "processing_state.json"
        )
        self._logger = get_logger(self.__class__.__name__)

    def run(
        self,
        *,
        generate_excel: bool = False,
        excel_mode: str = "single_sheet",
        ignore_duplicates: bool = False,
    ) -> ProcessingSummary:
        """Run the complete processing pipeline with optional Excel export."""
        return self.processar(
            generate_excel=generate_excel,
            excel_mode=excel_mode,
            ignore_duplicates=ignore_duplicates,
        )

    def processar(
        self,
        *,
        generate_excel: bool = False,
        excel_mode: str = "single_sheet",
        ignore_duplicates: bool = False,
    ) -> ProcessingSummary:
        """Process every PDF and always generate its normalized XML.

        Reprocessing is the default because each explicit run is a new user
        request. Duplicate protection remains available as an opt-in setting.
        """
        summary = ProcessingSummary()
        self._generated_xml_paths = []
        documents = self._storage.listar_arquivos()
        pdfs = [document for document in documents if document.is_pdf]
        xml_index = self._storage.indexar_xmls(documents)
        pending_rows: list[tuple[NotaFiscal, LocalDocument]] = []
        summary.listed = len(pdfs)
        completed_documents = 0
        self._report_progress(
            completed=completed_documents,
            total=len(pdfs),
            current_file=None,
            phase="Documentos localizados",
            stage_progress=0.0,
        )

        for remote_pdf in tqdm(pdfs, desc="Processando PDFs", unit="pdf"):
            start = time.perf_counter()
            self._report_progress(
                completed=completed_documents,
                total=len(pdfs),
                current_file=remote_pdf.name,
                phase="Baixando e lendo PDF",
                stage_progress=0.05,
            )

            try:
                local_pdf = self._storage.baixar_para_disco(remote_pdf)

                if ignore_duplicates and self._registry.is_processed(
                    remote_pdf.path,
                    local_pdf.sha256,
                ):
                    summary.duplicated += 1
                    self._logger.info("Document already processed: %s", remote_pdf.path)
                    continue

                nota = self._process_pdf(
                    remote_pdf,
                    local_pdf,
                    xml_index,
                    progress_callback=lambda phase, stage_progress: self._report_progress(
                        completed=completed_documents,
                        total=len(pdfs),
                        current_file=remote_pdf.name,
                        phase=phase,
                        stage_progress=stage_progress,
                    ),
                )
                self._report_progress(
                    completed=completed_documents,
                    total=len(pdfs),
                    current_file=remote_pdf.name,
                    phase="Gerando XML normalizado",
                    stage_progress=0.7,
                )
                xml_path = self._xml_writer.write(
                    nota,
                    self._xml_output_dir,
                    source_format="pdf",
                )
                nota.caminho_xml_local = str(xml_path)
                self._generated_xml_paths.append(xml_path)
                pending_rows.append((nota, local_pdf))
                self._report_progress(
                    completed=completed_documents,
                    total=len(pdfs),
                    current_file=remote_pdf.name,
                    phase="Preparando saída",
                    stage_progress=0.85,
                )

                if len(pending_rows) >= self._batch_size:
                    flushed = self._safe_flush(
                        pending_rows,
                        generate_excel=generate_excel,
                        excel_mode=excel_mode,
                    )
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
            finally:
                completed_documents += 1
                self._report_progress(
                    completed=completed_documents,
                    total=len(pdfs),
                    current_file=remote_pdf.name,
                    phase="Documento concluído",
                    stage_progress=0.0,
                )

        if pending_rows:
            flushed = self._safe_flush(
                pending_rows,
                generate_excel=generate_excel,
                excel_mode=excel_mode,
            )
            summary.processed += flushed
            summary.failed += len(pending_rows) - flushed

        summary.ignored = len(documents) - len(pdfs)
        self._logger.info("Processing summary: %s", summary)
        return summary

    def _report_progress(
        self,
        *,
        completed: int,
        total: int,
        current_file: str | None,
        phase: str,
        stage_progress: float,
    ) -> None:
        if self._progress_callback is None:
            return

        try:
            self._progress_callback(
                completed,
                total,
                current_file,
                phase,
                stage_progress,
            )
        except Exception:
            self._logger.exception("Could not persist processing progress.")

    def generated_xml_paths(self) -> list[Path]:
        """Return XML files generated by the most recent processing run."""
        return list(self._generated_xml_paths)

    def _process_pdf(
        self,
        remote_pdf: RemoteStorageFile,
        local_pdf: LocalDocument,
        xml_index: dict[str, RemoteStorageFile],
        progress_callback: Callable[[str, float], None] | None = None,
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
        if progress_callback is not None:
            progress_callback("Documento baixado e XML associado", 0.15)

        pdf = self._pdf_reader.read(local_pdf.local_path)
        if progress_callback is not None:
            progress_callback("Texto do PDF extraído", 0.3)

        if pdf.ocr_required:
            ocr_result = self._ocr_service.extract_text(
                local_pdf.local_path,
                progress_callback=(
                    lambda page, total: progress_callback(
                        f"OCR página {page} de {total}",
                        0.3 + 0.28 * (page / max(total, 1)),
                    )
                    if progress_callback is not None
                    else None
                ),
            )
            if ocr_result.text.strip():
                pdf = replace(
                    pdf,
                    text=ocr_result.text,
                    pages=ocr_result.pages or (ocr_result.text,),
                    words=ocr_result.words,
                    ocr_required=False,
                    ocr_used=True,
                    ocr_confidence=ocr_result.confidence,
                )
                self._logger.info(
                    "OCR completed: %s | engine=%s | confidence=%s",
                    local_pdf.local_path,
                    ocr_result.engine,
                    ocr_result.confidence,
                )
            else:
                self._logger.warning("OCR produced no usable text: %s", local_pdf.local_path)

        if progress_callback is not None:
            progress_callback("Dados fiscais interpretados", 0.65)

        nota = self._parser_manager.parse(
            pdf,
            remote_path=remote_pdf.path,
            xml_text=xml_text,
            xml_local_path=xml_document.local_path if xml_document else None,
        )
        nota.status_processamento = "success"
        return nota

    def _safe_flush(
        self,
        rows: list[tuple[NotaFiscal, LocalDocument]],
        *,
        generate_excel: bool,
        excel_mode: str,
    ) -> int:
        try:
            self._flush(
                rows,
                generate_excel=generate_excel,
                excel_mode=excel_mode,
            )
            return len(rows)
        except Exception as exc:
            for nota, local_document in rows:
                if nota.caminho_remoto:
                    self._registry.mark_error(
                        nota.caminho_remoto,
                        str(exc),
                        local_document.sha256,
                    )

            self._logger.exception("Document output flush failed; batch was skipped.")
            return 0

    def _flush(
        self,
        rows: list[tuple[NotaFiscal, LocalDocument]],
        *,
        generate_excel: bool,
        excel_mode: str,
    ) -> None:
        notas = [nota for nota, _ in rows]

        if generate_excel:
            self._excel_writer.write(notas, mode=excel_mode)

        for nota, local_document in rows:
            if nota.caminho_remoto:
                self._registry.mark_success(
                    nota.caminho_remoto,
                    local_document.sha256,
                )

    @staticmethod
    def _read_xml(path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")
