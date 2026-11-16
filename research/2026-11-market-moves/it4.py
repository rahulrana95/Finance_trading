import numpy as np, pandas as pd
from eng import *
import eng
calm=pd.read_pickle("calm.pkl").calm; cs=np.array([calm.get(t,np.nan) for t in idx])
def run2(tr,pt,stop,m,exit_th):
    """same as run, plus a regime exit: leave at the close if tomorrow's calm score (known tonight) is below exit_th"""
    cr=tr["credit"]; net=cr-tr["ecost"]
    if net<=0: return None
    lvl=m*cr; i=tr["i"]
    for j,(o,h,l,cl,spot) in enumerate(tr["pts"]):
        if j>0 and stop=="close" and o[0]>=max(lvl,3*cr): out=o[0]+o[1]; why="gap"; break
        if stop=="close" and cl[0]>=lvl: out=cl[0]+cl[1]; why="stop"; break
        if stop=="strike" and (spot>=tr["kc"] or spot<=tr["kp"]): out=cl[0]+cl[1]; why="stop"; break
        if pt and cl[0]<=(1-pt)*cr: out=cl[0]+cl[1]; why="target"; break
        if exit_th is not None and j<tr["hold"]-1 and cs[i+j+1]<exit_th: out=cl[0]+cl[1]; why="regime"; break
        if j==tr["hold"]-1: out=cl[0]+cl[1]; why="time"
    return (net-out)/(tr["width"]-net), why
cache={(s,dl):[build(i,s,dl) for i in first] for s in("condor",) for dl in(0.10,0.12)}
res=[]
for (s,dl),trs in cache.items():
  for pt in(None,0.5):
    for stop,m in(("close",2),("strike",0)):
      for ex in(None,0.3,0.4):
        allr=[(t["i"],*run2(t,pt,stop,m,ex)) for t in trs if run2(t,pt,stop,m,ex)]
        for th in(0.5,0.6):
          for sz in("flat","scaled"):
            rows=[(i,R,1.0 if sz=="flat" else float(np.clip((cs[i]-0.3)/0.4,0.5,1.5))) for i,R,_ in allr if cs[i]>=th]
            why=pd.Series([w for i,R,w in allr if cs[i]>=th]).value_counts(normalize=True).round(2).to_dict()
            res.append(((s,dl,pt,stop,m,ex,th,sz),stats(rows,*TRAIN),stats(rows,*VAL),why))
sc=lambda z:z["ret"]/max(-z["dd"],1.0)
def med(sel,lab):
    x=[(a,b) for k,a,b,_ in res if sel(k)]
    print("  %-22s train ret %+5.1f dd %6.1f score %.2f | val ret %+5.1f dd %6.1f score %.2f"%(lab,np.median([a["ret"] for a,_ in x]),np.median([a["dd"] for a,_ in x]),np.median([sc(a) for a,_ in x]),np.median([b["ret"] for _,b in x]),np.median([b["dd"] for _,b in x]),np.median([sc(b) for _,b in x])))
print("Medians across the other settings (condor, calm-gated)")
for ex in(None,0.3,0.4): med(lambda k:k[5]==ex,"regime exit < %s"%ex)
for sz in("flat","scaled"): med(lambda k:k[7]==sz,"size "+sz)
for dl in(0.10,0.12): med(lambda k:k[1]==dl,"delta %.2f"%dl)
for pt in(None,0.5): med(lambda k:k[2]==pt,"profit target %s"%pt)
for st in("close","strike"): med(lambda k:k[3]==st,"stop "+st)
for th in(0.5,0.6): med(lambda k:k[6]==th,"calm >= %.1f"%th)
print("\nTop 8 by min(train score, val score)")
for k,a,b,w in sorted(res,key=lambda x:-min(sc(x[1]),sc(x[2])))[:8]: print(" %s exits %s\n    TRAIN %s\n    VAL   %s"%(k,w,fmt(a),fmt(b)))
