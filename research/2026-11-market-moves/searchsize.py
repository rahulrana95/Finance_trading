"""Which rule, at which size, reaches 8 / 10 / 12 / 15 / 20% a year, and what does it risk?

No loss cap: the size (max loss of one trade as % of capital) is set to hit the target.
Kept from the hard limits: hedged spreads only, short delta <= 0.12, next week's Tuesday
expiry, exit at the close the day before expiry.

Rules are chosen on 2011-2020 (must work in 2011-15 AND 2016-20). 2021-2026 is never used to
choose; it is run once on the chosen rules. Size is set on 2011-2020, then applied to 2021-2026.
Calendar: entry Monday / Tuesday / Wednesday, expiry the following week's Tuesday (weekly
Tuesday expiry applied to all history). Option prices are MODELLED (Black-Scholes, India VIX,
assumed skew). Research only. Run from a folder holding data/*.json (see fetch.sh).
"""
import json, math, itertools, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

def load(name, tz="Asia/Kolkata"):
    r = json.load(open(f"data/{name}.json"))["chart"]["result"][0]; q = r["indicators"]["quote"][0]
    return pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")},
                        index=pd.to_datetime(r["timestamp"], unit="s").tz_localize("UTC").tz_convert(tz).normalize().tz_localize(None)).dropna()
