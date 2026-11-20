"""Systematic search for an option-selling rule that could make 20% a year inside the loss limits.

Every rule = a trade set-up (strike distance, sides, stop, entry day) x a filter (one or two
market conditions). Searched on 2016-2020 only. Anything that qualifies there is then checked
on two periods the search never saw: 2021-2026 and 2011-2015.

"Could make 20%" is tested without choosing a size first. R = max loss of one trade. A rule
qualifies in a period if, at the size that gives 20% a year:
  A. its worst drawdown stays within 5% of capital   (R per year / drawdown >= 4)
  B. its worst single trade stays within 1%          (R per year / worst trade >= 20)
  C. the max loss of one position stays within 3%    (R per year >= 6.67)
Option prices are MODELLED (Black-Scholes, India VIX, assumed skew). Research only.
Run from a folder holding data/*.json (see fetch.sh).
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
HOLD, DTE = 5, 7
c = N.close; r1 = np.log(c).diff()
macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean(); hist = macd - macd.ewm(span=9, adjust=False).mean()
dl = c.diff(); rsi = 100 - 100 / (1 + dl.clip(lower=0).ewm(alpha=1/14, adjust=False).mean() / (-dl.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean())
rv5, rv20 = r1.rolling(5).std() * math.sqrt(252) * 100, r1.rolling(20).std() * math.sqrt(252) * 100
usv = load("USVIX", "America/New_York").close; usv = usv.reindex(usv.index.union(idx)).ffill().shift(1).reindex(idx)
vx = N.vix
X = pd.DataFrame({                                             # atomic conditions, as of the close
    "VIX<13": vx < 13, "VIX 13-16": (vx >= 13) & (vx < 16), "VIX 16-20": (vx >= 16) & (vx < 20), "VIX<16": vx < 16, "VIX<20": vx < 20, "VIX>=14": vx >= 14, "VIX 14-22": (vx >= 14) & (vx < 22),
    "MACD>0": macd > 0, "MACD<0": macd < 0, "MACD bars rising": hist > hist.shift(1), "MACD bars falling": hist < hist.shift(1), "MACD>signal": hist > 0,
    "RSI<40": rsi < 40, "RSI 40-60": (rsi >= 40) & (rsi < 60), "RSI 50-70": (rsi >= 50) & (rsi < 70), "RSI>60": rsi > 60, "RSI>70": rsi > 70, "RSI 45-65": (rsi >= 45) & (rsi < 65),
    "above 200-day avg": c > c.rolling(200).mean(), "above 50-day avg": c > c.rolling(50).mean(), "50>200 avg": c.rolling(50).mean() > c.rolling(200).mean(),
    "realised vol < VIX": rv20 < vx, "realised vol < 0.8 VIX": rv20 < 0.8 * vx, "5-day vol < 20-day vol": rv5 < rv20,
    "VIX falling 5d": vx < vx.shift(5), "VIX below its 20-day avg": vx < vx.rolling(20).mean(),
    "last 5 days up": c > c.shift(5), "last 5 days down": c < c.shift(5), "within 5% of 60-day high": c > 0.95 * c.rolling(60).max(), "US VIX<20": usv < 20,
}).shift(1).fillna(False)                                      # row i = known before the open of day i
CALL_MULT, PUT_MULT = 0.92, 1.12
cdf = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
def bs(S, K, T, s, call):
    if T <= 0: return max(S - K, 0) if call else max(K - S, 0)
    sd = s * math.sqrt(T); d1 = (math.log(S / K) + .5 * sd * sd) / sd
    return S * cdf(d1) - K * cdf(d1 - sd) if call else K * cdf(sd - d1) - S * cdf(-d1)
def delta(S, K, T, s, call):
    sd = s * math.sqrt(T); d1 = (math.log(S / K) + .5 * sd * sd) / sd; return cdf(d1) if call else cdf(-d1)
r50 = lambda x: round(x / 50) * 50
def trade(i, sides, k, buf, stop):
    S = O[i]; s0 = V[i - 1] / 100; T = DTE / 252; w = max(50, r50(0.008 * S)); x = k * V[i - 1] * math.sqrt((HOLD + 1) / 252); legs = []; lv = {}
    for side in sides:
        call = side == "call"; mult = CALL_MULT if call else PUT_MULT
        K = r50(S * (1 + (x + buf) / 100)) if call else r50(S * (1 - (x + buf) / 100))
        while delta(S, K, T, s0 * mult, call) > 0.12: K += 50 if call else -50               # hard limit: short delta <= 0.12
        legs += [(-1, K, call), (1, K + w if call else K - w, call)]; lv[side] = (S * (1 + x / 100) if call else S * (1 - x / 100), K)
    def val(S_, T_, s_):
        ps = [bs(S_, K, T_, s_ * (CALL_MULT if cl else PUT_MULT), cl) for _, K, cl in legs]
        return -sum(sg * p for (sg, _, _), p in zip(legs, ps)) + 0.025 * sum(ps) + len(legs) * 0.15 * S_ / 25000
    ps0 = [bs(S, K, T, s0 * (CALL_MULT if cl else PUT_MULT), cl) for _, K, cl in legs]
    net = -sum(sg * p for (sg, _, _), p in zip(legs, ps0)) - (0.025 * sum(ps0) + len(legs) * 0.15 * S / 25000)
    if net <= 0.002 * w: return np.nan
    out = None
    for j in range(HOLD + 1):
        t = i + j; rem = DTE - j
        for side, (lvl, K) in lv.items():
            call = side == "call"
            if stop == "limit":                                   # leave when price reaches X (1.5% before the strike)
                if j > 0 and ((O[t] >= lvl) if call else (O[t] <= lvl)): out = val(O[t], rem / 252, V[t - 1] / 100)
                elif (H[t] >= lvl) if call else (L[t] <= lvl): out = val(lvl, (rem - .5) / 252, (V[t - 1] + V[t]) / 200)
            elif stop == "strike" and ((C[t] >= K) if call else (C[t] <= K)): out = val(C[t], (rem - 1) / 252, V[t] / 100)   # leave on a close beyond the strike
            if out is not None: break
        if out is not None: break
    if out is None: out = val(C[i + HOLD], (DTE - HOLD - 1) / 252, V[i + HOLD] / 100)
    return (net - out) / (w - net)

wk = idx.to_period("W"); firstday = np.r_[True, wk[1:] != wk[:-1]]
ENTRY = {"week's first day": firstday, "Wednesday": idx.weekday == 2}
valid = np.zeros(n, bool); valid[260:n - HOLD - 1] = True
SETUPS = list(itertools.product(ENTRY, (("put",), ("call",), ("call", "put")), (0.6, 0.8, 1.0, 1.25, 1.5), (1.5, 0.5), ("limit", "strike", "hold")))
R = {}
for e, sides, k, buf, stop in SETUPS:
    ii = np.flatnonzero(ENTRY[e] & valid); R[(e, sides, k, buf, stop)] = (ii, np.array([trade(i, sides, k, buf, stop) for i in ii]))
names = list(X.columns); FILT = [()] + [(a,) for a in names] + list(itertools.combinations(names, 2))
Xv = {k: X[k].values.astype(bool) for k in names}; yr = idx.year.values
PERIODS = {"build 2016-2020": (2016, 2020), "test 2021-2026": (2021, 2026), "earlier 2011-2015": (2011, 2015)}
def stats(ii, r, lo, hi):
    m = (yr[ii] >= lo) & (yr[ii] <= hi) & ~np.isnan(r); x = r[m]
    if len(x) < 8: return None
    years = hi - lo + 1 if hi < 2026 else (idx[-1] - pd.Timestamp(f"{lo}-01-01")).days / 365.25
    eq = np.cumsum(x); dd = min((eq - np.maximum(np.maximum.accumulate(eq), 0)).min(), -1e-9); byy = pd.Series(x).groupby(yr[ii][m]).sum()
    return dict(n=len(x), per_yr=len(x) / years, win=100 * (x > 0).mean(), R_yr=x.sum() / years, dd=dd, worst=x.min(), ratio=(x.sum() / years) / -dd,
                up_years=f"{int((byy > 0).sum())}/{len(byy)}", worst_year=byy.min())
def grade(z): return "" if z is None or z["R_yr"] <= 0 else ("A" if z["ratio"] >= 4 else "") + ("B" if z["R_yr"] / -min(z["worst"], -1e-9) >= 20 else "") + ("C" if z["R_yr"] >= 6.67 else "")
rows = []
for key, (ii, r) in R.items():
    for f in FILT:
        m = np.ones(len(ii), bool)
        for a in f: m &= Xv[a][ii]
        zb = stats(ii[m], r[m], 2016, 2020)
        if zb is None or zb["per_yr"] < 10: continue                 # must trade at least 10 times a year
        rows.append((key, f, m, zb))
print(f"Set-ups {len(SETUPS)} x filters {len(FILT)} = {len(SETUPS) * len(FILT)} rules; {len(rows)} trade at least 10 times a year in 2016-2020")
B = pd.DataFrame([dict(key=k, f=f, **z, grade=grade(z)) for k, f, m, z in rows])
print(f"Build 2016-2020: positive {int((B.R_yr > 0).sum())}; pass A (20% with drawdown <= 5%) {int(B.grade.str.contains('A').sum())}; pass A+B (and worst trade <= 1%) {int((B.grade.str.contains('A') & B.grade.str.contains('B')).sum())}; pass A+B+C {int((B.grade == 'ABC').sum())}")
print(f"   best R per year in build: {B.R_yr.max():.2f}; best ratio: {B.ratio.max():.1f}")
out = []
for (k, f, m, zb) in rows:
    if "A" not in grade(zb): continue
    ii, r = R[k]; zt, ze = stats(ii[m], r[m], 2021, 2026), stats(ii[m], r[m], 2011, 2015)
    out.append(dict(entry=k[0], sides="+".join(k[1]), k=k[2], buf=k[3], stop=k[4], filt=" & ".join(f) or "none",
                    b_n=zb["n"], b_win=zb["win"], b_R=zb["R_yr"], b_ratio=zb["ratio"], b_worst=zb["worst"],
                    t_n=zt["n"] if zt else 0, t_win=zt["win"] if zt else np.nan, t_R=zt["R_yr"] if zt else np.nan, t_dd=zt["dd"] if zt else np.nan, t_ratio=zt["ratio"] if zt else np.nan, t_worst=zt["worst"] if zt else np.nan, t_up=zt["up_years"] if zt else "", t_grade=grade(zt),
                    e_R=ze["R_yr"] if ze else np.nan, e_dd=ze["dd"] if ze else np.nan, e_ratio=ze["ratio"] if ze else np.nan, e_worst=ze["worst"] if ze else np.nan, e_grade=grade(ze)))
Q = pd.DataFrame(out); pd.set_option("display.width", 320); pd.set_option("display.max_colwidth", 60)
print(f"\nOf the {len(Q)} rules that pass A in the build years:")
print(f"   still positive in 2021-2026: {int((Q.t_R > 0).sum())};  pass A in 2021-2026: {int(Q.t_grade.str.contains('A').sum())};  pass A in 2011-2015: {int(Q.e_grade.str.contains('A').sum())};  pass A in BOTH unseen periods: {int((Q.t_grade.str.contains('A') & Q.e_grade.str.contains('A')).sum())}")
print(f"   median R per year: build {Q.b_R.median():.2f} -> test {Q.t_R.median():.2f} -> earlier {Q.e_R.median():.2f};  median ratio: build {Q.b_ratio.median():.1f} -> test {Q.t_ratio.median():.1f} -> earlier {Q.e_ratio.median():.1f}")
both = Q[Q.t_grade.str.contains("A") & Q.e_grade.str.contains("A")].copy(); both["min_ratio"] = both[["b_ratio", "t_ratio", "e_ratio"]].min(axis=1); both["min_R"] = both[["b_R", "t_R", "e_R"]].min(axis=1)
cols = ["entry", "sides", "k", "buf", "stop", "filt", "b_n", "b_win", "b_R", "b_ratio", "t_n", "t_win", "t_R", "t_dd", "t_ratio", "t_worst", "t_up", "e_R", "e_dd", "e_ratio", "e_worst"]
print("\nRules passing A in all three periods, best 15 by the weakest period's R per year:")
print(both.sort_values("min_R", ascending=False).head(15)[cols].round(2).to_string(index=False) if len(both) else "   none")
print("\nSize needed for 20% a year and what it implies, for those rules (using the weakest period):")
for _, x in both.sort_values("min_R", ascending=False).head(6).iterrows():
    s = 20 / x.min_R; wd = min(x.t_dd, x.e_dd); ww = min(x.t_worst, x.e_worst, x.b_worst)
    print(f"   {x.entry}, {x.sides}, {x.k}xVIX+{x.buf}%, stop {x.stop}, {x.filt}: risk {s:.1f}% of capital per trade -> worst drawdown seen {wd * s:.1f}%, worst trade seen {ww * s:.1f}%, a full loss would be {s:.1f}%")
both.to_csv("searchcombo_survivors.csv", index=False)
# how much of this is luck: the same count if the unseen periods were unrelated to the build period
p_t = (B.assign(g=[grade(stats(R[k][0][m], R[k][1][m], 2021, 2026)) for k, f, m, z in rows]).g.str.contains("A")).mean()
print(f"\nLuck check: among ALL {len(B)} rules, {100 * p_t:.1f}% pass A in 2021-2026; among the build-period passers it is {100 * Q.t_grade.str.contains('A').mean():.1f}%")
