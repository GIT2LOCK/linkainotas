"""Entry point for Lumina automation and fiscal document processing."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from lumina_bot.config import LoginCredentials
from lumina_bot.core.application import Application
from lumina_bot.core.logger import configure_logging, get_logger
from lumina_bot.core.processor import Processor
from lumina_bot.core.waits import wait_for_interval
from lumina_bot.exceptions import LuminaBotError
from lumina_bot.pages.login_page import LoginPage


def main() -> None:
    """Run Lumina login and then process fiscal documents from Supabase."""
    configure_logging()
    logger = get_logger(__name__)

    try:
        credentials = LoginCredentials.from_env()
        app = Application()

        logger.info("Launching Lumina...")
        main_window = app.launch_or_connect()

        logger.info("Waiting 10 seconds for Lumina to finish loading...")
        wait_for_interval(10)

        logger.info("Waiting for login screen...")
        login_page = LoginPage(main_window)

        logger.info("Login screen ready.")
        login_page.login(
            credentials.username,
            credentials.password,
        )
        logger.info("Login submitted successfully.")

        logger.info("Starting Supabase fiscal document processing...")
        summary = Processor().run()
        logger.info("Fiscal document processing finished: %s", summary)

    except LuminaBotError:
        logger.exception("Lumina automation failed.")
        raise
    except Exception:
        logger.exception("An unexpected error occurred.")
        raise


if __name__ == "__main__":
    main()
