"""Exhaustive search for an 80%-reliable direction signal on Nifty daily bars: every single, pair and triple of ~45 conditions,
4 holding periods, both directions. Three-way split so the search cannot fool us: find on 2008-2014, confirm on 2015-2020, final check 2021-2026."""
import itertools, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from feat import load
from patterns import signals
d=load("NIFTY","Asia/Kolkata").dropna(); d=d[(d.high>=d.low)&(d.open>0)].loc["2007-09":]
vix=load("INDIAVIX","Asia/Kolkata").close.reindex(d.index).ffill().values
L,S,ST=signals(d); o,h,l,c=(d[k].values for k in("open","high","low","close")); C=pd.Series(c); n=len(d)
rec=lambda a,k=3: pd.Series(a).rolling(k).max().fillna(0).astype(bool).values
cond={}
for k,v in L.items(): cond["UP:"+k]=rec(v)
for k,v in S.items(): cond["DN:"+k]=rec(v)
for k,v in ST.items(): cond[k]=v
r=C.pct_change()
def rsi(k): u=r.clip(lower=0).rolling(k).mean(); dn=(-r.clip(upper=0)).rolling(k).mean(); return (100-100/(1+u/dn)).values
r14,r2=rsi(14),rsi(2)
cond.update({"RSI14 below 30":r14<30,"RSI14 above 70":r14>70,"RSI2 below 10":r2<10,"RSI2 above 90":r2>90,
 "3 down closes in a row":(r<0).rolling(3).sum().values==3,"3 up closes in a row":(r>0).rolling(3).sum().values==3,
 "VIX above 25":vix>25,"VIX below 13":vix<13,"VIX up 20%+ in 5 days":(pd.Series(vix).pct_change(5)>0.2).values,"VIX down 15%+ in 5 days":(pd.Series(vix).pct_change(5)<-0.15).values,
 "5%+ below 20-day high":(c/C.rolling(20).max().values-1)<-0.05,"at 20-day high":c>=C.rolling(20).max().values,
 "close in bottom fifth of 10-day range":((c-pd.Series(l).rolling(10).min().values)/(pd.Series(h).rolling(10).max().values-pd.Series(l).rolling(10).min().values+1e-9))<0.2,
 "close in top fifth of 10-day range":((c-pd.Series(l).rolling(10).min().values)/(pd.Series(h).rolling(10).max().values-pd.Series(l).rolling(10).min().values+1e-9))>0.8})
w=C.copy(); w.index=d.index; wk=w.resample("W-FRI").last().dropna(); wm=wk.ewm(span=12,adjust=False).mean()-wk.ewm(span=26,adjust=False).mean()
def wstate(x): x=x.copy(); x.index=x.index+pd.Timedelta(days=1); return x.reindex(d.index,method="ffill").fillna(False).values.astype(bool)
cond["WEEKLY MACD above zero"]=wstate(wm>0); cond["WEEKLY MACD below zero"]=wstate(wm<0)
cond["WEEKLY close above 20-week avg"]=wstate(wk>wk.rolling(20).mean()); cond["WEEKLY close below 20-week avg"]=wstate(wk<wk.rolling(20).mean())
names=[k for k,v in cond.items() if np.nansum(v)>=60]; M=np.array([np.nan_to_num(cond[k]).astype(bool) for k in names]); print("conditions:",len(names),"| bars",n)
idx=d.index; P=[(idx>="2008-06-01")&(idx<"2015-01-01"),(idx>="2015-01-01")&(idx<"2021-01-01"),(idx>="2021-01-01")]
res=[]
for H in(1,3,5,10):
    fwd=np.full(n,np.nan); fwd[:n-H]=c[H:]/o[1:n-H+1]-1; ok=~np.isnan(fwd)
    up=(fwd>0)&ok; dnw=(fwd<0)&ok
    base=[(up[p&ok].mean(),dnw[p&ok].mean()) for p in P]
    U=[up&p for p in P]; Dn=[dnw&p for p in P]; A=[ok&p for p in P]
    def score(mask,combo):
        ns=[int((mask&a).sum()) for a in A]
        if ns[0]<25: return
        hu=(mask&U[0]).sum()/ns[0]; hd=(mask&Dn[0]).sum()/ns[0]
        for side,hit,arr in(("up",hu,U),("down",hd,Dn)):
            if hit>=0.70:
                ep=int((np.diff(np.flatnonzero(mask&A[0]))>H).sum()+1)      # separate episodes in the search period
                if ep<12: continue
                res.append(dict(H=H,side=side,combo=combo,size=len(combo),n0=ns[0],ep0=ep,h0=hit,n1=ns[1],h1=(mask&arr[1]).sum()/ns[1] if ns[1] else np.nan,n2=ns[2],h2=(mask&arr[2]).sum()/ns[2] if ns[2] else np.nan,
                                b0=base[0][side=="down"],b1=base[1][side=="down"],b2=base[2][side=="down"]))
    K=len(names)
    for i in range(K): score(M[i],(i,))
    for i,j in itertools.combinations(range(K),2):
        mij=M[i]&M[j]
        if (mij&A[0]).sum()<25: continue
        score(mij,(i,j))
        for k in range(j+1,K): score(mij&M[k],(i,j,k))
    print("hold %2d days: baseline up %.0f%% / %.0f%% / %.0f%%"%(H,*[100*b[0] for b in base]))
