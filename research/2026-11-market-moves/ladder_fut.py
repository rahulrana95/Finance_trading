"""ICICI Bank FUTURES ladder, literal terms: 1 lot = 700 units in every year, margin 18% of contract value (Rs 2 L today),
capital Rs 20 L, buy 2 lots at each 5% step below the 6-month high, sell all when back at that high."""
import numpy as np, pandas as pd
from ladder import run, c, idx, i0, CAP, MARGIN
def show(lab,x):
    cy=x["cycles"]; fo=(cy.why!="recovered").sum() if len(cy) else 0
    print("%-46s final Rs %5.1f L | profit Rs %5.1f L | CAGR %+5.1f%% | worst drawdown %5.1f%% | lowest capital Rs %4.1f L (%s) | most lots %2d | cycles %d, won %d, forced out %d"%(lab,x["final"],x["final"]-CAP,x["cagr"],x["dd"],x["low"],x["lowdate"],x["maxlots"],len(cy),(cy.why=="recovered").sum(),fo))
print("contract value of one 700-unit lot: Jan 2016 Rs %.1f L (margin Rs %.2f L) | Mar 2020 low Rs %.1f L | today Rs %.1f L (margin Rs %.1f L)\n"%(700*c[i0]/1e5,MARGIN*700*c[i0]/1e5,700*284/1e5,700*c[-1]/1e5,MARGIN*700*c[-1]/1e5))
A=run(2,units=700); show("2 lots every 5% down, no limit",A)
B=run(2,cap_lots=5,units=700); show("2 lots every 5% down, at most 5 lots",B)
cy=A["cycles"]; print("\nEvery cycle, 2 lots every 5%, no limit (700 units per lot):")
print(cy.assign(start=cy.start.dt.date,end=cy.end.dt.date,gain=cy.gain.round(2),pct=cy.pct.round(1)).rename(columns={"gain":"profit Rs L","pct":"% of capital then"}).to_string(index=False))
cv=A["curve"]; y=cv.groupby(cv.index.year).last(); prev=y.shift(1).fillna(CAP)
print("\nCapital at each year end (Rs L) and that year's profit:"); print(pd.DataFrame({"capital":y.round(1),"profit":(y-prev).round(1),"% of start-of-year capital":(100*(y/prev-1)).round(1)}).T.to_string())
print("\nSame literal rule started later (700 units per lot, Rs 20 L):")
for yr in(2018,2020,2022,2023,2024,2025):
    st=idx.searchsorted(pd.Timestamp("%d-01-01"%yr)); a=run(2,start=st,units=700); b=run(2,cap_lots=5,start=st,units=700)
    f=lambda x:(x["cycles"].why!="recovered").sum() if len(x["cycles"]) else 0
    print("  from %d: no limit -> final %5.1f L, CAGR %+5.1f%%, worst drawdown %5.1f%%, forced out %d | max 5 lots -> final %5.1f L, CAGR %+5.1f%%, worst drawdown %5.1f%%, forced out %d"%(yr,a["final"],a["cagr"],a["dd"],f(a),b["final"],b["cagr"],b["dd"],f(b)))
