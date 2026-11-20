"""Learn how far Nifty can travel in a week, sell beyond that, test on unseen years.

Owner's framing: say "price will not go beyond X this week", sell a strike 1.5% further out,
and count the week as good if price never crosses X.

Build: 2016-2020 only (walk-forward inside it: fit 2016-18 -> 2019, fit 2016-19 -> 2020, used
to pick ONE rule). Test: 2021 to now, run once with the frozen rule.
Model: LightGBM quantile regression on the week's largest move up and down, compared with a
plain VIX multiple. Trade: entry at the week's first open, defined-risk spread (hedge ~0.8%
further), short delta capped at 0.12, exit if price reaches X, else exit at the close the day
before expiry. Option prices are MODELLED (Black-Scholes, India VIX, assumed skew): not quotes.
Research only. Run from a folder holding data/*.json (see fetch.sh).
"""
import json, math, itertools, warnings
import numpy as np, pandas as pd, lightgbm as lgb
warnings.filterwarnings("ignore")

def load(name, tz="Asia/Kolkata"):
    r = json.load(open(f"data/{name}.json"))["chart"]["result"][0]; q = r["indicators"]["quote"][0]
    return pd.DataFrame({k: q[k] for k in ("open", "high", "low", "close")},
                        index=pd.to_datetime(r["timestamp"], unit="s").tz_localize("UTC").tz_convert(tz).normalize().tz_localize(None)).dropna()
N = load("NIFTY"); N["vix"] = load("INDIAVIX").close.reindex(N.index).ffill(); N = N.loc["2011-01-01":].dropna()
O, H, L, C, V = (N[k].values for k in ("open", "high", "low", "close", "vix")); idx = N.index; n = len(N)
HOLD, DTE, BUF = 5, 7, 1.5          # exit at close of day +5 (day before expiry); 7 sessions to expiry; 1.5% buffer

