"""Structured JSON logging with mandatory redaction (ENGINEERING.md section 10)."""

import logging
import sys
from collections.abc import MutableMapping
from datetime import datetime
from typing import Any, TextIO

import structlog

from fintrade.core.errors import ConfigError
from fintrade.core.redaction import redact_processor
from fintrade.core.timezone import IST

LOG_LEVELS: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def add_ist_timestamp(
    _logger: object, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Timezone-aware IST timestamp on every line (ENGINEERING.md section 10)."""
    event_dict["timestamp"] = datetime.now(tz=IST).isoformat()
    return event_dict


def configure_logging(level: str = "INFO", stream: TextIO = sys.stdout) -> None:
    """Configure structlog once at process start. Redaction always runs before rendering."""
    level_value = LOG_LEVELS.get(level.upper())
    if level_value is None:
        raise ConfigError(f"unknown log level: {level!r}")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            add_ist_timestamp,
            structlog.processors.format_exc_info,
            redact_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level_value),
        logger_factory=structlog.WriteLoggerFactory(file=stream),
        cache_logger_on_first_use=False,
    )
