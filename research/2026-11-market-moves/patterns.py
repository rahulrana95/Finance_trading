"""Which chart patterns (alone and in pairs) predicted Nifty's next move? Daily, 4-hour and 1-hour bars.
Signal is read at a bar's close; entry is the next bar's open; exit is the close H bars later. No costs. Research only."""
import json, sys, itertools, numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
from feat import load
def hourly():
    r=json.load(open("nsei_1h.json"))["chart"]["result"][0]; q=r["indicators"]["quote"][0]
    d=pd.DataFrame({k:q[k] for k in("open","high","low","close")},index=pd.to_datetime(r["timestamp"],unit="s",utc=True).tz_convert("Asia/Kolkata").tz_localize(None)).dropna()
    return d[(d.high>=d.low)&~d.index.duplicated()]
def four_hour(h):
    key=h.index.normalize()+pd.to_timedelta(np.where(h.index.hour*60+h.index.minute<13*60+15,9,13),unit="h")
    return h.groupby(key).agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"))
def signals(d):
    o,h,l,c=(d[k].values.astype(float) for k in("open","high","low","close")); n=len(d); C=pd.Series(c)
    tr=np.maximum(h-l,np.maximum(abs(h-np.roll(c,1)),abs(l-np.roll(c,1)))); tr[0]=h[0]-l[0]; atr=pd.Series(tr).rolling(14).mean().values
    L={};S={}                                        # long / short event signals (bool arrays)
    new=lambda a,k=5: a & ~(pd.Series(a).shift(1).rolling(k).max().fillna(0).astype(bool).values)   # first firing in k bars
    for N in(20,55,250):
        hh=C.shift(1).rolling(N).max().values; ll=C.shift(1).rolling(N).min().values
        nm={250:"1 high/low breakout, 250 bars",55:"1b breakout, 55 bars",20:"1c breakout, 20 bars"}[N]
        L[nm]=new(c>hh); S[nm]=new(c<ll)
    s50=C.rolling(50).mean().values; s200=C.rolling(200).mean().values
    cross=lambda a,b:(a>b)&(np.roll(a,1)<=np.roll(b,1))
    L["2 MA cross: price over 50-bar avg"]=cross(c,s50); S["2 MA cross: price over 50-bar avg"]=cross(s50,c)
    L["2b golden / death cross 50 over 200"]=cross(s50,s200); S["2b golden / death cross 50 over 200"]=cross(s200,s50)
    day=d.index.normalize(); first=np.r_[True,day[1:]!=day[:-1]]; gap=np.r_[0,o[1:]/c[:-1]-1]
    L["3 gap 0.5%+ that holds"]=first&(gap>=0.005)&(c>o); S["3 gap 0.5%+ that holds"]=first&(gap<=-0.005)&(c<o)
    rng=(pd.Series(h).shift(1).rolling(20).max()-pd.Series(l).shift(1).rolling(20).min())/C.shift(1)
    tight=(rng.rolling(250,min_periods=100).rank(pct=True)<=0.33).values
    L["4 breakout from a tight 20-bar range"]=new(tight&(c>pd.Series(h).shift(1).rolling(20).max().values)); S["4 breakout from a tight 20-bar range"]=new(tight&(c<pd.Series(l).shift(1).rolling(20).min().values))
    fl=np.zeros(n,bool); fs=np.zeros(n,bool)
    for t in range(30,n):
        a=atr[t-4]
        if not a>0: continue
        pole=c[t-4]-c[t-9]; ph=h[t-3:t].max(); pl=l[t-3:t].min()
        if ph-pl<=1.5*a:
            if pole>=2.5*a and pl>c[t-9]+0.5*pole and c[t]>ph: fl[t]=True
            if pole<=-2.5*a and ph<c[t-9]+0.5*pole and c[t]<pl: fs[t]=True
    L["5 flag after a sharp move"]=fl; S["5 flag after a sharp move"]=fs
    # confirmed swing pivots (3 bars each side, known 3 bars late)
    K=3; ph_=[];pl_=[]                              # (index, price)
    sup_b=np.zeros(n,bool);res_r=np.zeros(n,bool);dt=np.zeros(n,bool);db=np.zeros(n,bool);hs=np.zeros(n,bool);ihs=np.zeros(n,bool);tu=np.zeros(n,bool);td=np.zeros(n,bool)
    for t in range(2*K,n):
        i=t-K
        if h[i]==h[i-K:i+K+1].max(): ph_.append((i,h[i]))
        if l[i]==l[i-K:i+K+1].min(): pl_.append((i,l[i]))
        a=atr[t]
        if not a>0 or len(ph_)<3 or len(pl_)<3: continue
        H1,H2,H3=ph_[-3],ph_[-2],ph_[-1]; L1,L2,L3=pl_[-3],pl_[-2],pl_[-1]
        down3=c[t-1]<c[t-4]; up3=c[t-1]>c[t-4]
        # 6 support bounce / resistance rejection at the last confirmed swing level
        if t-L3[0]>=5 and abs(l[t]-L3[1])<=0.3*a and c[t]>o[t] and c[t]>L3[1]: sup_b[t]=True
        if t-H3[0]>=5 and abs(h[t]-H3[1])<=0.3*a and c[t]<o[t] and c[t]<H3[1]: res_r[t]=True
        # 8 double top / bottom: two swings within 0.5 ATR, break of the level between them
        if abs(H3[1]-H2[1])<=0.5*a and t-H3[0]<=30:
            mid=[p for p in pl_ if H2[0]<p[0]<H3[0]]
            if mid:
                nk=min(p[1] for p in mid)
                if c[t]<nk<=c[t-1]: dt[t]=True
        if abs(L3[1]-L2[1])<=0.5*a and t-L3[0]<=30:
            mid=[p for p in ph_ if L2[0]<p[0]<L3[0]]
            if mid:
                nk=max(p[1] for p in mid)
                if c[t]>nk>=c[t-1]: db[t]=True
        # 7 head and shoulders: middle swing highest, shoulders within 1 ATR, break of the neckline
        if H2[1]>H1[1]+0.5*a and H2[1]>H3[1]+0.5*a and abs(H1[1]-H3[1])<=1.0*a and t-H3[0]<=30:
            lows=[p[1] for p in pl_ if H1[0]<p[0]<H3[0]]
            if lows:
                nk=np.mean(lows)
                if c[t]<nk<=c[t-1]: hs[t]=True
        if L2[1]<L1[1]-0.5*a and L2[1]<L3[1]-0.5*a and abs(L1[1]-L3[1])<=1.0*a and t-L3[0]<=30:
            highs=[p[1] for p in ph_ if L1[0]<p[0]<L3[0]]
            if highs:
                nk=np.mean(highs)
                if c[t]>nk>=c[t-1]: ihs[t]=True
        # 9 triangle: lower highs and higher lows, then a close outside
        if H3[1]<H2[1] and L3[1]>L2[1] and t-max(H3[0],L3[0])<=20:
            if c[t]>H3[1]>=c[t-1]: tu[t]=True
            if c[t]<L3[1]<=c[t-1]: td[t]=True
    L["6 bounce off support / rejection at resistance"]=sup_b; S["6 bounce off support / rejection at resistance"]=res_r
    L["7 head and shoulders (inverse for long)"]=ihs; S["7 head and shoulders (inverse for long)"]=hs
    L["8 double bottom / double top"]=db; S["8 double bottom / double top"]=dt
    L["9 triangle breakout"]=tu; S["9 triangle breakout"]=td
    body=abs(c-o); pc,po=np.roll(c,1),np.roll(o,1); d3=np.roll(c,1)<np.roll(c,4); u3=np.roll(c,1)>np.roll(c,4)
    L["10 engulfing candle"]=d3&(pc<po)&(c>o)&(c>=po)&(o<=pc); S["10 engulfing candle"]=u3&(pc>po)&(c<o)&(c<=po)&(o>=pc)
    lo_sh=np.minimum(o,c)-l; up_sh=h-np.maximum(o,c)
    L["10b hammer / shooting star"]=d3&(lo_sh>=2*body)&(up_sh<=0.5*body+1e-9)&(body>0); S["10b hammer / shooting star"]=u3&(up_sh>=2*body)&(lo_sh<=0.5*body+1e-9)&(body>0)
    e12=C.ewm(span=12,adjust=False).mean(); e26=C.ewm(span=26,adjust=False).mean(); macd=(e12-e26).values
    ST={"trend up (price > 50 > 200 avg)":(c>s50)&(s50>s200),"trend down (price < 50 < 200 avg)":(c<s50)&(s50<s200),"MACD above zero":macd>0,"MACD below zero":macd<0,
        "above 200-bar avg":c>s200,"below 200-bar avg":c<s200}
    return L,S,ST
