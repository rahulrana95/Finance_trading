"""Which evidence raises the odds after a deep fall? Each factor checked in 2015-2020 and 2021-2026.

Same events as dipquality.py (first close X% below the 1-year high). A factor only counts as
evidence if it moves the 6- and 12-month result the same way in both periods.
Research only. Run from a folder holding dipquality.py, n500/*.json, lists/n500.csv, data/NIFTY.json.
"""
src = open("dipquality.py").read(); exec(src[:src.index("ev = []")])
ev = []
for s, (name, d) in S.items():
    c = d.c.values; n = len(c); idx = d.index; hi = d.c.rolling(252, min_periods=120).max().values; ma200 = d.c.rolling(200).mean().values
    armed = {X: True for X in (20, 25, 30, 40)}; last = {X: -999 for X in armed}; past = []       # past: (index, ended higher after a year) for 20% falls
    for t in range(252, n):
        depth = (1 - c[t] / hi[t]) * 100
        for X in armed:
            if depth <= 10 or t - last[X] > 252: armed[X] = True
            if armed[X] and depth >= X:
                armed[X] = False; last[X] = t
                if t + 126 >= n: continue
                known = [up for (i, up) in past if i + 252 <= t]                                  # only falls whose year had finished
                pk = int(np.argmax(c[t - 252:t + 1])) + t - 252; mk = float(nf_depth.get(idx[t], np.nan))
                f6 = c[t + 1:t + 127] / c[t]; f12 = c[t + 1:t + 253] / c[t] if t + 252 < n else None
                ev.append(dict(sym=s, date=idx[t], X=X, depth=depth, mkt=mk, excess=depth - mk, days=t - pk, prior=len(known), prior_up=np.mean(known) if known else np.nan,
                               big=rank[s].get(idx[t], 999) <= 100, top50=rank[s].get(idx[t], 999) <= 50, up5y=t >= 1260 and c[pk] > c[t - 1260] * 1.6,
                               one_day=(1 - c[t] / c[t - 1]) * 100, bounce5=(c[t] / c[max(t - 5, 0):t + 1].min() - 1) * 100,
                               end6=(f6[-1] - 1) * 100, max6=(f6.max() - 1) * 100, end12=(f12[-1] - 1) * 100 if f12 is not None else np.nan, min12=(f12.min() - 1) * 100 if f12 is not None else np.nan))
                if X == 20: past.append((t, t + 252 < n and c[t + 252] > c[t]))
E = pd.DataFrame(ev); E["per"] = np.where(E.date.dt.year <= 2020, "2015-20", "2021-26")
def L(g):
    h = g.dropna(subset=["end12"])
    return f"n={len(g):4d} up6 {100 * (g.end6 > 0).mean():3.0f}% +10% {100 * (g.max6 >= 10).mean():3.0f}% up12 {100 * (h.end12 > 0).mean():3.0f}% fell20 {100 * (h.min12 <= -20).mean():3.0f}% avg12 {h.end12.mean():+5.1f}" if len(g) >= 25 else f"n={len(g):4d} too few{'':38s}"
def split(title, base, tests):
    print(f"\n{title}")
    for nm, m in tests:
        print(f"  {nm:44s} | " + " | ".join(f"{p}: {L(base[m(base) & (base.per == p)])}" for p in ("2015-20", "2021-26")))
for X in (25,):
    D = E[(E.X == X) & (E.mkt >= 10)]; A = E[(E.X == X) & (E.mkt < 10)]
    split(f"MARKET IN A FALL, stock fell {X}%: baseline", D, [("all", lambda b: b.sym == b.sym)])
    split("  how far the market is down", D, [("Nifty 10-15% down", lambda b: b.mkt < 15), ("Nifty 15%+ down", lambda b: b.mkt >= 15)])
    split("  stock's fall beyond the market's", D, [("excess under 15 points", lambda b: b.excess < 15), ("excess 15-25", lambda b: (b.excess >= 15) & (b.excess < 25)), ("excess 25+", lambda b: b.excess >= 25)])
    split("  its own earlier falls (finished ones)", D, [("3+ earlier, 2/3 ended higher", lambda b: (b.prior >= 3) & (b.prior_up >= 0.66)), ("3+ earlier, under half ended higher", lambda b: (b.prior >= 3) & (b.prior_up < 0.5)), ("fewer than 3 earlier", lambda b: b.prior < 3)])
    split("  size", D, [("top 50 by trading", lambda b: b.top50), ("top 100", lambda b: b.big), ("outside top 100", lambda b: ~b.big)])
    split("  long-term trend before the fall", D, [("up 60%+ over 5 years", lambda b: b.up5y), ("not", lambda b: ~b.up5y)])
    split("  speed of the fall", D, [("under 40 days from high", lambda b: b.days < 40), ("40-120 days", lambda b: (b.days >= 40) & (b.days < 120)), ("120+ days", lambda b: b.days >= 120)])
    split("  biggest drop on the day itself", D, [("one-day drop under 4%", lambda b: b.one_day < 4), ("4-8%", lambda b: (b.one_day >= 4) & (b.one_day < 8)), ("8%+", lambda b: b.one_day >= 8)])
    split(f"STOCK FELL ALONE ({X}%), baseline", A, [("all", lambda b: b.sym == b.sym)])
    split("  size", A, [("top 50 by trading", lambda b: b.top50), ("outside top 100", lambda b: ~b.big)])
    split("  its own earlier falls", A, [("3+ earlier, 2/3 ended higher", lambda b: (b.prior >= 3) & (b.prior_up >= 0.66)), ("3+ earlier, under half ended higher", lambda b: (b.prior >= 3) & (b.prior_up < 0.5))])
    split("  long-term trend before the fall", A, [("up 60%+ over 5 years", lambda b: b.up5y), ("not", lambda b: ~b.up5y)])
    split("  speed of the fall", A, [("under 40 days from high", lambda b: b.days < 40), ("120+ days", lambda b: b.days >= 120)])
D = E[(E.mkt >= 10)]
split("MARKET IN A FALL, by stock fall size", D, [(f"fell {X}%", (lambda X: lambda b: b.X == X)(X)) for X in (20, 25, 30, 40)])
split("MARKET IN A FALL, combined: Nifty 15%+ down, stock fell 30%", E, [("both", lambda b: (b.mkt >= 15) & (b.X == 30)), ("both + top 100", lambda b: (b.mkt >= 15) & (b.X == 30) & b.big)])
print("\nmarket-fall episodes (X=25) by year:", E[(E.X == 25) & (E.mkt >= 15)].groupby(E.date.dt.year).size().to_dict(), "(Nifty 15%+)")
