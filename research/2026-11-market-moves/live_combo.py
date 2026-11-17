"""Shares + futures ladder run continuously: settings are re-chosen on a rolling basis from the trailing 1 or 2 years, and orders
trigger inside the day at their price levels (daily open/high/low/close stand in for a 5-minute loop; 10 years of 5-minute bars
are not available). Rs 20 L, today's proportions. Research only."""
import json, sys, time, numpy as np, pandas as pd
from ladder import LOT_FRAC, MARGIN, CARRY, ROLL, TRADE
from combo import seg, GRID, lab, SC, CASH, HAIR, DEBIT
r=json.load(open("data/ICICI.json"))["chart"]["result"][0]; q=r["indicators"]["quote"][0]
d=pd.DataFrame({k:q[k] for k in("open","high","low","close")},index=pd.to_datetime(r["timestamp"],unit="s",utc=True).tz_convert("Asia/Kolkata").normalize().tz_localize(None)).dropna()
d=d[~d.index.duplicated()]; d["high"]=d[["open","high","close"]].max(axis=1); d["low"]=d[["open","low","close"]].min(axis=1)
O,H,L,C=(d[k].values for k in("open","high","low","close")); idx=d.index; n=len(d); ref=d.close.rolling(126,min_periods=60).max().values
_cache={}
def pick(a,b,ddlim=0.35):
    best=None
    for g in GRID:
        e,dd,f=seg(a,b,*g); ok=(f==0 and dd>=-ddlim); key=(ok,e if ok else dd)
        if best is None or key>best[0]: best=(key,g)
    return best[1]
def run(start,end,window=None,every=5,fixed=None,intraday=True,eq0=20.0):
    cash=eq0; hs=0.0; pb=None; peak=None; fs=0.0; R=None; level=0; lots=0.0; locked=False; lot_sh=None; mark=C[start-1]
    g=None; forced=0; changes=0; hi=eq0; dd=0.0; curve=[]; ntr=0; held=False
    def equity(p): return cash+hs*p/1e5
    for t in range(start,end):
        # 1. choose settings from data up to yesterday
        if fixed is not None: ng=fixed
        elif g is None or (t-start)%every==0: ng=pick(t-window,t)
        else: ng=g
        if ng!=g:
            if g is not None: changes+=1
            g=ng
        core,tp,step,per,cap=g
        path=[(O[t],True)]+([(H[t],False),(L[t],False)] if C[t]<O[t] else [(L[t],False),(H[t],False)])+[(C[t],False)] if intraday else [(C[t],True)]
        rprev=ref[t-1]
        for b,gap in path:
            a=mark
            def move(x):
                nonlocal cash,mark
                cash+=fs*(x-mark)/1e5; mark=x
            ev=[]
            if b<a:                                             # falling: ladder buys, share buy-back
                if per>0 and not locked:
                    Rr=R if R is not None else (rprev if fs==0 else None)
                    if Rr is not None:
                        k=level+1 if R is not None else 1
                        while Rr*(1-k*step)>=b-1e-9:
                            ev.append((Rr*(1-k*step),"ladder",Rr)); k+=1
                if hs==0 and core>0 and held and peak is not None and peak*0.95>=b: ev.append((peak*0.95,"rebuy",None))
                ev.sort(key=lambda e:-e[0])
            elif b>a:                                           # rising: futures exit, share profit-take
                if fs>0 and R is not None and R<=b: ev.append((R,"exit",None))
                if tp and hs>0 and pb*(1+tp)<=b: ev.append((pb*(1+tp),"take",None))
                ev.sort(key=lambda e:e[0])
            for px,kind,Rr in ev:
                x=b if gap else min(max(px,min(a,b)),max(a,b)); move(x)
                if kind=="ladder":
                    if R is None: R=Rr; lot_sh=LOT_FRAC*equity(x)*1e5/x; level=0
                    level+=1; add=min(per,cap-lots)
                    if add>0: fs+=add*lot_sh; lots+=add; cash-=add*lot_sh*x/1e5*TRADE; ntr+=1
                elif kind=="rebuy": hs=core*equity(x)*1e5/x; cash-=hs*x/1e5*(1+SC); pb=x; ntr+=1
                elif kind=="exit": cash-=fs*x/1e5*TRADE; fs=0;lots=0;level=0;R=None; ntr+=1
                elif kind=="take": cash+=hs*x/1e5*(1-SC); hs=0; peak=x; ntr+=1
            move(b)
            if hs==0 and held: peak=max(peak,b) if peak is not None else b
            if fs>0 and cash+HAIR*hs*b/1e5<MARGIN*fs*b/1e5: cash-=fs*b/1e5*TRADE; fs=0;lots=0;level=0;R=None;locked=True;forced+=1; ntr+=1
            e=equity(b); hi=max(hi,e); dd=min(dd,e/hi-1)
        # end of day: first purchase / rebalance of shares to the chosen share, interest and futures premium
        p=C[t]; e=equity(p)
        if not held and core>0: hs=core*e*1e5/p; cash-=hs*p/1e5*(1+SC); pb=p; held=True; ntr+=1
        elif held and hs>0 and abs(hs*p/1e5-core*e)>0.2*e:       # only move shares when the target share changes a lot
            newh=core*e*1e5/p; cash-=(newh-hs)*p/1e5+abs(newh-hs)*p/1e5*SC; hs=newh; pb=p if hs>0 else pb; ntr+=1
            if hs==0: held=core>0; peak=p
        if core==0 and hs==0: held=False
        if fs>0: cash-=fs*p/1e5*(CARRY/252+ROLL/21)
        cash+=cash*(CASH if cash>0 else DEBIT)/252
        if R is not None and fs==0 and p>=R: R=None; level=0
        if locked and p>=ref[t]*0.999: locked=False
        e=equity(p); curve.append(e)
        if e<=0: break
    cv=pd.Series(curve,index=idx[start:start+len(curve)]); yrs=(cv.index[-1]-cv.index[0]).days/365.25
    by=cv.groupby(cv.index.year).last(); ann=by/by.shift(1).fillna(eq0)-1
    return dict(final=cv.iloc[-1],roi=100*(cv.iloc[-1]/eq0-1),cagr=100*((max(cv.iloc[-1],1e-9)/eq0)**(1/yrs)-1),dd=100*dd,forced=forced,changes=changes,trades=ntr,ann=ann,curve=cv,last=g)
