"""How reliable can reversal / breakout / range statements be made, and what does that reliability cost? Nifty daily, three periods."""
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from feat import load
d=load("NIFTY","Asia/Kolkata").dropna(); d=d[(d.high>=d.low)&(d.open>0)].loc["2007-09":]
o,h,l,c=(d[k].values for k in("open","high","low","close")); C=pd.Series(c); n=len(d); r=C.pct_change()
rsi2=(100-100/(1+r.clip(lower=0).rolling(2).mean()/(-r.clip(upper=0)).rolling(2).mean())).values
s200=C.rolling(200).mean().values; hh20=C.shift(1).rolling(20).max().values; ll20=C.shift(1).rolling(20).min().values
macd=(C.ewm(span=12,adjust=False).mean()-C.ewm(span=26,adjust=False).mean()).values
idx=d.index; P=[("2008-14",(idx>="2008-06-01")&(idx<"2015-01-01")),("2015-20",(idx>="2015-01-01")&(idx<"2021-01-01")),("2021-26",idx>="2021-01-01")]
H=5; E=np.full(n,np.nan); E[:-1]=o[1:]                                   # entry = next open
fh=np.full(n,np.nan); fl=np.full(n,np.nan); fc=np.full(n,np.nan)
for t in range(n-H): fh[t]=h[t+1:t+1+H].max(); fl[t]=l[t+1:t+1+H].min(); fc[t]=c[t+H]
ok=~np.isnan(fc)&(np.arange(n)>250)
def tp_sl(sig,tp,sl,side=1):
    """walk forward bar by bar: which comes first, target or stop? (if both in one bar, count the stop)"""
    w=[];pnl=[]
    for t in np.flatnonzero(sig&ok):
        e=E[t]; res=None
        for k in range(1,H+1):
            hi,lo=h[t+k],l[t+k]
            up=(hi/e-1) if side>0 else (1-lo/e); dn=(1-lo/e) if side>0 else (hi/e-1)
            if dn>=sl: res=-sl; break
            if up>=tp: res=tp; break
        if res is None: res=side*(c[t+H]/e-1)
        w.append(res>0); pnl.append(res)
    return np.array(w),np.array(pnl)
def rep(lab,sig):
    print("\n"+lab)
    for nm,m in P:
        s=sig&m&ok
        if s.sum()<15: print("  %s: too few (%d)"%(nm,s.sum())); continue
        up5=(fc[s]>E[s]).mean(); b=(fc[m&ok]>E[m&ok]).mean()
        line="  %s n=%3d | closes higher after 5 days %2.0f%% (all days %2.0f%%)"%(nm,s.sum(),100*up5,100*b)
        for tp,sl in((0.003,0.03),(0.005,0.02),(0.01,0.01)):
            w,p=tp_sl(s,tp,sl); wb,pb=tp_sl(m&ok&(np.arange(n)%3==0),tp,sl)
            line+=" | target +%.1f%% / stop -%.0f%%: wins %2.0f%% (all days %2.0f%%), avg %+.2f%% per trade (all days %+.2f%%)"%(100*tp,100*sl,100*w.mean(),100*wb.mean(),100*p.mean(),100*pb.mean())
        print(line)
rep("REVERSAL: sharp 2-day drop (RSI2 below 10) while above the 200-day average -> buy",(rsi2<10)&(c>s200))
rep("REVERSAL: sharp 2-day drop (RSI2 below 10), any trend -> buy",rsi2<10)
rep("BREAKOUT: close above the 20-day high -> buy",(c>hh20)&~(np.roll(c,1)>np.roll(hh20,1)))
rep("BREAKOUT: close above the 20-day high with MACD above zero -> buy",(c>hh20)&~(np.roll(c,1)>np.roll(hh20,1))&(macd>0))
print("\nBREAKOUT 'holds' (no close back below the old 20-day high within 5 days):")
bo=(c>hh20)&~(np.roll(c,1)>np.roll(hh20,1))
for nm,m in P:
    s=np.flatnonzero(bo&m&ok); held=[c[t+1:t+1+H].min()>=hh20[t] for t in s]; print("  %s n=%3d holds %2.0f%%"%(nm,len(s),100*np.mean(held)))