N = load("NIFTY"); N["vix"] = load("INDIAVIX").close.reindex(N.index).ffill(); N = N.loc["2009-06-01":].dropna()
O, H, L, C, V = (N[k].values for k in ("open", "high", "low", "close", "vix")); idx = N.index; n = len(N)
c = N.close; r1 = np.log(c).diff()
macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean(); hist = macd - macd.ewm(span=9, adjust=False).mean()
dl = c.diff(); rsi = 100 - 100 / (1 + dl.clip(lower=0).ewm(alpha=1/14, adjust=False).mean() / (-dl.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean())
rv5, rv20 = r1.rolling(5).std() * math.sqrt(252) * 100, r1.rolling(20).std() * math.sqrt(252) * 100
usv = load("USVIX", "America/New_York").close; usv = usv.reindex(usv.index.union(idx)).ffill().shift(1).reindex(idx)
vx = N.vix
X = pd.DataFrame({
    "VIX<13": vx < 13, "VIX 13-16": (vx >= 13) & (vx < 16), "VIX 16-20": (vx >= 16) & (vx < 20), "VIX<16": vx < 16, "VIX<20": vx < 20, "VIX>=14": vx >= 14, "VIX 14-22": (vx >= 14) & (vx < 22),
    "MACD>0": macd > 0, "MACD<0": macd < 0, "MACD bars rising": hist > hist.shift(1), "MACD bars falling": hist < hist.shift(1), "MACD>signal": hist > 0,
    "RSI<40": rsi < 40, "RSI 40-60": (rsi >= 40) & (rsi < 60), "RSI 50-70": (rsi >= 50) & (rsi < 70), "RSI>60": rsi > 60, "RSI>70": rsi > 70, "RSI 45-65": (rsi >= 45) & (rsi < 65),
    "above 200-day avg": c > c.rolling(200).mean(), "above 50-day avg": c > c.rolling(50).mean(), "50>200 avg": c.rolling(50).mean() > c.rolling(200).mean(),
    "realised vol < VIX": rv20 < vx, "realised vol < 0.8 VIX": rv20 < 0.8 * vx, "5-day vol < 20-day vol": rv5 < rv20,
    "VIX falling 5d": vx < vx.shift(5), "VIX below its 20-day avg": vx < vx.rolling(20).mean(),
    "last 5 days up": c > c.shift(5), "last 5 days down": c < c.shift(5), "within 5% of 60-day high": c > 0.95 * c.rolling(60).max(), "US VIX<20": usv < 20,
}).shift(1).fillna(False)
CALL_MULT, PUT_MULT = 0.92, 1.12
cdf = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
def bs(S, K, T, s, call):
    if T <= 0: return max(S - K, 0) if call else max(K - S, 0)
    sd = s * math.sqrt(T); d1 = (math.log(S / K) + .5 * sd * sd) / sd
    return S * cdf(d1) - K * cdf(d1 - sd) if call else K * cdf(sd - d1) - S * cdf(-d1)
def delta(S, K, T, s, call):
    sd = s * math.sqrt(T); d1 = (math.log(S / K) + .5 * sd * sd) / sd; return cdf(d1) if call else cdf(-d1)
r50 = lambda x: round(x / 50) * 50
# calendar: for each entry day, the next week's Tuesday (expiry) and the session before it (exit)
wkid = (idx - pd.to_timedelta(idx.weekday, unit="D")).values
EXP = np.full(n, -1)
for i in range(n):
    for j in range(i + 1, min(i + 10, n)):
        if wkid[j] > wkid[i] and idx[j].weekday() >= 1:        # first session on/after Tuesday of the following week
            EXP[i] = j if (idx[j] - idx[i]).days >= 6 else -1; break
def trade(i, sides, k, buf, stop):
    e = EXP[i]; hold = e - 1 - i; dte = e - i + 1
    S = O[i]; s0 = V[i - 1] / 100; T = dte / 252; w = max(50, r50(0.008 * S)); x = k * V[i - 1] * math.sqrt((hold + 1) / 252); legs = []; lv = {}
    for side in sides:
        call = side == "call"; mult = CALL_MULT if call else PUT_MULT
        K = r50(S * (1 + (x + buf) / 100)) if call else r50(S * (1 - (x + buf) / 100))
        while delta(S, K, T, s0 * mult, call) > 0.12: K += 50 if call else -50
        legs += [(-1, K, call), (1, K + w if call else K - w, call)]; lv[side] = (S * (1 + x / 100) if call else S * (1 - x / 100), K)
    def val(S_, T_, s_):
        ps = [bs(S_, K, T_, s_ * (CALL_MULT if cl else PUT_MULT), cl) for _, K, cl in legs]
        return -sum(sg * p for (sg, _, _), p in zip(legs, ps)) + 0.025 * sum(ps) + len(legs) * 0.15 * S_ / 25000
    ps0 = [bs(S, K, T, s0 * (CALL_MULT if cl else PUT_MULT), cl) for _, K, cl in legs]
    net = -sum(sg * p for (sg, _, _), p in zip(legs, ps0)) - (0.025 * sum(ps0) + len(legs) * 0.15 * S / 25000)
    if net <= 0.002 * w: return np.nan
    out = None
    for j in range(hold + 1):
        t = i + j; rem = dte - j
        for side, (lvl, K) in lv.items():
            call = side == "call"
            if stop == "limit":
                if j > 0 and ((O[t] >= lvl) if call else (O[t] <= lvl)): out = val(O[t], rem / 252, V[t - 1] / 100)
                elif (H[t] >= lvl) if call else (L[t] <= lvl): out = val(lvl, (rem - .5) / 252, (V[t - 1] + V[t]) / 200)
            elif stop == "strike" and ((C[t] >= K) if call else (C[t] <= K)): out = val(C[t], (rem - 1) / 252, V[t] / 100)
            if out is not None: break
        if out is not None: break
    if out is None: out = val(C[i + hold], (dte - hold - 1) / 252, V[i + hold] / 100)
    return (net - out) / (w - net)

ENTRY = {"Monday": 0, "Tuesday": 1, "Wednesday": 2}
valid = np.zeros(n, bool); valid[260:] = True; valid &= EXP > 0
SETUPS = list(itertools.product(ENTRY, (("put",), ("call",), ("call", "put")), (0.6, 0.8, 1.0, 1.25, 1.5), (1.5, 0.5), ("limit", "strike", "hold")))
R = {}
for e, sides, k, buf, stop in SETUPS:
    ii = np.flatnonzero((idx.weekday == ENTRY[e]) & valid & (EXP - np.arange(n) >= 3)); R[(e, sides, k, buf, stop)] = (ii, np.array([trade(i, sides, k, buf, stop) for i in ii]))
names = list(X.columns); FILT = [()] + [(a,) for a in names] + list(itertools.combinations(names, 2))
Xv = {k: X[k].values.astype(bool) for k in names}; yr = idx.year.values
def st(ii, r, lo, hi):
    m = (yr[ii] >= lo) & (yr[ii] <= hi) & ~np.isnan(r); x = r[m]
    if len(x) < 8: return None
    years = hi - lo + 1 if hi < 2026 else (idx[-1] - pd.Timestamp(f"{lo}-01-01")).days / 365.25
    eq = np.cumsum(x); byy = pd.Series(x).groupby(yr[ii][m]).sum()
    return dict(n=len(x), per_yr=len(x) / years, win=100 * (x > 0).mean(), R_yr=x.sum() / years, dd=(eq - np.maximum(np.maximum.accumulate(eq), 0)).min(), worst=x.min(), up=int((byy > 0).sum()), yrs=len(byy))
def sized(ii, r, m, lo, hi, s):
    """Compounded result at size s (fraction of capital lost if one trade loses fully), one step per expiry week."""
    mm = m & (yr[ii] >= lo) & (yr[ii] <= hi) & ~np.isnan(r)
    wkret = pd.Series(s * r[mm], index=idx[EXP[ii[mm]]]).groupby(level=0).sum().clip(lower=-0.99)
    eq = (1 + wkret).cumprod(); years = hi - lo + 1 if hi < 2026 else (idx[-1] - pd.Timestamp(f"{lo}-01-01")).days / 365.25
    by = (1 + wkret).groupby(wkret.index.year).prod() - 1
    return dict(cagr=100 * (eq.iloc[-1] ** (1 / years) - 1), dd=100 * (eq / eq.cummax().clip(lower=1) - 1).min(), worst_week=100 * wkret.min(), worst_year=100 * by.min(), up=f"{int((by > 0).sum())}/{len(by)}")
def size_for(ii, r, m, lo, hi, target):
    a, b = 0.0, 3.0
    for _ in range(50):
        mid = (a + b) / 2
        if sized(ii, r, m, lo, hi, mid)["cagr"] < target: a = mid
        else: b = mid
    return b

# ---- choose on 2011-2020 ----
cands = []
for key, (ii, r) in R.items():
    for f in FILT:
        m = np.ones(len(ii), bool)
        for a in f: m &= Xv[a][ii]
        z = st(ii[m], r[m], 2011, 2020)
        if z is None or z["per_yr"] < 8 or z["R_yr"] <= 0: continue
        z1, z2 = st(ii[m], r[m], 2011, 2015), st(ii[m], r[m], 2016, 2020)
        if z1 is None or z2 is None or min(z1["R_yr"], z2["R_yr"]) <= 0: continue
        cands.append(dict(key=key, f=f, m=m, **z, minR=min(z1["R_yr"], z2["R_yr"]), score=min(z1["R_yr"], z2["R_yr"]) / max(-z["dd"], 0.15)))
D = pd.DataFrame(cands); print(f"{len(SETUPS) * len(FILT)} rules; {len(D)} trade 8+ times a year and are positive in both 2011-15 and 2016-20")
robust = D[(D.up >= D.yrs - 1) & (D.worst > -0.6)].sort_values("score", ascending=False)
print(f"   of those, profitable in at least 9 of 10 years with no trade worse than -0.6 R: {len(robust)}")
top = robust.assign(fk=robust.f.map(str) + robust.key.map(lambda k: k[0])).drop_duplicates("fk").head(12)
pd.set_option("display.width", 330); pd.set_option("display.max_colwidth", 50); rows = []
for _, x in top.iterrows():
    ii, r = R[x.key]; zt = st(ii[x.m], r[x.m], 2021, 2026)
    rows.append(dict(entry=x.key[0], sides="+".join(x.key[1]), k=x.key[2], buf=x.key[3], stop=x.key[4], filt=" & ".join(x.f) or "none", n=x.n, win=x.win, R_yr=x.R_yr, dd=x.dd, worst=x.worst, up=f"{x.up}/{x.yrs}",
                     T_n=zt["n"], T_win=zt["win"], T_R_yr=zt["R_yr"], T_dd=zt["dd"], T_worst=zt["worst"], T_up=f"{zt['up']}/{zt['yrs']}"))
print("\nA. Top 12 rules chosen on 2011-2020 (ranked by weakest-half return over drawdown), with their unseen 2021-2026 result (T_ columns)")
print(pd.DataFrame(rows).round(2).to_string(index=False))
allT = [st(R[x.key][0][x.m], R[x.key][1][x.m], 2021, 2026) for _, x in robust.iterrows()]
tr = np.array([z["R_yr"] for z in allT if z]); print(f"\n   all {len(robust)} robust rules on 2021-2026: positive {int((tr > 0).sum())} ({100 * (tr > 0).mean():.0f}%), median {np.median(tr):+.2f} R/yr against {robust.R_yr.median():+.2f} in 2011-2020")

# ---- size each of the top 3 for each target on 2011-2020, then see 2021-2026 ----
print("\nB. Size set on 2011-2020 to hit the target there; the same size then applied to 2021-2026")
for rank, (_, x) in enumerate(top.head(3).iterrows(), 1):
    ii, r = R[x.key]; print(f"\n  Rule {rank}: enter {x.key[0]}, {'+'.join(x.key[1])}, limit {x.key[2]} x VIX move, strike {x.key[3]}% beyond, exit '{x.key[4]}', filter: {' & '.join(x.f) or 'none'}   ({x.per_yr:.0f} trades a year)")
    print(f"    {'target':>7s} {'size: one full loss costs':>26s} | 2011-2020: {'CAGR':>6s} {'max DD':>7s} {'worst wk':>9s} {'worst yr':>9s} {'up yrs':>6s} | 2021-2026: {'CAGR':>6s} {'max DD':>7s} {'worst wk':>9s} {'worst yr':>9s} {'up yrs':>6s}")
    for target in (8, 10, 12, 15, 20):
        s = size_for(ii, r, x.m, 2011, 2020, target); a, b = sized(ii, r, x.m, 2011, 2020, s), sized(ii, r, x.m, 2021, 2026, s)
        print(f"    {target:6d}% {100 * s:25.1f}% |            {a['cagr']:5.1f}% {a['dd']:6.1f}% {a['worst_week']:8.1f}% {a['worst_year']:8.1f}% {a['up']:>6s} |            {b['cagr']:5.1f}% {b['dd']:6.1f}% {b['worst_week']:8.1f}% {b['worst_year']:8.1f}% {b['up']:>6s}")
