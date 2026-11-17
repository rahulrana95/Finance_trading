"""Which large NSE stocks suited the 'shares 50% + half a futures lot per 10% fall, max 3 lots' rule, and does past suitability carry over?
Daily closes from 2014; results from 2016. Same proportions as before (one lot = 56% of capital in stock, margin 18%). Research only."""
import json, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
LOT=0.5595; MARGIN=0.179; CARRY=0.06; ROLL=0.0005; TRADE=0.0005; SC=0.0012; CASH=0.05; HAIR=0.85; DEBIT=0.12
def load(sym):
    try:
        r=json.load(open("stocks/%s.json"%sym))["chart"]["result"][0]; q=r["indicators"]["quote"][0]
        s=pd.Series(q["close"],index=pd.to_datetime(r["timestamp"],unit="s",utc=True).tz_convert("Asia/Kolkata").normalize().tz_localize(None)).dropna()
        s=s[~s.index.duplicated()]; return s if len(s)>2000 else None
    except Exception: return None
def rule(c,ref,a,b,core=0.5,step=0.10,per=0.5,cap=3,eq0=20.0):
    p=c[a]; hs=core*eq0*1e5/p; cash=eq0-hs*p/1e5*(1+SC); fs=0.0; R=None; level=0; lots=0.0; locked=False; forced=0; hi=eq0; dd=0.0; eq=eq0
    for t in range(a+1,b):
        p=c[t]
        if fs>0: cash+=fs*(p-c[t-1])/1e5-fs*p/1e5*(CARRY/252+ROLL/21)
        cash+=cash*(CASH if cash>0 else DEBIT)/252; eq=cash+hs*p/1e5
        if fs>0 and p>=R: cash-=fs*p/1e5*TRADE; fs=0;lots=0;level=0;R=None
        if locked and p>=ref[t]*0.999: locked=False
        if per>0 and not locked:
            if fs==0 and R is None and p<=ref[t]*(1-step): R=ref[t]; lot_sh=LOT*eq*1e5/p; level=0
            if R is not None:
                k=int(np.floor((1-p/R)/step+1e-9))
                while level<k:
                    level+=1; add=min(per,cap-lots)
                    if add>0: fs+=add*lot_sh; lots+=add; cash-=add*lot_sh*p/1e5*TRADE
        if fs>0 and cash+HAIR*hs*p/1e5<MARGIN*fs*p/1e5: cash-=fs*p/1e5*TRADE; fs=0;lots=0;level=0;R=None;locked=True;forced+=1
        eq=cash+hs*p/1e5; hi=max(hi,eq); dd=min(dd,eq/hi-1)
        if eq<=0: return 0.0,-1.0,forced+1
    return eq,dd,forced
def dips(c,ref,a,b,X=0.10):
    out=[]; t=a
    while t<b:
        if c[t]<=ref[t]*(1-X):
            R=ref[t]; rec=None
            for u in range(t+1,len(c)):
                if c[u]>=R: rec=u; break
            end=rec if rec is not None else len(c)-1
            out.append((rec-t if rec is not None else None, c[t:end+1].min()/R-1)); t=end+1
        else: t+=1
    return out
