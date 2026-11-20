"""MEASUREMENT: the "stops are requests" circuit-lock scenario re-run with NSE's OWN band data, 2019-01-01..2024-06-30.

Owner request 2026-11-18 (research/robust-sizing follow-up, item 5). Replaces the APPROXIMATE detector of
explore_stops_are_requests.py with NSE's daily band-hitter lists. Analysis only: no rule, trial or sealed read
(swing exits are searched only in prices truncated at 2024-06-30, as before).

DATA  pipelines/build/fetch_nse_price_bands.py -> data/nse_bands/{band_hitters,sec_list_bands}.parquet + manifest.json
      band_hitters: every security that touched its upper (H) or lower (L) price band that session (PRddmmyy.zip/bh*.csv)
      sec_list_bands: the band % in force for every banded security (from the first archived date; 2019 not archived)
      Symbols are matched as-is, plus data/delisted_alias_map.json renames (old -> new symbol, within valid_until).

LOCK DEFINITIONS (fixed before any result)
  real_lock    (primary) the ticker is on that session's lower-band list (side L) AND its close is within 0.1% of its
               low - it touched the lower band and finished there, so a sell order at the close was a queued request.
  real_touch   (upper bound) on the lower-band list at all, whatever the close: the whole session treated as locked.
  An exit dated on a locked session moves to the first later session that is not locked, filled at that session's
  open (explore_stops_are_requests.moved_exit); cash accounting and metrics exactly as that script
  (apply_cash and, added after the first look of the original study, apply_cash_scaled).

Also reported: agreement of the old APPROXIMATE detector with real_lock over all (ticker, session) pairs of the
universe in the window (precision / recall), and the blend at 15% AND 11% (the owner's provisional target; its
condition precedent is that the 11% blend's 156-week p95 at block 8 stays <= 25% under this scenario).

    python pipelines/diagnostics/explore_circuit_lock_real_bands.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"),
                str(ROOT / "pipelines" / "diagnostics"), str(ROOT / "pipelines" / "lifecycle")]
import core as C  # noqa: E402
import explore_blend_drawdown_sizing as B  # noqa: E402
import explore_stops_are_requests as S  # noqa: E402

BANDS = ROOT / "data" / "nse_bands"
OUT_JSON = ROOT / "diagnostics" / "research" / "explore" / "2026-11-18_circuit_lock_real_bands.json"
WINDOW = ("2019-01-01", "2024-06-30")
LOW_TOL = 0.001


def alias_map() -> dict[str, tuple[str, str | None]]:
    d = json.loads((ROOT / "data" / "delisted_alias_map.json").read_text(encoding="utf-8"))["aliases"]
    return {old: (v["to"], v.get("valid_until")) for old, v in d.items()}


def real_sets(universe: dict) -> tuple[dict, dict, dict]:
    h = pd.read_parquet(BANDS / "band_hitters.parquet")
    h = h[h["side"] == "L"].copy()
    h["date"] = pd.to_datetime(h["date"]).dt.normalize()
    al = alias_map()

    def to_t(sym, d):
        if sym in universe:
            return sym
        if sym in al:
            new, until = al[sym]
            if until is None or d <= pd.Timestamp(until):
                return new if new in universe else None
        return None
    h["tkr"] = [to_t(s, d) for s, d in zip(h["symbol"], h["date"])]
    matched = h.dropna(subset=["tkr"])
    touch, lock = {}, {}
    for t, g in matched.groupby("tkr"):
        df = universe[t]
        idx = pd.DatetimeIndex(df.index).normalize()
        cl = pd.Series((df["close"] if "close" in df else df["Close"]).to_numpy(), index=idx)
        lo = pd.Series((df["low"] if "low" in df else df["Low"]).to_numpy(), index=idx)
        ds = set(g["date"])
        touch[t] = ds
        lk = {d for d in ds if d in cl.index and cl[d] <= lo[d] * (1 + LOW_TOL)}
        if lk:
            lock[t] = lk
    info = {"lower_band_rows": int(len(h)), "matched_rows": int(len(matched)),
            "distinct_symbols_lower": int(h["symbol"].nunique()), "matched_universe_tickers": int(matched["tkr"].nunique()),
            "real_touch_sessions": int(sum(len(v) for v in touch.values())),
            "real_lock_sessions": int(sum(len(v) for v in lock.values()))}
    return touch, lock, info


def agreement(approx: dict, real: dict, universe: dict) -> dict:
    lo, hi = pd.Timestamp(WINDOW[0]), pd.Timestamp(WINDOW[1])
    A = {(t, d) for t, s in approx.items() for d in s if lo <= d <= hi}
    R = {(t, d) for t, s in real.items() for d in s if lo <= d <= hi}
    tp = len(A & R)
    return {"approx_pairs": len(A), "real_pairs": len(R), "both": tp,
            "precision_of_approx": round(tp / len(A), 3) if A else None, "recall_of_approx": round(tp / len(R), 3) if R else None}


def blend_both(mo_nav, sw_nav) -> dict:
    out = {}
    for t in (0.15, 0.11):
        r, _ = C.vol_target_blend(B.window(mo_nav).pct_change().dropna(), B.window(sw_nav).pct_change().dropna(), target=t)
        out[f"vt{int(t * 100)}"] = S.stats(B.to_nav(r))
    return out


def main() -> int:
    man = json.loads((BANDS / "manifest.json").read_text(encoding="utf-8"))
    d = B.navs()
    if round(d["swing_metrics"]["sharpe"], 3) != 1.025 or (round(d["momentum_metrics"]["cagr_pct"], 2), round(d["momentum_metrics"]["sharpe"], 3)) != (21.73, 1.13):
        raise SystemExit("anchor mismatch: stop")
    sw_nav, led, plog = d["swing"], d["swing_ledger"].copy(), d["swing_position_log"].copy()
    mo_nav, mtr = d["momentum"], d["momentum_trades"].copy()
    plog["date"] = pd.to_datetime(plog["date"])
    for c_ in ("entry_date", "exit_date"):
        led[c_] = pd.to_datetime(led[c_])
        mtr[c_] = pd.to_datetime(mtr[c_])
    from run_bhanushali_path1 import corrected_universe
    full = corrected_universe()
    touch, lock, info = real_sets(full)
    approx = S.locked_sessions(full)
    import diag_loss_diagnosis_2026_11 as D
    _cut, _P, _mem, _nifty, run = D.build_A()
    _, A = run(True)
    A["exit_date"] = pd.to_datetime(A["exit_date"])
    sw_closed = led[led.reason != "eos"].copy()
    sw_closed["shares"] = [S.shares_at_exit(plog, r.tkr, r.entry, r.exit_date, r.entry_date) for r in sw_closed.itertuples()]
    if sw_closed["shares"].isna().any():
        raise SystemExit("swing exits without a position-log row: stop")
    cut = pd.Timestamp("2024-06-30")
    full_cut = {t: df[pd.DatetimeIndex(df.index) <= cut] for t, df in full.items()}

    def count(df, tcol, dcol, sets):
        return int(sum(pd.Timestamp(r[dcol]).normalize() in sets.get(r[tcol], set()) for _, r in df.iterrows()))

    def deltas(df, tcol, pxcol, qty_fn, sets, prices):
        out, moved = [], []
        for r in df.itertuples():
            t = getattr(r, tcol)
            mv = S.moved_exit(prices[t], sets.get(t, set()), r.exit_date) if t in prices else None
            if mv:
                x = qty_fn(r) * (mv[1] - getattr(r, pxcol))
                out.append((mv[0], x))
                moved.append({"tkr": t, "exit_date": str(pd.Timestamp(r.exit_date).date()), "moved_to": str(mv[0].date()),
                              "old_px": round(float(getattr(r, pxcol)), 2), "new_px": round(mv[1], 2),
                              "move_pct": round((mv[1] / float(getattr(r, pxcol)) - 1) * 100, 2)})
        return out, moved

    res = {"data_manifest": {k: (v if not isinstance(v, list) else f"{len(v)} dates") for k, v in man.items()},
           "match": info, "approx_vs_real_lock": agreement(approx, lock, full),
           "approx_vs_real_touch": agreement(approx, touch, full)}
    base = {"swing": S.stats(sw_nav), "momentum": S.stats(mo_nav), "blend": blend_both(mo_nav, sw_nav)}
    res["base"] = base
    for name, sets in (("real_lock", lock), ("real_touch", touch), ("approx_rerun", approx)):
        sw_d, sw_mv = deltas(sw_closed, "tkr", "exit_px", lambda r: r.shares, sets, full_cut)
        mo_d, mo_mv = deltas(mtr, "ticker", "exit", lambda r: r.qty, sets, full)
        sw_n, mo_n = S.apply_cash(sw_nav, sw_d), S.apply_cash(mo_nav, mo_d)
        sw_s, mo_s = S.apply_cash_scaled(sw_nav, sw_d), S.apply_cash_scaled(mo_nav, mo_d)
        res[name] = {"trades_affected": {"dataset_A_uncapped": count(A[A.reason != "eos"], "tkr", "exit_date", sets),
                                         "dataset_A_closed": int((A.reason != "eos").sum()),
                                         "swing_book": count(sw_closed, "tkr", "exit_date", sets), "swing_closed": int(len(sw_closed)),
                                         "momentum": count(mtr, "ticker", "exit_date", sets), "momentum_trades": int(len(mtr))},
                     "moved_exits_swing": sw_mv, "moved_exits_momentum": mo_mv,
                     "fixed_rupee": {"swing": S.stats(sw_n), "momentum": S.stats(mo_n), "blend": blend_both(mo_n, sw_n)},
                     "equity_scaled": {"swing": S.stats(sw_s), "momentum": S.stats(mo_s), "blend": blend_both(mo_s, sw_s)}}
    res["condition_precedent_vt11"] = {k: {"boot156_p95_b8": round(res[k][v]["blend"]["vt11"]["boot156_p95_dd_pct"], 2),
                                           "meets_25": bool(res[k][v]["blend"]["vt11"]["boot156_p95_dd_pct"] <= 25.0)}
                                       for k in ("real_lock", "real_touch") for v in ("fixed_rupee",)}
    OUT_JSON.write_text(json.dumps(res, indent=1, default=float) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("real_lock", "real_touch", "approx_rerun")}, indent=1, default=float))
    for k in ("real_lock", "real_touch", "approx_rerun"):
        print(k, json.dumps(res[k]["trades_affected"]), json.dumps(res[k]["moved_exits_swing"] + res[k]["moved_exits_momentum"])[:1500])
        for acc in ("fixed_rupee", "equity_scaled"):
            print(" ", acc, json.dumps(res[k][acc], default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
