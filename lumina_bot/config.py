"""Configuration for Lumina automation and fiscal document processing."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self

from dotenv import load_dotenv

from lumina_bot.exceptions import ConfigurationError


PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


def _resolve_project_path(value: str | Path) -> Path:
    """Resolve relative paths from the project root."""
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value is None else float(value)


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


class Config:
    """Original Lumina ERP automation settings."""

    LUMINA_USER = os.getenv(
        "LUMINA_USER",
        os.getenv("LUMINA_USERNAME", "admin"),
    )
    LUMINA_PASSWORD = os.getenv("LUMINA_PASSWORD", "1234")

    LUMINA_PATH = os.getenv(
        "LUMINA_PATH",
        os.getenv(
            "LUMINA_EXECUTABLE_PATH",
            r"C:\Program Files (x86)\Lumina\Lumina.exe",
        ),
    )
    LUMINA_WORKDIR = os.getenv(
        "LUMINA_WORKDIR",
        r"C:\Program Files (x86)\Lumina",
    )

    LUMINA_TIMEOUT = int(os.getenv("LUMINA_TIMEOUT", "30"))
    ELEMENT_WAIT = int(os.getenv("ELEMENT_WAIT", "5"))
    POST_CLICK_DELAY = float(os.getenv("POST_CLICK_DELAY", "0.5"))
    WINDOW_OPEN_TIMEOUT = int(os.getenv("WINDOW_OPEN_TIMEOUT", "10"))

    HEADLESS = os.getenv("HEADLESS", "False").lower() in ("true", "1", "yes")
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = int(os.getenv("RETRY_DELAY", "2"))
    SCREENSHOT_ON_ERROR = os.getenv("SCREENSHOT_ON_ERROR", "True").lower() in (
        "true",
        "1",
        "yes",
    )
    SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "screenshots")

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "lumina_automation.log")

    MODULO_PADRAO = os.getenv("MODULO_PADRAO", "Faturamento")
    JANELA_PRINCIPAL_TITLE = os.getenv("JANELA_PRINCIPAL_TITLE", "Lumina ERP")
    MENU_TREE_DEPTH = int(os.getenv("MENU_TREE_DEPTH", "5"))
    POST_LOGIN_TIMEOUT = float(os.getenv("LUMINA_POST_LOGIN_TIMEOUT", "60"))


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Runtime settings shared by the Lumina desktop framework."""

    executable_path: Path
    main_window_title_re: str
    backend: Literal["uia"] = "uia"
    start_timeout: float = 30.0
    connect_timeout: float = 10.0
    window_timeout: float = 20.0
    implicit_timeout: float = 10.0
    post_login_timeout: float = 60.0
    retry_interval: float = 0.3
    max_retries: int = 3
    action_delay: float = 3.0
    wait_after_click: float = 0.2
    wait_after_set_text: float = 0.1
    screenshot_on_error: bool = False
    logs_dir: Path = PROJECT_ROOT / "logs"
    screenshots_dir: Path = PROJECT_ROOT / "screenshots"

    @property
    def default_timeout(self) -> float:
        """Backward-compatible alias for the implicit timeout."""
        return self.implicit_timeout

    @classmethod
    def from_env(cls) -> Self:
        """Build Lumina automation settings from environment variables."""
        executable = os.getenv(
            "LUMINA_EXECUTABLE_PATH",
            Config.LUMINA_PATH,
        )
        title_re = os.getenv(
            "LUMINA_MAIN_WINDOW_TITLE_RE",
            rf".*{Config.JANELA_PRINCIPAL_TITLE}.*",
        )

        return cls(
            executable_path=Path(executable),
            main_window_title_re=title_re,
            start_timeout=_get_float("LUMINA_START_TIMEOUT", Config.LUMINA_TIMEOUT),
            connect_timeout=_get_float(
                "LUMINA_CONNECT_TIMEOUT",
                Config.WINDOW_OPEN_TIMEOUT,
            ),
            window_timeout=_get_float("LUMINA_WINDOW_TIMEOUT", Config.LUMINA_TIMEOUT),
            implicit_timeout=_get_float("LUMINA_IMPLICIT_TIMEOUT", Config.ELEMENT_WAIT),
            post_login_timeout=_get_float(
                "LUMINA_POST_LOGIN_TIMEOUT",
                Config.POST_LOGIN_TIMEOUT,
            ),
            retry_interval=_get_float("LUMINA_RETRY_INTERVAL", 0.3),
            max_retries=_get_int("LUMINA_MAX_RETRIES", Config.MAX_RETRIES),
            action_delay=_get_float("LUMINA_ACTION_DELAY", 3.0),
            wait_after_click=_get_float(
                "LUMINA_WAIT_AFTER_CLICK",
                Config.POST_CLICK_DELAY,
            ),
            wait_after_set_text=_get_float("LUMINA_WAIT_AFTER_SET_TEXT", 0.1),
            screenshot_on_error=_get_bool(
                "LUMINA_SCREENSHOT_ON_ERROR",
                Config.SCREENSHOT_ON_ERROR,
            ),
            logs_dir=_resolve_project_path(os.getenv("LOGS_DIR", "logs")),
            screenshots_dir=_resolve_project_path(
                os.getenv("SCREENSHOT_DIR", Config.SCREENSHOT_DIR),
            ),
        )


