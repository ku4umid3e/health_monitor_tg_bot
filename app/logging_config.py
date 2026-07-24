"""Centralized logging configuration for the application."""
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path


def configure_logging():
    """Write logs to Docker stdout and to a rotating persistent file."""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M',
    )
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    log_path = Path(os.getenv("LOG_PATH", "logs/bot.log"))
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            RotatingFileHandler(
                log_path,
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
        )
    except OSError:
        # Stdout remains available through `docker logs`.
        pass

    for handler in handlers:
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Increase httpx logging level to avoid logging every HTTP request
    logging.getLogger("httpx").setLevel(logging.WARNING)


configure_logging()
