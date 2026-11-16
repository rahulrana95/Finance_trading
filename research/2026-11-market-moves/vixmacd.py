import numpy as np, pandas as pd
from eng import *
from combos import trade, C_, P_, cs
F=pd.read_pickle("F.pkl"); T=pd.read_pickle("T.pkl")
macd=np.array([F.macd.get(t,np.nan) for t in idx]); vix=PV
print("\nA. Touch rate of a 0.10-delta-distance strike (either side), all days 2008-2026, by MACD sign and VIX band")
y=(T.zmax>=1.28); b=pd.cut(F.vix,[0,13,16,20,26,100],labels=["VIX<13","13-16","16-20","20-26","VIX>26"]); m=np.where(F.macd>0,"MACD>0","MACD<0")
print((100*y.groupby([m,b],observed=True).mean()).unstack().round(1).to_string()); print("days:"); print(y.groupby([m,b],observed=True).size().unstack().to_string())
spec=[(C_,.12,1.5,1),(P_,.12,1.5,1)]
G={"every week":lambda i:True,"MACD>0":lambda i:macd[i]>0,"VIX 13-26":lambda i:13<=vix[i]<=26,"MACD>0 and VIX 13-26":lambda i:macd[i]>0 and 13<=vix[i]<=26,
   "MACD>0 and VIX>=13":lambda i:macd[i]>0 and vix[i]>=13,"MACD>0 and VIX<=26":lambda i:macd[i]>0 and vix[i]<=26,
   "calm>=0.5":lambda i:cs[i]>=.5,"calm>=0.5 and VIX>=13":lambda i:cs[i]>=.5 and vix[i]>=13,"calm>=0.5 and VIX 13-26":lambda i:cs[i]>=.5 and 13<=vix[i]<=26,
   "calm>=0.5 and MACD>0":lambda i:cs[i]>=.5 and macd[i]>0}
print("\nB. Condor 0.12 / 300 wide, hold, exit on close beyond short strike, max loss 4% per trade (modelled prices)")
for nm,f in G.items():
    rows=[(i,r[0],1.0) for i in first if f(i) and (r:=trade(i,spec,"all"))]
    a=[stats(rows,*p) for p in(TRAIN,VAL,HOLD,("2008-04-01","2026-10-31"))]
    print(" %-26s train %+5.1f | val %+5.1f | 22-26 %+5.1f | all %+5.1f  maxDD %6.1f  worst month %5.1f  worst yr %+5.1f  win %2.0f%%  trades/yr %2.0f"%(nm,a[0]["ret"],a[1]["ret"],a[2]["ret"],a[3]["ret"],a[3]["dd"],a[3]["wmonth"],a[3]["wyear"],a[3]["win"],a[3]["n"]/18.6))
