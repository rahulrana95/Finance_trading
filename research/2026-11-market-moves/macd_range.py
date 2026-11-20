"""MACD asked the question it can answer: will Nifty stay inside a range, Wednesday to next Tuesday?

For each Wednesday entry: did price ever trade (touch) or close on the last day beyond a level
X% below / above entry? Split by MACD state and India VIX at Tuesday's close.
Train before 2017, test from 2017. Research only, index prices.
Run from a folder holding data/NIFTY.json and data/INDIAVIX.json (see fetch.sh).
"""
import json
import numpy as np, pandas as pd

def load(name):
    r = json.load(open(f"data/{name}.json"))["chart"]["result"][0]; q = r["indicators"]["quote"][0]
    return pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")},
                        index=pd.to_datetime(r["timestamp"], unit="s").tz_localize("UTC").tz_convert("Asia/Kolkata").normalize().tz_localize(None)).dropna()
N = load("NIFTY"); V = load("INDIAVIX").close.reindex(N.index).ffill().values
o, h, l, c, idx = N.open.values, N.high.values, N.low.values, N.close.values, N.index
cs = N.close; macd = cs.ewm(span=12, adjust=False).mean() - cs.ewm(span=26, adjust=False).mean()
M = macd.values; H = (macd - macd.ewm(span=9, adjust=False).mean()).values
rows = []
for i in range(60, len(N)):
    if idx[i].weekday() != 2: continue
    j = next((k for k in range(i + 1, min(i + 8, len(N))) if idx[k].weekday() == 1), None)
    if j is None or np.isnan(V[i - 1]): continue
    p = i - 1; e = o[i]
    rows.append(dict(date=idx[i], lo=(l[i:j + 1].min() / e - 1) * 100, hi=(h[i:j + 1].max() / e - 1) * 100, end=(c[j] / e - 1) * 100, vix=V[p],
                     macd="MACD above zero" if M[p] > 0 else "MACD below zero",
                     state=("above zero, bars rising" if H[p] > H[p - 1] else "above zero, bars falling") if M[p] > 0 else ("below zero, bars rising" if H[p] > H[p - 1] else "below zero, bars falling"),
                     vband="VIX under 13" if V[p] < 13 else "VIX 13-16" if V[p] < 16 else "VIX 16-20" if V[p] < 20 else "VIX 20+"))
D = pd.DataFrame(rows); D["test"] = D.date >= "2017-01-01"
def row(name, g):
    out = f"{name:44s}"
    for per in (False, True):
        x = g[g.test == per]
        if len(x) < 15: out += f"{'n=' + str(len(x)) + ' too few':^46s}"; continue
        out += f" n={len(x):3d}"
        for X in (2.0, 3.0):
            out += f" | {X:.0f}%: dn {100 * (x.lo <= -X).mean():4.1f} up {100 * (x.hi >= X).mean():4.1f}"
    return out
def show(title, groups):
    print(f"\n{title}   (% of weeks where price TOUCHED the level; dn = below entry, up = above entry)\n{'':44s}{'train (before 2017)':^46s}{'test (from 2017)':^46s}")
    for name, g in groups: print(row(name, g))
print(f"Nifty Wednesday open to next Tuesday close, {len(D)} weeks, {D.date.min().date()} to {D.date.max().date()}")
show("ALL WEEKS", [("every week", D)]); show("BY MACD", D.groupby("macd")); show("BY MACD AND BARS", D.groupby("state")); show("BY VIX", D.groupby("vband"))
D["combo"] = D.macd + ", " + np.where(D.vix < 16, "VIX under 16", np.where(D.vix < 20, "VIX 16-20", "VIX 20+")); show("MACD AND VIX", D.groupby("combo"))
print("\nSAFE-SIDE VIEW: level placed 1.0 x (VIX-implied one-week move) away, i.e. the distance adapts to VIX")
D["sd"] = D.vix / np.sqrt(52); 
for name, g in [("every week", D)] + list(D.groupby("macd")) + list(D.groupby("state")):
    out = f"{name:44s}"
    for per in (False, True):
        x = g[g.test == per]; out += f" n={len(x):3d} | touched: dn {100 * (x.lo <= -x.sd).mean():4.1f} up {100 * (x.hi >= x.sd).mean():4.1f} | closed beyond: dn {100 * (x.end <= -x.sd).mean():4.1f} up {100 * (x.end >= x.sd).mean():4.1f}  "
    print(out)
Y = D[D.date >= "2026-01-01"]; print(f"\n2026 ({len(Y)} weeks): touched -2% in {100 * (Y.lo <= -2).mean():.0f}%, +2% in {100 * (Y.hi >= 2).mean():.0f}%; -3% in {100 * (Y.lo <= -3).mean():.0f}%, +3% in {100 * (Y.hi >= 3).mean():.0f}%")
for name, g in Y.groupby("macd"): print(f"  {name}: n={len(g)}  -2% {100 * (g.lo <= -2).mean():.0f}%  +2% {100 * (g.hi >= 2).mean():.0f}%  -3% {100 * (g.lo <= -3).mean():.0f}%  +3% {100 * (g.hi >= 3).mean():.0f}%")
