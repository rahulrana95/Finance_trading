"""Structured JSON logging with mandatory redaction (ENGINEERING.md section 10)."""

import logging
import sys
from typing import TextIO

import structlog

from fintrade.core.errors import ConfigError
from fintrade.core.redaction import redact_processor

LOG_LEVELS: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def configure_logging(level: str = "INFO", stream: TextIO = sys.stdout) -> None:
    """Configure structlog once at process start. Redaction always runs before rendering."""
    level_value = LOG_LEVELS.get(level.upper())
    if level_value is None:
        raise ConfigError(f"unknown log level: {level!r}")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            structlog.processors.format_exc_info,
            redact_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level_value),
        logger_factory=structlog.WriteLoggerFactory(file=stream),
        cache_logger_on_first_use=False,
    )
