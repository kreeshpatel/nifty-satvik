"""EXPLORE (tier 0): daily hard stop and disaster-floor arms on the live scaled exit, 2019..2024-06-30, PIT.

Writes diagnostics/research/explore/2026-11-12_stop_size_arms.json. No screen row, no n_trials change.
"""
import sys,json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[2]; sys.path[:0]=[str(ROOT),str(ROOT/"pipelines"/"diagnostics"),str(ROOT/"scripts")]
import diag_giveback_ratchet_0148 as G, run_bhanushali_weekly_rank as R94
from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT, LIVE_PREP, LIVE_STALENESS, load_demerger_rows
from run_bhanushali_path1 import corrected_universe
from nq.data.membership import load_membership
cut={t:df[pd.DatetimeIndex(df.index)<=pd.Timestamp(G.CUT)] for t,df in corrected_universe().items()}
cut={t:df for t,df in cut.items() if len(df)>60}
assert max(df.index.max() for df in cut.values())<=pd.Timestamp(G.CUT)
P=R94.prep_weekly_rank(cut,**LIVE_PREP); ev=R94.build_demerger_events(cut,load_demerger_rows(),**LIVE_PREP)
mem=load_membership(); A=R94.grade_a_entries(P)
ARMS={"base":{},"hard_stop":dict(hard_stop=True),"floor_3%":dict(disaster_floor_pct=0.03),"floor_5%":dict(disaster_floor_pct=0.05),"floor_10%":dict(disaster_floor_pct=0.10)}
res={}
for name,kw in ARMS.items():
  for book,unc in (("uncapped",True),("capped",False)):
    led=[]
    out=R94.backtest(P,mem,ledger=led,start=G.START,uncapped=unc,a_grade=A,**LIVE_DISCIPLINE,**LIVE_EXIT,**LIVE_STALENESS,demerger_events=ev,**kw)
    d=pd.DataFrame(led); d=d[(d.entry-d.stop0)/d.entry>=0.005]; c=d[d.reason!="eos"]
    loss=c[c.R<0]
    row=dict(n=len(c),win=round(100*(c.R>0).mean(),1),meanR=round(c.R.mean(),3),sumR=round(d.R.sum(),1),avg_loss=round(loss.R.mean(),2),
             big_loss_lt_m1_5=int((c.R<-1.5).sum()))
    if book=="capped":
      st=G._curve_stats(out["curve"],G.START,G.CUT); row.update({k:st[k] for k in st if k in("sharpe","maxdd","cagr")} if isinstance(st,dict) else {"stats":st})
    res.setdefault(name,{})[book]=row; print(name,book,row,flush=True)
json.dump(res,open(ROOT/"diagnostics/research/explore/2026-11-12_stop_size_arms.json","w"),indent=1,default=str)
