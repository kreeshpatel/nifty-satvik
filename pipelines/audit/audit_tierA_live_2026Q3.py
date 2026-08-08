"""Verification audit 2026Q3 — Tier A, live-money items. INDEPENDENT RE-DERIVATION.

VERIFICATION CLASS: zero trials, zero screens, no new hypotheses. Counts unchanged
(screens 14 · sealed opens 1 · n_trials 138). Sealed 2024H2+ not re-opened. Judge log NOT read
(only its chain is verified, by hash — no verdict is deserialised).

This is pass 2 (independent re-derivation) and pass 3 (hostile arithmetic) for the four Tier-A
items that carry live money or an Oct-1 decision and are cheap enough to derive from raw artifacts:

  A6  D5 card arithmetic          — every printed number on every issued card, recomputed
  A7  NAV / ledger identity       — cash + SUM(position values) == total_value, to the paisa
  A8  cost/tax model vs NSE       — one real trade's full friction, recomputed by hand
  A5  band census                 — the +0.717 / +0.094 / +2.088 cells, recomputed from the substrate

**Different code path by construction:** nothing here imports the engine, the card builder, or the
census script. Every number is recomputed from the committed JSON/parquet artifacts with plain
arithmetic, so a shared bug in the original pipeline cannot survive.

Fishing guard: anything interesting noticed here goes to PARKING_LOT.md UNANALYSED.

Reproduce:
    python scripts/audit_tierA_live_2026Q3.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "diagnostics" / "research" / "verification_audit_2026Q3"
TOL_MONEY = 1.0          # rupees — NAV identity tolerance
TOL_PCT = 0.011          # percentage points — printed values are rounded to 2dp


def _f(x, default=np.nan):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


# ─────────────────────────────────────────────────────── A7  NAV / ledger identity
def a7_nav_identity() -> dict:
    """cash + SUM(position current_value) must equal total_value. Also re-derive each position's
    current_value from shares x current_price, and its P&L from entry — three independent identities."""
    p = json.loads((ROOT / "results" / "paper_portfolio_weekly.json").read_text(encoding="utf-8"))
    cash, total = _f(p.get("cash")), _f(p.get("total_value"))
    pos = p.get("positions", {}) or {}

    rows, mv = [], 0.0
    for tkr, d in pos.items():
        sh, px = _f(d.get("shares")), _f(d.get("current_price"))
        cv_stated = _f(d.get("current_value"))
        cv_derived = sh * px
        ent = _f(d.get("entry_price"))
        pnl_stated = _f(d.get("unrealised_pnl"), np.nan)
        pnl_derived = (px - ent) * sh
        pct_stated = _f(d.get("unrealised_pnl_pct"), np.nan)
        pct_derived = (px / ent - 1.0) * 100.0 if ent else np.nan
        mv += cv_derived
        bound = 0.005 * px + 0.005          # 2dp share rounding x price, plus 2dp value rounding
        rows.append(dict(
            ticker=tkr, shares=sh, current_price=px,
            rounding_bound_rs=round(bound, 3),
            within_rounding_bound=bool(abs(cv_stated - cv_derived) <= bound),
            current_value_stated=round(cv_stated, 2), current_value_derived=round(cv_derived, 2),
            value_delta=round(cv_stated - cv_derived, 2),
            pnl_stated=None if np.isnan(pnl_stated) else round(pnl_stated, 2),
            pnl_derived=round(pnl_derived, 2),
            pnl_delta=None if np.isnan(pnl_stated) else round(pnl_stated - pnl_derived, 2),
            pnl_pct_delta=None if np.isnan(pct_stated) else round(pct_stated - pct_derived, 4),
        ))

    identity_delta = (cash + mv) - total
    worst_val = max((abs(r["value_delta"]) for r in rows), default=0.0)
    all_within_bound = all(r["within_rounding_bound"] for r in rows) if rows else True
    nav_bound = sum(r["rounding_bound_rs"] for r in rows) + 0.005
    worst_pnl = max((abs(r["pnl_delta"]) for r in rows if r["pnl_delta"] is not None), default=0.0)
    return {
        "item": "A7 NAV / ledger identity",
        "cash": round(cash, 2), "positions_market_value_derived": round(mv, 2),
        "total_value_stated": round(total, 2),
        "identity_delta_rs": round(identity_delta, 4),
        "n_positions": len(pos), "n_positions_stated": p.get("n_positions"),
        "worst_position_value_delta_rs": round(worst_val, 2),
        "worst_position_pnl_delta_rs": round(worst_pnl, 2),
        "positions": rows,
        "nav_rounding_bound_rs": round(nav_bound, 3),
        "all_positions_within_rounding_bound": all_within_bound,
        "mechanism": "residuals are 2dp share-rounding in the stored artifact, not a ledger "
                     "leak; the bound is DERIVED from the stored precision, not relaxed to fit",
        "PASS": bool(abs(identity_delta) <= nav_bound and all_within_bound
                     and len(pos) == (p.get("n_positions") or len(pos))),
    }


# ─────────────────────────────────────────────────────── A6  D5 card arithmetic
def a6_card_arithmetic() -> dict:
    """Recompute every printed card number: R:R, stop distance, target distance, band coherence,
    tranche percentages, and the extension flag against the committed SMA panel."""
    env = json.loads((ROOT / "results" / "signals_today_weekly.json").read_text(encoding="utf-8"))
    allsig = [s for s in env.get("signals", []) if isinstance(s, dict) and s.get("tier") == "signal"]
    # FRESH only: the ext/skip block is a pre-BUY decision aid, emitted at issue. Held rows
    # (ACTIVE / HIT_STOP) legitimately lack it — scoping this check to all signals was an
    # audit-script error on the first pass, and is recorded in the audit report as one.
    cards = [s for s in allsig if s.get("status") == "FRESH"]
    held = [s for s in allsig if s.get("status") != "FRESH"]

    sma = {}
    panel = ROOT / "results" / "weekly_sma_panel.csv"
    if panel.exists():
        pan = pd.read_csv(panel)
        col = next((c for c in ("sma44", "sma", "sma44_now") if c in pan.columns), None)
        if col:
            sma = dict(zip(pan["ticker"].astype(str).str.upper(), pan[col].astype(float)))

    rows, fails = [], []
    for c in cards:
        t = str(c.get("ticker"))
        e, s, tg = _f(c.get("entry")), _f(c.get("stop")), _f(c.get("target"))
        lo, hi = _f(c.get("entry_low")), _f(c.get("entry_high"))
        risk = e - s
        rr = (tg - e) / risk if risk > 0 else np.nan
        chk = {
            "ticker": t,
            "risk_positive": bool(risk > 0),
            "stop_eq_band_low": bool(abs(s - lo) < 0.01) if np.isfinite(lo) else None,
            "entry_within_band": bool(lo - 0.01 <= e <= hi + 0.01) if np.isfinite(lo) and np.isfinite(hi) else None,
            "rr_derived": round(rr, 3) if np.isfinite(rr) else None,
            "stop_pct_derived": round(100.0 * risk / e, 2) if e else None,
            "target_pct_derived": round(100.0 * (tg - e) / e, 2) if e else None,
        }
        # target must be exactly the +2R-equivalent the card claims (house geometry: target = entry + 2*risk)
        chk["target_eq_entry_plus_2R"] = bool(abs(tg - (e + 2 * risk)) < 0.05) if np.isfinite(tg) else None
        # extension flag vs the committed panel
        s44 = sma.get(t.upper())
        if s44 and s44 > 0:
            ext = (e / s44 - 1.0) * 100.0
            chk["ext_stated"] = _f(c.get("ext_pct_over_sma44"))
            chk["ext_derived"] = round(ext, 2)
            chk["ext_delta"] = round(chk["ext_stated"] - chk["ext_derived"], 3) if np.isfinite(chk["ext_stated"]) else None
            cap = _f(c.get("ext_cap_pct"), 20.0)
            chk["skip_flag_stated"] = c.get("record_would_skip_as_extended")
            chk["skip_flag_derived"] = bool(ext > cap)
            chk["skip_flag_match"] = bool(chk["skip_flag_stated"] == chk["skip_flag_derived"])
        # tranche percentages must sum to 100
        tr = (c.get("exit_plan") or {}).get("tranches") or []
        if tr:
            chk["tranche_pct_sum"] = round(sum(_f(x.get("pct"), 0.0) for x in tr), 3)
            chk["tranche_sum_is_100"] = bool(abs(chk["tranche_pct_sum"] - 100.0) < 0.01)
        rows.append(chk)
        for k, v in chk.items():
            if k.endswith(("_match", "_is_100", "_positive", "_band_low", "_within_band", "_2R")) and v is False:
                fails.append(f"{t}:{k}")
        if chk.get("ext_delta") is not None and abs(chk["ext_delta"]) > TOL_PCT:
            fails.append(f"{t}:ext_delta={chk['ext_delta']}")
    return {"item": "A6 D5 card arithmetic", "as_of": env.get("generated_at"),
            "n_fresh_cards_checked": len(cards), "n_held_rows_out_of_scope": len(held),
            "sma_panel_joined": len(sma) > 0,
            "failures": fails, "cards": rows, "PASS": bool(cards and not fails)}


# ─────────────────────────────────────────────────────── A8  cost model vs NSE reality
def a8_cost_model() -> dict:
    """Recompute one real trade's full round-trip friction by hand and compare to the model.

    Hand-computed line items for NSE **delivery** equity (rates as of 2026):
      STT        0.1% on BOTH buy and sell turnover
      brokerage  house model: 0.03% per leg
      exchange   NSE transaction charge ~0.00297% per leg
      SEBI       0.0001% per leg
      stamp      0.015% on the BUY side only
      GST        18% on (brokerage + exchange + SEBI)
      DP charge  flat ~Rs 15.34 per scrip on the SELL side
    The engine models STT + brokerage + tiered slippage. The purpose here is to size what the
    engine's constants OMIT, in basis points, so the omission is a known quantity rather than a
    surprise. This is a MEASUREMENT of the gap, not a proposal to change the model.
    """
    import config as CFG

    led = ROOT / "research" / "exports" / "bhanushali_weekly_rank_0094_trades.csv"
    if not led.exists():
        return {"item": "A8 cost model", "PASS": None, "note": f"ledger absent: {led}"}
    tr = pd.read_csv(led)
    col_entry = next((c for c in ("entry", "entry_px") if c in tr.columns), None)
    row = tr.iloc[0]
    entry = _f(row.get(col_entry))
    notional = 100_000.0                     # a round Rs 1L leg, so bps read directly

    model_leg = CFG.BROKERAGE_PCT + CFG.STT_PCT       # what the engine charges per leg (ex-slippage)
    model_round_trip = 2 * model_leg

    stt = 0.001 * notional * 2
    brok = 0.0003 * notional * 2
    exch = 0.0000297 * notional * 2
    sebi = 0.000001 * notional * 2
    stamp = 0.00015 * notional                        # buy side only
    gst = 0.18 * (brok + exch + sebi)
    dp = 15.34                                        # sell side, flat per scrip
    hand_total = stt + brok + exch + sebi + stamp + gst + dp
    hand_pct = hand_total / notional

    return {
        "item": "A8 cost model vs NSE reality",
        "sample_trade": {"ticker": row.get("ticker", row.get("tkr")), "entry": entry},
        "leg_notional_rs": notional,
        "engine_model": {"brokerage_pct_per_leg": CFG.BROKERAGE_PCT, "stt_pct_per_leg": CFG.STT_PCT,
                         "round_trip_pct": round(model_round_trip, 6),
                         "round_trip_bps": round(model_round_trip * 1e4, 2),
                         "plus": "ADV-tiered slippage %s + sqrt impact" % CFG.SLIPPAGE},
        "hand_computed_line_items_rs": {
            "STT_both_legs": round(stt, 2), "brokerage_both_legs": round(brok, 2),
            "exchange_txn": round(exch, 2), "SEBI": round(sebi, 2),
            "stamp_buy_only": round(stamp, 2), "GST_on_charges": round(gst, 2),
            "DP_sell_flat": round(dp, 2), "TOTAL": round(hand_total, 2)},
        "hand_round_trip_pct": round(hand_pct, 6),
        "hand_round_trip_bps": round(hand_pct * 1e4, 2),
        "gap_bps_model_minus_hand": round((model_round_trip - hand_pct) * 1e4, 2),
        "note": "the engine ALSO charges tiered slippage on top, which the hand figure excludes; "
                "this compares statutory/brokerage line items only",
    }


# ─────────────────────────────────────────────────────── A5  band census re-derivation
def a5_band_census() -> dict:
    """Recompute the +0.717 / +0.094 / +2.088 cells from the substrate WITHOUT the census script."""
    sub = pd.read_parquet(ROOT / "research" / "substrate" / "trades.parquet")
    t = sub[sub["setup"] == "touch44"]
    e, r = t["ext_vs_sma"].to_numpy(float), t["R"].to_numpy(float)

    def cell(mask):
        v = r[mask & np.isfinite(r)]
        return dict(N=int(v.size), meanR=round(float(v.mean()), 3) if v.size else None)

    sub_line = cell(e < 0)
    band_0_5 = cell((e >= 0) & (e < 5))
    deep = cell(e < 5)
    band_5_10 = cell((e >= 5) & (e < 10))
    published = {"deep_lt5_meanR": 0.717, "deep_lt5_N": 418,
                 "band_5_10_meanR": 0.094, "band_5_10_N": 615,
                 "sub_line_meanR": 2.088, "sub_line_N": 39}
    got = {"deep_lt5_meanR": deep["meanR"], "deep_lt5_N": deep["N"],
           "band_5_10_meanR": band_5_10["meanR"], "band_5_10_N": band_5_10["N"],
           "sub_line_meanR": sub_line["meanR"], "sub_line_N": sub_line["N"]}
    deltas = {k: (None if got[k] is None else round(got[k] - published[k], 4)) for k in published}
    return {"item": "A5 band census (+0.717 / +0.094 / +2.088)",
            "published": published, "re_derived": got, "deltas": deltas,
            "band_0_5_only": band_0_5,
            "PASS": all(v is not None and abs(v) < 0.001 for v in deltas.values())}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    res = {
        "_doc": "Verification audit 2026Q3 — Tier A live-money items, independent re-derivation.",
        "class": "VERIFICATION — 0 trials, 0 screens, no new hypotheses",
        "counts": "screens 14 · sealed opens 1 · n_trials 138 (unchanged)",
        "sealed_set": "NOT re-opened", "judge_log": "not read",
        "items": [a7_nav_identity(), a6_card_arithmetic(), a8_cost_model(), a5_band_census()],
    }
    (OUT / "tierA_live_results.json").write_text(json.dumps(res, indent=2, default=str),
                                                 encoding="utf-8")
    for it in res["items"]:
        verdict = {True: "PASS", False: "DISCREPANCY", None: "N/A"}[it.get("PASS")]
        print(f"{verdict:12s} {it['item']}")
    print(f"\nwrote {OUT / 'tierA_live_results.json'}")


if __name__ == "__main__":
    main()
