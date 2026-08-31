"""Document processing service for Supabase, folders, and selected files."""

from __future__ import annotations

import base64
import shutil
import time
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from lumina_bot.config import PROJECT_ROOT, get_supabase_config
from lumina_bot.core.excel_writer import ExcelWriter
from lumina_bot.core.logger import get_logger
from lumina_bot.core.parser_manager import ParserManager
from lumina_bot.core.ocr import OcrService
from lumina_bot.core.pdf_reader import PdfReadResult, PdfReader
from lumina_bot.core.processor import Processor
from lumina_bot.core.storage import StorageService
from lumina_bot.core.xml_writer import XmlWriter
from lumina_bot.models.nota import NotaFiscal

from backend.models.ui import ProcessingOptions
from backend.services.processing_ui_registry import ProcessingUiRegistry
from backend.storage.local_sources import LocalDocumentSource


class DocumentProcessingService:
    """Coordinates document processing use cases requested by the UI."""

    def __init__(self) -> None:
        self._local_source = LocalDocumentSource()
        self._pdf_reader = PdfReader()
        self._ocr_service = OcrService()
        self._parser_manager = ParserManager()
        self._registry = ProcessingUiRegistry()
        self._xml_writer = XmlWriter()
        self._xml_output_dir = PROJECT_ROOT / "output" / "xml"
        self._logger = get_logger(self.__class__.__name__)

    def process(self, options: ProcessingOptions) -> dict[str, Any]:
        """Process documents from the selected source."""
        download_dir = self._resolve_download_dir(options)

        if options.source == "supabase":
            return self._process_supabase(options, download_dir)

        return self._process_local(options, download_dir)

    def last_processing(self) -> dict[str, Any] | None:
        """Return the last processing response persisted for the UI."""
        return self._registry.last_processing()

    def list_files(self) -> list[dict[str, Any]]:
        """Return files registered by previous processing sessions."""
        return self._registry.list_files()

    def list_history(self) -> list[dict[str, Any]]:
        """Return processing history registered by previous sessions."""
        return self._registry.list_history()

    def default_download_path(self) -> dict[str, str]:
        """Return the backend default download folder."""
        return {"path": str(self._registry.default_download_path)}

    def _process_supabase(
        self,
        options: ProcessingOptions,
        download_dir: Path,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        config = replace(get_supabase_config(), pdf_download_path=download_dir)
        excel_output_dir = PROJECT_ROOT / "output" / "excel"
        previous_excel_exports = self._export_state(excel_output_dir, "*.xlsx")
        previous_xml_exports = self._export_state(self._xml_output_dir, "*.xml")
        processor = Processor(config=config)
        summary = processor.run(
            generate_excel=options.generate_excel,
            excel_mode=options.excel_mode,
            ignore_duplicates=options.ignore_duplicates,
        )
        elapsed = time.perf_counter() - started
        excel_files = self._file_exports(
            excel_output_dir,
            previous_excel_exports,
            "*.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        xml_files = self._file_exports(
            self._xml_output_dir,
            previous_xml_exports,
            "*.xml",
            "application/xml",
        )
        response = {
            "source": "supabase",
            "rows": [],
            "xmlFiles": xml_files,
            "excelFiles": excel_files,
            "summary": {
                "listed": summary.listed,
                "processed": summary.processed,
                "ignored": summary.ignored,
                "failed": summary.failed,
                "duplicated": summary.duplicated,
                "elapsedSeconds": elapsed,
            },
        }
        return self._registry.save_processing(
            response=response,
            file_records=[],
            source=options.source,
            download_path=download_dir,
            download_label=options.download_path_label,
        )

    def _process_local(
        self,
        options: ProcessingOptions,
        download_dir: Path,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        document_paths = self._local_source.documents_from_paths(
            options.paths,
            recursive=options.process_subfolders,
        )
        pdf_paths = [
            path for path in document_paths if path.suffix.lower() == ".pdf"
        ]
        xml_paths = [
            path for path in document_paths if path.suffix.lower() == ".xml"
        ]
        xml_index = self._build_xml_index(xml_paths) if options.detect_xml else {}
        matched_xmls: set[Path] = set()
        notas: list[NotaFiscal] = []
        rows: list[dict[str, Any]] = []
        file_records: list[dict[str, Any]] = []
        failed = 0
        duplicated = 0
        previous_xml_exports = self._export_state(self._xml_output_dir, "*.xml")

        for source_path in pdf_paths:
            source_hash = self._safe_sha256(source_path)

            if options.ignore_duplicates and self._registry.has_success_hash(source_hash):
                duplicated += 1
                row = self._duplicate_row(source_path, source_hash, options.source)
                rows.append(row)
                file_records.append(
                    self._file_record_from_row(row, source_path, source_path)
                )
                self._logger.info("PDF duplicated and ignored: %s", source_path)
                continue

            try:
                working_path = source_path
                downloaded = False

                if options.download_pdfs_locally:
                    working_path, downloaded = self._copy_document_to_download_dir(
                        source_path,
                        download_dir,
                        source_hash,
                    )

                pdf = self._read_pdf_with_ocr(working_path)
                xml_source_path = self._find_xml_for_pdf(
                    source_path,
                    pdf.text,
                    xml_index,
                )
                xml_working_path = None
                xml_text = None

                if xml_source_path:
                    matched_xmls.add(xml_source_path.resolve())
                    xml_working_path = xml_source_path

                    if options.download_pdfs_locally:
                        xml_working_path, _ = self._copy_document_to_download_dir(
                            xml_source_path,
                            download_dir,
                            self._safe_sha256(xml_source_path),
                        )

                    xml_text = self._read_xml(xml_working_path)

                nota = self._parser_manager.parse(
                    pdf,
                    remote_path=None,
                    xml_text=xml_text,
                    xml_local_path=xml_working_path,
                )
                nota.status_processamento = "success"
                nota.caminho_local = str(working_path)
                generated_xml_path = self._xml_writer.write(
                    nota,
                    self._xml_output_dir,
                    source_format="pdf",
                )
                nota.caminho_xml_local = str(generated_xml_path)
                notas.append(nota)

                row = self._row_from_nota(nota, options.source, "success", "PDF")
                row["originPath"] = str(source_path)
                row["path"] = str(working_path)
                row["downloadedPath"] = str(working_path) if options.download_pdfs_locally else None
                row["xmlPath"] = str(generated_xml_path)
                row["downloaded"] = options.download_pdfs_locally and downloaded
                rows.append(row)
                file_records.append(
                    self._file_record_from_row(row, source_path, working_path)
                )
                if xml_working_path:
                    file_records.append(
                        self._xml_file_record(
                            xml_source_path or xml_working_path,
                            xml_working_path,
                            row,
                        )
                    )
                file_records.append(
                    self._xml_file_record(source_path, generated_xml_path, row)
                )
                self._logger.info(
                    "PDF processed: %s | hash=%s | xml=%s | destination=%s",
                    source_path,
                    row.get("hash"),
                    generated_xml_path,
                    working_path,
                )
            except Exception as exc:
                failed += 1
                row = self._error_row(source_path, source_hash, options.source, str(exc))
                rows.append(row)
                file_records.append(
                    self._file_record_from_row(row, source_path, source_path)
                )
                self._logger.exception("PDF failed and will be skipped: %s", source_path)

        for source_path in xml_paths:
            if source_path.resolve() in matched_xmls:
                continue

            source_hash = self._safe_sha256(source_path)

            if options.ignore_duplicates and self._registry.has_success_hash(source_hash):
                duplicated += 1
                row = self._duplicate_row(source_path, source_hash, options.source, "XML")
                rows.append(row)
                file_records.append(
                    self._file_record_from_row(row, source_path, source_path)
                )
                self._logger.info("XML duplicated and ignored: %s", source_path)
                continue

            try:
                working_path = source_path
                downloaded = False

                if options.download_pdfs_locally:
                    working_path, downloaded = self._copy_document_to_download_dir(
                        source_path,
                        download_dir,
                        source_hash,
                    )

                nota = self._parser_manager.parse_xml(working_path)
                nota.status_processamento = "success"
                nota.caminho_xml_local = str(working_path)
                notas.append(nota)

                row = self._row_from_nota(nota, options.source, "success", "XML")
                row["originPath"] = str(source_path)
                row["path"] = str(working_path)
                row["downloadedPath"] = str(working_path) if options.download_pdfs_locally else None
                row["xmlPath"] = str(working_path)
                row["downloaded"] = options.download_pdfs_locally and downloaded
                rows.append(row)
                file_records.append(
                    self._file_record_from_row(row, source_path, working_path)
                )
                self._logger.info(
                    "XML processed: %s | hash=%s | destination=%s",
                    source_path,
                    row.get("hash"),
                    working_path,
                )
            except Exception as exc:
                failed += 1
                row = self._error_row(source_path, source_hash, options.source, str(exc), "XML")
                rows.append(row)
                file_records.append(
                    self._file_record_from_row(row, source_path, source_path)
                )
                self._logger.exception("XML failed and will be skipped: %s", source_path)

        xml_files = self._file_exports(
            self._xml_output_dir,
            previous_xml_exports,
            "*.xml",
            "application/xml",
        )
        excel_files: list[dict[str, str]] = []
        if options.generate_excel and notas:
            output_dir = PROJECT_ROOT / "output" / "excel"
            previous_exports = self._export_state(output_dir, "*.xlsx")
            writer = ExcelWriter(output_dir / "notas.xlsx")
            writer.write(notas, mode=options.excel_mode)
            excel_files = self._file_exports(
                output_dir,
                previous_exports,
                "*.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        elapsed = time.perf_counter() - started
        response = {
            "source": options.source,
            "rows": rows,
            "xmlFiles": xml_files,
            "excelFiles": excel_files,
            "summary": {
                "listed": len(document_paths),
                "processed": len(notas),
                "ignored": 0,
                "failed": failed,
                "duplicated": duplicated,
                "elapsedSeconds": elapsed,
            },
        }
        return self._registry.save_processing(
            response=response,
            file_records=file_records,
            source=options.source,
            download_path=download_dir,
            download_label=options.download_path_label,
        )

    def _read_pdf_with_ocr(self, path: Path) -> PdfReadResult:
        """Read a local PDF and OCR it when its text layer is incomplete."""
        pdf = self._pdf_reader.read(path)
        if not pdf.ocr_required:
            return pdf

        ocr_result = self._ocr_service.extract_text(path)
        if not ocr_result.text.strip():
            raise RuntimeError(
                "OCR necessario para este PDF, mas nenhum texto foi reconhecido. "
                f"Verifique o Tesseract e as dependencias do servico (engine={ocr_result.engine})."
            )

        return replace(
            pdf,
            text=ocr_result.text,
            pages=ocr_result.pages or (ocr_result.text,),
            words=ocr_result.words,
            ocr_required=False,
            ocr_used=True,
            ocr_confidence=ocr_result.confidence,
        )

    @staticmethod
    def _export_state(output_dir: Path, pattern: str) -> dict[Path, int]:
        """Capture existing generated files before a processing run."""
        if not output_dir.is_dir():
            return {}

        state: dict[Path, int] = {}
        for path in output_dir.glob(pattern):
            try:
                state[path] = path.stat().st_mtime_ns
            except OSError:
                continue

        return state

    @staticmethod
    def _file_exports(
        output_dir: Path,
        previous_exports: dict[Path, int],
        pattern: str,
        mime_type: str,
    ) -> list[dict[str, str]]:
        """Return newly created or updated generated files for browser download."""
        if not output_dir.is_dir():
            return []

        exports: list[dict[str, str]] = []
        for path in sorted(output_dir.glob(pattern)):
            try:
                if previous_exports.get(path) == path.stat().st_mtime_ns:
                    continue

                exports.append(
                    {
                        "name": path.name,
                        "contentBase64": base64.b64encode(path.read_bytes()).decode("ascii"),
                        "mimeType": mime_type,
                    }
                )
            except OSError:
                continue

        return exports

    def _resolve_download_dir(self, options: ProcessingOptions) -> Path:
        raw_path = options.download_path

        if raw_path:
            download_dir = Path(raw_path).expanduser()
            if not download_dir.is_absolute():
                download_dir = PROJECT_ROOT / download_dir
        else:
            download_dir = self._registry.default_download_path

        download_dir.mkdir(parents=True, exist_ok=True)
        return download_dir

    def _copy_document_to_download_dir(
        self,
        source_path: Path,
        download_dir: Path,
        source_hash: str | None,
    ) -> tuple[Path, bool]:
        destination = download_dir / source_path.name

        if self._same_path(source_path, destination):
            return source_path, False

        if destination.is_file():
            destination_hash = self._safe_sha256(destination)

            if source_hash and destination_hash == source_hash:
                return destination, False

            destination = self._unique_destination(destination, source_hash)

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        return destination, True

    @staticmethod
    def _unique_destination(destination: Path, source_hash: str | None) -> Path:
        suffix = (source_hash or "copy")[:8]
        candidate = destination.with_name(
            f"{destination.stem}_{suffix}{destination.suffix}"
        )
        counter = 2

        while candidate.exists():
            candidate = destination.with_name(
                f"{destination.stem}_{suffix}_{counter}{destination.suffix}"
            )
            counter += 1

        return candidate

    @staticmethod
    def _same_path(first: Path, second: Path) -> bool:
        try:
            return first.resolve() == second.resolve()
        except OSError:
            return False

    @staticmethod
    def _safe_sha256(path: Path) -> str | None:
        try:
            return StorageService.sha256_file(path)
        except OSError:
            return None

    def _build_xml_index(self, xml_paths: list[Path]) -> dict[str, Path]:
        index: dict[str, Path] = {}

        for xml_path in xml_paths:
            index[f"stem:{xml_path.stem.lower()}"] = xml_path

            for source in (xml_path.name, self._read_xml(xml_path)):
                key = self._extract_access_key(source)

                if key:
                    index[f"key:{key}"] = xml_path

        return index

    def _find_xml_for_pdf(
        self,
        pdf_path: Path,
        pdf_text: str,
        xml_index: dict[str, Path],
    ) -> Path | None:
        candidates = [
            f"stem:{pdf_path.stem.lower()}",
        ]
        key = self._extract_access_key(pdf_path.name) or self._extract_access_key(pdf_text)

        if key:
            candidates.append(f"key:{key}")

        for candidate in candidates:
            xml_path = xml_index.get(candidate)

            if xml_path:
                return xml_path

        return None

    @staticmethod
    def _read_xml(path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")

    @staticmethod
    def _extract_access_key(value: str) -> str | None:
        match = re.search(r"\d{44}", re.sub(r"\D", "", value))
        return match.group(0) if match else None

    @staticmethod
    def _row_from_nota(
        nota: NotaFiscal,
        source: str,
        status: str,
        file_type: str,
    ) -> dict[str, Any]:
        return {
            "name": nota.arquivo,
            "type": file_type,
            "pageCount": nota.quantidade_paginas if file_type == "PDF" else None,
            "sizeBytes": nota.tamanho_bytes,
            "status": status,
            "source": source,
            "hash": nota.sha256,
            "documentType": nota.tipo_documento,
            "parser": nota.parser,
            "error": nota.erro_processamento,
            "progress": 100,
        }

    @staticmethod
    def _duplicate_row(
        path: Path,
        sha256: str | None,
        source: str,
        file_type: str | None = None,
    ) -> dict[str, Any]:
        document_type = file_type or DocumentProcessingService._file_type(path)
        return {
            "name": path.name,
            "type": document_type,
            "pageCount": None,
            "sizeBytes": path.stat().st_size if path.is_file() else None,
            "status": "duplicated",
            "source": source,
            "hash": sha256,
            "documentType": None,
            "parser": None,
            "error": None,
            "progress": 100,
            "originPath": str(path),
            "path": str(path),
            "downloadedPath": None,
            "downloaded": False,
        }

    @staticmethod
    def _error_row(
        path: Path,
        sha256: str | None,
        source: str,
        error: str,
        file_type: str | None = None,
    ) -> dict[str, Any]:
        document_type = file_type or DocumentProcessingService._file_type(path)
        return {
            "name": path.name,
            "type": document_type,
            "pageCount": None,
            "sizeBytes": path.stat().st_size if path.is_file() else None,
            "status": "error",
            "source": source,
            "hash": sha256,
            "documentType": None,
            "parser": None,
            "error": error,
            "progress": 100,
            "originPath": str(path),
            "path": str(path),
            "downloadedPath": None,
            "downloaded": False,
        }

    @staticmethod
    def _file_record_from_row(
        row: dict[str, Any],
        source_path: Path,
        local_path: Path,
    ) -> dict[str, Any]:
        return {
            "id": row.get("hash") or str(local_path),
            "name": row.get("name") or local_path.name,
            "type": row.get("type") or DocumentProcessingService._file_type(local_path),
            "path": str(local_path),
            "originPath": str(source_path),
            "sizeBytes": row.get("sizeBytes"),
            "hash": row.get("hash"),
            "source": row.get("source"),
            "documentType": row.get("documentType"),
            "parser": row.get("parser"),
            "pageCount": row.get("pageCount"),
            "status": row.get("status"),
            "error": row.get("error"),
            "modifiedAt": (
                time.strftime(
                    "%Y-%m-%dT%H:%M:%S",
                    time.localtime(local_path.stat().st_mtime),
                )
                if local_path.is_file()
                else None
            ),
        }

    @staticmethod
    def _xml_file_record(
        source_path: Path,
        local_path: Path,
        pdf_row: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "id": DocumentProcessingService._safe_sha256(local_path) or str(local_path),
            "name": local_path.name,
            "type": "XML",
            "path": str(local_path),
            "originPath": str(source_path),
            "sizeBytes": local_path.stat().st_size if local_path.is_file() else None,
            "hash": DocumentProcessingService._safe_sha256(local_path),
            "source": pdf_row.get("source"),
            "documentType": pdf_row.get("documentType"),
            "parser": pdf_row.get("parser"),
            "pageCount": None,
            "status": pdf_row.get("status"),
            "error": pdf_row.get("error"),
            "modifiedAt": (
                time.strftime(
                    "%Y-%m-%dT%H:%M:%S",
                    time.localtime(local_path.stat().st_mtime),
                )
                if local_path.is_file()
                else None
            ),
        }

    @staticmethod
    def _file_type(path: Path) -> str:
        extension = path.suffix.lower()

        if extension == ".xml":
            return "XML"

        if extension == ".pdf":
            return "PDF"

        return "DOCUMENTO"
