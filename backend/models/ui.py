"""UI-facing dataclasses used by the desktop bridge."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


ExcelMode = Literal[
    "single_sheet",
    "multi_sheet",
    "one_file_per_pdf",
]
ProcessingSource = Literal["supabase", "folder", "files"]


@dataclass(slots=True)
class DashboardMetrics:
    """Dashboard metrics displayed by the React frontend."""

    pdf_count: int = 0
    processed_count: int = 0
    error_count: int = 0
    spreadsheet_count: int = 0
    last_processing: str | None = None
    last_sync: str | None = None
    average_time_seconds: float | None = None
    supabase_status: str = "not_configured"
    used_space_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable dictionary."""
        return asdict(self)


@dataclass(slots=True)
class OperatorProfile:
    """Current operator profile shown by the desktop shell."""

    name: str
    role: str
    email: str | None = None
    avatar_url: str | None = None
    source: str = "fallback"

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable dictionary."""
        return asdict(self)


@dataclass(slots=True)
class ProcessingOptions:
    """Options selected by the user before processing documents."""

    source: ProcessingSource
    paths: list[str] = field(default_factory=list)
    download_path: str | None = None
    download_path_label: str | None = None
    generate_excel: bool = True
    download_pdfs_locally: bool = True
    ignore_duplicates: bool = True
    use_cache: bool = True
    detect_xml: bool = True
    use_ai_when_needed: bool = False
    process_subfolders: bool = True
    excel_mode: ExcelMode = "single_sheet"

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ProcessingOptions":
        """Build options from frontend payload."""
        return cls(
            source=payload.get("source", "supabase"),
            paths=[str(path) for path in payload.get("paths", [])],
            download_path=(
                str(payload["downloadPath"]).strip()
                if payload.get("downloadPath")
                else None
            ),
            download_path_label=(
                str(payload["downloadPathLabel"]).strip()
                if payload.get("downloadPathLabel")
                else None
            ),
            generate_excel=bool(payload.get("generateExcel", True)),
            download_pdfs_locally=bool(payload.get("downloadPdfsLocally", True)),
            ignore_duplicates=bool(payload.get("ignoreDuplicates", True)),
            use_cache=bool(payload.get("useCache", True)),
            detect_xml=bool(payload.get("detectXml", True)),
            use_ai_when_needed=bool(payload.get("useAiWhenNeeded", False)),
            process_subfolders=bool(payload.get("processSubfolders", True)),
            excel_mode=payload.get("excelMode", "single_sheet"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable dictionary."""
        return asdict(self)
