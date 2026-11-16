import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from sklearn.metrics import roc_auc_score
F=pd.read_pickle("F.pkl"); T=pd.read_pickle("T.pkl")
tr=F.index<="2016-12-15"; va=(F.index>="2017-01-01")&(F.index<="2021-12-15")
# deterministic "calm score": each input is turned into a rolling 3-year percentile (no fitting, no look-ahead), then averaged
def pct(x,w=750): return x.rolling(w,min_periods=250).rank(pct=True)
def score(cols,signs):
    return pd.concat([pct(F[c]) if s>0 else 1-pct(F[c]) for c,s in zip(cols,signs)],axis=1).mean(axis=1)
CAND={"trend4 (ret22,macd,d50,rsi14)":(["ret22","macd","d50","rsi14"],[1,1,1,1]),
      "trend4 + low downside-vol share":(["ret22","macd","d50","rsi14","skew22"],[1,1,1,1,-1]),
      "trend + skew + us_term + dd250":(["ret22","macd","d50","rsi14","skew22","us_term","dd250"],[1,1,1,1,-1,-1,1]),
      "ret22 only":(["ret22"],[1]),"macd only":(["macd"],[1]),
      "trend + credit(hyg22) + eem5":(["ret22","macd","d50","rsi14","skew22","hyg_ret22","eem_ret5"],[1,1,1,1,-1,1,1])}
K=1.28; y=T.zmax>=K
for nm,(c,s) in CAND.items():
    S=score(c,s); out=[]
    for lab,m in(("train",tr),("val",va)):
        mm=m&S.notna(); q=pd.qcut(S[mm],5,labels=False)
        out.append("%s AUC %.3f  touch by calm-quintile (rough->calm): %s"%(lab,roc_auc_score(y[mm],-S[mm])," ".join("%4.1f"%(100*y[mm][q==k].mean()) for k in range(5))))
    print("%-34s\n   %s\n   %s"%(nm,out[0],out[1]))
S=score(*CAND["trend4 + low downside-vol share"]); F["calm"]=S; F[["calm"]].to_pickle("calm.pkl")
print("\nBy side, score = trend4+skew.  Quantiles of the week's max move UP and DOWN, in units of VIX-implied sigma")
for lab,m in(("train",tr),("val",va)):
    mm=m&S.notna(); q=pd.qcut(S[mm],5,labels=["1 rough","2","3","4","5 calm"])
    g=pd.DataFrame({"up q90":T.zu[mm].groupby(q,observed=True).quantile(.9),"up q95":T.zu[mm].groupby(q,observed=True).quantile(.95),
       "dn q90":T.zd[mm].groupby(q,observed=True).quantile(.9),"dn q95":T.zd[mm].groupby(q,observed=True).quantile(.95),
       "up touch@1.28 %":100*(T.zu[mm]>=K).groupby(q,observed=True).mean(),"dn touch@1.28 %":100*(T.zd[mm]>=K).groupby(q,observed=True).mean(),
       "end beyond 1.28 %":100*(T.zend[mm].abs()>=K).groupby(q,observed=True).mean(),"mean |end| / sigma":T.zend[mm].abs().groupby(q,observed=True).mean(),
       "avg vix":F.vix[mm].groupby(q,observed=True).mean(),"n":q.value_counts().sort_index()})
    print(lab); print(g.round(2).to_string())
print("\nIs it just VIX level? touch rate (val) in a 3x3 grid: calm tercile x VIX tercile")
mm=va&S.notna(); a=pd.qcut(S[mm],3,labels=["rough","mid","calm"]); b=pd.qcut(F.vix[mm],3,labels=["lowVIX","midVIX","highVIX"])
print((100*y[mm].groupby([a,b],observed=True).mean()).unstack().round(1).to_string())
mm=tr&S.notna(); a=pd.qcut(S[mm],3,labels=["rough","mid","calm"]); b=pd.qcut(F.vix[mm],3,labels=["lowVIX","midVIX","highVIX"])
print("train"); print((100*y[mm].groupby([a,b],observed=True).mean()).unstack().round(1).to_string())
