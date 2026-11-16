"""Prototype: a fixed-formula probability that each side's 0.10-delta-distance strike is touched in the next 6 sessions.
Fitted on 2008-2016 only, then frozen and checked for calibration on 2017-2026."""
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
F=pd.read_pickle("F.pkl"); T=pd.read_pickle("T.pkl"); calm=pd.read_pickle("calm.pkl").calm.reindex(F.index)
X=pd.DataFrame({"calm":calm,"macd_pos":(F.macd>0).astype(float),"log_vix":F.lvix,"us_night_abs":F.us_ret1.abs().fillna(0)*100,
                "yday_abs":F.absret1*100,"gap_abs":F.absgap*100,"ret22":F.ret22*100},index=F.index)
Y={"call side touched":T.zu>=1.28,"put side touched":T.zd>=1.28,"either side touched":T.zmax>=1.28,"ends beyond a strike":T.zend.abs()>=1.28}
ok=X.notna().all(axis=1); tr=ok&(F.index<="2016-12-15"); te=ok&(F.index>="2017-01-01")
mu,sd=X[tr].mean(),X[tr].std(); Z=(X-mu)/sd
models={}
for nm,y in Y.items():
    m=LogisticRegression(C=0.5,max_iter=1000).fit(Z[tr],y[tr]); p=pd.Series(m.predict_proba(Z[te])[:,1],index=F.index[te]); models[nm]=(m,p)
    base=y[tr].mean()
    print("\n%s | base rate train %.1f%% test %.1f%% | test AUC %.3f | Brier %.4f vs %.4f for a constant guess"%(nm,100*base,100*y[te].mean(),roc_auc_score(y[te],p),brier_score_loss(y[te],p),brier_score_loss(y[te],np.full(te.sum(),base))))
    print("   weights (per 1 sd): "+", ".join("%s %+.2f"%(c,w) for c,w in zip(X.columns,m.coef_[0])))
    q=pd.qcut(p,5,labels=False); print("   calibration on 2017-2026, 5 groups from safest to riskiest:  predicted -> actual")
    print("   "+"   ".join("%.0f%% -> %.0f%%"%(100*p[q==k].mean(),100*y[te][q==k].mean()) for k in range(5)))
    for lo,hi in(("2017","2021"),("2022","2026")):
        mm=(p.index>=lo)&(p.index<=hi+"-12-31"); qq=pd.qcut(p[mm],3,labels=False)
        print("   %s-%s thirds: "%(lo,hi)+"   ".join("%.0f%% -> %.0f%%"%(100*p[mm][qq==k].mean(),100*y[te][mm][qq==k].mean()) for k in range(3)))
print("\nExample output for the last 6 entry days in the data:")
out=pd.DataFrame({k.split(" touched")[0].replace("ends beyond a strike","ends beyond"):(100*v[1]).round(0) for k,v in models.items()}).tail(6)
out["vix"]=F.vix.reindex(out.index).round(1); out["calm"]=calm.reindex(out.index).round(2); print(out.to_string())