R=pd.DataFrame(res); R.to_pickle("search80.pkl")
tested=4*2*(len(names)+len(names)*(len(names)-1)//2+len(names)*(len(names)-1)*(len(names)-2)//6)
print("\nhypotheses examined: about %d"%tested)
print("found in SEARCH period (2008-2014) with hit rate >=70%%, >=25 days and >=12 separate episodes: %d"%len(R))
for th in(0.70,0.75,0.80,0.85):
    g=R[R.h0>=th]; g1=g[g.n1>=15]
    print("  search hit >= %.0f%%: %5d combos | their average hit in CONFIRM period: %.1f%% (baseline %.1f%%) | still >= 80%% there: %d | still >= 70%%: %d"%(100*th,len(g),100*g1.h1.mean() if len(g1) else float('nan'),100*g1.b1.mean() if len(g1) else float('nan'),(g1.h1>=0.8).sum(),(g1.h1>=0.7).sum()))
surv=R[(R.h0>=0.75)&(R.n1>=20)&(R.h1>=0.75)]
print("\nSURVIVORS (>=75%% in search AND confirm, >=20 days in confirm): %d | of those with >=15 days in FINAL period: %d"%(len(surv),(surv.n2>=15).sum()))
s2=surv[surv.n2>=15]
if len(s2): print("  their FINAL-period (2021-2026) hit rate: average %.1f%% | median %.1f%% | share >= 80%%: %.0f%% | share >= 70%%: %.0f%% | baseline %.1f%%"%(100*s2.h2.mean(),100*s2.h2.median(),100*(s2.h2>=.8).mean(),100*(s2.h2>=.7).mean(),100*s2.b2.mean()))
show=lambda r:"  hold %2dd %-4s | search %2.0f%% (n=%3d, %2d episodes) | confirm %2.0f%% (n=%3d) | final %s (n=%3d) | base %2.0f/%2.0f/%2.0f%% | %s"%(r.H,r.side,100*r.h0,r.n0,r.ep0,100*r.h1,r.n1,("%2.0f%%"%(100*r.h2)) if r.n2 else " n/a",r.n2,100*r.b0,100*r.b1,100*r.b2,"  &  ".join(names[i] for i in r.combo))
print("\nBest survivors by the weakest of the three periods (final period needs >=15 days):")
s2=s2.assign(m=s2[["h0","h1","h2"]].min(axis=1)).sort_values(["m","n2"],ascending=False)
seen=set()
for _,r in s2.iterrows():
    key=(r.H,r.side,frozenset(r.combo))
    if len(seen)>=12: break
    seen.add(key); print(show(r))
print("\nMost frequent conditions among survivors:"); 
cnt=pd.Series([names[i] for r in s2.combo for i in r]).value_counts().head(10); print(cnt.to_string())
