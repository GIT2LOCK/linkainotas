"""Logging setup for the Lumina automation framework."""

from __future__ import annotations

import logging
from pathlib import Path

from lumina_bot.config import DEFAULT_CONFIG


LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOGGER_NAME = "lumina_bot"


def configure_logging(
    log_dir: Path = DEFAULT_CONFIG.logs_dir,
    level: int = logging.INFO,
) -> logging.Logger:
    """Configure console and file logging once for the framework."""
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        for handler in logger.handlers:
            handler.setLevel(level)
        return logger

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        log_dir / "lumina_bot.log",
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the framework logger namespace."""
    normalized_name = name.replace("__main__", "main")
    return logging.getLogger(f"{LOGGER_NAME}.{normalized_name}")
