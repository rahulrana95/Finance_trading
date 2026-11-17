"""Top 300 NSE stocks by traded value: how reliably did each recover from falls since 2016, and how did the dip-ladder rule do on it?"""
import csv, json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from screen import rule
meta={r["Symbol"].strip():(r["Company Name"].strip(),r["Industry"].strip()) for r in csv.DictReader(open("lists/n500.csv"))}
def load(sym):
    try:
        r=json.load(open("n500/%s.json"%sym))["chart"]["result"][0]; q=r["indicators"]["quote"][0]
        d=pd.DataFrame({"close":q["close"],"volume":q["volume"]},index=pd.to_datetime(r["timestamp"],unit="s",utc=True).tz_convert("Asia/Kolkata").normalize().tz_localize(None)).dropna()
        return d[~d.index.duplicated()]
    except Exception: return None
D={s:x for s in meta if (x:=load(s)) is not None and len(x)>250}
tv=pd.Series({s:(x.close*x.volume).iloc[-250:].mean()/1e7 for s,x in D.items()}).sort_values(ascending=False)   # Rs crore a day
top=list(tv.index[:300]); print("stocks with data: %d | top 300 by average daily traded value over the last year: from Rs %.0f crore down to Rs %.0f crore a day"%(len(D),tv.iloc[0],tv.iloc[299]))
def dips(c,ref,a,X):
    out=[]; t=a; n=len(c)
    while t<n:
        if c[t]<=ref[t]*(1-X):
            R=ref[t]; rec=None
            for u in range(t+1,n):
                if c[u]>=R: rec=u; break
            end=rec if rec is not None else n-1
            out.append(dict(t=t,rec=(rec-t) if rec is not None else None,open_days=(n-1-t) if rec is None else 0,deep=c[t:end+1].min()/R-1)); t=end+1
        else: t+=1
    return out
rows=[]; START=pd.Timestamp("2016-01-01"); MID=pd.Timestamp("2021-06-01")
for s in top:
    x=D[s].close; c=x.values; idx=x.index; n=len(c); ref=x.rolling(126,min_periods=60).max().values
    a=max(idx.searchsorted(START),60); m=idx.searchsorted(MID)
    r=dict(stock=s,name=meta[s][0],industry=meta[s][1],traded=tv[s],since=idx[0].year if idx[0]>pd.Timestamp("2014-02-01") else 2014,full=idx[0]<=pd.Timestamp("2016-06-30"))
    yrs=(idx[-1]-idx[a]).days/365.25; r["hold"]=100*((c[-1]/c[a])**(1/yrs)-1) if yrs>1 else np.nan
    sx=x[a:]; r["maxdd"]=100*(sx/sx.cummax()-1).min(); r["below_high_now"]=100*(c[-1]/sx.max()-1)
    for X in(0.10,0.20,0.30):
        dp=dips(c,ref,a,X); k="%d"%(100*X)
        r["n"+k]=len(dp); r["rec"+k]=100*np.mean([d["rec"] is not None for d in dp]) if dp else np.nan
        r["rec12_"+k]=100*np.mean([(d["rec"] is not None and d["rec"]<=252) for d in dp]) if dp else np.nan
        recs=[d["rec"] for d in dp if d["rec"] is not None]; r["med"+k]=np.median(recs) if recs else np.nan; r["long"+k]=max(recs+[d["open_days"] for d in dp]) if dp else 0
        r["open"+k]=max([d["open_days"] for d in dp]+[0])
        if X==0.10:
            for lab,lo,hi in(("h1",a,m),("h2",m,n)):
                dd=[d for d in dp if lo<=d["t"]<hi]; r["rec12_"+lab]=100*np.mean([(d["rec"] is not None and d["rec"]<=252) for d in dd]) if dd else np.nan; r["n_"+lab]=len(dd)
    if r["full"]:
        for lab,i,j in(("all",a,n),("h1",a,m),("h2",m,n)):
            e,dd,f=rule(c,ref,i,j); y=(idx[j-1]-idx[i]).days/365.25; r["rule_"+lab]=100*((max(e,1e-9)/20)**(1/y)-1); r["drop_"+lab]=100*dd; r["mc_"+lab]=f
    by=sx.groupby(sx.index.year).last(); r["up"]="%d/%d"%((by.pct_change().dropna()>0).sum(),len(by)-1)
    rows.append(r)
