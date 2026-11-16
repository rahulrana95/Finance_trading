"""Modelled-price weekly spread simulator. Prices come from India VIX with an assumed skew (calls cheaper, puts richer). Research only."""
import math, numpy as np, pandas as pd
from statistics import NormalDist
from feat import load
ND=NormalDist(); cdf=lambda x:0.5*(1+math.erf(x/1.4142135623730951))
d=load("NIFTY","Asia/Kolkata").dropna(); d["vix"]=load("INDIAVIX","Asia/Kolkata").close.reindex(d.index).ffill(); d["pvix"]=d.vix.shift(1); d=d.loc["2008-03":]
O,H,L,C,V,PV=(d[k].values for k in("open","high","low","close","vix","pvix")); idx=d.index; pos={t:i for i,t in enumerate(idx)}
CALL_MULT,PUT_MULT=0.92,1.12          # assumed wing IV as a multiple of VIX
def bs(S,K,T,s,call):
    if T<=0: return max(S-K,0) if call else max(K-S,0)
    sd=s*math.sqrt(T); d1=(math.log(S/K)+0.5*sd*sd)/sd; d2=d1-sd
    return S*cdf(d1)-K*cdf(d2) if call else K*cdf(-d2)-S*cdf(-d1)
def kdelta(S,T,s,dl,call):
    sd=s*math.sqrt(T); d1=ND.inv_cdf(dl) if call else ND.inv_cdf(1-dl); return S*math.exp(-d1*sd+0.5*sd*sd)
r50=lambda x:round(x/50)*50
def build(i,struct,dl,dte=7,wmult=1.0,kc_over=None,kp_over=None):
    S=O[i]; s=PV[i]/100; T=dte/252; w=max(50,r50(0.008*S*wmult))
    kc=kc_over or max(r50(kdelta(S,T,s*CALL_MULT,dl,True)),r50(S)+50); kp=kp_over or min(r50(kdelta(S,T,s*PUT_MULT,dl,False)),r50(S)-50)
    legs={"call":[(-1,kc,1),(1,kc+w,1)],"put":[(-1,kp,0),(1,kp-w,0)],"condor":[(-1,kc,1),(1,kc+w,1),(-1,kp,0),(1,kp-w,0)]}[struct]
    def val(S_,T_,s_):
        ps=[bs(S_,K,T_,s_*(CALL_MULT if cl else PUT_MULT),cl) for _,K,cl in legs]
        return -sum(sg*p for (sg,_,_),p in zip(legs,ps)), 0.025*sum(ps)+len(legs)*0.15*S_/25000
    pts=[]
    for j in range(dte-1):
        t=i+j; rem=dte-j; sm=(PV[t]+V[t])/200
        pts.append((val(O[t],rem/252,PV[t]/100),val(H[t],(rem-.5)/252,sm),val(L[t],(rem-.5)/252,sm),val(C[t],(rem-1)/252,V[t]/100),C[t]))
    return dict(i=i,credit=pts[0][0][0],ecost=pts[0][0][1],width=w,kc=kc if struct!="put" else 9e9,kp=kp if struct!="call" else -9e9,pts=pts,hold=dte-1)
def run(tr,pt,stop,m):
    cr=tr["credit"]; net=cr-tr["ecost"]
    if net<=0: return None
    lvl=m*cr; out=None; why="time"
    for j,(o,h,l,cl,spot) in enumerate(tr["pts"]):
        if j>0 and stop and o[0]>=max(lvl,3*cr) and stop!="strike": out=o[0]+o[1]; why="stop"; break     # gap through the stop: exit at the open
        if stop=="intraday":
            worst=max([h,l],key=lambda x:x[0])
            if worst[0]>=lvl: out=lvl+worst[1]; why="stop"; break
        if stop=="close" and cl[0]>=lvl: out=cl[0]+cl[1]; why="stop"; break
        if stop=="strike" and (spot>=tr["kc"] or spot<=tr["kp"]): out=cl[0]+cl[1]; why="stop"; break
        if pt and cl[0]<=(1-pt)*cr: out=cl[0]+cl[1]; why="target"; break
        if j==tr["hold"]-1: out=cl[0]+cl[1]
    return (net-out)/(tr["width"]-net), why, j, net/tr["width"]
wk=pd.Series(idx.to_period("W"),index=idx); first=[i for i in np.where(~wk.duplicated().values)[0] if i>=1 and i+8<len(d) and not np.isnan(PV[i])]
def stats(rows,lo,hi,risk=4.0):
    """rows: (entry index, R, size). size scales the per-trade max loss (1.0 = risk% of capital)."""
    x=[(idx[i],R*sz) for i,R,sz in rows if lo<=str(idx[i].date())<=hi]
    if len(x)<20: return None
    s=pd.Series([v*risk for _,v in x],index=[a for a,_ in x]); yrs=(pd.Timestamp(hi)-pd.Timestamp(lo)).days/365.25
    cum=s.cumsum(); dd=(cum-cum.cummax().clip(lower=0)).min(); w=s[s>0]; ls=s[s<=0]; by=s.groupby(s.index.year).sum()
    mo=s.groupby([s.index.year,s.index.month]).sum()
    return dict(n=len(s),ret=s.sum()/yrs,dd=dd,worst=s.min(),wmonth=mo.min(),wyear=by.min(),posyears="%d/%d"%((by>0).sum(),len(by)),win=100*len(w)/len(s),
                ratio=(-ls.mean()/w.mean()) if len(w) and len(ls) else float("nan"))
fmt=lambda z:"none" if z is None else "n=%3d ret %+6.1f%%/yr maxDD %6.1f%% worst trade %5.1f%% worst month %5.1f%% worst yr %+6.1f%% up-years %s win %2.0f%% loss/win %4.1f"%(z["n"],z["ret"],z["dd"],z["worst"],z["wmonth"],z["wyear"],z["posyears"],z["win"],z["ratio"])
TRAIN=("2008-04-01","2016-12-15"); VAL=("2017-01-01","2021-12-15"); HOLD=("2022-01-01","2026-10-31")
