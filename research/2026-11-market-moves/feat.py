"""Build the feature table. Every feature for entry day t uses only data known before the open of t,
except 'gap' (the opening gap, known at the open)."""
import json, numpy as np, pandas as pd
D="data/"
def load(n,tz):
    r=json.load(open(D+n+".json"))["chart"]["result"][0]; q=r["indicators"]["quote"][0]
    d=pd.DataFrame({k:q[k] for k in("open","high","low","close")},
        index=pd.to_datetime(r["timestamp"],unit="s",utc=True).tz_convert(tz).normalize().tz_localize(None))
    d=d.dropna(subset=["close"]); return d[~d.index.duplicated()]
def build(H=6):
    n=load("NIFTY","Asia/Kolkata").dropna(); n=n[(n.high>=n.low)&(n.open>0)]
    iv=load("INDIAVIX","Asia/Kolkata").close.reindex(n.index).ffill()
    c,o,h,l=n.close,n.open,n.high,n.low; r=np.log(c).diff()
    F=pd.DataFrame(index=n.index)
    s1=lambda x:x.shift(1)                                   # known at previous close
    F["vix"]=s1(iv); F["lvix"]=np.log(F.vix)
    F["vix_chg1"]=s1(np.log(iv).diff()); F["vix_chg5"]=s1(np.log(iv).diff(5)); F["vix_chg20"]=s1(np.log(iv).diff(20))
    F["vix_pct250"]=s1(iv.rolling(250).rank(pct=True)); F["vix_vs_ma20"]=s1(iv/iv.rolling(20).mean()-1)
    F["vov20"]=s1(np.log(iv).diff().rolling(20).std())
    pk=np.sqrt((np.log(h/l)**2)/(4*np.log(2)))               # Parkinson daily vol
    gk=np.sqrt(np.maximum(0.5*np.log(h/l)**2-(2*np.log(2)-1)*np.log(c/o)**2,0))
    on=np.log(o/c.shift(1))                                  # overnight gap
    for w in(1,5,22,66):
        F[f"rv{w}"]=s1(np.sqrt((r**2).rolling(w).mean())*np.sqrt(252)*100)
        F[f"pk{w}"]=s1(np.sqrt((pk**2).rolling(w).mean())*np.sqrt(252)*100)
    F["gk5"]=s1(np.sqrt((gk**2).rolling(5).mean())*np.sqrt(252)*100)
    F["on5"]=s1(np.sqrt((on**2).rolling(5).mean())*np.sqrt(252)*100); F["on22"]=s1(np.sqrt((on**2).rolling(22).mean())*np.sqrt(252)*100)
    F["vrp22"]=np.log(F.vix/F.rv22); F["vrp5"]=np.log(F.vix/F.rv5); F["rv5_22"]=np.log(F.rv5/F.rv22); F["rv22_66"]=np.log(F.rv22/F.rv66)
    F["dnvol22"]=s1(np.sqrt((np.minimum(r,0)**2).rolling(22).mean())*np.sqrt(252)*100); F["skew22"]=F.dnvol22/F.rv22
    for w in(1,5,22,66): F[f"ret{w}"]=s1(np.log(c).diff(w))
    F["absret1"]=F.ret1.abs(); F["maxabs5"]=s1(r.abs().rolling(5).max()); F["maxabs22"]=s1(r.abs().rolling(22).max())
    macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean(); sig=macd.ewm(span=9,adjust=False).mean()
    F["macd"]=s1(macd/c); F["macd_hist"]=s1((macd-sig)/c)
    F["d50"]=s1(c/c.rolling(50).mean()-1); F["d200"]=s1(c/c.rolling(200).mean()-1)
    F["dd250"]=s1(c/c.rolling(250).max()-1); F["up250"]=s1(c/c.rolling(250).min()-1)
    F["rsi14"]=s1(100-100/(1+r.clip(lower=0).rolling(14).mean()/(-r.clip(upper=0)).rolling(14).mean()))
    F["adx_proxy"]=s1(np.log(c).diff(10).abs()/r.abs().rolling(10).sum())      # efficiency ratio (trendiness)
    F["gap"]=np.log(o/c.shift(1)); F["absgap"]=F.gap.abs()
    F["dow"]=n.index.dayofweek; F["dom"]=n.index.day; F["month"]=n.index.month
    bn=load("BANKNIFTY","Asia/Kolkata").close.reindex(n.index).ffill()
    F["bn_rel5"]=s1(np.log(bn).diff(5)-np.log(c).diff(5)); F["bn_rv22"]=s1(np.log(bn).diff().rolling(22).std()*np.sqrt(252)*100)/F.rv22
    # foreign series: last value dated strictly before the India date
    def ext(name,tz="America/New_York"):
        x=load(name,tz).close; return x
    base=pd.DataFrame({"date":n.index})
    def asof(df):
        df=df.dropna().reset_index(names="xd"); m=pd.merge_asof(base,df,left_on="date",right_on="xd",allow_exact_matches=False).set_index("date"); return m.drop(columns="xd")
    spx=ext("SPX"); uv=ext("USVIX"); v3=ext("VIX3M"); vv=ext("VVIX"); mv=ext("MOVE"); ty=ext("US10Y"); dx=ext("DXY"); nq=ext("NASDAQ"); hy=ext("HYG"); em=ext("EEM")
    U=pd.DataFrame({"us_ret1":np.log(spx).diff(),"us_ret5":np.log(spx).diff(5),"us_ret22":np.log(spx).diff(22),
        "us_rv5":np.log(spx).diff().rolling(5).std()*np.sqrt(252)*100,"us_rv22":np.log(spx).diff().rolling(22).std()*np.sqrt(252)*100,
        "usvix":uv,"usvix_chg1":np.log(uv).diff(),"usvix_chg5":np.log(uv).diff(5),"us_term":(uv/v3),"vvix":vv,"move":mv,"move_chg5":np.log(mv).diff(5),
        "us10y_chg5":ty.diff(5),"dxy_chg5":np.log(dx).diff(5),"dxy_chg22":np.log(dx).diff(22),"nq_ret5":np.log(nq).diff(5),
        "hyg_ret5":np.log(hy).diff(5),"hyg_ret22":np.log(hy).diff(22),"eem_ret5":np.log(em).diff(5),"eem_rv22":np.log(em).diff().rolling(22).std()*np.sqrt(252)*100})
    F=F.join(asof(U))
    F["us_dd250"]=asof(pd.DataFrame({"x":spx/spx.rolling(250).max()-1})).x
    for name,tz in(("USDINR","Europe/London"),("BRENT","America/New_York"),("GOLD","America/New_York"),("HSI","Asia/Hong_Kong"),("NIKKEI","Asia/Tokyo")):
        x=load(name,tz).close; lr=np.log(x).diff()
        F=F.join(asof(pd.DataFrame({f"{name.lower()}_ret5":np.log(x).diff(5),f"{name.lower()}_rv22":lr.rolling(22).std()*np.sqrt(252)*100})))
    F["vix_vs_usvix"]=np.log(F.vix/F.usvix)
    # targets over H sessions from the open of t
    hi=pd.concat([h.shift(-k) for k in range(H)],axis=1).max(axis=1); lo=pd.concat([l.shift(-k) for k in range(H)],axis=1).min(axis=1)
    ce=c.shift(-(H-1))
    T=pd.DataFrame({"entry":o,"up":hi/o-1,"dn":1-lo/o,"end":ce/o-1,"sig":F.vix/100*np.sqrt(8/365)},index=n.index)
    T["zu"]=T.up/T.sig; T["zd"]=T.dn/T.sig; T["zmax"]=T[["zu","zd"]].max(axis=1); T["zend"]=T.end/T.sig
    T.loc[ce.isna(),["up","dn","end","zu","zd","zmax","zend"]]=np.nan
    ok=F.vix.notna()&T.zu.notna()&F.rv66.notna()&(F.index>="2008-04-01")
    return F[ok],T[ok]
if __name__=="__main__":
    F,T=build(); print(F.shape,F.index[0].date(),F.index[-1].date()); print(F.isna().mean().sort_values().tail(8).round(3).to_string())
    print(T[["up","dn","zu","zd","zmax"]].describe().round(3).to_string())
    F.to_pickle("F.pkl"); T.to_pickle("T.pkl")
