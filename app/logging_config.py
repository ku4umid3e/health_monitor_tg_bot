"""Centralized logging configuration for the application."""
import logging


def configure_logging():
    logging.basicConfig(
        datefmt='%Y-%m-%d %H:%M',
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        filename='bot.log'
    )

    # Increase httpx logging level to avoid logging every HTTP request
    logging.getLogger("httpx").setLevel(logging.WARNING)


configure_logging()
