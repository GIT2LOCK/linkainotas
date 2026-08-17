"""Application lifecycle management for Lumina."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from pywinauto import Desktop
from pywinauto.application import Application as PywinautoApplication
from pywinauto.application import WindowSpecification

from lumina_bot.config import AppConfig, DEFAULT_CONFIG
from lumina_bot.core.logger import get_logger
from lumina_bot.exceptions import (
    ApplicationConnectionError,
    ApplicationStartError,
    ConfigurationError,
    WindowNotFound,
)

SHELL_LAUNCHER_SUFFIXES = {".appref-ms", ".lnk", ".url"}
LOGIN_CONTROL_IDS = frozenset({"txtLogin", "txtPassword", "btnOk"})


class Application:
    """Starts, connects to, and exposes the main Lumina window."""

    def __init__(self, config: AppConfig = DEFAULT_CONFIG) -> None:
        self._config = config
        self.app: PywinautoApplication | None = None
        self.main_window: Any = None
        self._logger = get_logger(self.__class__.__name__)

    def launch_or_connect(self) -> Any:
        """Attach to a running Lumina instance or start a new one."""
        try:
            return self.connect()
        except ApplicationConnectionError:
            self._logger.info("No running Lumina instance found.")
            return self.start()

    def start(self) -> Any:
        """Start Lumina from the configured executable or shell launcher."""
        launcher_path = self._config.executable_path
        self._validate_launcher_path(launcher_path)

        self._logger.info("Opening Lumina from %s...", launcher_path)

        try:
            if self._is_shell_launcher(launcher_path):
                self._start_with_windows_shell(launcher_path)
                # Damos um fÃ´lego inicial para o ClickOnce processar a abertura
                time.sleep(5)
            else:
                self.app = PywinautoApplication(backend=self._config.backend).start(
                    str(launcher_path),
                    timeout=self._config.start_timeout,
                )
                print("=" * 80)
                print(f"Lumina iniciado! PID do processo: {self.app.process}")
                print("=" * 80)

        except Exception as exc:
            raise ApplicationStartError(
                f"Could not start Lumina from '{launcher_path}'."
            ) from exc

        self.main_window = self._locate_main_window(self._config.window_timeout)
        self._connect_to_window(self.main_window)
        return self.get_main_window()

    def connect(self) -> Any:
        """Connect to Lumina when its main window is already open."""
        self._logger.info("Connecting to existing Lumina process...")

        try:
            self.main_window = self._locate_main_window(self._config.connect_timeout)
            self._connect_to_window(self.main_window)
            return self.get_main_window()
        except WindowNotFound:
            raise ApplicationConnectionError("No running Lumina window found.")
        except Exception as exc:
            raise ApplicationConnectionError(
                "Could not connect to the running Lumina instance."
            ) from exc

    def get_main_window(self) -> WindowSpecification:
        """Return the cached main window or raise a framework exception."""
        if self.main_window is None:
            raise WindowNotFound(
                "Main window is not available. Call launch_or_connect() first."
            )

        # Transforma a janela fÃ­sica de volta em uma WindowSpecification
        # usando o Handle para liberar o mÃ©todo .child_window()
        handle = getattr(self.main_window, "handle", None)
        if not handle and hasattr(self.main_window, "wrapper_object"):
            handle = self.main_window.wrapper_object().handle

        return self.app.window(handle=handle)

    def _locate_main_window(self, timeout: float) -> Any:
        """Find and cache the Lumina main window."""
        desktop = Desktop(backend=self._config.backend)
        self._logger.info("Waiting %s seconds for Lumina...", timeout)

        end = time.time() + timeout

        target_pid = self.app.process if self.app else None

        while time.time() < end:
            windows = desktop.windows(visible_only=True)

            for win in windows:
                try:
                    title = win.window_text() or ""
                    class_name = win.class_name() or ""
                    pid = win.process_id()

                    # 1. IGNORAR NAVEGADORES E VSCODE
                    if "chrome" in class_name.lower() or "msedge" in class_name.lower() or "code" in class_name.lower():
                        continue

                    is_process_window = bool(target_pid and pid == target_pid)
                    is_named_lumina_window = "lumina" in title.lower()
                    is_login_window = self._has_login_controls(win)

                    # 2. PROCURAR PELO TÃTULO OCULTO DO LUMINA ('Form1')
                    if not is_login_window:
                        if is_process_window or is_named_lumina_window:
                            self._logger.debug(
                                "Ignoring Lumina bootstrap window '%s' while "
                                "waiting for login controls...",
                                title,
                            )
                        continue

                    print("=" * 80)
                    print(">>> JANELA DO LUMINA ENCONTRADA COM SUCESSO <<<")
                    print(f"PID: {pid} | TÃ­tulo: '{title}' | Classe: {class_name}")
                    print("=" * 80)

                    wrapper = win if not hasattr(win, "wrapper_object") else win.wrapper_object()

                    # Retorna imediatamente a janela renderizada
                    return wrapper

                except Exception as exc:
                    print(f"Aviso: Erro ao tentar processar a janela PID {win.process_id()}: {exc}")
                    continue

            time.sleep(0.5)

        # Se falhar, imprime a lista para continuarmos monitorando
        print("\n" + "!" * 80)
        print("FALHA AO ENCONTRAR O LUMINA. LISTANDO TODAS AS JANELAS VISÃVEIS NO MOMENTO:")
        for w in desktop.windows(visible_only=True):
            try:
                print(f"PID: {w.process_id()} | TÃ­tulo: '{w.window_text()}' | Classe: '{w.class_name()}'")
            except Exception:
                pass
        print("!" * 80 + "\n")

        raise WindowNotFound(
            "NÃ£o foi possÃ­vel localizar a janela do Lumina."
        )

    @staticmethod
    def _has_login_controls(window: Any) -> bool:
        """Return True when a visible window exposes the Lumina login form."""
        try:
            control_ids = {
                str(getattr(control.element_info, "automation_id", "") or "")
                for control in window.descendants()
            }
            return LOGIN_CONTROL_IDS.issubset(control_ids)
        except Exception:
            return False

    @staticmethod
    def _validate_launcher_path(launcher_path: Path) -> None:
        if not launcher_path.is_file():
            raise ConfigurationError(
                "Lumina launcher was not found. Set LUMINA_EXECUTABLE_PATH "
                f"or update config.py. Current value: '{launcher_path}'."
            )

    @staticmethod
    def _is_shell_launcher(launcher_path: Path) -> bool:
        return launcher_path.suffix.lower() in SHELL_LAUNCHER_SUFFIXES

    def _start_with_windows_shell(self, launcher_path: Path) -> None:
        """Open ClickOnce and shortcut launchers through Windows Shell."""
        self._logger.info("Opening Lumina through Windows Shell launcher...")
        os.startfile(str(launcher_path))

    def _connect_to_window(self, window_spec: Any) -> None:
        """Attach pywinauto Application to an already located window by its Handle."""
        handle = getattr(window_spec, "handle", None)
        if not handle and hasattr(window_spec, "wrapper_object"):
            handle = window_spec.wrapper_object().handle

        self.app = PywinautoApplication(backend=self._config.backend).connect(
            handle=handle
        )
