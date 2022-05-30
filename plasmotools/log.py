import logging
import logging.handlers
import sys
from pathlib import Path

import coloredlogs

from plasmotools import settings


def setup() -> None:
    """Set up loggers."""
    format_string = "[%(asctime)s] [%(name)s/%(levelname)s]: %(message)s"
    log_format = logging.Formatter(format_string)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    # Set up file logging
    log_file = Path("logs/plasmo-tools.log")
    log_file.parent.mkdir(exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * (2 ** 20),
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)

    logging.getLogger("disnake").setLevel(logging.INFO)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    coloredlogs.DEFAULT_LEVEL_STYLES = {
        **coloredlogs.DEFAULT_LEVEL_STYLES,
        "trace": {"color": 246},
        "critical": {"background": "red"},
        "debug": coloredlogs.DEFAULT_LEVEL_STYLES["info"],
    }

    coloredlogs.DEFAULT_LOG_FORMAT = format_string

    coloredlogs.install(
        level=logging.DEBUG if settings.DEBUG else logging.INFO, stream=sys.stdout
    )
