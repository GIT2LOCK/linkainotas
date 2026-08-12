"""Compatibility exports for framework exceptions.

New code should import from lumina_bot.exceptions. This module remains so older
imports keep working while the framework evolves.
"""

from __future__ import annotations

from lumina_bot.exceptions import (
    ApplicationConnectionError,
    ApplicationError,
    ApplicationStartError,
    ConfigurationError,
    DocumentProcessingError,
    ElementInteractionError,
    ElementNotFound,
    LoginFailed,
    LuminaApplicationConnectionError,
    LuminaApplicationError,
    LuminaApplicationStartError,
    LuminaBotError,
    LuminaConfigError,
    LuminaElementInteractionError,
    LuminaElementNotFoundError,
    LuminaMainWindowNotFoundError,
    LuminaWaitTimeoutError,
    PdfReadError,
    StorageError,
    SupabaseClientError,
    TimeoutWaitingControl,
    WindowNotFound,
)

__all__ = [
    "ApplicationConnectionError",
    "ApplicationError",
    "ApplicationStartError",
    "ConfigurationError",
    "DocumentProcessingError",
    "ElementInteractionError",
    "ElementNotFound",
    "LoginFailed",
    "LuminaApplicationConnectionError",
    "LuminaApplicationError",
    "LuminaApplicationStartError",
    "LuminaBotError",
    "LuminaConfigError",
    "LuminaElementInteractionError",
    "LuminaElementNotFoundError",
    "LuminaMainWindowNotFoundError",
    "LuminaWaitTimeoutError",
    "PdfReadError",
    "StorageError",
    "SupabaseClientError",
    "TimeoutWaitingControl",
    "WindowNotFound",
]
