from collections.abc import Sequence
from datetime import date

import httpx
import pytest

from fintrade.adapters.nse.bhavcopy import (
    MAX_ATTEMPTS,
    REQUEST_HEADERS,
    BhavcopyFetcher,
    RetryableHttpError,
)
from fintrade.core.errors import DataError
from tests.support.http import ScriptedTransport, Step, make_zip

DAY = date(2026, 10, 23)


def _fetcher(steps: Sequence[Step]) -> tuple[BhavcopyFetcher, ScriptedTransport, list[float]]:
    transport = ScriptedTransport(steps)
    sleeps: list[float] = []
    fetcher = BhavcopyFetcher(httpx.Client(transport=transport), sleep=sleeps.append)
    return fetcher, transport, sleeps


def test_ok_returns_content_and_sends_browser_headers() -> None:
    content = make_zip()
    fetcher, transport, sleeps = _fetcher([httpx.Response(200, content=content)])
    result = fetcher.fetch(DAY)
    assert result.content == content
    assert result.day == DAY
    assert result.url.endswith("20261023_F_0000.csv.zip")
    assert transport.requests[0].headers["User-Agent"] == REQUEST_HEADERS["User-Agent"]
    assert sleeps == []


def test_404_means_no_file_that_day() -> None:
    fetcher, _, _ = _fetcher([httpx.Response(404, text="<html>not found</html>")])
    assert fetcher.fetch(DAY).content is None


@pytest.mark.parametrize("status", [429, 500, 503])
def test_retryable_status_then_success(status: int) -> None:
    content = make_zip()
    fetcher, transport, sleeps = _fetcher(
        [httpx.Response(status), httpx.Response(200, content=content)]
    )
    assert fetcher.fetch(DAY).content == content
    assert len(transport.requests) == 2
    assert len(sleeps) == 1


def test_retryable_status_gives_up_after_max_attempts() -> None:
    fetcher, transport, sleeps = _fetcher([httpx.Response(503)] * MAX_ATTEMPTS)
    with pytest.raises(RetryableHttpError, match="HTTP 503"):
        fetcher.fetch(DAY)
    assert len(transport.requests) == MAX_ATTEMPTS
    assert len(sleeps) == MAX_ATTEMPTS - 1


def test_network_error_then_success() -> None:
    content = make_zip()
    fetcher, _, _ = _fetcher([httpx.ConnectError("reset"), httpx.Response(200, content=content)])
    assert fetcher.fetch(DAY).content == content


def test_network_error_every_time_becomes_data_error() -> None:
    fetcher, transport, _ = _fetcher([httpx.ReadTimeout("slow")] * MAX_ATTEMPTS)
    with pytest.raises(DataError, match="network error"):
        fetcher.fetch(DAY)
    assert len(transport.requests) == MAX_ATTEMPTS


@pytest.mark.parametrize("status", [301, 401, 403])
def test_unexpected_status_fails_without_retry(status: int) -> None:
    fetcher, transport, _ = _fetcher([httpx.Response(status)])
    with pytest.raises(DataError, match=f"unexpected HTTP {status}"):
        fetcher.fetch(DAY)
    assert len(transport.requests) == 1


def test_html_page_with_200_rejected() -> None:
    fetcher, _, _ = _fetcher([httpx.Response(200, text="<html>blocked</html>")])
    with pytest.raises(DataError, match="not a zip"):
        fetcher.fetch(DAY)
