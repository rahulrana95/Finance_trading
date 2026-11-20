"""The public price adapter, with the network replaced by a fake transport (A01-A04)."""

from datetime import UTC, date, datetime
from typing import Any

import httpx2 as httpx
import pytest

from steady.adapters.yahoo import YahooPriceSource, new_client, parse_chart, ticker
from steady.constants import YAHOO_USER_AGENT
from steady.ports import PriceSourceError

NOW = datetime(2026, 11, 17, 10, 0, tzinfo=UTC)
# 2026-11-16 and 2026-11-17 at 09:15 India time, then a repeat of the 17th at the close.
STAMPS = [1794800700, 1794887100, 1794909600]


def chart(closes: list[float | None], stamps: list[int] | None = None) -> dict[str, Any]:
    quote = {"close": closes}
    return {
        "chart": {
            "result": [
                {"timestamp": stamps or STAMPS[: len(closes)], "indicators": {"quote": [quote]}}
            ]
        }
    }


def source(handler: Any) -> YahooPriceSource:
    return YahooPriceSource(httpx.Client(transport=httpx.MockTransport(handler)), lambda: NOW)


def test_parses_closes_in_india_dates_and_keeps_the_last_of_a_repeated_day():  # A01
    result = parse_chart(chart([100.0, 101.0, 102.5]))
    assert [(c.day, c.close) for c in result] == [
        (date(2026, 11, 16), 100.0),
        (date(2026, 11, 17), 102.5),
    ]


def test_skips_empty_rows():
    assert [c.close for c in parse_chart(chart([None, 101.0]))] == [101.0]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"chart": {"result": []}},
        {"chart": {"result": None}},
        chart([1.0], stamps=[1, 2]),
        chart([None]),
    ],
)
def test_malformed_or_empty_responses_are_errors(payload: dict[str, Any]):  # A04
    with pytest.raises(PriceSourceError):
        parse_chart(payload)


def test_fetches_the_symbol_on_the_nse_with_the_right_window():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=chart([100.0, 101.0]))

    assert len(source(handler).daily_closes("TITAN")) == 2
    url = seen[0].url
    assert url.path.endswith("/TITAN.NS")
    assert url.params["interval"] == "1d"
    assert int(url.params["period2"]) > int(NOW.timestamp())


def test_retries_once_after_a_network_error():  # A02
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("down")
        return httpx.Response(200, json=chart([100.0]))

    assert len(source(handler).daily_closes("TITAN")) == 1
    assert attempts == 2


def test_gives_up_after_two_failures():  # A03
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503)

    with pytest.raises(PriceSourceError, match="Could not fetch prices for TITAN"):
        source(handler).daily_closes("TITAN")
    assert attempts == 2


def test_a_reply_that_is_not_json_is_an_error():
    with pytest.raises(PriceSourceError):
        source(lambda request: httpx.Response(200, text="<html>blocked</html>")).daily_closes(
            "TITAN"
        )


def test_the_real_client_identifies_itself_and_has_a_timeout():
    client = new_client()
    assert client.headers["user-agent"] == YAHOO_USER_AGENT
    assert client.timeout.read == 15.0


def test_it_is_labelled_unofficial():
    assert YahooPriceSource.official is False
    assert "unofficial" in YahooPriceSource.name


def test_an_index_is_asked_for_without_the_share_suffix():
    assert ticker("TITAN") == "TITAN.NS"
    assert ticker("^NSEI") == "^NSEI"
