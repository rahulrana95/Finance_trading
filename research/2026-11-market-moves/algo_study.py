import json, math, itertools, numpy as np, pandas as pd
from statistics import NormalDist
ND=NormalDist(); cdf=lambda x:0.5*(1+math.erf(x/1.4142135623730951))
def load(p):
    r=json.load(open(p))["chart"]["result"][0]; q=r["indicators"]["quote"][0]
    d=pd.DataFrame({k:q[k] for k in("open","high","low","close")},
        index=pd.to_datetime(r["timestamp"],unit="s",utc=True).tz_convert("Asia/Kolkata").normalize().tz_localize(None)).dropna()
    return d[~d.index.duplicated()]
d=load("nsei.json"); d["vix"]=load("vix.json").close.reindex(d.index).ffill()
c=d.close; macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean()
d["macd_pos"]=(macd>0).shift(1); d["pvix"]=d.vix.shift(1); d=d.loc["2008-03":]
O,H,L,C,V,PV=(d[k].values for k in("open","high","low","close","vix","pvix")); idx=d.index
def bs(S,K,T,s,call):
    if T<=0: return max(S-K,0) if call else max(K-S,0)
    sd=s*math.sqrt(T); d1=(math.log(S/K)+0.5*sd*sd)/sd; d2=d1-sd
    return S*cdf(d1)-K*cdf(d2) if call else K*cdf(-d2)-S*cdf(-d1)
def kdelta(S,T,s,dl,call):
    sd=s*math.sqrt(T); d1=ND.inv_cdf(dl) if call else ND.inv_cdf(1-dl)
    return S*math.exp(-d1*sd+0.5*sd*sd)
r50=lambda x:round(x/50)*50
HOLD=6
def build(i,struct,dl,dte=7):
    """legs [(sign,K,call)], sign -1 short. entry at open of session i, dte sessions to expiry."""
    S=O[i]; s=PV[i]/100; T=dte/252; w=max(50,r50(0.008*S))
    kc=max(r50(kdelta(S,T,s,dl,True)),r50(S)+50); kp=min(r50(kdelta(S,T,s,dl,False)),r50(S)-50)
    if struct=="call": legs=[(-1,kc,1),(1,kc+w,1)]; width=w
    elif struct=="put": legs=[(-1,kp,0),(1,kp-w,0)]; width=w
    elif struct=="condor": legs=[(-1,kc,1),(1,kc+w,1),(-1,kp,0),(1,kp-w,0)]; width=w
    else: k0=r50(S); legs=[(-1,k0,1),(-1,k0,0),(1,kc,1),(1,kp,0)]; width=max(kc-k0,k0-kp)   # iron butterfly
    def val(S_,T_,s_):
        ps=[bs(S_,K,T_,s_,cl) for _,K,cl in legs]
        return -sum(sg*p for (sg,_,_),p in zip(legs,ps)), 0.025*sum(ps)+len(legs)*0.15*S_/25000   # value to buy back, fill cost
    hold=dte-1; pts=[]
    for j in range(hold):
        t=i+j; rem=dte-j; sm=(PV[t]+V[t])/200
        pts.append((val(O[t],rem/252,PV[t]/100),val(H[t],(rem-.5)/252,sm),val(L[t],(rem-.5)/252,sm),val(C[t],(rem-1)/252,V[t]/100),C[t]))
    return dict(i=i,credit=pts[0][0][0],ecost=pts[0][0][1],width=width,kc=kc if struct!="put" else 9e9,kp=kp if struct!="call" else -9e9,pts=pts,hold=hold)
def run(tr,pt,stop,m):
    cr=tr["credit"]; net=cr-tr["ecost"]
    if net<=0.02*tr["width"]*0: pass
    if net<=0: return None
    lvl=m*cr; out=None; why="time"
    for j,(o,h,l,cl,spot) in enumerate(tr["pts"]):
        if stop=="intraday":
            cands=[h,l]+([o] if j>0 else []); worst=max(cands,key=lambda x:x[0])
            if worst[0]>=lvl:
                gap=o[0] if j>0 else 0; out=max(lvl,gap)+worst[1]; why="stop"; break
        if stop=="close" and cl[0]>=lvl: out=cl[0]+cl[1]; why="stop"; break
        if stop=="strike" and (spot>=tr["kc"] or spot<=tr["kp"]): out=cl[0]+cl[1]; why="stop"; break
        if pt and cl[0]<=(1-pt)*cr: out=cl[0]+cl[1]; why="target"; break
        if j==tr["hold"]-1: out=cl[0]+cl[1]
    return (net-out)/(tr["width"]-net), why, j
