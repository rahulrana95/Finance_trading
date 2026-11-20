from steady.adapters.seed import load_seed_stocks, load_universe


def test_the_seed_has_twelve_stocks_in_three_groups():  # D04
    stocks = load_seed_stocks()
    assert len(stocks) == 12
    by_status = {
        s: [x.symbol for x in stocks if x.status == s] for s in ("approved", "watching", "rejected")
    }
    assert by_status["approved"] == ["ICICIBANK", "NESTLEIND", "PIDILITIND", "TITAN", "MARICO"]
    assert len(by_status["watching"]) == 4
    assert len(by_status["rejected"]) == 3


def test_each_stock_has_five_years_and_business_notes():
    for stock in load_seed_stocks():
        assert [y.period for y in stock.financials] == [f"FY{y}" for y in range(2022, 2027)]
        assert stock.business.durability in ("Strong", "Moderate")
    icici = load_seed_stocks()[0]
    assert (icici.lot_size, icici.is_lender, icici.financials[-1].net_profit) == (700, True, 50147)


def test_the_screener_list_has_about_500_distinct_stocks():
    universe = load_universe()
    assert len(universe) == 501
    assert len({listing.symbol for listing in universe}) == 501
    assert all(listing.name and listing.industry for listing in universe)
