"""Shares + futures ladder on one stock, with the settings re-chosen every January from the previous 1 or 2 years (walk-forward).
Sizes are in today's proportions: capital Rs 20 L, one futures lot = 56% of capital in stock, margin 18% of contract value.
Shares can be pledged as margin at an 85% value. Costs: shares 0.12% a side, futures 0.05% a side + 6%/yr premium; spare cash earns 5%."""
import itertools, numpy as np, pandas as pd
from ladder import c, idx, ref, LOT_FRAC, MARGIN, CARRY, ROLL, TRADE
n=len(c); SC=0.0012; CASH=0.05; HAIR=0.85; DEBIT=0.12
def seg(a,b,core,tp,step,per,cap,eq0=20.0):
    """simulate days a..b-1; returns final equity, max drawdown, forced exits"""
    p=c[a]; hs=core*eq0*1e5/p; cash=eq0-hs*p/1e5*(1+SC); pb=p; peak_sale=None
    fs=0.0; R=None; level=0; lots=0.0; locked=False; lot_sh=None; forced=0; hi=eq0; dd=0.0; eq=eq0
    for t in range(a+1,b):
        p=c[t]
        if fs>0: cash+=fs*(p-c[t-1])/1e5-fs*p/1e5*(CARRY/252+ROLL/21)
        cash+=cash*(CASH if cash>0 else DEBIT)/252
        eq=cash+hs*p/1e5
        # shares: optional profit-taking, then buy back after a 5% dip from the peak since the sale
        if tp and hs>0 and p>=pb*(1+tp): cash+=hs*p/1e5*(1-SC); hs=0; peak_sale=p
        elif hs==0 and core>0:
            peak_sale=max(peak_sale,p)
            if p<=peak_sale*0.95: hs=core*eq*1e5/p; cash-=hs*p/1e5*(1+SC); pb=p
        # futures ladder
        if fs>0 and p>=R: cash-=fs*p/1e5*TRADE; fs=0;lots=0;level=0;R=None
        if locked and p>=ref[t]*0.999: locked=False
        if per>0 and not locked:
            if fs==0 and R is None and p<=ref[t]*(1-step): R=ref[t]; lot_sh=LOT_FRAC*eq*1e5/p; level=0
            if R is not None:
                k=int(np.floor((1-p/R)/step+1e-9))
                while level<k:
                    level+=1; add=min(per,cap-lots)
                    if add>0: fs+=add*lot_sh; lots+=add; cash-=add*lot_sh*p/1e5*TRADE
                if fs==0 and p>=R: R=None
        if fs>0 and cash+HAIR*hs*p/1e5<MARGIN*fs*p/1e5:
            cash-=fs*p/1e5*TRADE; fs=0;lots=0;level=0;R=None;locked=True;forced+=1
        eq=cash+hs*p/1e5; hi=max(hi,eq); dd=min(dd,eq/hi-1)
        if eq<=0: return 0.0,-1.0,forced+1
    return eq,dd,forced
GRID=[(core,tp,step,per,cap) for core in(0,0.25,0.5,0.75,1.0) for tp in(None,0.10,0.20) for step in(0.05,0.10) for per in(0,0.5,1,2) for cap in(3,5,8)
      if not (per==0 and (cap!=3 or step!=0.05)) and not (core==0 and tp is not None) and not (core==0 and per==0)]
def lab(g):
    core,tp,step,per,cap=g
    s="shares %3.0f%% of capital"%(100*core)+(", sell at +%.0f%% and rebuy on a 5%% dip"%(100*tp) if tp else ", held")
    return s+(" | futures: %.1f lot per %.0f%% step, max %d lots"%(per,100*step,cap) if per>0 else " | no futures")
yi=lambda y:idx.searchsorted(pd.Timestamp("%d-01-01"%y))
def pick(a,b,ddlim):
    best=None
    for g in GRID:
        e,dd,f=seg(a,b,*g); ok=(f==0 and dd>=-ddlim)
        key=(ok,e if ok else dd)
        if best is None or key>best[0]: best=(key,g,e,dd,f)
    return best[1:]