if __name__=='__main__':
    big=open("stocks/_big.txt").read().split(); fallen=open("stocks/_fallen.txt").read().split(); rows=[]
    for grp,syms in(("large",big),("fallen",fallen)):
        for s in syms:
            x=load(s)
            if x is None: continue
            c=x.values; idx=x.index; ref=x.rolling(126,min_periods=60).max().values
            a=idx.searchsorted(pd.Timestamp("2016-01-01")); m=idx.searchsorted(pd.Timestamp("2021-06-01")); n=len(c)
            yr=lambda i,j:(idx[j-1]-idx[i]).days/365.25
            r={"stock":s,"group":grp}
            for lab,i,j in(("all",a,n),("h1",a,m),("h2",m,n)):
                e,dd,f=rule(c,ref,i,j); r["rule_"+lab]=100*((max(e,1e-9)/20)**(1/yr(i,j))-1); r["drop_"+lab]=100*dd; r["mc_"+lab]=f
                r["hold_"+lab]=100*((c[j-1]/c[i])**(1/yr(i,j))-1)
                dp=dips(c,ref,i,j); rec=[d[0] for d in dp if d[0] is not None]
                r["dips_"+lab]=len(dp); r["rec12_"+lab]=100*np.mean([(d[0] is not None and d[0]<=252) for d in dp]) if dp else np.nan
                r["recmed_"+lab]=np.median(rec) if rec else np.nan; r["deep_"+lab]=100*min(d[1] for d in dp) if dp else 0
            s_=x[a:]; r["maxdd"]=100*(s_/s_.cummax()-1).min(); by=s_.groupby(s_.index.year).last(); r["up_years"]="%d/%d"%((by.pct_change().dropna()>0).sum(),len(by)-1)
            rows.append(r)
    D=pd.DataFrame(rows).set_index("stock"); D.to_pickle("screen.pkl"); L=D[D.group=="large"]; F=D[D.group=="fallen"]
    pd.set_option("display.width",250)
    print("stocks: %d large, %d fallen | rule = shares 50%% + half a lot per 10%% fall, max 3 lots | periods: first half 2016 to May 2021, second half Jun 2021 to Nov 2026\n"%(len(L),len(F)))
    print("DOES THE PAST PREDICT? (large stocks, first half vs second half, rank correlation)")
    for k,nm in(("rule","rule return"),("hold","share return"),("drop","worst drop"),("rec12","share of 10% dips back within 12 months"),("recmed","typical days to recover")):
        print("  %-44s %+.2f"%(nm,L[k+"_h1"].rank().corr(L[k+"_h2"].rank())))
    top=L.sort_values("rule_h1",ascending=False).head(10); bot=L.sort_values("rule_h1").head(10)
    print("  top 10 by rule return in the first half -> second half: rule %.1f%% a year (all large stocks %.1f%%), margin calls %d"%(top.rule_h2.mean(),L.rule_h2.mean(),top.mc_h2.sum()))
    print("  bottom 10 in the first half              -> second half: rule %.1f%% a year, margin calls %d"%(bot.rule_h2.mean(),bot.mc_h2.sum()))
    steady=L[(L.rec12_h1>=75)&(L.drop_h1>=-55)&(L.mc_h1==0)]; rest=L.drop(steady.index)
    print("  'steady' in first half (no margin call, drop within 55%%, 75%%+ of dips back in a year): %d stocks -> second half rule %.1f%% a year, worst drop avg %.0f%%, margin calls %d"%(len(steady),steady.rule_h2.mean(),steady.drop_h2.mean(),steady.mc_h2.sum()))
    print("  the other %d large stocks                                                              -> second half rule %.1f%% a year, worst drop avg %.0f%%, margin calls %d"%(len(rest),rest.rule_h2.mean(),rest.drop_h2.mean(),rest.mc_h2.sum()))
    print("\nGROUP SUMMARY 2016-2026: large: rule %.1f%% a year median, hold %.1f%%, margin calls in %d of %d stocks | fallen: rule %.1f%% median, hold %.1f%%, margin calls in %d of %d, wiped out (below 25%% of capital): %d"%(
        L.rule_all.median(),L.hold_all.median(),(L.mc_all>0).sum(),len(L),F.rule_all.median(),F.hold_all.median(),(F.mc_all>0).sum(),len(F),(F.rule_all<-12).sum()))
    ok=L[(L.mc_all==0)&(L.mc_h1==0)&(L.mc_h2==0)&(L.rule_h1>5)&(L.rule_h2>5)&(L.rec12_all>=75)&(L.drop_all>=-60)].copy()
    ok["score"]=ok[["rule_h1","rule_h2"]].min(axis=1)
    cols=["rule_all","hold_all","rule_h1","rule_h2","drop_all","maxdd","dips_all","rec12_all","recmed_all","up_years"]
    print("\nPASSED EVERY CHECK in BOTH halves (no margin call, rule above 5%% a year in each half, 75%%+ of 10%% dips back within a year, rule's worst drop within 60%%): %d of %d"%(len(ok),len(L)))
    print(ok.sort_values("score",ascending=False)[cols].round(1).rename(columns={"rule_all":"rule %/yr","hold_all":"shares %/yr","rule_h1":"rule 2016-21","rule_h2":"rule 2021-26","drop_all":"rule worst drop %","maxdd":"share worst fall %","dips_all":"10% dips","rec12_all":"% back in 12m","recmed_all":"typical days","up_years":"up years"}).to_string())
    bad=L.drop(ok.index); print("\nFAILED A CHECK (%d): "%len(bad)+", ".join("%s (%s)"%(s,"margin call" if r.mc_all>0 or r.mc_h1>0 or r.mc_h2>0 else "weak half" if min(r.rule_h1,r.rule_h2)<=5 else "slow recovery" if r.rec12_all<75 else "deep drop") for s,r in bad.iterrows()))
    print("\nFALLEN GROUP under the same rule:"); print(F[["rule_all","hold_all","drop_all","mc_all","rec12_all"]].round(1).rename(columns={"rule_all":"rule %/yr","hold_all":"shares %/yr","drop_all":"worst drop %","mc_all":"margin calls","rec12_all":"% dips back in 12m"}).sort_values("rule %/yr").to_string())
