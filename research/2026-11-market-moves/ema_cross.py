"""9 / 21 EMA crossover on Nifty daily: when did it work and when not?

Signal at the close where the 9 EMA crosses the 21 EMA, entry next open. Two outcomes:
(a) the trade held until the opposite cross, (b) the move 10 trading days later, both in the
direction of the cross. Conditions are measured at the signal close. Train before 2017, test after.
Research only, index prices, 0.05% cost per trade. Run from a folder holding data/NIFTY.json
and data/INDIAVIX.json (see fetch.sh).
"""
import json
import numpy as np, pandas as pd

def load(name):
    r = json.load(open(f"data/{name}.json"))["chart"]["result"][0]; q = r["indicators"]["quote"][0]
    return pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")},
                        index=pd.to_datetime(r["timestamp"], unit="s").tz_localize("UTC").tz_convert("Asia/Kolkata").normalize().tz_localize(None)).dropna()
N = load("NIFTY"); V = load("INDIAVIX").close.reindex(N.index).ffill().values
o, h, l, c = (N[k].values for k in ("open", "high", "low", "close")); n = len(N); cs = N.close
e9, e21 = cs.ewm(span=9, adjust=False).mean().values, cs.ewm(span=21, adjust=False).mean().values
ma200 = cs.rolling(200).mean().values; ma50 = cs.rolling(50).mean().values
pc = np.r_[c[:1], c[:-1]]; tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
atr = pd.Series(tr).ewm(alpha=1/14, adjust=False).mean().values
upm, dnm = h - np.r_[h[:1], h[:-1]], np.r_[l[:1], l[:-1]] - l
pdm = np.where((upm > dnm) & (upm > 0), upm, 0.0); ndm = np.where((dnm > upm) & (dnm > 0), dnm, 0.0)
sm = lambda x: pd.Series(x).ewm(alpha=1/14, adjust=False).mean().values
pdi, ndi = 100 * sm(pdm) / atr, 100 * sm(ndm) / atr
adx = sm(100 * abs(pdi - ndi) / (pdi + ndi + 1e-9))
macd = cs.ewm(span=12, adjust=False).mean() - cs.ewm(span=26, adjust=False).mean(); M = macd.values
d = e9 - e21; cross = [i for i in range(210, n - 1) if d[i] * d[i - 1] < 0]
COST = 0.05
rows = []
for k, i in enumerate(cross):
    s = 1 if d[i] > 0 else -1
    j = cross[k + 1] if k + 1 < len(cross) else n - 2                       # opposite cross (exit next open)
    hold = s * (o[j + 1] / o[i + 1] - 1) * 100 - COST
    t10 = s * (c[min(i + 10, n - 1)] / o[i + 1] - 1) * 100 - COST
    last = i - cross[k - 1] if k else 99
    rows.append(dict(date=N.index[i], side="buy cross" if s > 0 else "sell cross", hold=hold, t10=t10, days=j - i,
                     trend="with the 200-day trend" if s * (c[i] - ma200[i]) > 0 else "against the 200-day trend",
                     ma="50 avg agrees (50 vs 200)" if s * (ma50[i] - ma200[i]) > 0 else "50 avg disagrees",
                     adx="ADX 25+" if adx[i] >= 25 else "ADX 18-25" if adx[i] >= 18 else "ADX under 18",
                     adxdir="ADX rising" if adx[i] > adx[i - 5] else "ADX falling",
                     vix="VIX under 14" if V[i] < 14 else "VIX 14-20" if V[i] < 20 else "VIX 20+",
                     since="last cross under 10 days ago" if last < 10 else "last cross 10-25 days ago" if last < 25 else "last cross 25+ days ago",
                     slope="21 EMA already sloping the same way" if s * (e21[i] - e21[i - 5]) > 0 else "21 EMA still sloping against",
                     macd="MACD same side of zero" if s * M[i] > 0 else "MACD other side of zero",
                     bar="cross bar bigger than 1 ATR" if abs(c[i] - pc[i]) > atr[i - 1] else "cross bar normal"))
D = pd.DataFrame(rows); D["test"] = D.date >= "2017-01-01"
def stat(x, col):
    w = x[col] > 0
    return len(x), 100 * w.mean(), x[col][w].mean() if w.any() else 0, x[col][~w].mean() if (~w).any() else 0, x[col].mean()
def show(title, groups):
    print(f"\n{title}\n{'':40s}{'--- held to the opposite cross ---':^58s}{'--- 10 days later ---':^30s}")
    print(f"{'':40s}{'train':^29s}{'test':^29s}{'train':^15s}{'test':^15s}")
    for name, g in groups:
        out = f"{name:40s}"
        for per in (False, True):
            x = g[g.test == per]
            if len(x) < 5: out += f"{'n=' + str(len(x)) + ' too few':^29s}"; continue
            nn, wr, aw, al, av = stat(x, "hold"); out += f" n={nn:3d} win {wr:3.0f}% avg {av:+5.2f}% "
        for per in (False, True):
            x = g[g.test == per]
            if len(x) < 5: out += f"{'':15s}"; continue
            nn, wr, aw, al, av = stat(x, "t10"); out += f" {wr:3.0f}% {av:+5.2f}% "
        print(out)
print(f"Nifty {N.index[0].date()} to {N.index[-1].date()}: {len(D)} crossovers ({len(D) / ((N.index[-1] - N.index[210]).days / 365.25):.1f} a year), median hold {int(D.days.median())} days")
a = stat(D, "hold"); print(f"All: win {a[1]:.0f}%, avg win {a[2]:+.2f}%, avg loss {a[3]:+.2f}%, avg {a[4]:+.2f}% per trade; best {D.hold.max():+.1f}%, worst {D.hold.min():+.1f}%")
top = D.hold.sort_values(ascending=False); print(f"The best 10% of trades ({len(D) // 10}) made {top.head(len(D) // 10).sum():+.0f}% of a total {D.hold.sum():+.0f}%")
show("ALL", [("every crossover", D)]); show("SIDE", D.groupby("side"))
for col in ("trend", "ma", "adx", "adxdir", "vix", "since", "slope", "macd", "bar"): show(col.upper(), D.groupby(col))
show("BUY CROSS ONLY, by trend", D[D.side == "buy cross"].groupby("trend")); show("SELL CROSS ONLY, by trend", D[D.side == "sell cross"].groupby("trend"))
B = D[(D.side == "buy cross") & (D.trend == "with the 200-day trend")]
show("BUY CROSS WITH THE TREND, by gap since last cross", B.groupby("since")); show("BUY CROSS WITH THE TREND, by VIX", B.groupby("vix"))
print("\n2026 crossovers:"); print(D[D.date >= "2026-01-01"][["date", "side", "trend", "days", "hold", "t10"]].round(2).to_string(index=False))
