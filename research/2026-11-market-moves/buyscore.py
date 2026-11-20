"""Can a 'chance of +4 / +5 / +10%' score for stocks be trusted? Built to 2020, checked on 2021-2026.

Universe: today's Nifty 500 members (so past results flatter the losers that dropped out).
Every 5th trading day for every stock is one sample. Outcome over the next 63 trading days
(about 3 months), on closing prices:
  up_T    : closed T% or more above the entry close at some point
  first_T : reached +T% BEFORE closing 10% below entry (the honest version: gain before pain)
  dd10    : closed 10% or more below entry at some point
Two scorers, both fitted on samples up to 2020 only:
  table : how often it happened in the same bucket (depth below 6-month high x trend x swing size x market)
  model : LightGBM on the raw inputs
Checked on 2021-2026: is a 70% score right about 70% of the time, and do the top picks beat the average?
Research only. Run from a folder holding n500/*.json, lists/n500.csv and data/NIFTY.json.
"""
import csv, json, warnings
import numpy as np, pandas as pd, lightgbm as lgb
from numpy.lib.stride_tricks import sliding_window_view
warnings.filterwarnings("ignore")
H, STEP, TARGETS = 63, 5, (4, 5, 10)

def load(path):
    r = json.load(open(path))["chart"]["result"][0]; q = r["indicators"]["quote"][0]
    adj = r["indicators"].get("adjclose", [{}])[0].get("adjclose") or q["close"]
    d = pd.Series(adj, index=pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("Asia/Kolkata").normalize().tz_localize(None)).dropna()
    return d[~d.index.duplicated()]
nifty = load("data/NIFTY.json"); mkt_up = (nifty > nifty.rolling(200).mean())
rows = []
for r in csv.DictReader(open("lists/n500.csv")):
    s = r["Symbol"].strip()
    try: c = load(f"n500/{s}.json")
    except Exception: continue
    if len(c) < 400: continue
    v = c.values; n = len(v); ret = np.log(c).diff()
    f = pd.DataFrame({"depth": (1 - c / c.rolling(126, min_periods=60).max()) * 100, "above200": (c > c.rolling(200).mean()).astype(float), "d200": (c / c.rolling(200).mean() - 1) * 100,
                      "d50": (c / c.rolling(50).mean() - 1) * 100, "vol20": ret.rolling(20).std() * 100, "vol60": ret.rolling(60).std() * 100, "ret5": c.pct_change(5) * 100, "ret20": c.pct_change(20) * 100,
                      "ret120": c.pct_change(120) * 100, "dd250": (c / c.rolling(250, min_periods=120).max() - 1) * 100})
    dl = c.diff(); f["rsi"] = 100 - 100 / (1 + dl.clip(lower=0).ewm(alpha=1/14, adjust=False).mean() / (-dl.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean())
    f["mkt_up"] = mkt_up.reindex(c.index).ffill().astype(float)
    w = sliding_window_view(v[1:], H) / v[:n - H, None]                         # row t: closes t+1..t+H relative to close t
    out = pd.DataFrame(index=c.index[:n - H])
    down = np.where((w <= 0.90).any(1), (w <= 0.90).argmax(1), H + 1)
    for T in TARGETS:
        hit = (w >= 1 + T / 100); first = np.where(hit.any(1), hit.argmax(1), H + 1)
        out[f"up{T}"] = hit.any(1); out[f"first{T}"] = hit.any(1) & (first < down)
    out["dd10"] = (w <= 0.90).any(1); out["end"] = (w[:, -1] - 1) * 100
    z = f.join(out, how="inner").iloc[250::STEP].dropna(); z["sym"] = s; rows.append(z)
D = pd.concat(rows); D["year"] = D.index.year
TR, TE = D[D.year <= 2020], D[D.year >= 2021]
print(f"{D.sym.nunique()} stocks, {len(D):,} samples ({len(TR):,} to 2020, {len(TE):,} from 2021); horizon {H} trading days")
print("\nA. How often it simply happens (no skill needed)")
print(pd.DataFrame({k: [100 * TR[k].mean(), 100 * TE[k].mean()] for k in [f"up{T}" for T in TARGETS] + [f"first{T}" for T in TARGETS] + ["dd10"]}, index=["to 2020", "2021-2026"]).round(1).to_string())
def bucket(d):
    part = lambda x: pd.Series(x, index=d.index).astype(int).astype(str)
    return part(np.digitize(d.depth, [3, 7, 12, 20, 30])) + "|" + part(d.above200) + "|" + part(np.digitize(d.vol60, [1.6, 2.2, 3.0])) + "|" + part(d.mkt_up)
TR = TR.assign(b=bucket(TR)); TE = TE.assign(b=bucket(TE))
FEAT = ["depth", "above200", "d200", "d50", "vol20", "vol60", "ret5", "ret20", "ret120", "dd250", "rsi", "mkt_up"]
def check(name, p, y):
    y = pd.Series(np.asarray(y, bool)); q = pd.qcut(p, 10, labels=False, duplicates="drop"); t = pd.DataFrame({"p": p, "y": y.values, "q": q}).groupby("q").agg(pred=("p", "mean"), actual=("y", "mean"), n=("y", "size"))
    auc = (pd.Series(p).rank().values[y.values].sum() - y.sum() * (y.sum() + 1) / 2) / (y.sum() * (~y).sum())
    return f"  {name:6s} lowest tenth: said {100 * t.pred.iloc[0]:3.0f}% got {100 * t.actual.iloc[0]:3.0f}% | middle: said {100 * t.pred.iloc[len(t) // 2]:3.0f}% got {100 * t.actual.iloc[len(t) // 2]:3.0f}% | top tenth: said {100 * t.pred.iloc[-1]:3.0f}% got {100 * t.actual.iloc[-1]:3.0f}% | avg error {100 * (t.pred - t.actual).abs().mean():4.1f} pts | ranking skill (0.5 = none) {auc:.2f}", t
P = {}
print("\nB. Scores fitted to 2020, checked on 2021-2026")
for k in [f"first{T}" for T in TARGETS] + [f"up{T}" for T in TARGETS] + ["dd10"]:
    base = TR[k].mean(); g = TR.groupby("b")[k].agg(["sum", "count"]); tab = ((g["sum"] + 50 * base) / (g["count"] + 50))
    pt = TE.b.map(tab).fillna(base).values
    m = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.03, num_leaves=15, min_child_samples=300, subsample=0.7, subsample_freq=1, colsample_bytree=0.7, reg_lambda=10, verbose=-1, random_state=3).fit(TR[FEAT], TR[k])
    pm = m.predict_proba(TE[FEAT])[:, 1]; P[k] = (pt, pm)
    print(f"{k} (base {100 * TE[k].mean():.0f}% in 2021-2026)"); print(check("table", pt, TE[k])[0]); print(check("model", pm, TE[k])[0])
