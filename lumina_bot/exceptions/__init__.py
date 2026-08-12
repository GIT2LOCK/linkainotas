"""Framework-specific exceptions."""

from __future__ import annotations


class LuminaBotError(Exception):
    """Base exception for all framework errors."""


class ConfigurationError(LuminaBotError):
    """Raised when required framework configuration is invalid."""


class ApplicationError(LuminaBotError):
    """Base exception for Lumina process and window failures."""


class ApplicationStartError(ApplicationError):
    """Raised when Lumina cannot be started."""


class ApplicationConnectionError(ApplicationError):
    """Raised when the framework cannot attach to a running Lumina process."""


class WindowNotFound(ApplicationError):
    """Raised when the main Lumina window cannot be located."""


class ElementNotFound(LuminaBotError):
    """Raised when an expected UI Automation control cannot be found."""


class ElementInteractionError(LuminaBotError):
    """Raised when a control is found but cannot be used."""


class TimeoutWaitingControl(LuminaBotError):
    """Raised when a control does not satisfy a wait condition in time."""


class LoginFailed(LuminaBotError):
    """Raised when the login workflow fails after submitting credentials."""


class SupabaseClientError(LuminaBotError):
    """Raised when Supabase operations fail after retries."""


class StorageError(LuminaBotError):
    """Raised when document storage operations fail."""


class PdfReadError(LuminaBotError):
    """Raised when a PDF cannot be read."""


class DocumentProcessingError(LuminaBotError):
    """Raised when a document fails during processing."""


# Compatibility aliases for the original core.exceptions module names.
LuminaConfigError = ConfigurationError
LuminaApplicationError = ApplicationError
LuminaApplicationStartError = ApplicationStartError
LuminaApplicationConnectionError = ApplicationConnectionError
LuminaMainWindowNotFoundError = WindowNotFound
LuminaElementNotFoundError = ElementNotFound
LuminaElementInteractionError = ElementInteractionError
LuminaWaitTimeoutError = TimeoutWaitingControl