wk=pd.Series(idx.to_period("W"),index=idx); first=np.where(~wk.duplicated().values)[0]
first=[i for i in first if i>=1 and i+8<len(d) and not np.isnan(PV[i])]
RISK=4.0   # each trade sized so its max loss = 4% of capital
def stats(rows,lo,hi):
    x=[(idx[i],R) for i,R in rows if lo<=idx[i].year<=hi]
    if len(x)<30: return None
    s=pd.Series([R*RISK for _,R in x],index=[a for a,_ in x]); yrs=hi-lo+1-(0.17 if lo==2008 else 0)-(0.15 if hi==2026 else 0)
    cum=s.cumsum(); dd=(cum-cum.cummax().clip(lower=0)).min(); w=s[s>0]; lo_=s[s<=0]
    return dict(n=len(s),ret=s.sum()/yrs,dd=dd,worst=s.min(),wyear=s.groupby(s.index.year).sum().min(),win=100*len(w)/len(s),
                ratio=(-lo_.mean()/w.mean()) if len(w) and len(lo_) else float("nan"))
fmt=lambda z:"none" if z is None else "n=%3d ret %+6.1f%%/yr  maxDD %6.1f%%  worst trade %5.1f%%  worst yr %+6.1f%%  win %2.0f%%  avgloss/avgwin %4.1f"%(z["n"],z["ret"],z["dd"],z["worst"],z["wyear"],z["win"],z["ratio"])
print("weeks",len(first),idx[first[0]].date(),idx[first[-1]].date(),"| sizing: max loss per trade = %.0f%% of capital | TRAIN 2008-2016, TEST 2017-2026"%RISK)
STRUCTS=["condor","call","put","butterfly"]; DELTAS=[0.08,0.10,0.12]
cache={(s,dl):[build(i,s,dl) for i in first] for s in STRUCTS for dl in DELTAS}
print("\n1. STRUCTURES, no stop, hold to day before expiry, take profit at 50% (all weeks traded)")
for s in STRUCTS:
    for dl in DELTAS:
        rows=[(t["i"],r[0]) for t in cache[(s,dl)] if (r:=run(t,0.5,None,0))]
        cr=np.mean([ (t["credit"]-t["ecost"])/t["width"] for t in cache[(s,dl)]])
        print(" %-9s d%.2f credit/width %4.1f%% | TRAIN %s\n %27s | TEST  %s"%(s,dl,100*cr,fmt(stats(rows,2008,2016)),"",fmt(stats(rows,2017,2026))))
print("\n2. STOP-LOSS TYPES on condor d0.10, take profit 50%  (2008-2026 all)")
base={t["i"]:run(t,0.5,None,0) for t in cache[("condor",0.10)]}
for stop,m in((None,0),("intraday",2),("intraday",3),("close",2),("close",3),("strike",0)):
    res={t["i"]:run(t,0.5,stop,m) for t in cache[("condor",0.10)]}
    rows=[(i,r[0]) for i,r in res.items() if r]; st=[i for i,r in res.items() if r and r[1]=="stop"]
    extra=""
    if st:
        rec=[base[i][0]>0 for i in st]; better=[base[i][0]>res[i][0] for i in st]
        extra="  | stopped %d (%.0f%% of trades); of those, %.0f%% would have ended in PROFIT without the stop, %.0f%% better off without it"%(len(st),100*len(st)/len(rows),100*np.mean(rec),100*np.mean(better))
    print(" stop=%-9s x%d  %s%s"%(stop,m,fmt(stats(rows,2008,2026)),extra))
print("\n3. ENTRY DAY (condor d0.10, no stop, PT 50%, always 7 sessions to expiry) 2008-2026")
for off,name in enumerate(["Mon","Tue","Wed","Thu","Fri"]):
    rows=[]
    for i in first:
        if wk.iloc[i+off]!=wk.iloc[i] or i+off+8>=len(d): continue
        r=run(build(i+off,"condor",0.10),0.5,None,0)
        if r: rows.append((i+off,r[0]))
    print(" enter %s: %s"%(name,fmt(stats(rows,2008,2026))))
