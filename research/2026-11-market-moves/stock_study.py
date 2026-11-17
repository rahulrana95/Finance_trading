"""Pattern reliability on one NSE stock (default ICICI Bank), daily bars, three periods. Research only, no costs."""
import sys, json, itertools, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from patterns import signals
name=sys.argv[1] if len(sys.argv)>1 else "ICICI"
def loadv(p,tz="Asia/Kolkata"):
    r=json.load(open(p))["chart"]["result"][0]; q=r["indicators"]["quote"][0]
    d=pd.DataFrame({k:q[k] for k in("open","high","low","close","volume")},index=pd.to_datetime(r["timestamp"],unit="s",utc=True).tz_convert(tz).normalize().tz_localize(None)).dropna()
    d=d[(d.high>=d.low)&(d.open>0)&(d.volume>0)]; return d[~d.index.duplicated()]
d=loadv("data/%s.json"%name).loc["2003-01":]
bad=(d.close.pct_change().abs()>0.25); print(name,"bars",len(d),d.index[0].date(),"to",d.index[-1].date(),"| last close %.1f | days with |move|>25%% (possible data errors): %d"%(d.close.iloc[-1],bad.sum()))
nf=loadv("data/NIFTY.json") if False else None
from feat import load
nif=load("NIFTY","Asia/Kolkata").close.reindex(d.index).ffill()
L,S,ST=signals(d); o,h,l,c,v=(d[k].values.astype(float) for k in("open","high","low","close","volume")); C=pd.Series(c); n=len(d); r=C.pct_change()
rec=lambda a,k=3: pd.Series(a).rolling(k).max().fillna(0).astype(bool).values
cond={}
for k,x in L.items(): cond["UP:"+k]=rec(x)
for k,x in S.items(): cond["DN:"+k]=rec(x)
cond.update(ST)
def rsi(k): u=r.clip(lower=0).rolling(k).mean(); dn=(-r.clip(upper=0)).rolling(k).mean(); return (100-100/(1+u/dn)).values
r14,r2=rsi(14),rsi(2); V=pd.Series(v); N=pd.Series(nif.values)
cond.update({"RSI14 below 30":r14<30,"RSI14 above 70":r14>70,"RSI2 below 10":r2<10,"RSI2 above 90":r2>90,
 "3 down closes in a row":(r<0).rolling(3).sum().values==3,"3 up closes in a row":(r>0).rolling(3).sum().values==3,
 "volume 1.5x its 20-day average":(V>1.5*V.rolling(20).mean()).values,"volume below half its 20-day average":(V<0.5*V.rolling(20).mean()).values,
 "up 3%+ today":(r>0.03).values,"down 3%+ today":(r<-0.03).values,
 "stronger than Nifty over 22 days":(C.pct_change(22)>N.pct_change(22)).values,"weaker than Nifty over 22 days":(C.pct_change(22)<N.pct_change(22)).values,
 "Nifty above its 200-day average":(N>N.rolling(200).mean()).values,"Nifty below its 200-day average":(N<N.rolling(200).mean()).values,
 "10%+ below 50-day high":(c/C.rolling(50).max().values-1)<-0.10,"at 50-day high":c>=C.rolling(50).max().values})
