"""Wednesday to next Tuesday, direction from the MACD histogram's slope.

Rule (owner's): histogram falling (green shrinking or red growing) -> price will end below entry;
histogram rising (red shrinking or green growing) -> price will end above entry.
Signal from Tuesday's close, entry Wednesday open, exit next Tuesday close. Research only.
Run from a folder holding data/NIFTY.json (see fetch.sh).
"""
import json
import numpy as np, pandas as pd

r = json.load(open("data/NIFTY.json"))["chart"]["result"][0]; q = r["indicators"]["quote"][0]
N = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")},
                 index=pd.to_datetime(r["timestamp"], unit="s").tz_localize("UTC").tz_convert("Asia/Kolkata").normalize().tz_localize(None)).dropna()
c = N.close; macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
hist = (macd - macd.ewm(span=9, adjust=False).mean()).values
o, cl, idx = N.open.values, c.values, N.index
rows = []
for i in range(40, len(N)):
    if idx[i].weekday() != 2: continue                       # Wednesday entries only
    j = next((k for k in range(i + 1, min(i + 8, len(N))) if idx[k].weekday() == 1), None)   # next Tuesday
    if j is None: continue
    h, hp = hist[i - 1], hist[i - 2]
    side = 1 if h > hp else -1
    state = ("green growing" if h > 0 else "red shrinking") if side > 0 else ("green shrinking" if h > 0 else "red growing")
    move = (cl[j] / o[i] - 1) * 100
    rows.append((idx[i].date(), idx[j].date(), state, "above" if side > 0 else "below", round(o[i]), round(cl[j]), round(move, 2), side * move > 0, side * move))
D = pd.DataFrame(rows, columns=["enter Wed", "exit Tue", "histogram", "call", "entry", "exit", "move %", "won", "signed"])
D["year"] = pd.to_datetime(D["enter Wed"]).dt.year
Y = D[D.year == 2026]
print(Y.drop(columns=["signed", "year"]).to_string(index=False))
def line(x): return f"{int(x.won.sum())} of {len(x)} = {100 * x.won.mean():.0f}%   avg win {x.signed[x.won].mean():+.2f}%  avg loss {x.signed[~x.won].mean():+.2f}%  avg {x.signed.mean():+.2f}%"
print("\n2026 all:", line(Y))
for s, g in Y.groupby("histogram"): print(f"  {s:16s}", line(g))
for cname, g in Y.groupby("call"): print(f"  call {cname:11s}", line(g))
up = (Y["move %"] > 0); print(f"  for comparison, 'always above' in 2026: {int(up.sum())} of {len(Y)} = {100 * up.mean():.0f}%")
print("\nBy year (win rate of the rule | 'always above'):")
for y, g in D[D.year >= 2015].groupby("year"): print(f"  {y}: {int(g.won.sum()):2d} of {len(g):2d} = {100 * g.won.mean():3.0f}%  |  {100 * (g['move %'] > 0).mean():3.0f}%")
A = D[D.year >= 2008]; print(f"\n2008-2026: {line(A)}  | always above {100 * (A['move %'] > 0).mean():.0f}%")
