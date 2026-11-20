"""GET /api/stocks and GET /api/stocks/{symbol}, through the real app (H05-H07, H12)."""

from tests.conftest import ClientFactory
from tests.support import FakePrices, closes

STOCK_FIELDS = {
    "symbol",
    "name",
    "industry",
    "status",
    "lastPrice",
    "priceAsOf",
    "priceSource",
    "referenceHigh",
    "belowHighPct",
    "zone",
    "lotSize",
    "isLender",
    "falls10",
    "recovered12mPct",
    "longestRecoveryDays",
    "maxDrawdownPct",
    "historyYears",
    "financials",
    "debtToEquity",
    "promoterPledgePct",
    "business",
    "scores",
    "needs",
    "history",
}


def test_lists_all_twelve_stocks_in_the_shape_the_interface_expects(make_client: ClientFactory):
    response = make_client(None).get("/api/stocks")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 12
    assert set(rows[0]) == STOCK_FIELDS
    assert set(rows[0]["scores"]) == {"stability", "financial", "dataQuality", "evidence"}
    assert set(rows[0]["business"]) == {"durability", "aiImpact", "watch", "revenueLabel"}
    assert rows[0]["financials"][0] == {"period": "FY2022", "revenue": 47467, "netProfit": 23339}


def test_one_stock_has_its_computed_figures(make_client: ClientFactory):
    stock = make_client(None).get("/api/stocks/NESTLEIND").json()
    assert stock["name"] == "Nestle India"
    assert (stock["lastPrice"], stock["referenceHigh"], stock["belowHighPct"], stock["zone"]) == (
        85.0,
        100.0,
        15.0,
        1,
    )
    assert stock["priceSource"] == "Fake prices"
    assert "Futures lot size" in stock["needs"]


def test_the_symbol_is_not_case_sensitive(make_client: ClientFactory):
    assert make_client(None).get("/api/stocks/titan").json()["symbol"] == "TITAN"


def test_an_unknown_stock_is_404(make_client: ClientFactory):
    response = make_client(None).get("/api/stocks/NOPE")
    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown stock NOPE"}


def test_a_stock_without_prices_is_still_listed_and_says_what_it_needs(make_client: ClientFactory):
    client = make_client(None, FakePrices({"TITAN": None}, default=closes([100.0] * 80)))
    titan = client.get("/api/stocks/TITAN").json()
    assert titan["lastPrice"] == 0
    assert titan["priceAsOf"] == ""
    assert titan["needs"][0] == "Price history (the price source did not answer)"
    assert len(client.get("/api/stocks").json()) == 12


def test_the_stock_routes_are_read_only(make_client: ClientFactory):
    client = make_client(None)
    for response in (
        client.post("/api/stocks"),
        client.patch("/api/stocks/TITAN"),
        client.delete("/api/stocks/TITAN"),
    ):
        assert response.status_code == 404


def test_the_routes_are_in_the_published_schema(make_client: ClientFactory):
    paths = make_client(None).get("/api/openapi.json").json()["paths"]
    assert list(paths) == [
        "/api/health",
        "/api/stocks",
        "/api/stocks/{symbol}",
        "/api/runs",
        "/api/runs/{run_id}",
        "/api/recommendations",
        "/api/screens/latest",
        "/api/screens",
    ]