names=[k for k,x in cond.items() if np.nansum(x)>=60]; M=np.array([np.nan_to_num(cond[k]).astype(bool) for k in names])
idx=d.index; cuts=[idx[250],idx[250+(n-250)//3],idx[250+2*(n-250)//3]]
P=[(idx>=cuts[0])&(idx<cuts[1]),(idx>=cuts[1])&(idx<cuts[2]),idx>=cuts[2]]; plab=["%d-%d"%(idx[p][0].year,idx[p][-1].year) for p in P]
print("conditions:",len(names),"| periods:",plab)
out=[]; single=[]
for H in(1,3,5,10):
    fwd=np.full(n,np.nan); fwd[:n-H]=c[H:]/o[1:n-H+1]-1; ok=~np.isnan(fwd)
    up=(fwd>0)&ok; dn=(fwd<0)&ok; A=[ok&p for p in P]; U=[up&p for p in P]; Dn=[dn&p for p in P]
    base=[(up[a].mean(),dn[a].mean(),fwd[a].mean()) for a in A]
    print("hold %2d days: stock closes higher %s | average move %s"%(H," / ".join("%.0f%%"%(100*b[0]) for b in base)," / ".join("%+.2f%%"%(100*b[2]) for b in base)))
    def score(mask,combo):
        ns=[int((mask&a).sum()) for a in A]
        if min(ns)<20: return
        for side,arr,bi in(("up",U,0),("down",Dn,1)):
            hs=[(mask&arr[k]).sum()/ns[k] for k in range(3)]
            ep=int((np.diff(np.flatnonzero(mask&A[0]))>H).sum()+1)
            sg=1 if side=="up" else -1; ed=[sg*(fwd[mask&A[k]].mean()-base[k][2]) for k in range(3)]
            rec_=dict(H=H,side=side,combo=combo,size=len(combo),ns=ns,ep0=ep,h=hs,b=[base[k][bi] for k in range(3)],edge=ed)
            if len(combo)==1: single.append(rec_)
            if ep>=10: out.append(rec_)
    K=len(names)
    for i in range(K): score(M[i],(i,))
    for i,j in itertools.combinations(range(K),2):
        mij=M[i]&M[j]
        if min((mij&a).sum() for a in A)<20: continue
        score(mij,(i,j))
        for k in range(j+1,K): score(mij&M[k],(i,j,k))
R=pd.DataFrame(out); R["h0"]=R.h.str[0];R["h1"]=R.h.str[1];R["h2"]=R.h.str[2]; R["lift"]=[min(h[k]-b[k] for k in range(3)) for h,b in zip(R.h,R.b)]; R["minh"]=R[["h0","h1","h2"]].min(axis=1)
print("\ncombinations scored (>=20 days in every period): %d"%len(R))
for th in(0.65,0.70,0.75,0.80):
    g=R[R.h0>=th]; print("  first period hit >= %.0f%%: %5d | their average in period 2: %.1f%% and period 3: %.1f%% | >= %.0f%% in ALL three: %d"%(100*th,len(g),100*g.h1.mean() if len(g) else float('nan'),100*g.h2.mean() if len(g) else float('nan'),100*th,((R.h0>=th)&(R.h1>=th)&(R.h2>=th)).sum()))
print("  hit rate >= 60%% in all three periods: %d | >= 65%%: %d | >= 70%%: %d"%((R.minh>=.60).sum(),(R.minh>=.65).sum(),(R.minh>=.70).sum()))
fm=lambda r:"  hold %2dd %-4s | %s | base %s | n %s | extra avg move %s | %s"%(r.H,r.side," / ".join("%2.0f%%"%(100*x) for x in r.h)," / ".join("%2.0f%%"%(100*x) for x in r.b),"/".join(str(x) for x in r.ns)," / ".join("%+.2f%%"%(100*x) for x in r.edge),"  &  ".join(names[i] for i in r.combo))
print("\nMOST RELIABLE across all three periods (ranked by the lowest hit rate of the three):")
for _,r in R.sort_values("minh",ascending=False).head(12).iterrows(): print(fm(r))
print("\nBIGGEST CONSISTENT ADVANTAGE over the stock's own baseline (ranked by the smallest lift of the three):")
for _,r in R.sort_values("lift",ascending=False).head(10).iterrows(): print(fm(r))
Sg=pd.DataFrame(single); Sg["minlift"]=[min(h[k]-b[k] for k in range(3)) for h,b in zip(Sg.h,Sg.b)]
print("\nSINGLE CONDITIONS, hold 5 days, best and worst by smallest lift over baseline:")
x=Sg[Sg.H==5].sort_values("minlift",ascending=False)
for _,r in pd.concat([x.head(8),x.tail(4)]).iterrows(): print(fm(r))
