import logging


def configure_logging():
    logging.basicConfig(
        datefmt='%Y-%m-%d %H:%M',
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        filename='bot.log'
    )

    # set higher logging level for httpx to avoid all GET and POST requests being logged
    logging.getLogger("httpx").setLevel(logging.WARNING)


configure_logging()
