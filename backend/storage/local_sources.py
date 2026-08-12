"""Local folder and file discovery for fiscal document processing."""

from __future__ import annotations

from pathlib import Path


class LocalDocumentSource:
    """Discovers local PDF/XML documents selected from the desktop frontend."""

    SUPPORTED_EXTENSIONS = {".pdf", ".xml"}

    def from_paths(self, paths: list[str], *, recursive: bool = True) -> list[Path]:
        """Return all PDFs represented by selected files or folders."""
        return [
            path
            for path in self.documents_from_paths(paths, recursive=recursive)
            if path.suffix.lower() == ".pdf"
        ]

    def documents_from_paths(
        self,
        paths: list[str],
        *,
        recursive: bool = True,
    ) -> list[Path]:
        """Return all supported PDF/XML documents represented by files or folders."""
        documents: list[Path] = []

        for raw_path in paths:
            path = Path(raw_path)

            if path.is_file() and path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                documents.append(path)
                continue

            if path.is_dir():
                documents.extend(self._documents_from_directory(path, recursive))

        return sorted({document.resolve() for document in documents})

    def _documents_from_directory(self, path: Path, recursive: bool) -> list[Path]:
        pattern_prefix = "**/*" if recursive else "*"
        documents: list[Path] = []

        for extension in self.SUPPORTED_EXTENSIONS:
            documents.extend(sorted(path.glob(f"{pattern_prefix}{extension}")))

        return documents
