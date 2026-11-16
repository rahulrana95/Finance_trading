import json, sys, numpy as np, pandas as pd
def load(p):
    r=json.load(open(p))["chart"]["result"][0]; q=r["indicators"]["quote"][0]
    d=pd.DataFrame({k:q[k] for k in("open","high","low","close")},
        index=pd.to_datetime(r["timestamp"],unit="s",utc=True).tz_convert("Asia/Kolkata").normalize().tz_localize(None))
    return d.dropna()
n=load(sys.argv[1]); v=load(sys.argv[2])["close"].rename("vix")
n=n[~n.index.duplicated()]; v=v[~v.index.duplicated()]
df=n.join(v,how="left"); df["vix"]=df["vix"].ffill()
c=df.close
macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean()
sig=macd.ewm(span=9,adjust=False).mean(); hist=macd-sig
# signals known at previous close (no look-ahead)
df["line_gt_sig"]=(macd>sig).shift(1); df["macd_gt0"]=(macd>0).shift(1)
df["hist_rising"]=(hist>hist.shift(1)).shift(1); df["pvix"]=df.vix.shift(1)
df["fresh_cross"]=((macd>sig)!=(macd.shift(5)>sig.shift(5))).shift(1)  # crossed in last 5 sessions
print("data",df.index[0].date(),df.index[-1].date(),len(df))
wk=df.index.to_period("W"); first=~pd.Series(wk,index=df.index).duplicated()
rows=[]; idx=df.index
for i in np.where(first.values)[0]:
    if i<40 or i+5>=len(df) or np.isnan(df.pvix.iloc[i]): continue
    e=df.open.iloc[i]; sd=e*df.pvix.iloc[i]/100*np.sqrt(8/365); k=1.28*sd
    w=df.iloc[i:i+6]
    rows.append(dict(date=idx[i],put_touch=w.low.min()<=e-k,call_touch=w.high.max()>=e+k,
        put_end=w.close.iloc[-1]<=e-k,call_end=w.close.iloc[-1]>=e+k,
        ret=w.close.iloc[-1]/e-1,dist=k/e,
        **{s:bool(df[s].iloc[i]) for s in("line_gt_sig","macd_gt0","hist_rising","fresh_cross")}))
t=pd.DataFrame(rows).set_index("date")
print("weeks",len(t),t.index[0].date(),"avg strike distance %.2f%%"%(100*t.dist.mean()))
def rate(x):
    k,nn=int(x.sum()),len(x); p=k/nn if nn else float("nan")
    se=(p*(1-p)/nn)**.5 if nn else 0
    return "%5.1f%% ±%4.1f (n=%d)"%(100*p,196*se,nn)
print("\nBASELINE  put touched:",rate(t.put_touch),"| call touched:",rate(t.call_touch))
print("BASELINE  put breached at end:",rate(t.put_end),"| call at end:",rate(t.call_end))
def directed(t,s):
    bull=t[s]
    with_=pd.concat([t.put_touch[bull],t.call_touch[~bull]])     # sell the side MACD says is safe
    against=pd.concat([t.call_touch[bull],t.put_touch[~bull]])
    return with_,against
for s in("line_gt_sig","macd_gt0","hist_rising"):
    print("\n==",s,"  bullish weeks: %d of %d"%(t[s].sum(),len(t)))
    print("  bullish: put touched",rate(t.put_touch[t[s]]),"| call touched",rate(t.call_touch[t[s]]))
    print("  bearish: put touched",rate(t.put_touch[~t[s]]),"| call touched",rate(t.call_touch[~t[s]]))
    w,a=directed(t,s); print("  FOLLOW MACD side touched:",rate(w),"| OPPOSITE side touched:",rate(a))
    for lo,hi in(("2008","2013"),("2014","2019"),("2020","2026")):
        w,a=directed(t.loc[lo:hi],s); print("   ",lo,hi,"follow",rate(w),"| opposite",rate(a))
s="line_gt_sig"
for name,m in(("fresh cross (<=5 sessions)",t.fresh_cross),("old signal",~t.fresh_cross),
              ("line>sig AND macd>0 / line<sig AND macd<0",t.line_gt_sig==t.macd_gt0),
              ("VIX<14",t.dist<1.28*.14*(8/365)**.5),("VIX>=20",t.dist>=1.28*.20*(8/365)**.5)):
    w,a=directed(t[m],s); print("\n",name,": follow",rate(w),"| opposite",rate(a))
print("\nmean 6-session return: bullish %.2f%%  bearish %.2f%%"%(100*t.ret[t[s]].mean(),100*t.ret[~t[s]].mean()))
print("\n--- either side touched, by MACD above/below zero")
t["any"]=t.put_touch|t.call_touch
for lo,hi in(("2008","2026"),("2008","2013"),("2014","2019"),("2020","2026")):
    x=t.loc[lo:hi]; print(lo,hi,"macd>0:",rate(x["any"][x.macd_gt0]),"| macd<0:",rate(x["any"][~x.macd_gt0]),"| all:",rate(x["any"]))