print("\nC. 'Best buys': each sample date, the 20 stocks with the highest model score for 'first10' (+10% before -10%), 2021-2026")
TE = TE.assign(score=P["first10"][1], risk=P["dd10"][1], tscore=P["first10"][0])
for nm, col in (("model", "score"), ("table", "tscore")):
    top = TE.groupby(level=0, group_keys=False).apply(lambda g: g.nlargest(20, col))
    print(f"  {nm}: top-20 picks: +10% before -10% in {100 * top.first10.mean():.0f}% (all stocks {100 * TE.first10.mean():.0f}%) | +5% first {100 * top.first5.mean():.0f}% ({100 * TE.first5.mean():.0f}%) | +4% first {100 * top.first4.mean():.0f}% ({100 * TE.first4.mean():.0f}%) | fell 10% at some point {100 * top.dd10.mean():.0f}% ({100 * TE.dd10.mean():.0f}%) | avg 3-month result {top.end.mean():+.1f}% ({TE.end.mean():+.1f}%) | worst tenth of picks {top.end.quantile(.1):+.1f}%")
    by = top.groupby(top.index.year).agg(first10=("first10", "mean"), end=("end", "mean")); allby = TE.groupby(TE.index.year).agg(first10=("first10", "mean"), end=("end", "mean"))
    print("     by year, picks vs all (avg 3-month result %):", {int(y): f"{by.end[y]:+.1f} vs {allby.end[y]:+.1f}" for y in by.index})
safe = TE.groupby(level=0, group_keys=False).apply(lambda g: g[g.risk <= g.risk.quantile(.3)].nlargest(20, "score"))
print(f"  model, picks limited to the safest 30% by fall-risk: +10% first {100 * safe.first10.mean():.0f}% | +5% first {100 * safe.first5.mean():.0f}% | +4% first {100 * safe.first4.mean():.0f}% | fell 10% {100 * safe.dd10.mean():.0f}% | avg {safe.end.mean():+.1f}% | worst tenth {safe.end.quantile(.1):+.1f}%")
m = lgb.LGBMClassifier(n_estimators=200, learning_rate=0.03, num_leaves=15, min_child_samples=300, verbose=-1, random_state=3).fit(TR[FEAT], TR["first10"])
print("\nD. What the model leans on:", ", ".join(f"{a} {b}" for a, b in sorted(zip(FEAT, m.feature_importances_), key=lambda x: -x[1])[:8]))
print("\nE. Table view (to 2020 -> 2021-2026), '+5% before -10%' by depth below the 6-month high, stock above its 200-day average, market above its 200-day average")
for dlab, lo, hi in (("0-3%", -1, 3), ("3-7%", 3, 7), ("7-12%", 7, 12), ("12-20%", 12, 20), ("20-30%", 20, 30), ("30%+", 30, 100)):
    out = f"  {dlab:7s}"
    for a2 in (1, 0):
        for nm, d in (("to 2020", TR), ("2021-26", TE)):
            x = d[(d.depth > lo) & (d.depth <= hi) & (d.above200 == a2) & (d.mkt_up == 1)]; out += f" | {'above' if a2 else 'below'} 200d {nm}: {100 * x.first5.mean():3.0f}% dd10 {100 * x.dd10.mean():3.0f}% (n={len(x):5d})"
    print(out)