if __name__=='__main__':
    print("settings tried each time: %d\n"%len(GRID))
    years=list(range(2018,2027))
    def walk(window,ddlim):
        eq=20.0; rows=[]; curve_hi=20.0; worst=0
        for y in years:
            g,te,tdd,tf=pick(yi(y-window),yi(y),ddlim); a,b=yi(y),(yi(y+1) if y<2026 else n)
            e,dd,f=seg(a,b,*g,eq0=eq); rows.append(dict(year=y,ret=100*(e/eq-1),dd=100*dd,forced=f,train_ret=100*(te/20-1),choice=lab(g))); eq=e
        R=pd.DataFrame(rows); yrs=(idx[-1]-idx[yi(2018)]).days/365.25
        return eq,100*((max(eq,1e-9)/20)**(1/yrs)-1),R
    def fixed(g):
        eq=20.0; rows=[]
        for y in years:
            a,b=yi(y),(yi(y+1) if y<2026 else n); e,dd,f=seg(a,b,*g,eq0=eq); rows.append((y,100*(e/eq-1),100*dd,f)); eq=e
        yrs=(idx[-1]-idx[yi(2018)]).days/365.25; return eq,100*((max(eq,1e-9)/20)**(1/yrs)-1),rows
    print("TEST PERIOD 2018 to Nov 2026, Rs 20 L at the start. Each January the settings are chosen using only earlier data.")
    for window in(1,2):
        for ddlim in(0.25,0.35,1.0):
            eq,cg,R=walk(window,ddlim)
            print("\nchosen from the previous %d year(s); rule: highest return with no margin call and drawdown within %s -> final Rs %.1f L, %.1f%% a year, worst year %+.0f%%, worst drawdown inside a year %.0f%%, margin calls %d"%(window,"%.0f%%"%(100*ddlim) if ddlim<1 else "any size",eq,cg,R.ret.min(),R.dd.min(),R.forced.sum()))
            if ddlim==0.35: print(R.assign(ret=R.ret.round(1),dd=R.dd.round(1),train_ret=R.train_ret.round(1)).rename(columns={"ret":"result %","dd":"worst dip %","train_ret":"looked like % in training"}).to_string(index=False))
    print("\nFIXED SETTINGS over the same period, for comparison:")
    for nm,g in(("hold the shares only (100%)",(1.0,None,0.05,0,3)),("your ladder only: 2 lots per 5%, max 5",(0,None,0.05,2,5)),("shares 50% + 1 lot per 10%, max 3",(0.5,None,0.10,1,3)),
                ("shares 100% + 0.5 lot per 10%, max 3",(1.0,None,0.10,0.5,3)),("shares 75% + 1 lot per 10%, max 3",(0.75,None,0.10,1,3)),("shares 100%, sell at +20% and rebuy on dips",(1.0,0.20,0.05,0,3))):
        eq,cg,rows=fixed(g); print("  %-44s final Rs %6.1f L | %5.1f%% a year | worst year %+4.0f%% | worst dip %4.0f%% | margin calls %d"%(nm,eq,cg,min(r[1] for r in rows),min(r[2] for r in rows),sum(r[3] for r in rows)))
    allr=[]
    for g in GRID:
        eq,cg,rows=fixed(g); allr.append((cg,min(r[2] for r in rows),sum(r[3] for r in rows),g))
    allr.sort(key=lambda x:-x[0]); print("\nBest fixed settings WITH HINDSIGHT (not achievable in advance):")
    for cg,dd,f,g in allr[:5]: print("  %5.1f%% a year | worst dip %4.0f%% | margin calls %d | %s"%(cg,dd,f,lab(g)))
    safe=[x for x in allr if x[2]==0 and x[1]>=-35]; print("Best with hindsight among those with no margin call and dips within 35%:")
    for cg,dd,f,g in safe[:3]: print("  %5.1f%% a year | worst dip %4.0f%% | %s"%(cg,dd,lab(g)))
    print("\nWHAT THE ALGO WOULD CHOOSE TODAY (drawdown limit 35%, no margin call):")
    for window in(1,2):
        a=idx.searchsorted(idx[-1]-pd.Timedelta(days=365*window)); g,e,dd,f=pick(a,n,0.35); print("  from the last %d year(s): %s  (made %+.1f%% in that window, worst dip %.0f%%)"%(window,lab(g),100*(e/20-1),100*dd))
