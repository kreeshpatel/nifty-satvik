"""The 0121 DEFERRAL ACTIVATION BOUND (MEASUREMENT, 0 trials; ledger row #10, running count 10;
sealed opens 1). Owner-gated Step 1 for the 0120 Q2 deferral rule.

Universe: exactly the 0120-activated train trades (results event ANNOUNCED by the signal-week Friday,
dated within 14cd of the entry-week Monday; N=14 FROZEN). The rule as proposed: the entry defers past
the event; ENGINE-FAITHFUL re-qualification = the substrate contains another trade for the same ticker
entering within 28cd AFTER the event (the engine itself re-signaled) -> the deferred outcome is that
trade's R, engine-exact, no invented thresholds. No re-signal -> the trade LAPSES (foregone original R).
Deferral anchor = the (final) true event date >= sig_fri; postponements are announced rows in the
calendar (lag median 8d), so react-when-announced converges to the final date before it occurs — stated.

Gate (pre-committed by the owner): net annual R delta must clear the +-10R/yr path-noise floor with
majority-year sign consistency; FAIL -> addendum, bank, stop. CLEAR -> proceed to trial #139.

    python scripts/diag_deferral_bound_0121.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nq.data.earnings import EARNINGS_RAW_PATH, build_event_table  # noqa: E402
from nq.data.delivery import apply_alias_map  # noqa: E402

CTX = ROOT / "research" / "substrate" / "context_windows.parquet"
TRAIN_LO, TRAIN_HI = "2019-01-01", "2024-06-30"
YRS = 5.5


def main() -> int:
    print("LEDGER: row #10 (running screen count 10; sealed opens 1).")
    ev = build_event_table(apply_alias_map(pd.read_parquet(EARNINGS_RAW_PATH)))
    evs = {s: g.sort_values("event_date")[["event_date", "ann_ts"]].to_numpy() for s, g in ev.groupby("symbol")}
    t = pd.read_parquet(CTX)
    col = {c.lower(): c for c in t.columns}
    t["entry_date"] = pd.to_datetime(t[col["entry_date"]])
    full = t.copy()                                            # all trades (for re-signal lookup)
    tr = t[(t["entry_date"] >= TRAIN_LO) & (t["entry_date"] <= TRAIN_HI)].copy()
    tr["sig_fri"] = tr["entry_date"] - pd.to_timedelta(tr["entry_date"].dt.weekday + 3, unit="D")
    rr = col["r"]

    # activation (0120 Q2, frozen) + the anchor event date
    act = []
    for i, r in tr.iterrows():
        a = evs.get(r[col["ticker"]])
        if a is None:
            continue
        monday = r["sig_fri"] + pd.Timedelta(days=3)
        known = a[a[:, 1] <= np.datetime64(r["sig_fri"])]
        if not len(known):
            continue
        m = known[(known[:, 0] >= np.datetime64(monday)) &
                  (known[:, 0] <= np.datetime64(monday + pd.Timedelta(days=14)))]
        if len(m):
            act.append((i, pd.Timestamp(m[:, 0].min())))
    print(f"activated train trades: {len(act)}  (0120 reported 275)")

    by_tkr = {s: g.sort_values("entry_date") for s, g in full.groupby(full[col["ticker"]])}
    rows = []
    for i, e_dt in act:
        r0 = tr.loc[i]
        g = by_tkr[r0[col["ticker"]]]
        nxt = g[(g["entry_date"] > e_dt) & (g["entry_date"] <= e_dt + pd.Timedelta(days=28))]
        nxt = nxt[nxt.index != i]
        if len(nxt):
            rows.append(dict(idx=i, yr=r0["entry_date"].year, r_orig=float(r0[rr]),
                             lapsed=False, r_def=float(nxt.iloc[0][rr]),
                             ft=bool(r0["false_touch"] == True), ns=bool(r0["noise_stop"] == True),  # noqa: E712
                             win=bool(r0[rr] > 0)))
        else:
            rows.append(dict(idx=i, yr=r0["entry_date"].year, r_orig=float(r0[rr]),
                             lapsed=True, r_def=0.0,
                             ft=bool(r0["false_touch"] == True), ns=bool(r0["noise_stop"] == True),  # noqa: E712
                             win=bool(r0[rr] > 0)))
    d = pd.DataFrame(rows)
    lap = d[d["lapsed"]]; re_ = d[~d["lapsed"]]
    print(f"\nlapse rate: {len(lap)}/{len(d)} ({len(lap)/len(d)*100:.0f}%)  "
          f"(engine never re-signaled within 28cd post-event)")
    print("slot succession on the capped book: NOT resolvable from the uncapped substrate (no slot "
          "contention modeled) — stated, not invented.")
    if len(re_):
        print(f"re-entered {len(re_)}: mean R orig {re_['r_orig'].mean():+.3f} -> deferred "
              f"{re_['r_def'].mean():+.3f} | per-trade delta {(re_['r_def']-re_['r_orig']).mean():+.3f}")
    print(f"lapsed foregone: mean orig R {lap['r_orig'].mean():+.3f} (delta = -R_orig each)")
    d["delta"] = d["r_def"] - d["r_orig"]
    net = d["delta"].sum() / YRS
    skip = (-d["r_orig"]).sum() / YRS
    ceil = d["r_orig"].clip(upper=0).abs().sum() / YRS
    print(f"\ncohort accounting of the AVOIDED/ALTERED originals: false_touch {d['ft'].mean()*100:.0f}% "
          f"| noise_stop {d['ns'].mean()*100:.0f}% | winners {d['win'].mean()*100:.0f}%  "
          f"(train base: ft 12%, ns 15%, win 53%)")
    print("\nper-year net delta (R):")
    for y, gy in d.groupby("yr"):
        print(f"  {y}: {gy['delta'].sum():+.1f}  (n={len(gy)}, lapse {gy['lapsed'].mean()*100:.0f}%)")
    signs = [np.sign(gy["delta"].sum()) for _, gy in d.groupby("yr")]
    dom = int(max((np.array(signs) > 0).sum(), (np.array(signs) < 0).sum()))
    print(f"\nBOOKENDS: pure-skip {skip:+.2f} R/yr | clairvoyant ceiling {ceil:+.2f} R/yr")
    print(f"THE PROPOSAL (deferral): NET {net:+.2f} R/yr | year-sign consistency {dom}/{len(signs)}")
    ok = net >= 10.0 and dom > len(signs) / 2
    print("GATE:", "CLEARS -> proceed to trial #139" if ok
          else "FAILS the +-10R/yr floor (or year consistency) -> addendum, bank, STOP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
