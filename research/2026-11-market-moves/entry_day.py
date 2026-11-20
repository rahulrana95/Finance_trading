"""The frozen rule by entry weekday (expiry = next week's Tuesday). Reuses searchsize.py's engine.

Thursday and Friday entries are closer than 6 days to expiry and are shown for comparison only.
Research only; modelled option prices. Run from a folder holding data/*.json and searchsize.py.
"""
src = open("searchsize.py").read(); head = src[:src.index("ENTRY = {")]
exec(head.replace("EXP[i] = j if (idx[j] - idx[i]).days >= 6 else -1; break", "EXP[i] = j; break"))
valid = np.zeros(n, bool); valid[260:] = True; valid &= (EXP > 0) & (EXP - np.arange(n) >= 2)
yr = idx.year.values; M = X["MACD>0"].values.astype(bool)
def st(ii, r, lo, hi):
    m = (yr[ii] >= lo) & (yr[ii] <= hi) & ~np.isnan(r); x = r[m]
    years = hi - lo + 1 if hi < 2026 else (idx[-1] - pd.Timestamp(f"{lo}-01-01")).days / 365.25
    eq = np.cumsum(x); byy = pd.Series(x).groupby(yr[ii][m]).sum()
    return f"n={len(x):3d} win {100 * (x > 0).mean():3.0f}% {x.sum() / years:+5.2f} R/yr DD {(eq - np.maximum(np.maximum.accumulate(eq), 0)).min():5.2f} worst {x.min():5.2f} up {int((byy > 0).sum())}/{len(byy)}"
for label, use in (("with MACD>0", True), ("every week", False)):
    print(f"\nBoth sides, limit 0.8 x VIX move, strike 1.5% beyond, exit at the limit, {label}")
    for d, wd in {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4}.items():
        ii = np.flatnonzero((idx.weekday == wd) & valid); r = np.array([trade(i, ("call", "put"), 0.8, 1.5, "limit") for i in ii]); m = M[ii] if use else np.ones(len(ii), bool)
        print(f"  {d:10s} | " + " | ".join(f"{lo}-{str(hi)[2:]}: {st(ii[m], r[m], lo, hi)}" for lo, hi in ((2011, 2015), (2016, 2020), (2021, 2026))))
