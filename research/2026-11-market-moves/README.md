# Market-move research, November 2026 (T4.8)

Exploratory scripts, **not** production code: no tests, not imported by `backend/`, and
nothing here places or suggests orders. Results are logged in `BACKTEST_RESULTS.md`.

Option prices in `eng.py` and `algo_study.py` are **modelled** from India VIX with an
assumed skew. They are not real quotes.

Run from this folder (needs `pandas`, `scikit-learn`, `lightgbm`):

    ./fetch.sh                 # public daily data into ./data
    python3 macd_study.py nsei.json vix.json   # does MACD pick the safe side?
    python3 move_study.py      # what predicts direction and size of the daily move
    python3 algo_study.py      # structures, stop types, entry day (flat-vol prices)
    python3 feat.py            # feature table -> F.pkl, T.pkl
    python3 it1.py             # feature scan, first models (train / validation)
    python3 it2.py             # deterministic calm score -> calm.pkl
    python3 it3.py             # calm gate on modelled trades
    python3 it4.py             # regime exit, score-based sizing (no gain)
    python3 final.py           # frozen rule on the 2022-2026 holdout (run once)
    python3 xmkt.py            # same signal on S&P 500 and Nasdaq 100
    python3 combos.py          # structure / width / skew / ratio / management comparison
    python3 vixmacd.py         # VIX and MACD combined as a filter
    python3 dir_grid.py        # 109 indicator settings tested for direction
    python3 causes.py          # why Nifty moves more than 0.5% in a day (uses fomc_dates.json)
    python3 probmodel.py       # prototype touch-probability model, fitted 2008-2016, checked 2017-2026
    python3 macd_tf.py         # MACD timeframe and setting comparison (hourly needs nsei_1h.json)
    python3 patterns.py        # ten chart patterns and their pairs on daily, 4-hour and 1-hour bars
    python3 search80.py        # exhaustive search for an 80% direction signal, three-way split
    python3 monday.py          # Monday open as the line: MACD + RSI direction, at-the-money hedged spread
    python3 rel90.py           # reversal and breakout signals with target / stop outcomes
    python3 stock_study.py ICICI   # same search on one stock (needs data/ICICI.json from Yahoo ICICIBANK.NS)
    python3 dips.py ICICI 2016-01-01 126   # falls of 5-30% from the 6-month high and time to recover
    python3 dipalgo.py         # buy-the-dip rule across ~49 large and ~16 collapsed stocks (needs stocks/*.json from Yahoo)
    python3 ladder.py          # dip ladder in ICICI Bank futures with margin, Rs 20 L capital
    python3 ladder_fut.py      # same ladder with a fixed 700-unit lot in every year
    python3 combo.py           # shares + futures ladder, settings re-chosen yearly from the prior 1 or 2 years
    python3 live_combo.py      # same, settings re-chosen weekly or monthly, orders triggered inside the day, 10 years
    python3 screen.py          # which large stocks suited the rule, and whether past fit carried over (needs stocks/*.json)
    python3 fetch500.py; python3 screen300.py   # top 300 by traded value: recovery from falls, shortlist (needs lists/n500.csv)

Split used: train to 2016-12, validation 2017-2021, holdout 2022-01 to 2026-10.
The holdout has now been looked at; it can no longer count as unseen data.
