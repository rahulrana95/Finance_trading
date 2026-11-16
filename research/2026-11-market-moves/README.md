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

Split used: train to 2016-12, validation 2017-2021, holdout 2022-01 to 2026-10.
The holdout has now been looked at; it can no longer count as unseen data.
