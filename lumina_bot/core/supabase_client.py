"""Singleton Supabase Storage client for private buckets."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, ClassVar, TypeVar

from supabase import Client, create_client

from lumina_bot.config import SupabaseConfig
from lumina_bot.core.logger import get_logger
from lumina_bot.exceptions import SupabaseClientError


T = TypeVar("T")


class SupabaseStorageClient:
    """Singleton wrapper around the official Supabase SDK."""

    _instance: ClassVar["SupabaseStorageClient | None"] = None

    def __new__(cls, config: SupabaseConfig) -> "SupabaseStorageClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False

        return cls._instance

    def __init__(self, config: SupabaseConfig) -> None:
        if self._initialized:
            return

        self._config = config
        self._logger = get_logger(self.__class__.__name__)
        self._client: Client = create_client(
            self._config.url,
            self._config.service_role_key,
        )
        self._list_cache: dict[str, list[dict[str, Any]]] = {}
        self._exists_cache: dict[str, bool] = {}
        self._initialized = True

    def listar(self, path: str = "") -> list[dict[str, Any]]:
        """List files and folders from a bucket path."""
        normalized_path = self._normalize_path(path)

        if normalized_path in self._list_cache:
            return self._list_cache[normalized_path]

        def operation() -> list[dict[str, Any]]:
            bucket = self._bucket()
            all_items: list[dict[str, Any]] = []
            limit = 1000
            offset = 0

            while True:
                items = bucket.list(
                    normalized_path,
                    {
                        "limit": limit,
                        "offset": offset,
                        "sortBy": {"column": "name", "order": "asc"},
                    },
                )
                normalized_items = [dict(item) for item in items or []]
                all_items.extend(normalized_items)

                if len(normalized_items) < limit:
                    break

                offset += limit

            return all_items

        result = self._with_retry(
            f"list Supabase path '{normalized_path}'",
            operation,
        )
        self._list_cache[normalized_path] = result
        return result

    def listar_recursivamente(self, path: str = "") -> list[dict[str, Any]]:
        """List bucket files recursively."""
        normalized_path = self._normalize_path(path)
        result: list[dict[str, Any]] = []

        for item in self.listar(normalized_path):
            name = str(item.get("name", "")).strip("/")

            if not name:
                continue

            item_path = self._join_path(normalized_path, name)

            if self._is_folder(item):
                result.extend(self.listar_recursivamente(item_path))
                continue

            copied = dict(item)
            copied["path"] = item_path
            result.append(copied)

        return result

    def download(self, path: str) -> bytes:
        """Download an object from Supabase Storage into memory."""
        return self.download_em_memoria(path)

    def download_em_memoria(self, path: str) -> bytes:
        """Download an object from Supabase Storage into memory."""
        normalized_path = self._normalize_path(path)
        self._logger.info("Downloading from Supabase: %s", normalized_path)

        def operation() -> bytes:
            data = self._bucket().download(normalized_path)
            return bytes(data)

        return self._with_retry(f"download '{normalized_path}'", operation)

    def download_para_disco(self, path: str, destination: str) -> None:
        """Download an object and save it to disk."""
        data = self.download_em_memoria(path)

        with open(destination, "wb") as file:
            file.write(data)

    def upload(
        self,
        path: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
        upsert: bool = True,
    ) -> Any:
        """Upload bytes to Supabase Storage."""
        normalized_path = self._normalize_path(path)

        def operation() -> Any:
            return self._bucket().upload(
                normalized_path,
                data,
                {
                    "content-type": content_type,
                    "upsert": str(upsert).lower(),
                },
            )

        response = self._with_retry(f"upload '{normalized_path}'", operation)
        self._invalidate_cache(normalized_path)
        return response

    def delete(self, path: str) -> Any:
        """Delete an object from Supabase Storage."""
        normalized_path = self._normalize_path(path)

        def operation() -> Any:
            return self._bucket().remove([normalized_path])

        response = self._with_retry(f"delete '{normalized_path}'", operation)
        self._invalidate_cache(normalized_path)
        return response

    def exists(self, path: str) -> bool:
        """Return True when an object exists in Supabase Storage."""
        normalized_path = self._normalize_path(path)

        if normalized_path in self._exists_cache:
            return self._exists_cache[normalized_path]

        parent, file_name = self._split_parent(normalized_path)
        exists = any(item.get("name") == file_name for item in self.listar(parent))
        self._exists_cache[normalized_path] = exists
        return exists

    def signed_url(self, path: str, expires_in: int = 3600) -> str:
        """Create a temporary signed URL for a private object."""
        normalized_path = self._normalize_path(path)

        def operation() -> Any:
            return self._bucket().create_signed_url(normalized_path, expires_in)

        response = self._with_retry(f"signed URL '{normalized_path}'", operation)

        if isinstance(response, dict):
            for key in ("signedURL", "signedUrl", "signed_url"):
                if response.get(key):
                    return str(response[key])

        return str(response)

    def _bucket(self) -> Any:
        return self._client.storage.from_(self._config.bucket)

    def _with_retry(self, description: str, operation: Callable[[], T]) -> T:
        max_retries = 3
        retry_delay = 1.0
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                return operation()
            except Exception as exc:
                last_error = exc
                self._logger.warning(
                    "Supabase operation failed (%s/%s): %s",
                    attempt,
                    max_retries,
                    description,
                    exc_info=True,
                )

                if attempt < max_retries:
                    time.sleep(retry_delay * attempt)

        raise SupabaseClientError(
            f"Supabase operation failed after retries: {description}"
        ) from last_error

    def _invalidate_cache(self, path: str) -> None:
        parent, _ = self._split_parent(path)
        self._list_cache.pop(parent, None)
        self._exists_cache.pop(path, None)

    @staticmethod
    def _is_folder(item: dict[str, Any]) -> bool:
        metadata = item.get("metadata")
        item_id = item.get("id")
        name = str(item.get("name", ""))
        return metadata in (None, {}) and item_id in (None, "") and "." not in name

    @staticmethod
    def _split_parent(path: str) -> tuple[str, str]:
        normalized = path.strip("/")

        if "/" not in normalized:
            return "", normalized

        parent, file_name = normalized.rsplit("/", 1)
        return parent, file_name

    @staticmethod
    def _join_path(parent: str, name: str) -> str:
        return "/".join(part.strip("/") for part in (parent, name) if part.strip("/"))

    @staticmethod
    def _normalize_path(path: str) -> str:
        return path.replace("\\", "/").strip("/")
