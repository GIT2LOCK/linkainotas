"""Operator profile service backed by Supabase Database."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, ClassVar

from supabase import Client, create_client

from backend.models.ui import OperatorProfile
from lumina_bot.config import (
    OperatorProfileConfig,
    get_operator_profile_config,
    get_supabase_connection_config,
)
from lumina_bot.core.logger import get_logger


class OperatorService:
    """Loads the current desktop operator without exposing Supabase to React."""

    _client: ClassVar[Client | None] = None
    _NAME_FALLBACK_KEYS = ("name", "full_name", "display_name", "nome")
    _ROLE_FALLBACK_KEYS = ("role", "position", "job_title", "cargo")
    _EMAIL_FALLBACK_KEYS = ("email", "mail")
    _AVATAR_FALLBACK_KEYS = ("avatar_url", "photo_url", "image_url", "foto")

    def __init__(self, config: OperatorProfileConfig | None = None) -> None:
        self._config = config or get_operator_profile_config()
        self._logger = get_logger(self.__class__.__name__)

    def profile(self) -> OperatorProfile:
        """Return the configured operator profile or a safe local fallback."""
        try:
            record = self._fetch_operator_record()
        except Exception as exc:
            self._logger.warning("Unable to load operator profile: %s", exc)
            return self._fallback()

        if not record:
            return self._fallback()

        return OperatorProfile(
            name=self._string_from_record(
                record,
                self._config.name_column,
                self._NAME_FALLBACK_KEYS,
                self._config.fallback_name,
            ),
            role=self._string_from_record(
                record,
                self._config.role_column,
                self._ROLE_FALLBACK_KEYS,
                self._config.fallback_role,
            ),
            email=self._optional_string_from_record(
                record,
                self._config.email_column,
                self._EMAIL_FALLBACK_KEYS,
            ),
            avatar_url=self._optional_string_from_record(
                record,
                self._config.avatar_url_column,
                self._AVATAR_FALLBACK_KEYS,
            ),
            source="supabase",
        )

    def _fetch_operator_record(self) -> dict[str, Any] | None:
        client = self._database_client()
        query = client.table(self._config.table).select("*")

        if self._config.id_value:
            query = query.eq(self._config.id_column, self._config.id_value)
        elif self._config.email_value:
            query = query.eq(self._config.email_column, self._config.email_value)
        elif self._config.username_value:
            query = query.eq(self._config.username_column, self._config.username_value)
        else:
            self._logger.info("Operator lookup skipped: no operator identifier set.")
            return None

        response = query.limit(1).execute()
        data = getattr(response, "data", None) or []

        if not data:
            self._logger.info("No operator profile found in table '%s'.", self._config.table)
            return None

        return dict(data[0])

    @classmethod
    def _database_client(cls) -> Client:
        if cls._client is None:
            supabase_config = get_supabase_connection_config()
            cls._client = create_client(
                supabase_config.url,
                supabase_config.service_role_key,
            )

        return cls._client

    def _fallback(self) -> OperatorProfile:
        return OperatorProfile(
            name=self._config.fallback_name,
            role=self._config.fallback_role,
            source="fallback",
        )

    @staticmethod
    def _string_from_record(
        record: dict[str, Any],
        primary_key: str,
        fallback_keys: Iterable[str],
        default: str,
    ) -> str:
        value = OperatorService._optional_string_from_record(
            record,
            primary_key,
            fallback_keys,
        )
        return value or default

    @staticmethod
    def _optional_string_from_record(
        record: dict[str, Any],
        primary_key: str,
        fallback_keys: Iterable[str],
    ) -> str | None:
        keys = (primary_key, *fallback_keys)

        for key in keys:
            value = record.get(key)
            if value is None:
                continue

            text = str(value).strip()
            if text:
                return text

        return None
