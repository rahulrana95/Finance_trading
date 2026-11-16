import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
from eng import *
F=pd.read_pickle("F.pkl"); T=pd.read_pickle("T.pkl"); calm=pd.read_pickle("calm.pkl").calm; cs=np.array([calm.get(t,np.nan) for t in idx])
print("A. SIGNAL on the untouched holdout 2022-01 to 2026-10 (daily entries, 6-session windows)")
ho=(F.index>="2022-01-01")&calm.reindex(F.index).notna().values; S=calm.reindex(F.index)[ho]; y=(T.zmax>=1.28)[ho]
q=pd.qcut(S,5,labels=["1 rough","2","3","4","5 calm"])
g=pd.DataFrame({"either side touched %":100*y.groupby(q,observed=True).mean(),"up touched %":100*(T.zu[ho]>=1.28).groupby(q,observed=True).mean(),
  "down touched %":100*(T.zd[ho]>=1.28).groupby(q,observed=True).mean(),"ended beyond %":100*(T.zend[ho].abs()>=1.28).groupby(q,observed=True).mean(),"n":q.value_counts().sort_index()})
print(g.round(1).to_string()); print("AUC %.3f | touch when calm>=0.5: %.1f%% (n=%d) vs calm<0.5: %.1f%% (n=%d)"%(roc_auc_score(y,-S),100*y[S>=.5].mean(),(S>=.5).sum(),100*y[S<.5].mean(),(S<.5).sum()))
print("\nB. FROZEN RULE: iron condor, short strikes 0.10 delta, hedge ~0.8% of spot away, enter first session of week only if calm>=0.5,")
print("   exit at the close if Nifty closes beyond a short strike, else hold to the day before expiry. Max loss per trade = 4% of capital.")
trs=[build(i,"condor",0.10) for i in first]; allr=[(t["i"],run(t,None,"strike",0)) for t in trs]
gated=[(i,r[0],1.0) for i,r in allr if r and cs[i]>=0.5]; ung=[(i,r[0],1.0) for i,r in allr if r]; rough=[(i,r[0],1.0) for i,r in allr if r and cs[i]<0.5]
for lab,p in(("TRAIN 2008-16",TRAIN),("VAL   2017-21",VAL),("HOLDOUT 22-26",HOLD),("ALL   2008-26",("2008-04-01","2026-10-31"))):
    print(" %s  gated   %s\n %s  always  %s\n %s  skipped weeks only %s"%(lab,fmt(stats(gated,*p)),lab,fmt(stats(ung,*p)),lab,fmt(stats(rough,*p))))
s=pd.Series({idx[i]:R*4 for i,R,_ in gated}); by=s.groupby(s.index.year).agg(["sum","count","min"]).round(1); by.columns=["ret %","trades","worst trade %"]
print("\nC. Year by year (gated rule, 4% max loss per trade)"); print(by.T.to_string())
cr=np.mean([r[3] for i,r in allr if r and cs[i]>=0.5]); why=pd.Series([r[1] for i,r in allr if r and cs[i]>=0.5]).value_counts(normalize=True).round(2).to_dict()
print("avg net credit = %.1f%% of hedge width | exits %s"%(100*cr,why))
print("\nD. Same rule at other sizes (ALL years): max loss per trade -> return / maxDD / worst month / worst year")
z=stats(gated,"2008-04-01","2026-10-31")
for risk in(4,8,12,16): k=risk/4; print("  %2d%%: ret %+5.1f%%/yr  maxDD %5.1f%%  worst month %5.1f%%  worst year %+5.1f%%"%(risk,z["ret"]*k,z["dd"]*k,z["wmonth"]*k,z["wyear"]*k))
print("\nE. Sensitivity of the holdout result to the price assumptions (gated rule)")
import eng
for cm,pm in((0.92,1.12),(1.0,1.0),(0.85,1.05),(0.80,1.00)):
    eng.CALL_MULT,eng.PUT_MULT=cm,pm; tt=[build(i,"condor",0.10) for i in first]; rr=[(t["i"],r[0],1.0) for t in tt if (r:=run(t,None,"strike",0)) and cs[t["i"]]>=0.5]
    print("  call IV %.2f x VIX, put IV %.2f x VIX: HOLDOUT %s"%(cm,pm,fmt(stats(rr,*HOLD))))
