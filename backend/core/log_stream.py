"""Log reading helpers for the desktop UI."""

from __future__ import annotations

from pathlib import Path

from lumina_bot.config import DEFAULT_CONFIG, PROJECT_ROOT


class LogStream:
    """Reads recent log lines without keeping files open."""

    def __init__(self, log_path: Path | None = None) -> None:
        self._log_path = log_path or DEFAULT_CONFIG.logs_dir / "lumina_bot.log"

    def latest(self, lines: int = 300) -> list[str]:
        """Return the latest log lines."""
        if not self._log_path.is_file():
            return []

        content = self._log_path.read_text(encoding="utf-8", errors="ignore")
        return content.splitlines()[-lines:]

    def export_path(self) -> str:
        """Return the current log path as a string."""
        return str(self._log_path)


def output_log_directory() -> Path:
    """Return the output log directory used by new processing modules."""
    path = PROJECT_ROOT / "output" / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
