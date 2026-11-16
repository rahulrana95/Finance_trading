"""Compare spread combinations on modelled prices. Each side (call spread, put spread) is priced separately so sides can differ
in delta, width and quantity, and can be managed separately. Research only."""
import numpy as np, pandas as pd, itertools
from eng import *
import eng
calm=pd.read_pickle("calm.pkl").calm; cs=np.array([calm.get(t,np.nan) for t in idx])
def side(i,call,dl,wm,dte=7):
    S=O[i]; s=PV[i]/100; mult=eng.CALL_MULT if call else eng.PUT_MULT; w=max(50,r50(0.008*S*wm))
    k=max(r50(kdelta(S,dte/252,s*mult,dl,True)),r50(S)+50) if call else min(r50(kdelta(S,dte/252,s*mult,dl,False)),r50(S)-50)
    k2=k+w if call else k-w
    def val(S_,T_,s_):
        a=bs(S_,k,T_,s_*mult,call); b=bs(S_,k2,T_,s_*mult,call); return a-b, 0.025*(a+b)+2*0.15*S_/25000
    pts=[(val(O[i+j],(dte-j)/252,PV[i+j]/100),val(C[i+j],(dte-j-1)/252,V[i+j]/100),C[i+j]) for j in range(dte-1)]
    return dict(k=k,w=w,call=call,pts=pts,credit=pts[0][0][0],ecost=pts[0][0][1])
SIDES={}
def get(i,call,dl,wm):
    key=(i,call,dl,wm)
    if key not in SIDES: SIDES[key]=side(i,call,dl,wm)
    return SIDES[key]
def trade(i,spec,manage,pt=None):
    """spec: list of (call?,delta,width_mult,qty). manage: 'all' = close everything when Nifty closes beyond any short strike;
    'side' = close only the breached side, keep the other; 'none' = hold. Returns P&L / max loss."""
    ss=[(get(i,c,dl,wm),q) for c,dl,wm,q in spec]
    net=sum(q*(s["credit"]-s["ecost"]) for s,q in ss)
    if net<=0: return None
    maxloss=max(q*s["w"] for s,q in ss)-net
    openq=[True]*len(ss); pnl=net; n=len(ss[0][0]["pts"])
    for j in range(n):
        spot=ss[0][0]["pts"][j][2]
        breach=[(s["call"] and spot>=s["k"]) or ((not s["call"]) and spot<=s["k"]) for s,q in ss]
        last=j==n-1
        closeall=last or (manage=="all" and any(b and o for b,o in zip(breach,openq)))
        if pt and not closeall:
            cur=sum(q*s["pts"][j][1][0] for (s,q),o in zip(ss,openq) if o); cr=sum(q*s["credit"] for (s,q),o in zip(ss,openq) if o)
            if cr>0 and cur<=(1-pt)*cr: closeall=True
        for m,((s,q),o) in enumerate(zip(ss,openq)):
            if o and (closeall or (manage=="side" and breach[m])):
                v,cst=s["pts"][j][1]; pnl-=q*(v+cst); openq[m]=False
        if not any(openq): break
    return pnl/maxloss, net/max(q*s["w"] for s,q in ss)
