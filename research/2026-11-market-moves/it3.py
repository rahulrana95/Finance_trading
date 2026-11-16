import numpy as np, pandas as pd, itertools, sys
from eng import *
calm=pd.read_pickle("calm.pkl").calm; cs=np.array([calm.get(idx[i],np.nan) for i in range(len(idx))])
res=[]; cache={}
for s in("condor","call","put"):
    for dl in(0.08,0.10,0.12):
        cache[(s,dl)]=[build(i,s,dl) for i in first]
for (s,dl),trs in cache.items():
    for pt in(None,0.5):
        for stop,m in((None,0),("close",2),("close",3),("strike",0)):
            allr=[(t["i"],r[0]) for t in trs if (r:=run(t,pt,stop,m))]
            for th in(None,0.4,0.5,0.6,0.7):
                rows=[(i,R,1.0) for i,R in allr if th is None or cs[i]>=th]
                a=stats(rows,*TRAIN); b=stats(rows,*VAL)
                if a and b: res.append(((s,dl,pt,stop,m,th),a,b,rows))
sc=lambda z:z["ret"]/max(-z["dd"],1.0)
print("configs",len(res),"| assumed skew: call IV = %.2f x VIX, put IV = %.2f x VIX | size: max loss per trade 4%% of capital"%(CALL_MULT,PUT_MULT))
print("\nEffect of the calm gate (median over all other settings), return %/yr and maxDD")
for s in("condor","call","put"):
    for th in(None,0.4,0.5,0.6,0.7):
        x=[(a,b) for k,a,b,_ in res if k[0]==s and k[5]==th]
        print("  %-7s calm>=%-4s train ret %+5.1f dd %6.1f | val ret %+5.1f dd %6.1f | trades/yr %.0f"%(s,th,np.median([a["ret"] for a,_ in x]),np.median([a["dd"] for a,_ in x]),np.median([b["ret"] for _,b in x]),np.median([b["dd"] for _,b in x]),np.median([b["n"] for _,b in x])/5))
R=pd.DataFrame({"tr":[sc(a) for _,a,_,_ in res],"va":[sc(b) for _,_,b,_ in res]})
print("\nrank corr train vs val score: %.2f"%R.tr.rank().corr(R.va.rank()))
print("\nTop 10 by TRAIN score, with VALIDATION result")
for k,a,b,_ in sorted(res,key=lambda x:-sc(x[1]))[:10]: print(" %s\n    TRAIN %s\n    VAL   %s"%(k,fmt(a),fmt(b)))