if __name__=="__main__":
    end=n; start=idx.searchsorted(idx[-1]-pd.Timedelta(days=3652)); print("ICICI Bank, %s to %s (10 years), Rs 20 L | share price %.0f -> %.0f"%(idx[start].date(),idx[-1].date(),C[start],C[-1]))
    def show(lab_,x): print("%-66s final Rs %6.1f L | ROI %+6.0f%% | %5.1f%% a year | worst drop %4.0f%% | worst year %+4.0f%% | margin calls %d | setting changes %3d | orders %d"%(lab_,x["final"],x["roi"],x["cagr"],x["dd"],100*x["ann"].min(),x["forced"],x["changes"],x["trades"]))
    print("\nBENCHMARKS (fixed settings, orders trigger inside the day)")
    show("hold the shares only",run(start,end,fixed=(1.0,None,0.05,0,3)))
    show("your ladder only: 2 lots per 5%, max 5 lots",run(start,end,fixed=(0,None,0.05,2,5)))
    show("shares 100% + half a lot per 10% step, max 3 lots",run(start,end,fixed=(1.0,None,0.10,0.5,3)))
    show("same, but orders only at the day's close",run(start,end,fixed=(1.0,None,0.10,0.5,3),intraday=False))
    print("\nROLLING ALGO (settings re-chosen from the trailing window; orders trigger inside the day)")
    res={}
    for window,wl in((504,"2 years"),(252,"1 year")):
        for every,el in((5,"every week"),(21,"every month")):
            t0=time.time(); x=run(start,end,window=window,every=every); res[(wl,el)]=x; show("trailing %s, re-chosen %s"%(wl,el),x)
    x=res[("2 years","every week")]; print("\nYear by year, trailing 2 years re-chosen weekly:"); print((100*x["ann"]).round(1).to_frame("result %").T.to_string())
    print("setting in force today:",lab(x["last"]))
    pd.to_pickle({k:v["curve"] for k,v in res.items()},"live_combo_curves.pkl")
