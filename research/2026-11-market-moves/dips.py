"""After a stock falls X% from its recent high, how long until it is back at that high, and what happened in between? Daily closes."""
import sys, json, numpy as np, pandas as pd
name=sys.argv[1] if len(sys.argv)>1 else "ICICI"; start=sys.argv[2] if len(sys.argv)>2 else "2016-01-01"; LOOK=int(sys.argv[3]) if len(sys.argv)>3 else 126
r=json.load(open("data/%s.json"%name))["chart"]["result"][0]; q=r["indicators"]["quote"][0]
s=pd.Series(q["close"],index=pd.to_datetime(r["timestamp"],unit="s",utc=True).tz_convert("Asia/Kolkata").normalize().tz_localize(None)).dropna(); s=s[~s.index.duplicated()]
c=s.values; idx=s.index; n=len(s); i0=idx.searchsorted(pd.Timestamp(start))
ref=s.rolling(LOOK,min_periods=20).max().values; refpos=s.rolling(LOOK,min_periods=20).apply(np.argmax,raw=True).values
print("%s daily closes %s to %s | events from %s | 'recent high' = highest close of the previous %d trading days (~%d months) | last close %.1f"%(name,idx[0].date(),idx[-1].date(),start,LOOK,LOOK//21,c[-1]))
def events(X):
    out=[]; t=i0
    while t<n:
        if c[t]<=ref[t]*(1-X):
            R=ref[t]; hi=int(t-(min(LOOK,t+1)-1)+refpos[t]); rec=None
            for u in range(t+1,n):
                if c[u]>=R: rec=u; break
            end=rec if rec is not None else n-1
            low=c[t:end+1].min(); lowi=t+int(np.argmin(c[t:end+1]))
            f=lambda k:(c[t+k]/c[t]-1) if t+k<n else np.nan
            out.append(dict(date=idx[t],high_date=idx[hi],high=R,price=c[t],days_down=t-hi,low=low,low_date=idx[lowi],total_fall=low/R-1,further=low/c[t]-1,
                            rec_date=idx[rec] if rec is not None else pd.NaT,rec_days=(rec-t) if rec is not None else np.nan,rec_cal=(idx[rec]-idx[t]).days if rec is not None else np.nan,
                            r21=f(21),r63=f(63),r126=f(126),r252=f(252),gain_to_high=R/c[t]-1))
            t=end+1
        else: t+=1
    return pd.DataFrame(out)
rows=[]; ALL={}
for X in(5,7,10,13,15,17,20,23,25,30):
    E=events(X/100); ALL[X]=E
    if not len(E): rows.append(dict(fall="%d%%"%X,times=0)); continue
    rc=E.rec_days.dropna(); k=len(E)
    w=lambda d:"%d of %d"%((E.rec_days<=d).sum(),k)
    rows.append({"fall":"%d%%"%X,"times":k,"recovered":"%d of %d"%(len(rc),k),"days high->fall (median)":int(E.days_down.median()),
      "further fall after (avg)":"%.1f%%"%(100*E.further.mean()),"further fall (worst)":"%.1f%%"%(100*E.further.min()),"total fall from high (avg)":"%.1f%%"%(100*E.total_fall.mean()),
      "recover: median days":int(rc.median()) if len(rc) else None,"avg days":int(rc.mean()) if len(rc) else None,"longest days":int(rc.max()) if len(rc) else None,
      "back in 1 month":w(21),"3 months":w(63),"6 months":w(126),"12 months":w(252),
      "avg after 1m":"%+.1f%%"%(100*E.r21.mean()),"3m":"%+.1f%%"%(100*E.r63.mean()),"6m":"%+.1f%%"%(100*E.r126.mean()),"higher after 3m":"%d of %d"%((E.r63>0).sum(),E.r63.notna().sum()),
      "gain needed to regain high":"%.1f%%"%(100*E.gain_to_high.mean())})
T=pd.DataFrame(rows).set_index("fall"); pd.set_option("display.width",300); pd.set_option("display.max_columns",40)
print("\n(days = trading days; 21 = about 1 month)\n"); print(T.T.to_string())
for X in(10,20):
    E=ALL[X]
    if len(E):
        print("\nEvery %d%% fall:"%X)
        for _,e in E.iterrows():
            print("  high %s %.0f -> down %d%% on %s at %.0f (%d days) | lowest %.0f on %s (%.0f%% below high) | %s | 1m %s 3m %s 6m %s"%(e.high_date.date(),e.high,X,e.date.date(),e.price,e.days_down,e.low,e.low_date.date(),-100*e.total_fall,
                  ("back at high %s, %d trading days (%.1f months)"%(e.rec_date.date(),e.rec_days,e.rec_cal/30.4)) if pd.notna(e.rec_date) else "NOT yet back at high",
                  *[("%+.0f%%"%(100*v) if pd.notna(v) else "n/a") for v in(e.r21,e.r63,e.r126)]))
