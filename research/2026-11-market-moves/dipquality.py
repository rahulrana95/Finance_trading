"""Owner's idea: a strong stock that has fallen 25%+ is a very good buy for the next 6-12 months.

Event: the first close X% or more below the stock's 1-year high (a new event only after the
stock has closed back within 10% of that high, or a year has passed). Buy at that close.
Outcome over the next 126 and 252 trading days, closing prices, dividends included.
'Strong' is judged only from what was known on the event day:
  big      : in the top 100 by rupees traded over the previous year
  grower   : price at the 1-year high was above its level 3 years earlier by 12%+ a year
  healer   : every earlier 20% fall (at least one) was back at its high within 2 years
Universe: today's Nifty 500 members, so companies that failed and left the index are missing;
real results would be worse. Research only.
Run from a folder holding n500/*.json, lists/n500.csv and data/NIFTY.json.
"""
import csv, json, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

def load(path):
    r = json.load(open(path))["chart"]["result"][0]; q = r["indicators"]["quote"][0]
    adj = r["indicators"].get("adjclose", [{}])[0].get("adjclose") or q["close"]
    d = pd.DataFrame({"c": adj, "raw": q["close"], "v": q["volume"]}, index=pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("Asia/Kolkata").normalize().tz_localize(None)).dropna()
    return d[~d.index.duplicated()]
nf = load("data/NIFTY.json").c; nf_depth = (1 - nf / nf.rolling(252, min_periods=120).max()) * 100
S = {}
for r in csv.DictReader(open("lists/n500.csv")):
    try: d = load(f"n500/{r['Symbol'].strip()}.json")
    except Exception: continue
    if len(d) > 600: S[r["Symbol"].strip()] = (r["Company Name"].strip(), d)
tv = pd.DataFrame({s: (d.raw * d.v).rolling(250, min_periods=120).mean() for s, (_, d) in S.items()}); rank = tv.rank(axis=1, ascending=False)
ev = []
for s, (name, d) in S.items():
    c = d.c.values; n = len(c); idx = d.index; hi = d.c.rolling(252, min_periods=120).max().values
    falls = []                                               # history of 20% falls: (start, recovered index or None, peak)
    open_fall = None; armed = {X: True for X in (15, 20, 25, 30, 40)}; last = {X: -999 for X in armed}
    for t in range(252, n):
        depth = (1 - c[t] / hi[t]) * 100
        if open_fall is None and depth >= 20: open_fall = (t, hi[t])
        elif open_fall is not None and c[t] >= open_fall[1]: falls.append((open_fall[0], t)); open_fall = None
        for X in armed:
            if depth <= 10 or t - last[X] > 252: armed[X] = True
            if armed[X] and depth >= X:
                armed[X] = False; last[X] = t
                if t + 126 >= n: continue
                done = [f for f in falls]; healer = len(done) >= 1 and all(b - a <= 504 for a, b in done) and (open_fall is None or open_fall[0] == t or t - open_fall[0] <= 504)
                pk = int(np.argmax(c[max(0, t - 252):t + 1])) + max(0, t - 252); grower = pk >= 756 and (c[pk] / c[pk - 756]) ** (1 / 3) - 1 >= 0.12
                f6 = c[t + 1:t + 127] / c[t]; f12 = c[t + 1:t + 253] / c[t] if t + 252 < n else None
                ev.append(dict(sym=s, name=name, date=idx[t], X=X, depth=depth, big=rank[s].get(idx[t], 999) <= 100, grower=grower, healer=healer, mkt=nf_depth.get(idx[t], np.nan),
                               max6=(f6.max() - 1) * 100, min6=(f6.min() - 1) * 100, end6=(f6[-1] - 1) * 100,
                               max12=(f12.max() - 1) * 100 if f12 is not None else np.nan, min12=(f12.min() - 1) * 100 if f12 is not None else np.nan, end12=(f12[-1] - 1) * 100 if f12 is not None else np.nan))
