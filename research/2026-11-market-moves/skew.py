"""Win bigger than you lose: Nifty trades with a fixed stop and a larger target or a trailing stop.

Question: does any simple entry give 50-60% wins AND wins larger than losses, in both periods?
Research only. Index prices as a stand-in for the future, 0.05% cost per trade. Signals use the
previous close, entry at the next open. If stop and target are both inside one day's range the
stop is assumed to come first. R = the amount risked per trade (entry to stop).
Run from a folder holding data/NIFTY.json (see fetch.sh).
"""
import json
import numpy as np, pandas as pd

r = json.load(open("data/NIFTY.json"))["chart"]["result"][0]; q = r["indicators"]["quote"][0]
N = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")}, index=pd.to_datetime(r["timestamp"], unit="s")).dropna()
o, h, l, c = (N[k].values for k in ("open", "high", "low", "close")); n = len(N)
cs = N.close
macd = (cs.ewm(span=12, adjust=False).mean() - cs.ewm(span=26, adjust=False).mean()); sig = macd.ewm(span=9, adjust=False).mean()
d = cs.diff(); rsi = (100 - 100 / (1 + d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean() / (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean())).values
tr = np.maximum(h - l, np.maximum(abs(h - np.r_[c[:1], c[:-1]]), abs(l - np.r_[c[:1], c[:-1]])))
atr = pd.Series(tr).ewm(alpha=1/14, adjust=False).mean().values
ma50, ma200 = cs.rolling(50).mean().values, cs.rolling(200).mean().values
hi20, lo20 = cs.rolling(20).max().shift(1).values, cs.rolling(20).min().shift(1).values
M, S = macd.values, sig.values
COST = 0.0005

ENTRIES = {  # value at close p -> +1 long, -1 short, 0 nothing
    "always long": lambda p: 1,
    "MACD above zero: long, else short": lambda p: 1 if M[p] > 0 else -1,
    "MACD above zero: long only": lambda p: 1 if M[p] > 0 else 0,
    "MACD crosses its signal line": lambda p: 1 if (M[p] > S[p] and M[p-1] <= S[p-1]) else -1 if (M[p] < S[p] and M[p-1] >= S[p-1]) else 0,
    "MACD and RSI agree": lambda p: 1 if (M[p] > S[p] and rsi[p] > 50) else -1 if (M[p] < S[p] and rsi[p] < 50) else 0,
    "20-day high / low breakout": lambda p: 1 if c[p] > hi20[p] else -1 if c[p] < lo20[p] else 0,
    "breakout up, in uptrend (50 > 200 avg)": lambda p: 1 if (c[p] > hi20[p] and ma50[p] > ma200[p]) else 0,
    "pullback in uptrend (RSI < 40, 50 > 200)": lambda p: 1 if (rsi[p] < 40 and ma50[p] > ma200[p]) else 0,
}
EXITS = {"stop 1 ATR, target 1.5 ATR": (1, 1.5, None), "stop 1 ATR, target 2 ATR": (1, 2, None), "stop 1 ATR, target 3 ATR": (1, 3, None),
         "stop 1.5 ATR, trail 2.5 ATR": (1.5, None, 2.5)}
MAXHOLD = 15

def trade(i, s, stop_k, tgt_k, trail_k):
    """Result in R of a trade entered at open of day i."""
    e = o[i]; a = atr[i - 1]; risk = stop_k * a; stop = e - s * risk; tgt = e + s * tgt_k * a if tgt_k else None; best = e
    for j in range(i, min(i + MAXHOLD, n)):
        lo_, hi_ = (l[j], h[j]) if s > 0 else (-h[j], -l[j]); st = s * stop
        if lo_ <= st: x = stop; break
        if tgt is not None and hi_ >= s * tgt: x = tgt; break
        if trail_k:
            best = max(best, h[j]) if s > 0 else min(best, l[j]); new = best - s * trail_k * a
            stop = max(stop, new) if s > 0 else min(stop, new)
    else:
        j = min(i + MAXHOLD, n) - 1; x = c[j]
    return (s * (x - e) - COST * e) / risk, j

SPLIT = np.searchsorted(N.index, pd.Timestamp("2017-01-01")); rows = []
for en, f in ENTRIES.items():
    for ex, (sk, tk, trk) in EXITS.items():
        res = []; i = 210
        while i < n - 1:
            s = f(i - 1)
            if s == 0: i += 1; continue
            R, j = trade(i, s, sk, tk, trk); res.append((i, R)); i = j + 1          # one trade at a time
        for per, lo, hi in (("train", 0, SPLIT), ("test", SPLIT, n)):
            x = np.array([R for i, R in res if lo <= i < hi]); yrs = (N.index[min(hi, n) - 1] - N.index[max(lo, 210)]).days / 365.25
            if len(x) < 10: continue
            w, ls = x[x > 0], x[x <= 0]; eq = np.cumsum(x)
            rows.append((en, ex, per, len(x), len(x) / yrs, 100 * len(w) / len(x), w.mean() / -ls.mean(), x.mean(), x.sum() / yrs, (eq - np.maximum.accumulate(eq)).min()))
T = pd.DataFrame(rows, columns=["entry", "exit", "period", "n", "per yr", "win %", "win/loss size", "avg R", "R per yr", "max DD R"])
P = T.pivot(index=["entry", "exit"], columns="period")[["per yr", "win %", "win/loss size", "avg R", "R per yr", "max DD R"]].reindex(columns=["train", "test"], level=1)
pd.set_option("display.width", 250); print(f"Nifty {N.index[0].date()} to {N.index[-1].date()}; train before 2017, test from 2017; R per yr ~ % per year at 1% risk per trade\n")
print(P.round(2).to_string())
both = P[(P[("avg R", "train")] > 0) & (P[("avg R", "test")] > 0)]
print(f"\nPositive in both periods: {len(both)} of {len(P)}"); print(both[["win %", "win/loss size", "R per yr", "max DD R"]].round(2).to_string())