def evaluate(d,name,H,split):
    L,S,ST=signals(d); o,c=d.open.values,d.close.values; n=len(d)
    fwd=np.full(n,np.nan); fwd[:n-H]=c[H:]/o[1:n-H+1]-1          # enter next open, exit close H bars later
    idx=d.index; tr=(idx<split); te=(idx>=split); ok=~np.isnan(fwd)&(np.arange(n)>=260)
    def thin(sig):                                               # drop firings within H bars of the previous one
        out=np.zeros(n,bool); last=-10**9
        for t in np.flatnonzero(sig&ok):
            if t-last>H: out[t]=True; last=t
        return out
    def st(sig,side,m):
        x=side*fwd[sig&m]; b=side*fwd[ok&m]
        if len(x)<8: return None
        return dict(n=len(x),hit=100*(x>0).mean(),bhit=100*(b>0).mean(),edge=1e4*(x.mean()-b.mean()),t=(x.mean()-b.mean())/(x.std(ddof=1)/np.sqrt(len(x))+1e-12))
    rows=[]
    def add(lab,sig,side):
        s=thin(sig); a=st(s,side,tr); b=st(s,side,te)
        if a and b: rows.append(dict(sig=lab,side="long" if side>0 else "short",**{k+"_tr":v for k,v in a.items()},**{k+"_te":v for k,v in b.items()}))
    for k,v in L.items(): add(k,v,1)
    for k,v in S.items(): add(k,v,-1)
    R=pd.DataFrame(rows)
    recent=lambda a,k=3: pd.Series(a).rolling(k).max().fillna(0).astype(bool).values
    combo=[]
    for side,E,states in((1,L,["trend up (price > 50 > 200 avg)","MACD above zero","above 200-bar avg","trend down (price < 50 < 200 avg)","below 200-bar avg"]),
                         (-1,S,["trend down (price < 50 < 200 avg)","MACD below zero","below 200-bar avg","trend up (price > 50 > 200 avg)","above 200-bar avg"])):
        def addc(lab,sig):
            s=thin(sig); a=st(s,side,tr); b=st(s,side,te)
            if a and b and a["n"]>=12 and b["n"]>=12: combo.append(dict(sig=lab,side="long" if side>0 else "short",**{k+"_tr":v for k,v in a.items()},**{k+"_te":v for k,v in b.items()}))
        for k,v in E.items():
            for s_ in states: addc(k+"  +  "+s_,v&ST[s_])
        for (k1,v1),(k2,v2) in itertools.combinations(E.items(),2):
            if k1.split()[0][:2]==k2.split()[0][:2] and k1[0]=="1": continue
            addc(k1+"  +  "+k2,(v1&recent(v2))|(v2&recent(v1)))
    Cb=pd.DataFrame(combo)
    f=lambda r:"%-50s %-5s | train n=%3d hit %2.0f%% (base %2.0f%%) edge %+5.0f bp | test n=%3d hit %2.0f%% (base %2.0f%%) edge %+5.0f bp"%(r.sig[:50],r.side,r.n_tr,r.hit_tr,r.bhit_tr,r.edge_tr,r.n_te,r.hit_te,r.bhit_te,r.edge_te)
    print("\n"+"="*150+"\n%s | %d bars %s to %s | hold %d bars | train before %s (%d bars), test after (%d bars)"%(name,n,idx[0].date(),idx[-1].date(),H,split,tr.sum(),te.sum()))
    print("SINGLE PATTERNS (edge = average result minus the average of all bars, in basis points; 100 bp = 1%)")
    for _,r in R.sort_values(["side","sig"]).iterrows(): print(" "+f(r))
    good=R[(R.edge_tr>0)&(R.edge_te>0)&(R.hit_tr>R.bhit_tr)&(R.hit_te>R.bhit_te)]
    print(" -> better than baseline on hit rate AND average result in BOTH periods: %d of %d"%(len(good),len(R)))
    if len(Cb):
        gc=Cb[(Cb.edge_tr>0)&(Cb.edge_te>0)&(Cb.hit_tr>Cb.bhit_tr)&(Cb.hit_te>Cb.bhit_te)]
        print("COMBINATIONS tested: %d | positive in train: %d | positive in both periods: %d | rank corr of edge train vs test: %.2f"%(len(Cb),(Cb.edge_tr>0).sum(),len(gc),Cb.edge_tr.rank().corr(Cb.edge_te.rank())))
        print(" top 8 by TRAIN t-stat, with their TEST result:")
        for _,r in Cb.sort_values("t_tr",ascending=False).head(8).iterrows(): print("  "+f(r))
        gc=gc.assign(m=np.minimum(gc.t_tr,gc.t_te)).sort_values("m",ascending=False)
        print(" most consistent (ranked by the weaker of the two periods):")
        for _,r in gc.head(8).iterrows(): print("  "+f(r))
    R["tf"]=name;Cb["tf"]=name; return R,Cb
if __name__=="__main__":
    dly=load("NIFTY","Asia/Kolkata").dropna(); dly=dly[(dly.high>=dly.low)&(dly.open>0)].loc["2007-09":]
    h1=hourly(); h4=four_hour(h1); mid=str(h1.index[len(h1)//2].date())
    out=[]
    for d,nm,H,sp in((dly,"DAILY",5,"2017-01-01"),(dly,"DAILY",10,"2017-01-01"),(h4,"4-HOUR",5,mid),(h4,"4-HOUR",10,mid),(h1,"1-HOUR",5,mid),(h1,"1-HOUR",10,mid)):
        R,Cb=evaluate(d,nm,H,sp); R["H"]=H;Cb["H"]=H; out.append((R,Cb))
    pd.concat([x[0] for x in out]).to_pickle("pat_single.pkl"); pd.concat([x[1] for x in out]).to_pickle("pat_combo.pkl")
