"""Does any indicator setting predict direction? Signal read at yesterday's close; outcome measured from today's open."""
import numpy as np, pandas as pd, itertools
from feat import load
n=load("NIFTY","Asia/Kolkata").dropna(); n=n[(n.high>=n.low)&(n.open>0)].loc["2008-01":]
c,o,h,l=n.close,n.open,n.high,n.low; r=c.pct_change()
out1=(c/o-1); out6=(c.shift(-5)/o-1)                      # same day open-to-close; 6 sessions from the open
S={}
ema=lambda x,k:x.ewm(span=k,adjust=False).mean()
for f,s,g in itertools.product((5,8,12,19),(17,26,39,52),(5,9,13)):
    if f<s:
        m=ema(c,f)-ema(c,s); S[f"MACD {f}/{s}/{g} cross"]=np.sign(m-ema(m,g)); S[f"MACD {f}/{s} zero"]=np.sign(m)
for k in(5,7,9,14,21):
    up=r.clip(lower=0).rolling(k).mean(); dn=(-r.clip(upper=0)).rolling(k).mean(); rsi=100-100/(1+up/dn)
    S[f"RSI {k} >50 (trend)"]=np.sign(rsi-50); S[f"RSI {k} 30/70 (reversal)"]=pd.Series(np.where(rsi<30,1,np.where(rsi>70,-1,0)),index=c.index)
for a,b in((5,20),(10,30),(10,50),(20,50),(20,100),(50,200)): S[f"MA cross {a}/{b}"]=np.sign(c.rolling(a).mean()-c.rolling(b).mean())
for k in(10,20,50,100,200): S[f"price vs MA {k}"]=np.sign(c-c.rolling(k).mean())
for k,w in itertools.product((10,20,30),(1.5,2,2.5)):
    mu=c.rolling(k).mean(); sd=c.rolling(k).std(); S[f"Bollinger {k}/{w} reversal"]=pd.Series(np.where(c<mu-w*sd,1,np.where(c>mu+w*sd,-1,0)),index=c.index)
for k in(10,20,55): S[f"breakout {k}-day"]=pd.Series(np.where(c>=h.rolling(k).max().shift(1),1,np.where(c<=l.rolling(k).min().shift(1),-1,0)),index=c.index)
for k in(1,3,5,10,22,66): S[f"momentum {k}-day"]=np.sign(c.pct_change(k)); S[f"reversal {k}-day"]=-np.sign(c.pct_change(k))
for k in(7,10,14):
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1); atr=tr.rolling(k).mean()
    for mlt in(2,3):
        st=np.sign(c-(( (h+l)/2).rolling(k).mean()-0*atr)); S[f"supertrend-like {k}/{mlt}"]=np.sign(c-(c.rolling(k).max()-mlt*atr))
k=14; lo=l.rolling(k).min(); hi=h.rolling(k).max(); st=100*(c-lo)/(hi-lo); S["stochastic 14 20/80 reversal"]=pd.Series(np.where(st<20,1,np.where(st>80,-1,0)),index=c.index)
tr_=n.index<="2016-12-31"; te=n.index>="2017-01-01"
def hit(sig,out,m):
    s=sig.shift(1)[m]; y=out[m]; k=(s!=0)&s.notna()&y.notna()&(y!=0)
    return (np.sign(y[k])==s[k]).mean() if k.sum()>100 else np.nan, int(k.sum())
rows=[]
for nm,sig in S.items():
    a1,n1=hit(sig,out1,tr_); b1,n2=hit(sig,out1,te); a6,_=hit(sig,out6,tr_); b6,_=hit(sig,out6,te)
    rows.append((nm,a1,b1,a6,b6,n1,n2))
D=pd.DataFrame(rows,columns=["signal","day_train","day_test","wk_train","wk_test","n_train","n_test"]).dropna()
base=lambda out,m:(out[m]>0).mean()
print("signals tested:",len(D),"| always-up baseline: same-day train %.1f%% test %.1f%% | 6-session train %.1f%% test %.1f%%"%(100*base(out1,tr_),100*base(out1,te),100*base(out6,tr_),100*base(out6,te)))
for col,lab in(("day","SAME DAY open-to-close"),("wk","NEXT 6 SESSIONS from the open")):
    a,b=D[col+"_train"],D[col+"_test"]
    print("\n%s: hit rate train median %.1f%% (range %.1f-%.1f) | test median %.1f%% (range %.1f-%.1f) | rank corr train vs test %.2f"%(lab,100*a.median(),100*a.min(),100*a.max(),100*b.median(),100*b.min(),100*b.max(),a.rank().corr(b.rank())))
    print(" top 6 on TRAIN and what they did on TEST:")
    for _,x in D.sort_values(col+"_train",ascending=False).head(6).iterrows(): print("   %-30s train %.1f%% -> test %.1f%% (n %d / %d)"%(x.signal,100*x[col+"_train"],100*x[col+"_test"],x.n_train,x.n_test))
    print(" share of signals above 52%% on BOTH train and test: %.0f%% ; above 55%% on both: %.0f%%"%(100*((a>.52)&(b>.52)).mean(),100*((a>.55)&(b>.55)).mean()))