T=pd.DataFrame(rows).set_index("stock"); T.to_pickle("screen300.pkl"); F=T[T.full]
print("with price history back to mid-2016: %d of 300 (the rest listed later and cannot be judged over a full cycle)"%len(F))
print("\nHOW COMMON IS 'ALWAYS RECOVERS'? (stocks with full history, 2016 to Nov 2026)")
print("  every 10%% fall got back to its earlier high (or is still open for under 6 months): %d"%((F.rec10==100)|((F.open10<126)&(F.rec10>=100*(F.n10-1)/F.n10))).sum())
alw=F[(F.open10<126)&(F.open20<126)&(F.long10<=504)&(F.rec12_10>=70)]
print("  ... and never took longer than 2 years, with 70%%+ back inside a year: %d"%len(alw))
print("  at least one 10%% fall still not recovered after a year or more: %d | after 2 years or more: %d"%((F.open10>=252).sum(),(F.open10>=504).sum()))
print("  dip-ladder rule: margin call on %d of %d; rule lost money on %d"%((F.mc_all>0).sum(),len(F),(F.rule_all<0).sum()))
print("  does first-half recovery predict second-half recovery? rank corr %.2f | rule return first vs second half %.2f"%(F.rec12_h1.rank().corr(F.rec12_h2.rank()),F.rule_h1.rank().corr(F.rule_h2.rank())))
g=F[F.rec12_h1>=90]; h=F[F.rec12_h1<60]
print("  stocks with 90%%+ quick recoveries in 2016-21 (%d): in 2021-26 %.0f%% of their dips were back within a year, margin calls on %d | stocks under 60%% (%d): %.0f%%, margin calls on %d"%(len(g),g.rec12_h2.mean(),(g.mc_h2>0).sum(),len(h),h.rec12_h2.mean(),(h.mc_h2>0).sum()))
S=F[(F.open10<126)&(F.open20<126)&(F.long10<=504)&(F.rec12_10>=75)&(F.rec12_h1>=70)&(F.rec12_h2>=70)&(F.mc_all==0)&(F.mc_h1==0)&(F.mc_h2==0)&(F.rule_h1>5)&(F.rule_h2>5)&(F.drop_all>=-60)&(F.n10>=6)].copy()
S["score"]=S[["rule_h1","rule_h2"]].min(axis=1); S=S.sort_values("score",ascending=False)
pd.set_option("display.width",260); pd.set_option("display.max_rows",80)
print("\nSHORTLIST: recovered from every 10%% and 20%% fall within 2 years, 75%%+ within a year, steady in both halves, no margin call, rule above 5%% a year in both halves: %d stocks"%len(S))
cols=["name","industry","hold","rule_all","rule_h1","rule_h2","drop_all","maxdd","n10","rec12_10","med10","long10","n20","below_high_now","up"]
print(S[cols].assign(name=S.name.str[:26],industry=S.industry.str[:22]).round(1).rename(columns={"hold":"shares %/yr","rule_all":"rule %/yr","rule_h1":"rule 16-21","rule_h2":"rule 21-26","drop_all":"rule worst drop","maxdd":"share worst fall","n10":"10% dips","rec12_10":"% back in 12m","med10":"typical days","long10":"longest days","n20":"20% dips","below_high_now":"now vs high %","up":"up years"}).to_string())
print("\nby industry in the shortlist:",S.industry.value_counts().to_dict())
print("by industry among all %d full-history stocks: share that made the shortlist"%len(F)); ind=(S.industry.value_counts()/F.industry.value_counts()).dropna().sort_values(ascending=False); print((100*ind).round(0).to_dict())
S[cols].to_csv("shortlist.csv")
