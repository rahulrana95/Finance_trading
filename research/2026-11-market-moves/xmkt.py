import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from feat import load
def study(px,vx,tz,name,H=6):
    n=load(px,tz).dropna(); n=n[(n.high>=n.low)&(n.open>0)]; iv=load(vx,tz).close.reindex(n.index).ffill()
    c,o,h,l=n.close,n.open,n.high,n.low; r=np.log(c).diff(); s1=lambda x:x.shift(1)
    macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean()
    rv22=np.sqrt((r**2).rolling(22).mean()); dn22=np.sqrt((np.minimum(r,0)**2).rolling(22).mean())
    f={"ret22":s1(np.log(c).diff(22)),"macd":s1(macd/c),"d50":s1(c/c.rolling(50).mean()-1),
       "rsi14":s1(100-100/(1+r.clip(lower=0).rolling(14).mean()/(-r.clip(upper=0)).rolling(14).mean())),"skew":-s1(dn22/rv22)}
    pct=lambda x:x.rolling(750,min_periods=250).rank(pct=True)
    calm=pd.concat([pct(v) for v in f.values()],axis=1).mean(axis=1)
    hi=pd.concat([h.shift(-k) for k in range(H)],axis=1).max(axis=1); lo=pd.concat([l.shift(-k) for k in range(H)],axis=1).min(axis=1)
    sig=s1(iv)/100*np.sqrt(8/365); zu=(hi/o-1)/sig; zd=(1-lo/o)/sig; ze=((c.shift(-(H-1))/o-1)/sig).abs()
    ok=calm.notna()&zu.notna()&ze.notna()&sig.notna(); y=(np.maximum(zu,zd)>=1.28)
    print("\n%s  %s to %s"%(name,n.index[ok][0].date(),n.index[ok][-1].date()))
    print("  period      touch%% calm>=0.5 | calm<0.5 | ended-beyond%% calm>=0.5 | calm<0.5 |  n")
    yrs=sorted(set(n.index[ok].year)); edges=[(a,min(a+4,yrs[-1])) for a in range(yrs[0],yrs[-1]+1,5)]
    for a,b in edges+[(yrs[0],yrs[-1])]:
        m=ok&(n.index.year>=a)&(n.index.year<=b); hi_=m&(calm>=.5); lo_=m&(calm<.5)
        if hi_.sum()<50 or lo_.sum()<50: continue
        print("  %d-%d        %5.1f      | %5.1f    |        %5.1f          | %5.1f    | %d"%(a,b,100*y[hi_].mean(),100*y[lo_].mean(),100*(ze[hi_]>=1.28).mean(),100*(ze[lo_]>=1.28).mean(),m.sum()))
    return pd.DataFrame({"calm":calm,"y":y,"ze":ze,"vix":s1(iv)})[ok]
A=study("SPXL","USVIXL","America/New_York","S&P 500 / VIX")
B=study("NDX","VXN","America/New_York","Nasdaq 100 / VXN")
try: C=study("RUT","RVX","America/New_York","Russell 2000 / RVX")
except Exception as e: print("RUT fail",e)
N=study("NIFTY","INDIAVIX","Asia/Kolkata","Nifty / India VIX")
print("\nNifty by year: touch% when calm>=0.5 vs <0.5, and avg VIX")
g=N.groupby([N.index.year,N.calm>=.5]).y.mean().unstack()*100; g["vix"]=N.groupby(N.index.year).vix.mean(); g["all"]=N.groupby(N.index.year).y.mean()*100
print(g.round(1).T.to_string())