E = pd.DataFrame(ev); E["strong"] = E.big & E.grower & E.healer; E["mktfall"] = E.mkt >= 10
def line(g):
    h = g.dropna(subset=["end12"])
    return (f"n={len(g):4d} | 6 months: +10% reached {100 * (g.max6 >= 10).mean():3.0f}%  +20% {100 * (g.max6 >= 20).mean():3.0f}%  +30% {100 * (g.max6 >= 30).mean():3.0f}%  ended up {100 * (g.end6 > 0).mean():3.0f}%  avg {g.end6.mean():+5.1f}%  fell 20% more {100 * (g.min6 <= -20).mean():3.0f}%"
            f" | 12 months (n={len(h)}): +30% reached {100 * (h.max12 >= 30).mean():3.0f}%  ended up {100 * (h.end12 > 0).mean():3.0f}%  avg {h.end12.mean():+5.1f}%  worst tenth {h.end12.quantile(.1):+5.1f}%  fell 20% more {100 * (h.min12 <= -20).mean():3.0f}%" if len(g) >= 8 else f"n={len(g)} too few")
print(f"{len(S)} stocks, events from {E.date.min().date()} to {E.date.max().date()}")
A = E[E.X == 25]
print("\nA. Fell 25% from the 1-year high: all stocks, then by strength"); 
for nm, g in (("all stocks", A), ("big (top 100 by trading)", A[A.big]), ("grower (12%+ a year before)", A[A.grower]), ("healer (always recovered)", A[A.healer]), ("STRONG = big + grower + healer", A[A.strong]), ("not strong", A[~A.strong])): print(f"  {nm:30s} {line(g)}")
print("\nB. STRONG stocks by how far they fell")
for X in (15, 20, 25, 30, 40): print(f"  fell {X}%+ {'':21s} {line(E[(E.X == X) & E.strong])}")
print("\nC. STRONG stocks, fell 25%: does it matter whether the whole market fell too?")
g = A[A.strong]; print(f"  market also 10%+ down {'':8s} {line(g[g.mktfall])}"); print(f"  market fine, stock fell alone  {line(g[~g.mktfall])}")
print("\nD. STRONG stocks, fell 25%: by period")
for nm, lo, hi in (("2015-2020", 2015, 2020), ("2021-2026", 2021, 2026)): print(f"  {nm:30s} {line(g[(g.date.dt.year >= lo) & (g.date.dt.year <= hi)])}")
print("   without March 2020:", line(g[~((g.date >= "2020-02-15") & (g.date <= "2020-04-30"))]))
print("\nE. For comparison: buying a STRONG stock on any ordinary day (every 20th day, not after a fall)")
base = []
for s, (name, d) in S.items():
    c = d.c.values
    for t in range(1000, len(c) - 253, 20): base.append(dict(big=rank[s].iloc[t] <= 100, max6=(c[t + 1:t + 127].max() / c[t] - 1) * 100, end6=(c[t + 126] / c[t] - 1) * 100, max12=(c[t + 1:t + 253].max() / c[t] - 1) * 100, end12=(c[t + 252] / c[t] - 1) * 100, min12=(c[t + 1:t + 253].min() / c[t] - 1) * 100))
B = pd.DataFrame(base); b = B[B.big]
print(f"  big stocks, any day: n={len(b)} | 6 months: +10% reached {100 * (b.max6 >= 10).mean():.0f}%  +30% {100 * (b.max6 >= 30).mean():.0f}%  ended up {100 * (b.end6 > 0).mean():.0f}%  avg {b.end6.mean():+.1f}% | 12 months: +30% reached {100 * (b.max12 >= 30).mean():.0f}%  ended up {100 * (b.end12 > 0).mean():.0f}%  avg {b.end12.mean():+.1f}%  worst tenth {b.end12.quantile(.1):+.1f}%  fell 20% {100 * (b.min12 <= -20).mean():.0f}%")
print("\nF. The worst STRONG 25% events (12-month result)"); print(g.dropna(subset=["end12"]).nsmallest(10, "end12")[["name", "date", "depth", "min12", "max12", "end12"]].round(1).to_string(index=False))
print("\nG. ICICI Bank, every fall of 20%+ and 25%+"); print(E[(E.sym == "ICICIBANK") & E.X.isin([20, 25])][["date", "X", "depth", "strong", "mkt", "max6", "end6", "max12", "end12", "min12"]].round(1).to_string(index=False))
now = []
for s, (name, d) in S.items():
    c = d.c; dep = (1 - c.iloc[-1] / c.iloc[-252:].max()) * 100
    if dep >= 20: now.append((name, round(dep, 1), bool(rank[s].iloc[-1] <= 100)))
print(f"\nH. Today ({list(S.values())[0][1].index[-1].date()}): {len(now)} of {len(S)} stocks are 20%+ below their 1-year high; {sum(1 for x in now if x[2])} of them are in the top 100 by trading")
