"""Monday open as the line: does a MACD + RSI direction call put the later close on the right
side of it, and by 0.4% or more? Then: does an at-the-money hedged spread sold on that call pay?

Research only. Index prices; option credits are modelled (Black-Scholes, India VIX as volatility),
not traded prices. Signals use Friday's close only, entry is the next week's first open.
Run from a folder holding data/NIFTY.json and data/INDIAVIX.json (see fetch.sh).
"""
import json, math, sys
import numpy as np, pandas as pd

def load(name):
    r = json.load(open(f"data/{name}.json"))["chart"]["result"][0]; q = r["indicators"]["quote"][0]
    d = pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")},
                     index=pd.to_datetime(r["timestamp"], unit="s").tz_localize("UTC").tz_convert("Asia/Kolkata").normalize().tz_localize(None))
    return d.dropna()

N = load("NIFTY"); V = load("INDIAVIX").close.reindex(N.index).ffill()
c = N.close
macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
sig = macd.ewm(span=9, adjust=False).mean()
d = c.diff(); up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
rsi = 100 - 100 / (1 + up / dn)
wk = N.index.to_period("W"); first = np.flatnonzero(wk != np.r_[wk[:1] - 1, wk[:-1]])
first = first[(first >= 60)]                      # indicators need history
o = N.open.values; cl = c.values; n = len(N)
M, S, R, VX = macd.values, sig.values, rsi.values, V.values

# direction at each week's first open, from the previous close: +1 up, -1 down, 0 no call
def calls(i):
    p = i - 1; m, s, r = M[p], S[p], R[p]
    return {
        "always up": 1, "always down": -1,
        "MACD above its signal line": 1 if m > s else -1,
        "MACD above zero": 1 if m > 0 else -1,
        "RSI above 50": 1 if r > 50 else -1,
        "MACD>signal and RSI>50 / both opposite": 1 if (m > s and r > 50) else -1 if (m < s and r < 50) else 0,
        "MACD>0 and RSI>50 / both opposite": 1 if (m > 0 and r > 50) else -1 if (m < 0 and r < 50) else 0,
        "all three agree": 1 if (m > s and m > 0 and r > 50) else -1 if (m < s and m < 0 and r < 50) else 0,
        "up only: MACD>signal, MACD>0, RSI 50-70": 1 if (m > s and m > 0 and 50 < r < 70) else 0,
        "reversal: RSI<35 up, RSI>70 down": 1 if r < 35 else -1 if r > 70 else 0,
    }

HOR = {"same day close": 0, "Tuesday close (+1)": 1, "Friday close (+4)": 4, "next Tuesday close (+6)": 6}
SPLIT = pd.Timestamp("2017-01-01")
rows = []
for i in first:
    for name, s in calls(i).items():
        if s == 0: continue
        for h, k in HOR.items():
            if i + k >= n: continue
            rows.append((N.index[i], name, h, s * (cl[i + k] / o[i] - 1) * 100, s))
D = pd.DataFrame(rows, columns=["date", "call", "hor", "ret", "side"]); D["test"] = D.date >= SPLIT

def part(x):
    return pd.Series({"n": len(x), "right side %": 100 * (x.ret > 0).mean(), "right by 0.4%+": 100 * (x.ret >= .4).mean(),
                      "wrong by 0.4%+": 100 * (x.ret <= -.4).mean(), "avg move %": x.ret.mean()})
print(f"Nifty {N.index[0].date()} to {N.index[-1].date()}, {len(first)} weeks. Train before 2017, test from 2017.\n")
for h in HOR:
    print(f"== Exit at {h} ==")
    t = D[D.hor == h].groupby(["call", "test"], sort=False).apply(part, include_groups=False).unstack("test")
    t.columns = [f"{a} {'test' if b else 'train'}" for a, b in t.columns]
    print(t[[f"{m} {p}" for m in ("n", "right side %", "right by 0.4%+", "wrong by 0.4%+", "avg move %") for p in ("train", "test")]].round(1).to_string(), "\n")

# ---- at-the-money hedged spread sold on the call side that should expire worthless ----
def ncdf(x): return .5 * (1 + math.erf(x / math.sqrt(2)))
def bs(S0, K, T, v, put):
    if T <= 0: return max(K - S0, 0) if put else max(S0 - K, 0)
    d1 = (math.log(S0 / K) + .5 * v * v * T) / (v * math.sqrt(T)); d2 = d1 - v * math.sqrt(T)
    return K * ncdf(-d2) - S0 * ncdf(-d1) if put else S0 * ncdf(d1) - K * ncdf(d2)
WIDTH, COST = .0083, .00015        # 200 points at 24,000; about 3.5 points of charges and slippage per spread

def spread(i, k, s, ivmult):
    """Profit as a fraction of max loss. s=+1: sell ATM put spread. s=-1: sell ATM call spread."""
    S0 = o[i]; K = S0; W = WIDTH * S0; T = (k + .95) / 252; v = VX[i - 1] / 100 * ivmult
    put = s > 0; K2 = K - W if put else K + W
    credit = bs(S0, K, T, v, put) - bs(S0, K2, T, v, put) - COST * S0
    ST = cl[i + k]
    loss = min(max((K - ST) if put else (ST - K), 0), W)
    return (credit - loss) / (W - credit), credit / W
print("== ATM spread, hedge 0.83% away (200 points at 24,000), held to the close of expiry day ==")
print("   profit is % of the money at risk per trade; 'need' is the win rate that breaks even if every loss were a full loss\n")
out = []
for k, lab in ((1, "this Tuesday (+1)"), (6, "next Tuesday (+6)")):
    for ivm in (1.0, 0.85):
        for name in ("always up", "always down", "MACD above its signal line", "MACD above zero", "RSI above 50",
                     "MACD>signal and RSI>50 / both opposite", "all three agree", "up only: MACD>signal, MACD>0, RSI 50-70"):
            for lo, hi, per in ((pd.Timestamp("2008-04-01"), SPLIT, "train"), (SPLIT, pd.Timestamp("2100-01-01"), "test")):
                r = [spread(i, k, s, ivm) for i in first if lo <= N.index[i] < hi and i + k < n and not np.isnan(VX[i - 1]) and (s := calls(i)[name])]
                if not r: continue
                p = np.array([x[0] for x in r]); cr = np.mean([x[1] for x in r]); eq = np.cumsum(p); dd = (eq - np.maximum.accumulate(eq)).min()
                yrs = (min(hi, N.index[-1]) - lo).days / 365.25
                out.append((lab, f"VIX x {ivm}", name, per, len(p), 100 * (p > 0).mean(), 100 * (1 - cr), 100 * p.mean(), 100 * p.sum() / yrs, 100 * dd, 100 * p.min()))
O = pd.DataFrame(out, columns=["expiry", "vol", "call", "period", "n", "win %", "need %", "avg % of risk", "sum per yr %", "max DD %", "worst %"])
pd.set_option("display.width", 250)
for (e, v), g in O.groupby(["expiry", "vol"], sort=False):
    print(f"-- expiry {e}, credit priced at {v} --"); print(g.drop(columns=["expiry", "vol"]).round(1).to_string(index=False), "\n")
