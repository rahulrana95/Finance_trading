"""Buy-the-dip rule across many NSE stocks, 2016 onward: buy at the close when a stock is X% below its 6-month high;
sell when it is back at that high, or at a stop-loss, or after 12 months. Costs 0.25% per round trip. Research only."""
import json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
def load(sym):
    try:
        r=json.load(open("stocks/%s.json"%sym))["chart"]["result"][0]; q=r["indicators"]["quote"][0]
        s=pd.Series(q["close"],index=pd.to_datetime(r["timestamp"],unit="s",utc=True).tz_convert("Asia/Kolkata").normalize().tz_localize(None)).dropna()
        s=s[~s.index.duplicated()]; return s if len(s)>600 else None
    except Exception: return None
LOOK=126; COST=0.0025; MAXH=252
def trades(s,X,stop):
    c=s.values; idx=s.index; n=len(c); ref=s.rolling(LOOK,min_periods=60).max().values; i0=idx.searchsorted(pd.Timestamp("2016-01-01")); out=[]; t=max(i0,60)
    armed=True
    while t<n-1:
        if armed and c[t]<=ref[t]*(1-X):
            R=ref[t]; e=c[t]; ex=None; why="open"
            for u in range(t+1,min(n,t+MAXH+1)):
                if c[u]>=R: ex=u; why="back at high"; break
                if stop and c[u]<=e*(1-stop): ex=u; why="stop"; break
            if ex is None:
                if t+MAXH<n: ex=t+MAXH; why="12-month exit"
                else: ex=n-1; why="still open"
            out.append(dict(entry=idx[t],ret=c[ex]/e-1-COST,days=ex-t,why=why,low=c[t:ex+1].min()/e-1)); t=ex+1; armed=False
        else:
            if not armed and c[t]>=ref[t]*(1-X/2): armed=True          # re-arm once the stock has recovered at least half the fall
            t+=1
    return out
G={"Large Nifty stocks (today's members)":open("stocks/_big.txt").read().split(),"Stocks that were large in 2016 and later collapsed or stagnated":open("stocks/_fallen.txt").read().split()}
D={g:{s:x for s in syms if (x:=load(s)) is not None} for g,syms in G.items()}
for g,d in D.items():
    bh=[(x[x.index>="2016-01-01"].iloc[-1]/x[x.index>="2016-01-01"].iloc[0])**(1/((x.index[-1]-x[x.index>="2016-01-01"].index[0]).days/365.25))-1 for x in d.values() if len(x[x.index>="2016-01-01"])>300]
    print("%s: %d stocks loaded | buy-and-hold since 2016: median %+.1f%% a year, worst %+.1f%%, best %+.1f%%"%(g,len(d),100*np.median(bh),100*min(bh),100*max(bh)))
for stop in(None,0.15):
    print("\n"+"="*40+"  stop-loss: %s  "%("none" if not stop else "-%d%% from entry"%(100*stop))+"="*40)
    for g,d in D.items():
        print(g)
        for X in(0.05,0.10,0.15,0.20,0.30):
            T=pd.DataFrame([dict(sym=s,**tr) for s,x in d.items() for tr in trades(x,X,stop)])
            if not len(T): continue
            w=T.ret>0; yrs=T.days.mean()/252
            print("  buy at -%2d%%: %4d trades | won %2.0f%% | avg %+5.1f%% | median %+5.1f%% | worst %+4.0f%% | avg hold %3.0f days | avg worst dip while holding %+4.0f%% | back at high %2.0f%%, stopped %2.0f%%, sold after 12 months %2.0f%% (avg %+.0f%%) | return per year invested %+.0f%%"%(
                100*X,len(T),100*w.mean(),100*T.ret.mean(),100*T.ret.median(),100*T.ret.min(),T.days.mean(),100*T.low.mean(),100*(T.why=="back at high").mean(),100*(T.why=="stop").mean(),100*(T.why=="12-month exit").mean(),
                100*T.ret[T.why=="12-month exit"].mean() if (T.why=="12-month exit").any() else 0,100*T.ret.mean()/max(yrs,1e-9)))
T=pd.DataFrame([dict(sym=s,**tr) for s,x in D["Large Nifty stocks (today's members)"].items() for tr in trades(x,0.10,None)])
by=T.groupby(T.entry.dt.year).ret.agg(["count","mean",lambda x:(x>0).mean()]); by.columns=["trades","avg","won"]
print("\nLarge stocks, buy at -10%, no stop, by year of entry:"); print((by.assign(avg=(100*by.avg).round(1),won=(100*by.won).round(0))).T.to_string())
ic=pd.DataFrame(trades(D["Large Nifty stocks (today's members)"]["ICICIBANK"],0.10,None)); print("\nICICI Bank alone, buy at -10%, no stop:"); print(ic.assign(ret=(100*ic.ret).round(1),low=(100*ic.low).round(1)).to_string(index=False))
