"""Why does Nifty move more than 0.5% in a day? Counts per year, a rule-based cause for each day, and what could be known before the open."""
import json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from feat import load
n=load("NIFTY","Asia/Kolkata").dropna(); n=n[(n.high>=n.low)&(n.open>0)]
vix=load("INDIAVIX","Asia/Kolkata").close.reindex(n.index).ffill()
D=pd.DataFrame({"cc":n.close.pct_change(),"gap":n.open/n.close.shift(1)-1,"oc":n.close/n.open-1,"vix":vix.shift(1)},index=n.index)
base=pd.DataFrame({"date":n.index})
def prev(name,tz,col):    # last session strictly before the India date
    x=load(name,tz).close.pct_change().rename(col).dropna().to_frame().reset_index(names="xd")
    return pd.merge_asof(base,x,left_on="date",right_on="xd",allow_exact_matches=False).set_index("date")
u=prev("SPX","America/New_York","us"); D["us"]=u.us.where(u.xd!=u.xd.shift(1))        # only a fresh US session
for nm,tz in(("NIKKEI","Asia/Tokyo"),("HSI","Asia/Hong_Kong")): D[nm.lower()]=load(nm,tz).close.pct_change().reindex(n.index)   # same-day Asia
b=prev("BRENT","America/New_York","oil"); D["oil"]=b.oil.where(b.xd!=b.xd.shift(1)); f=prev("USDINR","Europe/London","inr"); D["inr"]=f.inr
fomc=pd.to_datetime(json.load(open("fomc_dates.json")))
D["fomc_next"]=False
for d in fomc:      # India reacts on its first session after the US announcement
    k=n.index.searchsorted(d,side="right")
    if k<len(n.index): D.iloc[k,D.columns.get_loc("fomc_next")]=True
budget=pd.to_datetime(["2008-02-29","2009-02-16","2009-07-06","2010-02-26","2011-02-28","2012-03-16","2013-02-28","2014-02-17","2014-07-10","2015-02-28","2016-02-29","2017-02-01","2018-02-01","2019-02-01","2019-07-05","2020-02-01","2021-02-01","2022-02-01","2023-02-01","2024-02-01","2024-07-23","2025-02-01","2026-02-01"])
elect=pd.to_datetime(["2009-05-18","2014-05-16","2019-05-20","2019-05-23","2024-06-03","2024-06-04","2024-06-05"])
D["india_event"]=D.index.isin(budget)|D.index.isin(elect)
D=D.loc["2008-04":"2026-10"].dropna(subset=["cc","vix"]); D["a"]=D.cc.abs(); D["ycc"]=D.a.shift(1)
print("days",len(D),"| average |move| %.2f%% | median %.2f%%"%(100*D.a.mean(),100*D.a.median()))
print("\n1. HOW OFTEN (close-to-close), share of all days and days per year")
for th in(0.5,1,1.5,2,3): print("  beyond %.1f%%: %4.1f%% of days = %5.1f per year  (up %d, down %d)"%(th,100*(D.a>th/100).mean(),(D.a>th/100).mean()*247,(D.cc>th/100).sum(),(D.cc<-th/100).sum()))
y=D.groupby(D.index.year).agg(days=("a","size"),gt05=("a",lambda x:(x>.005).sum()),gt1=("a",lambda x:(x>.01).sum()),gt2=("a",lambda x:(x>.02).sum()),vix=("vix","mean"))
y["gt05 %"]=(100*y.gt05/y.days).round(0); print(y.round(1).T.to_string())
def cause(r):
    s=np.sign(r.cc)
    if r.india_event: return "1 India event (Budget / election)"
    us=(not np.isnan(r.us)) and abs(r.us)>=0.0075 and np.sign(r.us)==s
    asia=any((not np.isnan(v)) and abs(v)>=0.01 and np.sign(v)==s for v in(r.nikkei,r.hsi))
    if r.fomc_next and (us or asia): return "2 Day after US Fed decision"
    if us and asia: return "3 Global: US overnight + Asia same way"
    if us: return "4 US overnight move same way"
    if asia: return "5 Asia same day, no US lead"
    if (not np.isnan(r.oil)) and abs(r.oil)>=0.03 and np.sign(r.oil)==-s: return "6 Crude oil shock (opposite way)"
    if r.fomc_next: return "2 Day after US Fed decision"
    if r.ycc>=0.01 and r.vix>=20: return "7 No trigger found, but already volatile (VIX>=20, big move yesterday)"
    return "8 No measurable trigger (local news / flows)"
D["cause"]=D.apply(cause,axis=1)
print("\n2. LIKELY CAUSE of move days (first matching rule), % of those days")
T=pd.DataFrame({">0.5%":D[D.a>.005].cause.value_counts(normalize=True),">1%":D[D.a>.01].cause.value_counts(normalize=True),">2%":D[D.a>.02].cause.value_counts(normalize=True),"quiet days <0.5% (same test)":D[D.a<=.005].cause.value_counts(normalize=True)}).fillna(0).sort_index()
print((100*T).round(1).to_string()); print("  n:",(D.a>.005).sum(),(D.a>.01).sum(),(D.a>.02).sum(),(D.a<=.005).sum())
print("\n3. Is it consistent? share of >1% days with a global trigger (rules 2-5), and with no trigger (rule 8), by period")
g=D[D.a>.01]
for lo,hi in((2008,2012),(2013,2017),(2018,2021),(2022,2026)):
    x=g[(g.index.year>=lo)&(g.index.year<=hi)]; print("  %d-%d: global %.0f%% | none %.0f%% | n=%d"%(lo,hi,100*x.cause.str[0].isin(list("2345")).mean(),100*(x.cause.str[0]=="8").mean(),len(x)))
print("  how much of a >1%% day arrives in the gap: %.0f%% on global-trigger days, %.0f%% on no-trigger days"%(100*np.mean(np.clip(g.gap/g.cc,0,1)[g.cause.str[0].isin(list("2345"))]),100*np.mean(np.clip(g.gap/g.cc,0,1)[g.cause.str[0]=="8"])))
print("\n4. WHAT YOU CAN KNOW BEFORE / AT THE OPEN: chance of a >0.5% and >1% day (close-to-close | open-to-close after the gap)")
def tab(lab,key):
    t=D.groupby(key,observed=True).agg(n=("a","size"),cc05=("a",lambda x:100*(x>.005).mean()),cc1=("a",lambda x:100*(x>.01).mean()),oc05=("oc",lambda x:100*(x.abs()>.005).mean()),oc1=("oc",lambda x:100*(x.abs()>.01).mean()))
    print(" "+lab); print(t.round(1).to_string())
tab("yesterday's VIX",pd.cut(D.vix,[0,12,14,17,21,28,100]))
tab("size of US overnight move",pd.cut(D.us.abs()*100,[-1,0.25,0.5,1,1.5,10]))
tab("size of today's opening gap",pd.cut(D.gap.abs()*100,[-1,0.2,0.5,1,10]))
tab("day after Fed decision",D.fomc_next); tab("Budget / election day",D.india_event)
tab("yesterday's own move",pd.cut(D.ycc*100,[-1,0.3,0.7,1.2,20]))
D.to_pickle("causes.pkl")
