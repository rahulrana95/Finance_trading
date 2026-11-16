"""Which MACD timeframe / setting works best as a 'rough week ahead' filter? Signal known at the previous close."""
import json, numpy as np, pandas as pd, itertools
T=pd.read_pickle("T.pkl"); F=pd.read_pickle("F.pkl")
from feat import load
n=load("NIFTY","Asia/Kolkata").dropna(); c=n.close
ema=lambda x,k:x.ewm(span=k,adjust=False).mean()
y=(T.zmax>=1.28); yend=(T.zend.abs()>=1.28); up=(T.end>0)
tr=T.index<="2016-12-31"; te=T.index>="2017-01-01"
def line(nm,pos,idx=None):
    p=pos.reindex(T.index); ok=p.notna()
    out=[]
    for m in(tr,te):
        mm=m&ok; a=y[mm&(p==1)].mean(); b=y[mm&(p==0)].mean(); out+= [100*a,100*b,100*(b-a)]
    mm=te&ok; d=100*((up[mm]==(p[mm]==1)).mean())
    print("  %-34s train: %4.1f vs %4.1f (gap %4.1f) | test: %4.1f vs %4.1f (gap %4.1f) | above-zero share %2.0f%% | direction hit %4.1f%%"%(nm,*out,100*p[ok].mean(),d))
print("touch rate when MACD ABOVE zero vs BELOW zero (lower when above = useful); 'gap' is the difference in points")
print("\nDAILY bars, MACD line vs zero")
for f,s in((5,13),(8,17),(12,26),(19,39),(24,52),(50,100)):
    m=ema(c,f)-ema(c,s); line("daily %d/%d zero line"%(f,s),(m>0).astype(float).shift(1))
print("\nDAILY bars, MACD line vs signal line (crossover state)")
for f,s,g in((12,26,9),(5,13,5),(19,39,9),(8,17,9)):
    m=ema(c,f)-ema(c,s); line("daily %d/%d/%d crossover"%(f,s,g),(m>ema(m,g)).astype(float).shift(1))
print("\nWEEKLY bars (last completed week)")
w=c.resample("W-FRI").last().dropna()
for f,s in((12,26),(6,13),(4,9)):
    m=ema(w,f)-ema(w,s); pos=(m>0).astype(float); pos.index=pos.index+pd.Timedelta(days=1)       # usable from the following Monday
    line("weekly %d/%d zero line"%(f,s),pos.reindex(c.index,method="ffill"))
m=ema(w,12)-ema(w,26); pos=(m>ema(m,9)).astype(float); pos.index=pos.index+pd.Timedelta(days=1); line("weekly 12/26/9 crossover",pos.reindex(c.index,method="ffill"))
print("\nMONTHLY bars (last completed month)")
mo=c.resample("ME").last().dropna(); m=ema(mo,12)-ema(mo,26); pos=(m>0).astype(float); pos.index=pos.index+pd.Timedelta(days=1); line("monthly 12/26 zero line",pos.reindex(c.index,method="ffill"))
print("\nCOMBINED")
d=(ema(c,12)-ema(c,26)>0).astype(float).shift(1); wm=ema(w,12)-ema(w,26); wp=(wm>0).astype(float); wp.index=wp.index+pd.Timedelta(days=1); wp=wp.reindex(c.index,method="ffill")
line("daily AND weekly above zero",((d==1)&(wp==1)).astype(float).where(d.notna()&wp.notna()))
line("daily OR weekly above zero",((d==1)|(wp==1)).astype(float).where(d.notna()&wp.notna()))
# hourly (about 3 years only)
r=json.load(open("nsei_1h.json"))["chart"]["result"][0]; q=r["indicators"]["quote"][0]
h=pd.Series(q["close"],index=pd.to_datetime(r["timestamp"],unit="s",utc=True).tz_convert("Asia/Kolkata").tz_localize(None)).dropna()
print("\nHOURLY bars (only %s to %s), value at the previous day's last bar; all of this is in the 'test' column"%(h.index[0].date(),h.index[-1].date()))
for f,s in((12,26),(24,52),(48,104)):
    m=ema(h,f)-ema(h,s); last=(m>0).astype(float).groupby(m.index.normalize()).last().shift(1)
    p=last.reindex(T.index); ok=p.notna()
    print("  hourly %d/%d zero line: touch %4.1f vs %4.1f (gap %4.1f) n=%d | direction hit %4.1f%%"%(f,s,100*y[ok&(p==1)].mean(),100*y[ok&(p==0)].mean(),100*(y[ok&(p==0)].mean()-y[ok&(p==1)].mean()),ok.sum(),100*(up[ok]==(p[ok]==1)).mean()))
dd=d.reindex(T.index); ok=dd.notna()&(T.index>=h.index[0])
print("  (same period) daily 12/26 zero line: touch %4.1f vs %4.1f n=%d"%(100*y[ok&(dd==1)].mean(),100*y[ok&(dd==0)].mean(),ok.sum()))