@dataclass(frozen=True, slots=True)
class LoginCredentials:
    """Credentials used by the Lumina login flow."""

    username: str
    password: str

    @classmethod
    def from_env(cls) -> Self:
        """Build credentials from environment variables."""
        username = os.getenv("LUMINA_USERNAME", Config.LUMINA_USER)
        password = os.getenv("LUMINA_PASSWORD", Config.LUMINA_PASSWORD)

        missing = [
            name
            for name, value in {
                "LUMINA_USERNAME or LUMINA_USER": username,
                "LUMINA_PASSWORD": password,
            }.items()
            if not value
        ]

        if missing:
            raise ConfigurationError(
                "Missing required login environment variable(s): "
                + ", ".join(missing)
            )

        return cls(username=str(username), password=str(password))


@dataclass(frozen=True, slots=True)
class SupabaseConnectionConfig:
    """Base Supabase credentials shared by database and storage services."""

    url: str
    service_role_key: str

    @classmethod
    def from_env(cls) -> Self:
        """Build base Supabase settings from environment variables."""
        values = {
            "SUPABASE_URL": os.getenv("SUPABASE_URL"),
            "SUPABASE_SERVICE_ROLE_KEY": os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        }
        missing = [name for name, value in values.items() if not value]

        if missing:
            raise ConfigurationError(
                "Missing required Supabase variable(s): " + ", ".join(missing)
            )

        return cls(
            url=str(values["SUPABASE_URL"]),
            service_role_key=str(values["SUPABASE_SERVICE_ROLE_KEY"]),
        )


@dataclass(frozen=True, slots=True)
class SupabaseConfig:
    """Supabase Storage settings for private fiscal document buckets."""

    url: str
    service_role_key: str
    bucket: str
    folder: str
    pdf_download_path: Path
    excel_output_path: Path

    @classmethod
    def from_env(cls) -> Self:
        """Build Supabase settings from environment variables."""
        connection = SupabaseConnectionConfig.from_env()
        values = {"SUPABASE_BUCKET": os.getenv("SUPABASE_BUCKET")}
        missing = [name for name, value in values.items() if not value]

        if missing:
            raise ConfigurationError(
                "Missing required Supabase variable(s): " + ", ".join(missing)
            )

        return cls(
            url=connection.url,
            service_role_key=connection.service_role_key,
            bucket=str(values["SUPABASE_BUCKET"]),
            folder=os.getenv("SUPABASE_FOLDER", "").strip("/"),
            pdf_download_path=_resolve_project_path(
                os.getenv("PDF_DOWNLOAD_PATH", "output/pdfs"),
            ),
            excel_output_path=_resolve_project_path(
                os.getenv("EXCEL_OUTPUT_PATH", "output/excel/notas.xlsx"),
            ),
        )


def get_supabase_config() -> SupabaseConfig:
    """Return Supabase settings only when the processing module needs them."""
    return SupabaseConfig.from_env()


def get_supabase_connection_config() -> SupabaseConnectionConfig:
    """Return base Supabase credentials without requiring Storage settings."""
    return SupabaseConnectionConfig.from_env()


@dataclass(frozen=True, slots=True)
class OperatorProfileConfig:
    """Supabase table settings used to load the current desktop operator."""

    table: str
    id_column: str
    id_value: str | None
    email_column: str
    email_value: str | None
    username_column: str
    username_value: str | None
    name_column: str
    role_column: str
    avatar_url_column: str
    fallback_name: str
    fallback_role: str

    @classmethod
    def from_env(cls) -> Self:
        """Build operator profile lookup settings from environment variables."""
        return cls(
            table=os.getenv("SUPABASE_OPERATOR_TABLE", "operators"),
            id_column=os.getenv("SUPABASE_OPERATOR_ID_COLUMN", "id"),
            id_value=os.getenv("SUPABASE_OPERATOR_ID") or None,
            email_column=os.getenv("SUPABASE_OPERATOR_EMAIL_COLUMN", "email"),
            email_value=os.getenv("SUPABASE_OPERATOR_EMAIL") or None,
            username_column=os.getenv("SUPABASE_OPERATOR_USERNAME_COLUMN", "username"),
            username_value=(
                os.getenv("SUPABASE_OPERATOR_USERNAME")
                or os.getenv("LUMINA_USERNAME")
                or Config.LUMINA_USER
                or None
            ),
            name_column=os.getenv("SUPABASE_OPERATOR_NAME_COLUMN", "name"),
            role_column=os.getenv("SUPABASE_OPERATOR_ROLE_COLUMN", "role"),
            avatar_url_column=os.getenv(
                "SUPABASE_OPERATOR_AVATAR_URL_COLUMN",
                "avatar_url",
            ),
            fallback_name=os.getenv("OPERATOR_FALLBACK_NAME", "Operador"),
            fallback_role=os.getenv("OPERATOR_FALLBACK_ROLE", "LinkAI Web"),
        )


def get_operator_profile_config() -> OperatorProfileConfig:
    """Return settings used to locate the current operator profile."""
    return OperatorProfileConfig.from_env()


DEFAULT_CONFIG = AppConfig.from_env()
