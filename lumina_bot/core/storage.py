"""Storage orchestration for Supabase fiscal documents."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from lumina_bot.config import SupabaseConfig
from lumina_bot.core.logger import get_logger
from lumina_bot.core.supabase_client import SupabaseStorageClient
from lumina_bot.exceptions import StorageError


@dataclass(frozen=True, slots=True)
class RemoteStorageFile:
    """Remote file metadata from Supabase Storage."""

    path: str
    name: str
    extension: str
    size: int | None = None
    updated_at: str | None = None
    metadata: dict[str, Any] | None = None

    @property
    def is_pdf(self) -> bool:
        """Return True when the remote file is a PDF."""
        return self.extension == ".pdf"

    @property
    def is_xml(self) -> bool:
        """Return True when the remote file is an XML."""
        return self.extension == ".xml"

    @property
    def stem_key(self) -> str:
        """Return a normalized key used to match PDF and XML pairs."""
        return str(PurePosixPath(self.path).with_suffix("")).lower()


@dataclass(frozen=True, slots=True)
class LocalDocument:
    """Local document saved from Supabase Storage."""

    remote: RemoteStorageFile
    local_path: Path
    sha256: str
    size_bytes: int
    downloaded: bool


class StorageService:
    """Lists, filters, downloads, and caches documents locally."""

    ALLOWED_EXTENSIONS = {".pdf", ".xml"}
    IGNORED_EXTENSIONS = {
        ".txt",
        ".csv",
        ".zip",
        ".rar",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".tmp",
        ".temp",
        ".crdownload",
        ".part",
    }

    def __init__(
        self,
        config: SupabaseConfig,
        client: SupabaseStorageClient | None = None,
    ) -> None:
        self._config = config
        self._client = client or SupabaseStorageClient(config)
        self._download_dir = config.pdf_download_path
        self._logger = get_logger(self.__class__.__name__)

    def listar_arquivos(self) -> list[RemoteStorageFile]:
        """List supported document files recursively from Supabase."""
        self._logger.info(
            "Listing Supabase bucket '%s' folder '%s'",
            self._config.bucket,
            self._config.folder or "/",
        )
        raw_files = self._client.listar_recursivamente(self._config.folder)
        documents: list[RemoteStorageFile] = []

        for item in raw_files:
            document = self._to_remote_file(item)

            if document is None:
                continue

            if document.extension in self.ALLOWED_EXTENSIONS:
                documents.append(document)
                continue

            self._logger.info("Ignored unsupported file: %s", item.get("path"))

        self._logger.info("Supported remote documents found: %s", len(documents))
        return documents

    def listar_pdfs(self) -> list[RemoteStorageFile]:
        """List only PDFs from the configured bucket/folder."""
        return [document for document in self.listar_arquivos() if document.is_pdf]

    def listar_xmls(self) -> list[RemoteStorageFile]:
        """List only XML files from the configured bucket/folder."""
        return [document for document in self.listar_arquivos() if document.is_xml]

    def baixar(self, remote_file: RemoteStorageFile) -> LocalDocument:
        """Download a remote file to the configured local output folder."""
        return self.baixar_para_disco(remote_file)

    def baixar_para_disco(self, remote_file: RemoteStorageFile) -> LocalDocument:
        """Download a remote file and avoid rewriting identical content."""
        try:
            self._download_dir.mkdir(parents=True, exist_ok=True)
            local_path = self._local_path_for(remote_file)
            local_path.parent.mkdir(parents=True, exist_ok=True)

            data = self._client.download_em_memoria(remote_file.path)
            remote_hash = self.sha256_bytes(data)

            if local_path.is_file():
                local_hash = self.sha256_file(local_path)

                if local_hash == remote_hash:
                    self._logger.info("Local cache hit: %s", local_path)
                    return LocalDocument(
                        remote=remote_file,
                        local_path=local_path,
                        sha256=remote_hash,
                        size_bytes=local_path.stat().st_size,
                        downloaded=False,
                    )

            local_path.write_bytes(data)
            self._logger.info("Saved document: %s", local_path)
            return LocalDocument(
                remote=remote_file,
                local_path=local_path,
                sha256=remote_hash,
                size_bytes=len(data),
                downloaded=True,
            )
        except Exception as exc:
            raise StorageError(f"Could not download '{remote_file.path}'.") from exc

    def baixar_xml_correspondente(
        self,
        pdf_file: RemoteStorageFile,
        xml_index: dict[str, RemoteStorageFile],
    ) -> LocalDocument | None:
        """Download matching XML when it exists."""
        xml_file = xml_index.get(pdf_file.stem_key)

        if xml_file is None:
            return None

        self._logger.info("Matching XML found for %s: %s", pdf_file.path, xml_file.path)
        return self.baixar_para_disco(xml_file)

    def indexar_xmls(
        self,
        documents: list[RemoteStorageFile],
    ) -> dict[str, RemoteStorageFile]:
        """Build a PDF/XML matching index by remote stem."""
        return {document.stem_key: document for document in documents if document.is_xml}

    @staticmethod
    def sha256_bytes(data: bytes) -> str:
        """Return SHA256 from in-memory bytes."""
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def sha256_file(path: Path) -> str:
        """Return SHA256 from a local file without loading it fully."""
        digest = hashlib.sha256()

        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)

        return digest.hexdigest()

    def _local_path_for(self, remote_file: RemoteStorageFile) -> Path:
        safe_parts = [
            part
            for part in PurePosixPath(remote_file.path).parts
            if part not in {"", ".", ".."}
        ]
        return self._download_dir.joinpath(*safe_parts)

    @staticmethod
    def _to_remote_file(item: dict[str, Any]) -> RemoteStorageFile | None:
        path = str(item.get("path") or item.get("name") or "").strip("/")

        if not path:
            return None

        name = PurePosixPath(path).name
        extension = PurePosixPath(name).suffix.lower()
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        size = metadata.get("size") or item.get("size")

        try:
            parsed_size = int(size) if size is not None else None
        except (TypeError, ValueError):
            parsed_size = None

        return RemoteStorageFile(
            path=path,
            name=name,
            extension=extension,
            size=parsed_size,
            updated_at=item.get("updated_at"),
            metadata=metadata,
        )
