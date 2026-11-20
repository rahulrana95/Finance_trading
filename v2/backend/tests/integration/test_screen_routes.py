"""The screener over HTTP: start a screen, then read the result."""

from tests.conftest import ClientFactory
from tests.support import FakePrices, closes

FLAT = closes([100.0] * 400)
FELL = closes([100.0] * 130 + [70.0] + [84.0] * 126 + [91.0] * 130 + [100.0] * 12 + [75.0])
ROW_KEYS = {
    "symbol", "name", "industry", "lastPrice", "priceAsOf", "yearHigh", "belowPct", "level",
    "ownFalls", "ownHigherAfterYear", "ownFallsWithYear", "worstDayPct", "confidence", "evidence",
}  # fmt: skip
ODDS_KEYS = {
    "level", "market", "events", "gain10In6mPct", "gain20In6mPct", "higherAfter6mPct",
    "eventsWithYear", "gain30In12mPct", "higherAfter12mPct", "fellFurtherPct",
}  # fmt: skip


def test_before_any_screen_there_is_nothing_to_show(make_client: ClientFactory):
    body = make_client(None).get("/api/screens/latest").json()
    assert body == {"running": False, "error": None, "screen": None}


def test_a_screen_runs_in_the_background_and_can_then_be_read(make_client: ClientFactory):
    client = make_client(None, FakePrices({"TITAN": FELL, "ICICIBANK": FELL}, default=FLAT))
    started = client.post("/api/screens")
    assert started.status_code == 202
    assert started.json() == {"running": True, "error": None, "screen": None}
    body = client.get("/api/screens/latest").json()
    assert (body["running"], body["error"]) == (False, None)
    screen = body["screen"]
    assert (screen["universe"], screen["priced"], screen["market"]) == (501, 501, "fine")
    assert [r["symbol"] for r in screen["rows"]] == ["ICICIBANK", "TITAN"]
    assert set(screen["rows"][0]) == ROW_KEYS
    assert len(screen["odds"]) == 12
    assert screen["rows"][0]["confidence"] == "low"
    assert set(screen["rows"][0]["evidence"][0]) == {"label", "met", "detail"}
    assert set(screen["odds"][0]) == ODDS_KEYS


def test_asking_again_while_one_is_running_does_not_start_another(make_client: ClientFactory):
    client = make_client(None, FakePrices(default=FLAT))
    assert client.app.state.screener.start() is True  # type: ignore[attr-defined]
    assert client.post("/api/screens").json()["running"] is True
    assert client.get("/api/screens/latest").json() == {
        "running": True,
        "error": None,
        "screen": None,
    }


def test_a_failed_screen_says_why(make_client: ClientFactory):
    client = make_client(None, FakePrices(default=None))
    client.post("/api/screens")
    body = client.get("/api/screens/latest").json()
    assert (body["running"], body["screen"]) == (False, None)
    assert body["error"] == "no prices for ^NSEI"