# ---------- features, all known at the close before entry ----------
c = N.close; r1 = np.log(c).diff()
F = pd.DataFrame(index=idx)
F["vix"] = N.vix; F["vix_rel20"] = N.vix / N.vix.rolling(20).mean(); F["vix_chg5"] = N.vix.pct_change(5); F["vix_pct250"] = N.vix.rolling(250).rank(pct=True)
for w in (5, 10, 20): F[f"rv{w}"] = r1.rolling(w).std() * math.sqrt(252) * 100
F["rv20_vix"] = F.rv20 / N.vix; F["rv5_rv20"] = F.rv5 / F.rv20
pc = c.shift(1); tr = pd.concat([N.high - N.low, (N.high - pc).abs(), (N.low - pc).abs()], axis=1).max(axis=1)
F["atr14"] = tr.ewm(alpha=1/14, adjust=False).mean() / c * 100
F["park5"] = (np.log(N.high / N.low) ** 2).rolling(5).mean() ** .5 * 100
F["up5"] = (N.high.rolling(5).max() / c.shift(5) - 1) * 100; F["dn5"] = (1 - N.low.rolling(5).min() / c.shift(5)) * 100
for w in (1, 5, 20): F[f"ret{w}"] = c.pct_change(w) * 100
for w in (20, 50, 200): F[f"dist{w}"] = (c / c.rolling(w).mean() - 1) * 100
macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean(); hist = macd - macd.ewm(span=9, adjust=False).mean()
F["macd"] = macd / c * 100; F["hist"] = hist / c * 100; F["hist_slope"] = hist.diff() / c * 100
dl = c.diff(); F["rsi"] = 100 - 100 / (1 + dl.clip(lower=0).ewm(alpha=1/14, adjust=False).mean() / (-dl.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean())
F["bbw"] = c.rolling(20).std() / c.rolling(20).mean() * 400
F["dd60"] = (c / c.rolling(60).max() - 1) * 100
def ext(name):   # foreign series: only values dated before the Indian session are used
    x = load(name, "America/New_York").close; return x.reindex(x.index.union(idx)).ffill().shift(1).reindex(idx)
spx, usv = ext("SPX"), ext("USVIX"); F["spx_ret1"] = spx.pct_change().mul(100); F["spx_ret5"] = spx.pct_change(5).mul(100)
F["usvix"] = usv; F["usvix_chg5"] = usv.pct_change(5)
F["inr_ret5"] = ext("USDINR").pct_change(5).mul(100); F["brent_ret5"] = ext("BRENT").pct_change(5).mul(100)
F = F.shift(1)                                              # row i = what was known before the open of day i
F["dow"] = idx.weekday
COLS = list(F.columns)
up = np.array([(H[i:i + HOLD + 1].max() / O[i] - 1) * 100 if i + HOLD < n else np.nan for i in range(n)])
dn = np.array([(1 - L[i:i + HOLD + 1].min() / O[i]) * 100 if i + HOLD < n else np.nan for i in range(n)])
ok = F.notna().all(axis=1).values & ~np.isnan(up)
wk = idx.to_period("W"); monday = np.r_[True, wk[1:] != wk[:-1]] & ok
yr = idx.year.values

# ---------- models ----------
PARAMS = dict(objective="quantile", n_estimators=150, learning_rate=0.03, num_leaves=6, min_child_samples=40,
              subsample=0.8, subsample_freq=1, colsample_bytree=0.7, reg_lambda=5.0, verbose=-1, random_state=7)
def fit_predict(train_mask, pred_mask, q):
    tm = train_mask.copy(); last = np.flatnonzero(tm)[-1]; tm[last - HOLD:last + 1] = False      # purge labels that overlap the next period
    out = {}
    for side, y in (("up", up), ("dn", dn)):
        m = lgb.LGBMRegressor(alpha=q, **PARAMS).fit(F.values[tm], y[tm]); out[side] = m.predict(F.values[pred_mask])
    return out
def vix_bound(mask, k): x = k * V[np.flatnonzero(mask) - 1] * math.sqrt((HOLD + 1) / 252); return {"up": x, "dn": x}

# ---------- modelled trade ----------
CALL_MULT, PUT_MULT = 0.92, 1.12
cdf = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
def bs(S, K, T, s, call):
    if T <= 0: return max(S - K, 0) if call else max(K - S, 0)
    sd = s * math.sqrt(T); d1 = (math.log(S / K) + .5 * sd * sd) / sd
    return S * cdf(d1) - K * cdf(d1 - sd) if call else K * cdf(sd - d1) - S * cdf(-d1)
def delta(S, K, T, s, call):
    sd = s * math.sqrt(T); d1 = (math.log(S / K) + .5 * sd * sd) / sd; return cdf(d1) if call else cdf(-d1)
r50 = lambda x: round(x / 50) * 50
def trade(i, sides, xup, xdn):
    """R (profit / max loss), whether price crossed X, short strike distances %."""
    S = O[i]; s0 = V[i - 1] / 100; T = DTE / 252; w = max(50, r50(0.008 * S)); legs = []; lv = {}
    for side, x in (("call", xup), ("put", xdn)):
        if side not in sides: continue
        call = side == "call"; mult = CALL_MULT if call else PUT_MULT
        K = r50(S * (1 + (x + BUF) / 100)) if call else r50(S * (1 - (x + BUF) / 100))
        while delta(S, K, T, s0 * mult, call) > 0.12: K += 50 if call else -50              # hard limit: short delta <= 0.12
        legs += [(-1, K, call), (1, K + w if call else K - w, call)]; lv[side] = (S * (1 + x / 100) if call else S * (1 - x / 100), K)
    def val(S_, T_, s_):
        ps = [bs(S_, K, T_, s_ * (CALL_MULT if cl else PUT_MULT), cl) for _, K, cl in legs]
        return -sum(sg * p for (sg, _, _), p in zip(legs, ps)), 0.025 * sum(ps) + len(legs) * 0.15 * S_ / 25000
    cr, ec = val(S, T, s0); net = cr - ec
    if net <= 0.002 * w: return None                                                        # nothing worth selling
    crossed = False; out = None
    for j in range(HOLD + 1):
        t = i + j; rem = DTE - j; sm = (V[t - 1] + V[t]) / 200
        for side, (lvl, K) in lv.items():
            call = side == "call"
            if j > 0 and ((O[t] >= lvl) if call else (O[t] <= lvl)): v, x = val(O[t], rem / 252, V[t - 1] / 100); out = v + x; crossed = True
            elif (H[t] >= lvl) if call else (L[t] <= lvl): v, x = val(lvl, (rem - .5) / 252, sm); out = v + x; crossed = True
            if crossed: break
        if crossed: break
    if out is None: v, x = val(C[i + HOLD], (DTE - HOLD - 1) / 252, V[i + HOLD] / 100); out = v + x
    return (net - out) / (w - net), crossed, {k: abs(K / S - 1) * 100 for k, (_, K) in lv.items()}

FILTERS = {"every week": lambda i: True, "MACD>0": lambda i: F.macd.values[i] > 0, "VIX<20": lambda i: V[i - 1] < 20,
           "MACD>0 & VIX<20": lambda i: F.macd.values[i] > 0 and V[i - 1] < 20}
STRUCT = {"put side": ("put",), "call side": ("call",), "both sides": ("call", "put")}
def simulate(mask, bounds, sides, filt):
    rows = []
    for k, i in enumerate(np.flatnonzero(mask)):
        if not FILTERS[filt](i): continue
        t = trade(i, sides, max(bounds["up"][k], 0.3), max(bounds["dn"][k], 0.3))
        if t: rows.append((idx[i], t[0], t[1]))
    return pd.DataFrame(rows, columns=["date", "R", "crossed"])
def summary(T, years):
    if len(T) < 10: return None
    eq = T.R.cumsum(); by = T.groupby(T.date.dt.year).R.sum(); mo = T.groupby([T.date.dt.year, T.date.dt.month]).R.sum()
    return dict(n=len(T), per_yr=len(T) / years, good=100 * (1 - T.crossed.mean()), win=100 * (T.R > 0).mean(), avgR=T.R.mean(), R_yr=T.R.sum() / years,
                dd=(eq - eq.cummax().clip(lower=0)).min(), worst=T.R.min(), worst_month=mo.min(), worst_year=by.min(), up_years=f"{(by > 0).sum()}/{len(by)}")

# ---------- 1. build on 2016-2020: walk-forward predictions for 2019 and 2020 ----------
BUILD = (yr >= 2016) & (yr <= 2020) & ok; TEST = (yr >= 2021) & ok
val_mask = monday & (yr >= 2019) & (yr <= 2020)
PRED = {}
for q in (0.80, 0.90):
    parts = [fit_predict(BUILD & (yr <= y - 1), monday & (yr == y), q) for y in (2019, 2020)]
    PRED[f"model q{int(q * 100)}"] = {s: np.concatenate([p[s] for p in parts]) for s in ("up", "dn")}
for k in (0.8, 1.0, 1.25, 1.5): PRED[f"VIX x {k}"] = vix_bound(val_mask, k)
print(f"Build 2016-2020: {int(BUILD.sum())} daily samples, {int((monday & BUILD).sum())} weekly entries. Validation weeks (2019-2020): {int(val_mask.sum())}")
print("\nA. Does the predicted limit hold? (validation 2019-2020, % of weeks price stayed inside X)")
for nm, b in PRED.items():
    a = np.flatnonzero(val_mask); print(f"  {nm:10s} avg X up {b['up'].mean():4.2f}% dn {b['dn'].mean():4.2f}% | stayed below X-up {100 * (up[a] < b['up']).mean():3.0f}%  above X-dn {100 * (dn[a] < b['dn']).mean():3.0f}%  both {100 * ((up[a] < b['up']) & (dn[a] < b['dn'])).mean():3.0f}%")
grid = []
for (pn, b), (sn, sides), fn in itertools.product(PRED.items(), STRUCT.items(), FILTERS):
    z = summary(simulate(val_mask, b, sides, fn), 2.0)
    if z: grid.append(dict(predictor=pn, structure=sn, filter=fn, **z))
G = pd.DataFrame(grid); G["score"] = G.R_yr + 2 * G.dd.clip(upper=0) / 2.0            # return per year, penalised by drawdown
G = G.sort_values("score", ascending=False)
pd.set_option("display.width", 250)
print(f"\nB. Rule search on validation only ({len(G)} rules tried; R = profit as a multiple of the money at risk per trade)")
print(G.head(10).drop(columns=["score"]).round(2).to_string(index=False))
print(f"   rules with a positive result on validation: {(G.R_yr > 0).sum()} of {len(G)}")
best = G.iloc[0]; print(f"\nFROZEN RULE: {best.predictor} | {best.structure} | {best['filter']}")

# ---------- 2. test once on 2021 onward, model refitted on all of 2016-2020 ----------
test_mask = monday & TEST; years = (idx[test_mask][-1] - idx[test_mask][0]).days / 365.25
TP = {}
for q in (0.80, 0.90): TP[f"model q{int(q * 100)}"] = fit_predict(BUILD, test_mask, q)
for k in (0.8, 1.0, 1.25, 1.5): TP[f"VIX x {k}"] = vix_bound(test_mask, k)
a = np.flatnonzero(test_mask)
print(f"\nC. TEST {idx[a[0]].date()} to {idx[a[-1]].date()} ({len(a)} weeks). Does the limit hold?")
for nm, b in TP.items():
    print(f"  {nm:10s} avg X up {b['up'].mean():4.2f}% dn {b['dn'].mean():4.2f}% | stayed below X-up {100 * (up[a] < b['up']).mean():3.0f}%  above X-dn {100 * (dn[a] < b['dn']).mean():3.0f}%  both {100 * ((up[a] < b['up']) & (dn[a] < b['dn'])).mean():3.0f}%")
def line(nm, T):
    z = summary(T, years)
    return f"  {nm:44s} none" if z is None else (f"  {nm:44s} n={z['n']:3d} good weeks {z['good']:3.0f}% win {z['win']:3.0f}% avg {z['avgR']:+.3f}R  {z['R_yr']:+5.2f}R/yr  maxDD {z['dd']:5.2f}R  "
                                                 f"worst trade {z['worst']:5.2f}R worst month {z['worst_month']:5.2f}R worst yr {z['worst_year']:+5.2f}R up-years {z['up_years']}")
Tb = simulate(test_mask, TP[best.predictor], STRUCT[best.structure], best["filter"])
print("\nD. TEST result of the frozen rule"); print(line("FROZEN: " + best.predictor + ", " + best.structure + ", " + best["filter"], Tb))
print("   by year (R):", {int(k): round(v, 2) for k, v in Tb.groupby(Tb.date.dt.year).R.sum().items()})
print("\nE. For comparison only (not used to choose): other rules on the same test years")
for pn, sn, fn in [(best.predictor, "put side", "every week"), (best.predictor, "both sides", "every week"), ("VIX x 1.0", "both sides", "every week"), ("VIX x 1.0", "both sides", "MACD>0 & VIX<20"),
                   ("VIX x 1.25", "put side", "MACD>0 & VIX<20"), ("model q90", "both sides", "MACD>0 & VIX<20"), ("model q80", "both sides", "every week"), ("model q90", "put side", "every week")]:
    print(line(f"{pn}, {sn}, {fn}", simulate(test_mask, TP[pn], STRUCT[sn], fn)))
allres = [summary(simulate(test_mask, TP[p], s, f), years) for (p, (sn, s), f) in itertools.product(TP, STRUCT.items(), FILTERS)]
rr = np.array([z["R_yr"] for z in allres if z]); print(f"\n   all {len(rr)} rules on test: best {rr.max():+.2f}R/yr, median {np.median(rr):+.2f}R/yr, worst {rr.min():+.2f}R/yr, positive {int((rr > 0).sum())}")
m = lgb.LGBMRegressor(alpha=0.9, **PARAMS).fit(F.values[BUILD], dn[BUILD]); imp = pd.Series(m.feature_importances_, COLS).sort_values(ascending=False)
print("\nF. What the model leans on (down-move model):", ", ".join(f"{k} {v}" for k, v in imp.head(8).items()))
