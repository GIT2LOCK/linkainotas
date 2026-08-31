"""Regression tests for explicit reprocessing of identical documents."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from types import SimpleNamespace

from backend.models.ui import ProcessingOptions
from lumina_bot.core.pdf_reader import PdfReadResult
from lumina_bot.core.processor import ProcessingRegistry, Processor
from lumina_bot.core.storage import LocalDocument, RemoteStorageFile
from lumina_bot.models.nota import NotaFiscal


class _FakeStorage:
    def __init__(self, remote: RemoteStorageFile, local: LocalDocument) -> None:
        self.remote = remote
        self.local = local

    def listar_arquivos(self) -> list[RemoteStorageFile]:
        return [self.remote]

    def indexar_xmls(self, documents: list[RemoteStorageFile]) -> dict[str, RemoteStorageFile]:
        return {}

    def baixar_para_disco(self, remote: RemoteStorageFile) -> LocalDocument:
        return self.local

    def baixar_xml_correspondente(
        self,
        pdf_file: RemoteStorageFile,
        xml_index: dict[str, RemoteStorageFile],
    ) -> None:
        return None


class _FakePdfReader:
    def read(self, path: Path) -> PdfReadResult:
        return PdfReadResult(
            path=path,
            text="DANFE\nDocumento Auxiliar da Nota Fiscal Eletrônica",
            page_count=1,
            author=None,
            creator=None,
            producer=None,
            size_bytes=10,
            sha256="pdf-hash",
            pages=("DANFE",),
        )


class _FakeParserManager:
    def parse(self, pdf: PdfReadResult, *, remote_path: str, **kwargs: object) -> NotaFiscal:
        return NotaFiscal(
            caminho_remoto=remote_path,
            numero="1",
            valor_total=10.0,
        )


class _FakeXmlWriter:
    def write(self, nota: NotaFiscal, output_dir: Path, *, source_format: str) -> Path:
        return output_dir / "sample.xml"


class _FakeExcelWriter:
    def write(self, notas: list[NotaFiscal], *, mode: str) -> None:
        return None


class DuplicateProcessingTests(unittest.TestCase):
    def test_reprocessing_is_allowed_by_default(self) -> None:
        options = ProcessingOptions.from_payload({"source": "folder"})
        self.assertFalse(options.ignore_duplicates)

    def test_identical_pdf_is_processed_again_unless_opted_out(self) -> None:
        remote = RemoteStorageFile(
            path="sample.pdf",
            name="sample.pdf",
            extension=".pdf",
        )
        local = LocalDocument(
            remote=remote,
            local_path=Path("sample.pdf"),
            sha256="same-hash",
            size_bytes=10,
            downloaded=False,
        )

        with TemporaryDirectory() as temp_dir:
            processor = Processor(
                config=SimpleNamespace(excel_output_path=Path(temp_dir) / "output.xlsx"),
                storage=_FakeStorage(remote, local),
                pdf_reader=_FakePdfReader(),
                parser_manager=_FakeParserManager(),
                excel_writer=_FakeExcelWriter(),
                xml_writer=_FakeXmlWriter(),
            )
            processor._registry = ProcessingRegistry(Path(temp_dir) / "state.json")

            first = processor.processar()
            second = processor.processar()
            skipped = processor.processar(ignore_duplicates=True)

        self.assertEqual(first.processed, 1)
        self.assertEqual(second.processed, 1)
        self.assertEqual(second.duplicated, 0)
        self.assertEqual(skipped.processed, 0)
        self.assertEqual(skipped.duplicated, 1)


if __name__ == "__main__":
    unittest.main()
