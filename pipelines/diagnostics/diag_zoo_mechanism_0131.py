"""Verify the four links of the claimed mechanism, from committed artifacts:
   stop width -> notional -> seat count -> queue depth (CRS walk-down)."""
import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
sys.path.insert(0, "scripts")

EQ0, RISK = 1_000_000.0, 0.02

# ---- link 1 & 2 : stop width and notional, per setup, from the substrate --------------------
t = pd.read_parquet("research/substrate/trades.parquet")
t["notional_pct_of_EQ0"] = 100.0 * (EQ0 * RISK / (t["risk_pct"] / 100.0)) / EQ0
elected = ["touch44", "cup_handle", "box", "double_bottom"]
print("== LINK 1+2: stop width -> notional (substrate, all origins) ==")
rows = []
for s in elected:
    g = t[t["setup"] == s]
    if not len(g):
        continue
    rows.append({"setup": s, "N": len(g),
                 "median_stop_width_pct": round(float(g["risk_pct"].median()), 2),
                 "median_notional_pct_of_equity": round(
                     float((RISK * 100.0) / (g["risk_pct"] / 100.0)).__float__()
                     if False else float(((RISK * 100.0) / (g["risk_pct"] / 100.0)).median()), 2)})
print(pd.DataFrame(rows).to_string(index=False))

# ---- link 3 : seat count, from the two shadow-book arms ------------------------------------
import run_bhanushali_weekly_rank as R94  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
import run_zoo_shadow_book as Z  # noqa: E402

ohlcv = corrected_universe()
mem = load_membership()

def _arm(pool_kwargs):
    P = R94.prep_weekly_rank(ohlcv, **pool_kwargs)
    led = []
    R94.backtest(P, mem, ledger=led, start="2017-01-01")
    L = pd.DataFrame(led)
    L["entry_date"] = pd.to_datetime(L["entry_date"])
    L["exit_date"] = pd.to_datetime(L["exit_date"])
    return L

L_live = _arm({})
L_zoo = _arm(Z._pool_kwargs())

def _conc(L):
    span = pd.date_range(L["entry_date"].min(), L["exit_date"].max(), freq="W")
    occ = [int(((L["entry_date"] <= w) & (L["exit_date"] >= w)).sum()) for w in span]
    return round(float(np.mean(occ)), 2), int(np.max(occ))

for name, L in (("live", L_live), ("shadow", L_zoo)):
    mean_c, max_c = _conc(L)
    notional = EQ0 * RISK / ((L["entry"] - L["stop0"]))
    notional_pct = 100.0 * (notional * L["entry"]) / EQ0
    print(f"\n== LINK 3: seats — {name} ==")
    print(f"   trades {len(L)}  mean concurrent {mean_c}  max {max_c}")
    print(f"   median position notional: {notional_pct.median():.2f}% of equity")
    print(f"   median stop width: {(100*(L['entry']-L['stop0'])/L['entry']).median():.2f}%")

# ---- link 4 : queue depth / CRS walk-down --------------------------------------------------
print("\n== LINK 4: CRS rank of what actually got funded ==")
for name, L in (("live", L_live), ("shadow", L_zoo)):
    print(f"   {name:<7} mean crs_dist of funded fills = {L['rank'].mean():+.4f}  "
          f"median {L['rank'].median():+.4f}  p10 {L['rank'].quantile(0.10):+.4f}")

out = {
    "link1_2_stop_and_notional": rows,
    "link3_seats": {n: dict(zip(("mean_concurrent", "max_concurrent"), _conc(L)))
                    for n, L in (("live", L_live), ("shadow", L_zoo))},
    "link4_crs": {n: {"mean_rank": round(float(L["rank"].mean()), 4),
                      "median_rank": round(float(L["rank"].median()), 4),
                      "p10_rank": round(float(L["rank"].quantile(0.10)), 4)}
                  for n, L in (("live", L_live), ("shadow", L_zoo))},
}
pathlib.Path("diagnostics/research/foundation_audit_2026Q3/zoo_mechanism.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8")
print("\nwrote zoo_mechanism.json")
