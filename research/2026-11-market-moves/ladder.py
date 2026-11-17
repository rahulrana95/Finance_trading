"""Ladder into ICICI Bank futures on dips: buy N lots at every 5% below the 6-month high, sell all when back at that high.
Capital Rs 20 L. One lot = Rs 11.2 L of stock today (700 x ~1,598) = 56% of capital, margin ~Rs 2 L (18% of contract value).
Position size keeps that same proportion to capital in every year (lot sizes are revised over time). Research only."""
import json, sys, numpy as np, pandas as pd
r=json.load(open("data/ICICI.json"))["chart"]["result"][0]; q=r["indicators"]["quote"][0]
s=pd.Series(q["close"],index=pd.to_datetime(r["timestamp"],unit="s",utc=True).tz_convert("Asia/Kolkata").normalize().tz_localize(None)).dropna(); s=s[~s.index.duplicated()]
c=s.values; idx=s.index; n=len(c); ref=s.rolling(126,min_periods=60).max().values; i0=idx.searchsorted(pd.Timestamp("2016-01-01"))
CAP=20.0; LOT_FRAC=700*1598.1/20e5; MARGIN=2.0/(700*1598.1/1e5)     # lot notional as a share of capital; margin as a share of contract value
CARRY=0.06; ROLL=0.0005; TRADE=0.0005                               # futures premium over spot per year; cost per monthly roll; cost per buy or sell
def run(lots_per_step,cap_lots=None,step=0.05,liquidate=True,start=i0,verbose=False):
    eq=CAP; sh=0.0; lot_sh=None; R=None; level=0; lots=0; locked=False; curve=[]; cyc=[]; maxlots=0; maxlev=0; short=0; events=[]; e0=None; d0=None
    for t in range(start,n):
        p=c[t]
        if sh>0:
            eq+=sh*(p-c[t-1])/1e5 - sh*p/1e5*(CARRY/252+ROLL/21)
        if sh>0 and p>=R:                                           # back at the original high: sell everything
            eq-=sh*p/1e5*TRADE; cyc.append(dict(start=d0,end=idx[t],days=(idx[t]-d0).days,lots=lots,gain=eq-e0,pct=100*(eq/e0-1),why="recovered")); sh=0;lots=0;level=0;R=None
        if locked and p>=ref[t]*0.999: locked=False                 # after a forced exit, wait for a fresh 6-month high
        if not locked:
            if sh==0 and p<=ref[t]*(1-step): R=ref[t]; lot_sh=LOT_FRAC*eq*1e5/p; e0=eq; d0=idx[t]; level=0
            if R is not None:
                k=int(np.floor((1-p/R)/step+1e-9))
                while level<k:
                    level+=1; add=lots_per_step if cap_lots is None else min(lots_per_step,cap_lots-lots)
                    if add>0: sh+=add*lot_sh; lots+=add; eq-=add*lot_sh*p/1e5*TRADE
        if sh>0:
            need=MARGIN*sh*p/1e5; maxlots=max(maxlots,lots); maxlev=max(maxlev,sh*p/1e5/max(eq,1e-9))
            if eq<need:
                short+=1; events.append((idx[t].date(),lots,round(eq,1),round(need,1)))
                if liquidate or eq<=0:
                    eq-=sh*p/1e5*TRADE; cyc.append(dict(start=d0,end=idx[t],days=(idx[t]-d0).days,lots=lots,gain=eq-e0,pct=100*(eq/e0-1),why="MARGIN CALL, forced out")); sh=0;lots=0;level=0;R=None;locked=True
        curve.append(eq)
        if eq<=0: break
    cv=pd.Series(curve,index=idx[start:start+len(curve)]); yrs=(cv.index[-1]-cv.index[0]).days/365.25
    cagr=(max(cv.iloc[-1],1e-9)/CAP)**(1/yrs)-1; dd=(cv/cv.cummax()-1).min()
    return dict(final=cv.iloc[-1],cagr=100*cagr,dd=100*dd,low=cv.min(),lowdate=cv.idxmin().date(),maxlots=maxlots,maxlev=maxlev,cycles=pd.DataFrame(cyc),events=events,curve=cv,open_lots=lots)
bh=(c[-1]/c[i0])**(1/((idx[-1]-idx[i0]).days/365.25))-1
print("ICICI Bank %s to %s: %.0f -> %.0f | buy and hold the shares, no leverage: %.1f%% a year (before dividends)"%(idx[i0].date(),idx[-1].date(),c[i0],c[-1],100*bh))
print("assumptions: capital Rs 20 L | 1 lot = %.0f%% of capital in stock | margin %.0f%% of contract value | futures carry %.0f%%/yr | idle cash earns nothing\n"%(100*LOT_FRAC,100*MARGIN,100*CARRY))
def show(lab,x):
    cy=x["cycles"]; fo=(cy.why!="recovered").sum() if len(cy) else 0
    print("%-62s final Rs %6.1f L | CAGR %+6.1f%% | worst drawdown %5.1f%% | lowest capital Rs %5.1f L on %s | most lots held %2d (%.1fx capital) | cycles %d, forced out %d"%(lab,x["final"],x["cagr"],x["dd"],x["low"],x["lowdate"],x["maxlots"],x["maxlev"],len(cy),fo))
A=run(2); show("A. YOUR RULE: 2 lots every 5% down, no limit",A)
B=run(2,cap_lots=5); show("B. 2 lots every 5% down, at most 5 lots (2 + 2 + 1)",B)
C=run(1); show("C. 1 lot every 5% down, no limit",C)
D=run(1,cap_lots=3); show("D. 1 lot every 5% down, at most 3 lots",D)
E=run(1,cap_lots=5,step=0.10); show("E. 1 lot every 10% down, at most 5 lots",E)
F=run(2,liquidate=False); show("A*. your rule IF the broker never forced you out (not real)",F)
for lab,x in(("A",A),("B",B)):
    print("\nVariant %s, every cycle:"%lab); cy=x["cycles"]
    if len(cy): print(cy.assign(start=cy.start.dt.date,end=cy.end.dt.date,gain=cy.gain.round(1),pct=cy.pct.round(1)).rename(columns={"gain":"gain Rs L","pct":"% of capital"}).to_string(index=False))
    if x["events"]: print("margin shortfalls (date, lots, capital Rs L, margin needed Rs L):",x["events"][:6])
print("\nStarting in other years (variant A / variant B CAGR to today):")
for y in(2017,2018,2019,2020,2021,2022,2023):
    st=idx.searchsorted(pd.Timestamp("%d-01-01"%y)); a=run(2,start=st); b=run(2,cap_lots=5,start=st); print("  start %d: A %+6.1f%% (final %.1f L, forced out %d) | B %+6.1f%% (final %.1f L, forced out %d)"%(y,a["cagr"],a["final"],(a["cycles"].why!="recovered").sum() if len(a["cycles"]) else 0,b["cagr"],b["final"],(b["cycles"].why!="recovered").sum() if len(b["cycles"]) else 0))
