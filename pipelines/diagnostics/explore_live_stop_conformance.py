"""MEASUREMENT (read-only audit): live swing stops vs the frozen 0094 engine stop, the 0143 width-gap root cause, and
fills beyond the stop. Method: diagnostics/research/explore/2026-11-19_stop_conformance_and_fall_discriminator.md.

Reads committed artifacts only (results/attribution_ledger.csv, results/cards_archive.jsonl) for the live book; the
historical decomposition reads the CUT train panel (2019-01..2024-06) via nq.lab. No engine run on post-cut prices.

    python pipelines/diagnostics/explore_live_stop_conformance.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"),
                str(ROOT / "pipelines" / "diagnostics"), str(ROOT / "pipelines" / "lifecycle")]
OUT = ROOT / "diagnostics" / "research" / "explore" / "2026-11-19_live_stop_conformance.json"
MRP = 0.10
STOP_REASONS = ("stop", "stop_part")


def med(x) -> float:
    x = pd.to_numeric(pd.Series(x), errors="coerce").dropna()
    return round(float(x.median()), 3) if len(x) else float("nan")


def main() -> int:
    led = pd.read_csv(ROOT / "results" / "attribution_ledger.csv")
    cards = pd.read_json(ROOT / "results" / "cards_archive.jsonl", lines=True)
    cards["signal_date"] = pd.to_datetime(cards["signal_date"]).dt.strftime("%Y-%m-%d")
    led["signal_date"] = pd.to_datetime(led["signal_date"]).dt.strftime("%Y-%m-%d")
    cb = cards.dropna(subset=["entry_low", "entry_high"]).drop_duplicates(["ticker", "signal_date"], keep="last")
    j = led.merge(cb[["ticker", "signal_date", "entry_low", "entry_high"]], on=["ticker", "signal_date"], how="left")
    j["week_low"] = j["stop_week_low"].fillna(j["entry_low"])
    j["fill"] = j["entry_price_filled"].fillna(j["entry"])
    j["live_width_pct"] = (j["entry"] - j["stop"]) / j["entry"] * 100
    j["engine_stop"] = np.maximum(j["week_low"], j["fill"] * (1 - MRP))
    j["engine_width_recomputed_pct"] = (j["fill"] - j["engine_stop"]) / j["fill"] * 100
    j["engine_width_pct"] = j["stop_width_pct_engine"].fillna(j["engine_width_recomputed_pct"])
    j["width_gap_pp"] = j["live_width_pct"] - j["engine_width_pct"]
    j["live_capped"] = j["stop"] > j["week_low"] + 0.011
    j["band_range_pct"] = (j["entry_high"] - j["entry_low"]) / j["entry"] * 100
    j["entry_pos_in_band"] = (j["entry"] - j["entry_low"]) / (j["entry_high"] - j["entry_low"])
    out = {"population": {"ledger_rows": int(len(led)), "by_provenance": led["provenance"].value_counts().to_dict(),
                          "with_card_band": int(j["entry_low"].notna().sum()),
                          "with_engine_width": int(j["engine_width_pct"].notna().sum())}}
    g = j.dropna(subset=["engine_width_pct"])
    out["width_gap"] = {"n": int(len(g)), "median_live_width_pct": med(g["live_width_pct"]),
                        "median_engine_width_pct": med(g["engine_width_pct"]),
                        "median_gap_pp": med(g["width_gap_pp"]), "max_abs_gap_pp": round(float(g["width_gap_pp"].abs().max()), 3),
                        "n_abs_gap_gt_0.5pp": int((g["width_gap_pp"].abs() > 0.5).sum()),
                        "per_trade": g[["ticker", "signal_date", "provenance", "entry", "fill", "stop", "engine_stop",
                                        "live_width_pct", "engine_width_pct", "width_gap_pp"]].round(4).to_dict("records")}
    out["code_path"] = {"live_card_stop": "scripts/run_bhanushali_cron.py:596 stop = round(_record_stop(entry, lo), 2); "
                                          "_record_stop at :332 = max(week_low, entry*(1-max_risk_pct)); LIVE_DISCIPLINE :91",
                        "engine_stop": "scripts/run_bhanushali_weekly_rank.py:1330 st = o_['lo'] (signal-week low, _stop_arr = wlow :394); "
                                       ":1344-1345 st = max(st, en*(1-max_risk_pct)), en = the fill (next-week open in band)",
                        "difference": "same rule; only the reference price differs (card entry = last close or band midpoint, "
                                      "cron :594; engine = the actual fill open). Widths differ only where the 10% cap binds "
                                      "or the fill differs from the card entry"}

    # -------- historical decomposition (train panel, cut)
    import explore_blend_drawdown_sizing as B
    from nq.lab import ensemble as E
    d = B.navs()
    hl = d["swing_ledger"].copy()
    ctx = E.prepare_context()
    rows = []
    for r in hl.itertuples():
        s = ctx.P.get(r.tkr)
        if s is None:
            continue
        dts = pd.DatetimeIndex(s["dates"]).normalize()
        ei = int(dts.searchsorted(pd.Timestamp(r.entry_date).normalize()))
        lo = hi = None
        for e0, win in s["entry_win"].items():
            if ei in win[0]:
                lo, hi = float(win[1]), float(win[2])
        if lo is None:
            continue
        rows.append({"tkr": r.tkr, "entry": r.entry, "stop0": r.stop0, "lo": lo, "hi": hi, "reason": r.reason})
    h = pd.DataFrame(rows)
    h["width_pct"] = (h["entry"] - h["stop0"]) / h["entry"] * 100
    h["band_range_pct"] = (h["hi"] - h["lo"]) / h["entry"] * 100
    h["entry_pos_in_band"] = (h["entry"] - h["lo"]) / (h["hi"] - h["lo"])
    h["capped"] = h["stop0"] > h["lo"] + 0.011
    lv = j.dropna(subset=["entry_low", "entry_high"])
    hloss = h[h["reason"].isin(STOP_REASONS)]
    out["root_cause_decomposition"] = {
        "formula": "uncapped width = band_range x entry_position (entry-lo)/(hi-lo); cap lifts the stop to entry x 0.90",
        "historical_all": {"n": int(len(h)), "median_width_pct": med(h["width_pct"]), "median_band_range_pct": med(h["band_range_pct"]),
                           "median_entry_pos": med(h["entry_pos_in_band"]), "share_capped": round(float(h["capped"].mean()), 3)},
        "historical_stop_losses": {"n": int(len(hloss)), "median_width_pct": med(hloss["width_pct"]),
                                   "median_band_range_pct": med(hloss["band_range_pct"]), "median_entry_pos": med(hloss["entry_pos_in_band"]),
                                   "share_capped": round(float(hloss["capped"].mean()), 3)},
        "live_with_card_band": {"n": int(len(lv)), "median_width_pct": med(lv["live_width_pct"]),
                                "median_band_range_pct": med(lv["band_range_pct"]), "median_entry_pos": med(lv["entry_pos_in_band"]),
                                "share_capped": round(float(lv["live_capped"].mean()), 3)}}
    # swap attribution on medians: width ~ range x pos (uncapped approximation)
    rh, ph = float(h["band_range_pct"].median()), float(h["entry_pos_in_band"].median())
    rl, pl = float(lv["band_range_pct"].median()), float(lv["entry_pos_in_band"].median())
    out["root_cause_decomposition"]["swap_on_medians"] = {
        "hist_range_x_hist_pos": round(rh * ph, 2), "live_range_x_hist_pos": round(rl * ph, 2),
        "hist_range_x_live_pos": round(rh * pl, 2), "live_range_x_live_pos": round(rl * pl, 2)}

    # -------- fills beyond the stop
    st = j[j["exit_reason"].isin(STOP_REASONS)].copy()
    st["slippage_pct"] = (st["close_price"] - st["stop"]) / st["stop"] * 100
    out["fills_beyond_stop"] = {
        "n_stop_exits": int(len(st)), "n_beyond": int((st["slippage_pct"] < -1e-9).sum()),
        "median_slippage_pct": med(st["slippage_pct"]), "median_beyond_stop_r": med(st["beyond_stop_r"]),
        "worst_slippage_pct": round(float(st["slippage_pct"].min()), 2), "worst_beyond_stop_r": round(float(st["beyond_stop_r"].min()), 2),
        "gap_through_share": round(float(st["gap_through"].astype(str).eq("True").mean()), 3),
        "order_type": "none placed by the system: a modelled market exit at the next session's open (pending full exit, "
                      "run_bhanushali_weekly_rank.py:868); no broker stop / GTT order exists in the live path",
        "trigger_basis": "CLOSE basis, weekly: run_bhanushali_weekly_rank.py:1118 `if wc <= p['stop']` on the week's last "
                         "close; not an intraday trigger",
        "per_trade": st[["ticker", "signal_date", "close_date", "stop", "close_price", "slippage_pct", "beyond_stop_r",
                         "gap_through", "provenance"]].round(4).to_dict("records")}
    g_ = subprocess.run(["git", "grep", "-n", "-i", "-E", "gtt|sl-m|place_order|stoploss_order|stop_order", "--", "scripts", "nq"],
                        cwd=ROOT, capture_output=True, text=True).stdout.strip().splitlines()
    out["fills_beyond_stop"]["broker_order_grep"] = g_
    OUT.write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    slim = {k: ({kk: vv for kk, vv in v.items() if kk != "per_trade"} if isinstance(v, dict) else v) for k, v in out.items()}
    print(json.dumps(slim, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