C_,P_=True,False
SPECS={
 "condor 0.10 / 200 wide":[(C_,.10,1,1),(P_,.10,1,1)],
 "condor 0.08 / 200":[(C_,.08,1,1),(P_,.08,1,1)],
 "condor 0.12 / 200":[(C_,.12,1,1),(P_,.12,1,1)],
 "condor 0.10 / 100 wide":[(C_,.10,.5,1),(P_,.10,.5,1)],
 "condor 0.10 / 300 wide":[(C_,.10,1.5,1),(P_,.10,1.5,1)],
 "condor 0.12 / 100":[(C_,.12,.5,1),(P_,.12,.5,1)],
 "condor 0.12 / 300":[(C_,.12,1.5,1),(P_,.12,1.5,1)],
 "call spread 0.10 / 200":[(C_,.10,1,1)],
 "put spread 0.10 / 200":[(P_,.10,1,1)],
 "call spread 0.12 / 100":[(C_,.12,.5,1)],
 "put spread 0.12 / 100":[(P_,.12,.5,1)],
 "call closer: call 0.12, put 0.08":[(C_,.12,1,1),(P_,.08,1,1)],
 "put closer: call 0.08, put 0.12":[(C_,.08,1,1),(P_,.12,1,1)],
 "call heavy: 2 call : 1 put":[(C_,.10,1,2),(P_,.10,1,1)],
 "put heavy: 1 call : 2 put":[(C_,.10,1,1),(P_,.10,1,2)],
 "call 100 wide, put 300 wide":[(C_,.10,.5,1),(P_,.10,1.5,1)],
 "call 300 wide, put 100 wide":[(C_,.10,1.5,1),(P_,.10,.5,1)],
 "call 0.12/100 x2 + put 0.08/200":[(C_,.12,.5,2),(P_,.08,1,1)],
}
ALL=("2008-04-01","2026-10-31"); out=[]
for name,spec in SPECS.items():
    for manage in(("all","side","none") if len(spec)>1 else ("all","none")):
        for pt in(None,0.5):
            for gate in(True,False):
                rows=[];crs=[]
                for i in first:
                    if gate and not cs[i]>=0.5: continue
                    r=trade(i,spec,manage,pt)
                    if r: rows.append((i,r[0],1.0)); crs.append(r[1])
                st=[stats(rows,*p) for p in(TRAIN,VAL,HOLD,ALL)]
                if all(st): out.append(dict(combo=name,manage=manage,pt=pt,gate=gate,credit=100*np.mean(crs),st=st))
sc=lambda z:z["ret"]/max(-z["dd"],1.0)
D=pd.DataFrame([dict(combo=o["combo"],manage=o["manage"],pt=o["pt"] or 0,gate=o["gate"],credit=o["credit"],
    tr=o["st"][0]["ret"],va=o["st"][1]["ret"],ho=o["st"][2]["ret"],all=o["st"][3]["ret"],dd=o["st"][3]["dd"],wm=o["st"][3]["wmonth"],wy=o["st"][3]["wyear"],
    win=o["st"][3]["win"],lw=o["st"][3]["ratio"],n=o["st"][3]["n"],up=o["st"][3]["posyears"],score=sc(o["st"][3]),worst_period=min(o["st"][k]["ret"] for k in range(3))) for o in out])
pd.set_option("display.width",250); D.to_pickle("combos.pkl")
print("configs",len(D),"| every trade sized to max loss 4% of capital | returns are % of capital per year")
g=D[D.gate]
print("\n1. STRUCTURE (calm weeks only; best management + profit-target setting for each, chosen by all-years return/drawdown)")
b=g.sort_values("score",ascending=False).groupby("combo",sort=False).head(1)
print(b[["combo","manage","pt","credit","tr","va","ho","all","dd","wm","wy","win","lw","up","score"]].round(1).to_string(index=False))
print("\n2. What each choice does on average (calm weeks only, median across all other choices)")
def med(col,frame=g):
    print(frame.groupby(col)[["tr","va","ho","all","dd","win","lw","score"]].median().round(2).to_string())
two=g[~g.combo.str.contains("spread")]
print("- management of a two-sided position"); med("manage",two)
print("- profit target (0 = hold)"); med("pt")
print("- calm gate on/off (all combos)"); med("gate",D)
print("\n3. Width and delta (symmetric condors, calm weeks, close-all management, no profit target)")
x=g[(g.manage=="all")&(g.pt==0)&g.combo.str.startswith("condor")]; print(x[["combo","credit","tr","va","ho","all","dd","wm","win","lw","score"]].round(1).to_string(index=False))
print("\n4. Most consistent: top 10 by the WORST of the three periods (calm weeks only)")
print(g.sort_values("worst_period",ascending=False).head(10)[["combo","manage","pt","tr","va","ho","all","dd","wm","win","lw"]].round(1).to_string(index=False))