print("\n4. DAYS TO EXPIRY at entry (condor d0.10, no stop, PT 50%), exit with 1 session left, 2008-2026")
for dte in(7,5,3,2):
    rows=[(i,r[0]) for i in first if (r:=run(build(i+7-dte,"condor",0.10,dte),0.5,None,0))]
    print(" %d sessions to expiry: %s"%(dte,fmt(stats(rows,2008,2026))))
print("\n5. ALGO SEARCH: choose on TRAIN (2008-2016) only, then look at TEST (2017-2026)")
vtr=[PV[i] for i in first if idx[i].year<=2016]; p80=np.percentile(vtr,80); p20=np.percentile(vtr,20)
print(" VIX thresholds learned on train: low %.1f high %.1f"%(p20,p80))
FILT={"none":lambda i:True,"macd>0":lambda i:bool(d.macd_pos.iloc[i]),"vix<=hi":lambda i:PV[i]<=p80,"vix>=lo":lambda i:PV[i]>=p20,
      "macd>0&vix<=hi":lambda i:bool(d.macd_pos.iloc[i]) and PV[i]<=p80,"vix in band":lambda i:p20<=PV[i]<=p80}
res=[]
for (s,dl),trs in cache.items():
    for pt in(0.5,0.75,None):
        for stop,m in((None,0),("intraday",2),("intraday",3),("close",2),("close",3),("strike",0)):
            allr=[(t["i"],r[0]) for t in trs if (r:=run(t,pt,stop,m))]
            for fn,f in FILT.items():
                rows=[(i,R) for i,R in allr if f(i)]; a=stats(rows,2008,2016); b=stats(rows,2017,2026)
                if a and b and a["n"]>=100: res.append(((s,dl,pt,stop,m,fn),a,b))
sc=lambda z:z["ret"]/max(-z["dd"],1.0)
R=pd.DataFrame({"tr":[sc(a) for _,a,_ in res],"te":[sc(b) for _,_,b in res],"trret":[a["ret"] for _,a,_ in res],"teret":[b["ret"] for _,_,b in res]})
print(" configs tested: %d | profitable on train: %d | of those profitable on test: %d | rank corr train vs test score %.2f"%(len(R),(R.trret>0).sum(),((R.trret>0)&(R.teret>0)).sum(),R.tr.rank().corr(R.te.rank())))
print(" test return of ALL configs: median %+.1f%%/yr, best %+.1f, worst %+.1f"%(R.teret.median(),R.teret.max(),R.teret.min()))
top=sorted(res,key=lambda x:-sc(x[1]))[:8]
for k,a,b in top: print(" %s\n    TRAIN %s\n    TEST  %s"%(k,fmt(a),fmt(b)))
print("\n by structure: share of configs profitable in BOTH periods, median test ret")
for s in STRUCTS:
    x=[(a,b) for k,a,b in res if k[0]==s]; print("  %-9s %3.0f%% of %d | median test %+.1f%%/yr | median train %+.1f%%/yr"%(s,100*np.mean([a["ret"]>0 and b["ret"]>0 for a,b in x]),len(x),np.median([b["ret"] for _,b in x]),np.median([a["ret"] for a,_ in x])))
print(" by filter (condor only): median train / test ret")
for fn in FILT:
    x=[(a,b) for k,a,b in res if k[0]=="condor" and k[5]==fn]; print("  %-15s train %+.1f  test %+.1f"%(fn,np.median([a["ret"] for a,_ in x]),np.median([b["ret"] for _,b in x])))
print(" by stop (condor only): median train / test ret")
for stop,m in((None,0),("intraday",2),("intraday",3),("close",2),("close",3),("strike",0)):
    x=[(a,b) for k,a,b in res if k[0]=="condor" and k[3]==stop and k[4]==m]; print("  %-9s x%d train %+.1f  test %+.1f | median test maxDD %.1f"%(stop,m,np.median([a["ret"] for a,_ in x]),np.median([b["ret"] for _,b in x]),np.median([b["dd"] for _,b in x])))
