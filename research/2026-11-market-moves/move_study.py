import json, numpy as np, pandas as pd
def load(p,tz):
    r=json.load(open(p))["chart"]["result"][0]; q=r["indicators"]["quote"][0]
    d=pd.DataFrame({k:q[k] for k in("open","high","low","close")},
        index=pd.to_datetime(r["timestamp"],unit="s",utc=True).tz_convert(tz).normalize().tz_localize(None)).dropna()
    return d[~d.index.duplicated()]
n=load("nsei.json","Asia/Kolkata"); iv=load("vix.json","Asia/Kolkata").close
us=load("GSPC.json","America/New_York"); uv=load("VIX.json","America/New_York").close
d=n.copy(); d["vix"]=iv.reindex(d.index).ffill()
u=pd.DataFrame({"us_ret":us.close.pct_change(),"usvix_chg":uv.reindex(us.index).pct_change()}).dropna()
d=pd.merge_asof(d.reset_index(names="date"),u.reset_index(names="usdate"),left_on="date",right_on="usdate",allow_exact_matches=False).set_index("date")
fresh=d.usdate!=d.usdate.shift(1)          # new US session since last India session
c=d.close; r=c.pct_change()
d["gap"]=d.open/c.shift(1)-1; d["oc"]=d.close/d.open-1; d["cc"]=r
d["rng"]=(d.high-d.low)/d.open
macd=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean(); sig=macd.ewm(span=9,adjust=False).mean()
P=pd.DataFrame({"yday_ret":r.shift(1),"5d_ret":c.shift(1)/c.shift(6)-1,"macd_line_vs_signal":(macd-sig).shift(1),
 "macd_vs_zero":macd.shift(1),"above_50dma":(c/c.rolling(50).mean()-1).shift(1),
 "us_overnight":d.us_ret.where(fresh),"today_gap":d.gap},index=d.index)
d=d.loc["2008-03":]; P=P.loc[d.index]
print("days",len(d),d.index[0].date(),d.index[-1].date())
print("\nA. DIRECTION: how often does the sign of the predictor match the move?  (50% = coin toss)")
print("%-22s %-26s %-26s %-22s"%("predictor","gap at open","open-to-close (tradable)","next close-to-close"))
def hit(p,y):
    m=p.notna()&y.notna()&(p!=0)&(y!=0); k=(np.sign(p[m])==np.sign(y[m])).mean(); nn=m.sum()
    return "%.1f%% ±%.1f (n=%d)"%(100*k,196*(k*(1-k)/nn)**.5,nn)
for k in P:
    print("%-22s %-26s %-26s %-22s"%(k,"-" if k=="today_gap" else hit(P[k],d.gap),hit(P[k],d.oc),"-" if k=="today_gap" else hit(P[k],d.cc)))
print("up days: close-to-close %.1f%%, open-to-close %.1f%%"%(100*(d.cc>0).mean(),100*(d.oc>0).mean()))
def sc(a,b):
    m=a.notna()&b.notna(); return a[m].rank().corr(b[m].rank())
print("\nB. SIZE of move: correlation of predictor with today's absolute open-to-close move and range")
rv5=r.abs().rolling(5).mean().shift(1); rv20=r.abs().rolling(20).mean().shift(1)
S=pd.DataFrame({"india_vix_yday":d.vix.shift(1),"avg_abs_move_5d":rv5,"avg_abs_move_20d":rv20,"yday_range":d.rng.shift(1),
 "abs_today_gap":d.gap.abs(),"abs_us_overnight":d.us_ret.where(fresh).abs(),"us_vix_change":d.usvix_chg.where(fresh)}).loc[d.index]
for k in S: print("  %-18s |open-close| %.2f   range %.2f"%(k,sc(S[k],d.oc.abs()),sc(S[k],d.rng)))
print("\nC. Days sorted by yesterday's India VIX (5 equal groups): what the day looked like")
q=pd.qcut(d.vix.shift(1),5,labels=["lowest","low","mid","high","highest"])
g=d.groupby(q,observed=True).agg(vix=("vix","mean"),avg_abs_move=("cc",lambda x:100*x.abs().mean()),avg_range=("rng",lambda x:100*x.mean()),big_day_pct=("cc",lambda x:100*(x.abs()>0.015).mean()),up_pct=("cc",lambda x:100*(x>0).mean()),n=("cc","size"))
print(g.round(2).to_string())
print("\nD. WEEK AHEAD (6 sessions from week's first open): actual move vs what VIX implied")
wk=pd.Series(d.index.to_period("W"),index=d.index); fi=np.where(~wk.duplicated().values)[0]; rows=[]
for i in fi:
    if i<25 or i+5>=len(d): continue
    e=d.open.iloc[i]; w=d.iloc[i:i+6]; imp=d.vix.iloc[i-1]/100*np.sqrt(8/365)
    rows.append(dict(date=d.index[i],imp=imp,act=abs(w.close.iloc[-1]/e-1),maxex=max(w.high.max()/e-1,1-w.low.min()/e),
      rv=r.iloc[i-20:i].std()*np.sqrt(6),))
W=pd.DataFrame(rows).set_index("date"); W["ratio"]=W.imp/W.rv
print("weeks",len(W)," mean implied 1-sd move %.2f%%, mean actual |move| %.2f%% (a fair 1-sd implies ~%.2f%%)"%(100*W.imp.mean(),100*W.act.mean(),100*W.imp.mean()*0.8))
print("actual move bigger than implied 1-sd: %.1f%% of weeks (fair value ~32%%)"%(100*(W.act>W.imp).mean()))
print("rank corr with actual |move|: VIX-implied %.2f | last-20-day actual vol %.2f"%(sc(W.imp,W.act),sc(W.rv,W.act)))
q=pd.qcut(W.ratio,4,labels=["VIX cheap vs recent","2","3","VIX rich vs recent"])
print(W.groupby(q,observed=True).apply(lambda x:pd.Series({"implied/recent":x.ratio.mean(),"actual/implied":(x.act/x.imp).mean(),"beyond 1.28sd at end %":100*(x.act>1.28*x.imp).mean(),"touched 1.28sd %":100*(x.maxex>1.28*x.imp).mean(),"n":len(x)})).round(2).to_string())
for lo,hi in(("2008","2013"),("2014","2019"),("2020","2026")):
    x=W.loc[lo:hi]; qq=x.ratio>x.ratio.median()
    print(lo,hi,"touched 1.28sd: VIX rich %.1f%% | VIX cheap %.1f%%"%(100*(x.maxex>1.28*x.imp)[qq].mean(),100*(x.maxex>1.28*x.imp)[~qq].mean()))
