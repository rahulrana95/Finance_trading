import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb
F=pd.read_pickle("F.pkl"); T=pd.read_pickle("T.pkl")
tr=F.index<="2016-12-15"; va=(F.index>="2017-01-01")&(F.index<="2021-12-15")      # holdout 2022+ NOT touched here
K=1.28
for nm,y in(("touch_any",(T.zmax>=K)),("touch_up",(T.zu>=K)),("touch_dn",(T.zd>=K))):
    print(nm,"rate train %.3f val %.3f"%(y[tr].mean(),y[va].mean()))
print("\nUnivariate: rank corr with zmax, and AUC for touch_any (train | val). Sorted by weaker of the two |IC|")
rows=[]
for f in F.columns:
    x=F[f]; a=x[tr].rank().corr(T.zmax[tr].rank()); b=x[va].rank().corr(T.zmax[va].rank())
    m=x.notna()
    rows.append((f,a,b,roc_auc_score((T.zmax>=K)[tr&m],x[tr&m]),roc_auc_score((T.zmax>=K)[va&m],x[va&m]),
                 x[tr].rank().corr((T.zu-T.zd)[tr].rank()),x[va].rank().corr((T.zu-T.zd)[va].rank())))
R=pd.DataFrame(rows,columns=["f","ic_tr","ic_va","auc_tr","auc_va","dir_tr","dir_va"]).set_index("f")
R["stable"]=np.where(np.sign(R.ic_tr)==np.sign(R.ic_va),np.minimum(R.ic_tr.abs(),R.ic_va.abs()),0)
print(R.sort_values("stable",ascending=False).head(22).round(3).to_string())
R["dstable"]=np.where(np.sign(R.dir_tr)==np.sign(R.dir_va),np.minimum(R.dir_tr.abs(),R.dir_va.abs()),0)
print("\nDirection (zu - zd): most stable features"); print(R.sort_values("dstable",ascending=False)[["dir_tr","dir_va"]].head(8).round(3).to_string())
y=(T.zmax>=K).astype(int)
def ev(name,p): print("  %-38s val AUC %.3f | touch rate by predicted-risk tercile: %s"%(name,roc_auc_score(y[va],p),
      " / ".join("%.1f%%"%(100*y[va][g].mean()) for g in [pd.qcut(pd.Series(p,index=F.index[va]).rank(method="first"),3,labels=False)==k for k in range(3)])))
print("\nModels for touch_any (fit on train, scored on validation)")
X=F.fillna(F[tr].median())
for cols in(["lvix"],["vrp22"],["lvix","vrp22","rv5_22","macd","absgap"],
            ["lvix","vrp22","vrp5","rv5_22","rv22_66","macd","d50","dd250","absgap","vix_chg5","us_term","usvix_chg5","skew22","vov20"]):
    sc=StandardScaler().fit(X.loc[tr,cols]); m=LogisticRegression(C=0.3,max_iter=500).fit(sc.transform(X.loc[tr,cols]),y[tr])
    ev("logit "+("+".join(cols))[:30],m.predict_proba(sc.transform(X.loc[va,cols]))[:,1])
for params in(dict(n_estimators=150,learning_rate=0.03,num_leaves=4,min_child_samples=80,subsample=0.7,subsample_freq=1,colsample_bytree=0.5,reg_lambda=5),
              dict(n_estimators=300,learning_rate=0.02,num_leaves=8,min_child_samples=60,subsample=0.7,subsample_freq=1,colsample_bytree=0.5,reg_lambda=5)):
    m=lgb.LGBMClassifier(**params,verbose=-1,random_state=0).fit(F[tr],y[tr]); p=m.predict_proba(F[va])[:,1]
    ev("lgbm leaves=%d all features"%params["num_leaves"],p)
    imp=pd.Series(m.booster_.feature_importance("gain"),index=F.columns).sort_values(ascending=False); print("     top gain:",", ".join(imp.index[:10]))
