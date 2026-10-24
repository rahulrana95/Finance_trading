import io
import json

import pytest
import structlog

from fintrade.core.errors import ConfigError
from fintrade.core.redaction import REDACTED
from fintrade.services.logging_setup import configure_logging


@pytest.fixture(autouse=True)
def _reset_structlog() -> None:
    structlog.reset_defaults()


def _lines(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines()]


def test_logs_json_with_level_timestamp_and_context() -> None:
    stream = io.StringIO()
    configure_logging("INFO", stream)
    structlog.get_logger().info("decision_made", position_id="P-1", lots=2)
    (line,) = _lines(stream)
    assert line["event"] == "decision_made"
    assert line["level"] == "info"
    assert line["position_id"] == "P-1"
    assert line["lots"] == 2
    assert "timestamp" in line


def test_secrets_never_reach_the_output() -> None:
    stream = io.StringIO()
    configure_logging("info", stream)
    structlog.get_logger().warning(
        "login", access_token="s3cr3t", headers={"Authorization": "Bearer s3cr3t"}
    )
    output = stream.getvalue()
    assert "s3cr3t" not in output
    (line,) = _lines(stream)
    assert line["access_token"] == REDACTED
    assert line["headers"] == {"Authorization": REDACTED}


def test_level_filter_drops_lower_levels() -> None:
    stream = io.StringIO()
    configure_logging("WARNING", stream)
    log = structlog.get_logger()
    log.info("hidden")
    log.error("shown")
    assert [line["event"] for line in _lines(stream)] == ["shown"]


def test_exception_info_is_rendered() -> None:
    stream = io.StringIO()
    configure_logging("ERROR", stream)
    try:
        raise ValueError("boom")  # noqa: TRY301 - exercising exc_info rendering
    except ValueError:
        structlog.get_logger().exception("failed")
    (line,) = _lines(stream)
    assert "ValueError: boom" in str(line["exception"])


def test_unknown_level_rejected() -> None:
    with pytest.raises(ConfigError, match="unknown log level"):
        configure_logging("LOUD", io.StringIO())
