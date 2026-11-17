"""MEASUREMENT: reconcile the 650.2R anchor with the 260.44R replay, trade by trade, and state both conventions.

Owner request 2026-11-17, as the priority before anything else. Analysis only: no live change, no trial, no screen
row, no sealed read. Prices cut at 2024-06-30 and the cut asserted by the lab.

Mission line: every total-R comparison in the programme, including the anchor that gates rule 4, is quoted in one
number whose convention was never written down. If two reproducible paths disagree by 390R, no total-R verdict can be
trusted until the difference is named. This names it.

THE TWO LEDGERS

  A  diag_loss_diagnosis_2026_11.build_A().run(uncapped=True)       the path that produced the published 650.2R
     It applies one filter the engine does not: trades whose initial stop sits closer than 0.5% of entry are
     DROPPED -- `d[(d.entry - d.stop0) / d.entry >= 0.005]`, diag_loss_diagnosis_2026_11.py:204.
  B  nq.lab.runs.replay({"start": "2019-01-01", "uncapped": True})["ledger"]      the raw engine ledger

Both run the same engine over the same window with PIT membership and the live blocks. Both force-close every open
position at the last bar with reason "eos" (scripts/run_bhanushali_weekly_rank.py:1464-1479), so "open at the cut" is
a LABEL in the published table (reason == "eos"), not a different valuation.

JOIN: outer, on (tkr, entry_date), no duplicate keys. Every trade with |dR| > 0.05 is reported with its exit date,
exit price and reason under each method, and the differences are grouped by cause. The bucket totals must add to the
gap exactly.

CONVENTIONS REPORTED FROM NOW ON, for both ledgers:
  closed-only     sum of R over trades whose reason is not "eos"
  marked-at-cut   sum of R over every trade, open ones marked at the final close

    python pipelines/diagnostics/reconcile_total_r_conventions.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "diagnostics")]
from nq.lab import runs as L  # noqa: E402

OUT_MD = ROOT / "diagnostics" / "research" / "2026-11-17_total_r_convention_reconciliation.md"
OUT_JSON = OUT_MD.with_suffix(".json")
TOL = 0.05
STOP_FILTER = 0.005


def conventions(d: pd.DataFrame) -> dict:
    closed = d[d.reason != "eos"]
    return {"n_trades": int(len(d)), "n_closed": int(len(closed)), "n_eos_marked_at_cut": int((d.reason == "eos").sum()),
            "total_R_closed_only": round(float(closed.R.sum()), 3),
            "total_R_marked_at_cut": round(float(d.R.sum()), 3),
            "net_pnl_closed_only": round(float(closed.net_pnl.sum()), 2),
            "net_pnl_marked_at_cut": round(float(d.net_pnl.sum()), 2)}


def main() -> int:
    import diag_loss_diagnosis_2026_11 as D
    _cut, _P, _mem, _nifty, run = D.build_A()
    _, A = run(True)
    B = L.replay({"start": "2019-01-01", "uncapped": True})["ledger"]
    for d in (A, B):
        d["entry_date"] = pd.to_datetime(d["entry_date"])
        d["exit_date"] = pd.to_datetime(d["exit_date"])

    k = ["tkr", "entry_date"]
    assert not A.duplicated(k).any() and not B.duplicated(k).any(), "duplicate (ticker, entry date) keys"
    m = A.merge(B, on=k, how="outer", suffixes=("_a", "_b"), indicator="src")
    m["dR"] = m.R_a.fillna(0.0) - m.R_b.fillna(0.0)
    gap = float(A.R.sum() - B.R.sum())

    diffs = m[m.dR.abs() > TOL].copy()
    rows = [{"tkr": r.tkr, "entry_date": str(r.entry_date.date()),
             "in_A": r.src != "right_only", "in_B": r.src != "left_only",
             "stop_distance_pct": (None if pd.isna(r.entry_b) else round(float((r.entry_b - r.stop0_b) / r.entry_b * 100), 4)),
             "risk0_rupees": (None if pd.isna(r.entry_b) else round(float(r.entry_b - r.stop0_b), 4)),
             "A": {"reason": None if pd.isna(r.R_a) else r.reason_a,
                   "exit_date": None if pd.isna(r.exit_date_a) else str(r.exit_date_a.date()),
                   "exit_px": None if pd.isna(r.exit_px_a) else float(r.exit_px_a),
                   "R": None if pd.isna(r.R_a) else float(r.R_a)},
             "B": {"reason": None if pd.isna(r.R_b) else r.reason_b,
                   "exit_date": None if pd.isna(r.exit_date_b) else str(r.exit_date_b.date()),
                   "exit_px": None if pd.isna(r.exit_px_b) else float(r.exit_px_b),
                   "R": None if pd.isna(r.R_b) else float(r.R_b)},
             "net_pnl_rupees": None if pd.isna(r.net_pnl_b) else float(r.net_pnl_b),
             "dR": round(float(r.dR), 3)} for r in diffs.itertuples()]

    # ---- buckets, by cause. Each trade lands in exactly one bucket; the totals must add to the gap.
    def bucket(r) -> str:
        if r.src == "right_only":
            d = (r.entry_b - r.stop0_b) / r.entry_b
            return ("degenerate risk basis: initial stop inside 0.5% of entry, dropped by A's filter"
                    if d < STOP_FILTER else "present only in B for another reason")
        if r.src == "left_only":
            return "present only in A"
        if r.reason_a != r.reason_b:
            return "same trade, different exit rule fired"
        if r.reason_a == "eos":
            return "open at the cut, valued differently"
        return "same trade, same exit rule, different R"
    diffs["bucket"] = [bucket(r) for r in diffs.itertuples()]
    buckets = {b: {"n_trades": int(len(g)), "dR_total": round(float(g.dR.sum()), 3)}
               for b, g in diffs.groupby("bucket")}
    explained = round(sum(v["dR_total"] for v in buckets.values()), 3)
    residual = round(gap - explained, 3)

    res = {"window": "2019-01-01..2024-06-28 (prices cut 2024-06-30, asserted by nq.lab.runs)",
           "ledger_A": {"path": "diag_loss_diagnosis_2026_11.build_A().run(uncapped=True)",
                        "extra_filter": "(entry - stop0) / entry >= 0.005, diag_loss_diagnosis_2026_11.py:204",
                        **conventions(A)},
           "ledger_B": {"path": 'nq.lab.runs.replay({"start": "2019-01-01", "uncapped": True})["ledger"]',
                        "extra_filter": None, **conventions(B)},
           "join": {"on": k, "both": int((m.src == "both").sum()),
                    "only_A": int((m.src == "left_only").sum()), "only_B": int((m.src == "right_only").sum())},
           "gap_total_R_marked_at_cut": round(gap, 3), "tolerance": TOL,
           "trades_differing": rows, "buckets": buckets,
           "explained_total": explained, "residual_after_buckets": residual,
           "buckets_add_up_exactly": abs(residual) < 1e-6,
           "open_position_valuation": {
               "engine": "every open position is force-closed at the last bar with reason 'eos', "
                         "scripts/run_bhanushali_weekly_rank.py:1464-1479 — identical in both ledgers",
               "live": "scripts/run_bhanushali_cron.py:1213-1226 (_trade_r): closed trades at their booked R, open "
                       "positions marked at the last close as realized_r + frac_left * (cur - entry) / risk0",
               "conclusion": "mark-at-cut is what live does; the two ledgers do not differ on it"}}
    OUT_JSON.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({kk: res[kk] for kk in ("gap_total_R_marked_at_cut", "buckets", "residual_after_buckets",
                                             "buckets_add_up_exactly")}, indent=1))
    print("A", conventions(A))
    print("B", conventions(B))
    for r in rows:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
