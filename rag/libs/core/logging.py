"""Structured logging configuration for the RAG system.

Uses stdlib logging with JSON-like structured format for production
and human-readable format for development. Configured via LOG_LEVEL env var.
"""

import logging
import sys
from typing import Literal

from libs.core.settings import get_settings


def setup_logging(
    service_name: str = "rag",
    level: str | None = None,
    fmt: Literal["json", "text"] = "text",
) -> logging.Logger:
    """Configure root logger and return a named logger for the service.

    Args:
        service_name: Logger name prefix (e.g. 'rag.api', 'rag.worker').
        level: Override log level. Defaults to settings.api.log_level.
        fmt: 'json' for structured production logs, 'text' for dev.
    """
    settings = get_settings()
    log_level = (level or settings.api.log_level).upper()

    if fmt == "json":
        formatter = logging.Formatter(
            '{"time":"%(asctime)s","level":"%(levelname)s",'
            '"logger":"%(name)s","message":"%(message)s"}',
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level)
    # Avoid duplicate handlers on repeated calls
    if not root.handlers:
        root.addHandler(handler)

    # Quiet noisy third-party loggers
    for noisy in ("httpcore", "httpx", "urllib3", "asyncio", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logger = logging.getLogger(service_name)
    logger.setLevel(log_level)
    return logger
