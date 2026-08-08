"""0128 — PEAD Gate-1: does post-earnings drift exist on OUR universe, 2019+? MEASUREMENT.

Pre-registration: `diagnostics/research/preregistry/0128-pead-gate1.md`. Every definition, the gate
and both doors are frozen there. Nothing here is swept.

Takes up the OPEN registry row SL-002 ("NSE PEAD sleeve — not yet measured"). Does NOT read the
banked 0116/0117 label set, so it takes no screen-ledger row (pre-reg §0.3).

The event-time convention and why it is conservative (pre-reg §1): `ann_ts` is the board-meeting
INTIMATION timestamp (median 7 days before the event), NOT the results-release time. Nothing in the
harvest says when the numbers hit the tape. So the surprise is measured over CAR(0,+1) — capturing
the reaction whether it landed intraday on day 0 or after the close — and entry is the open of
day +2, strictly after the whole surprise window. Leakage-free regardless of release time.

Reproduce:
    python scripts/diag_pead_gate1_0128.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_weekly_crs as CRS  # noqa: E402
from nq.data.earnings import build_event_table  # noqa: E402
from nq.data.membership import load_membership, ticker_in_index_on  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402

# ---- FROZEN (pre-reg §1). No sweep. ----
HORIZONS = [10, 21, 42, 63]      # trading days
SURPRISE_END = 1                 # CAR(0, +1)
ENTRY_OFFSET = 2                 # open of day +2
ADV_MIN = 5e7                    # Rs 5 cr
TRAIN = (2019, 2022)             # decision basis
ROUND_TRIP_COST_PCT = 0.26       # STT 0.1%x2 + brokerage 0.03%x2 + slippage
MIN_NET_PCT = 0.5                # economic-magnitude floor, net of cost
MIN_TOPDEC_PER_YR = 150          # famine floor

OUT_JSON = ROOT / "diagnostics" / "research" / "pead_gate1_0128.json"
OUT_MD = ROOT / "diagnostics" / "research" / "pead_gate1_0128.md"


def boot_ci(x, n=4000, seed=0):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if x.size < 3:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    m = x[rng.integers(0, x.size, size=(n, x.size))].mean(axis=1)
    return (round(float(np.percentile(m, 2.5)), 3), round(float(np.percentile(m, 97.5)), 3))


def diff_ci(a, b, n=4000, seed=0):
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    if a.size < 3 or b.size < 3:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    d = (a[rng.integers(0, a.size, size=(n, a.size))].mean(axis=1)
         - b[rng.integers(0, b.size, size=(n, b.size))].mean(axis=1))
    return (round(float(np.percentile(d, 2.5)), 3), round(float(np.percentile(d, 97.5)), 3))


def md_table(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(
            "—" if (r[c] is None or (isinstance(r[c], float) and np.isnan(r[c]))) else str(r[c])
            for c in cols) + " |")
    return "\n".join(out)


def main() -> None:
    ohlcv = corrected_universe()
    mem = load_membership() or {}
    idx = (pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"])
           .set_index("date")["nifty50_close"].sort_index())
    idx_ret = idx.pct_change()

    ev = build_event_table(pd.read_parquet(ROOT / "data" / "_earnings_raw.parquet"))
    n_events_all = len(ev)
    ev = ev[ev["symbol"].isin(ohlcv.keys())].copy()
    n_joinable = len(ev)
    ev = ev[[ticker_in_index_on(s, d.date(), mem)
             for s, d in zip(ev["symbol"], ev["event_date"])]].copy()
    n_member = len(ev)

    rows = []
    n_short = 0
    maxH = max(HORIZONS)
    for tkr, g in ev.groupby("symbol", sort=False):
        df = ohlcv[tkr]
        dates = pd.DatetimeIndex(df.index)
        close = df["Close"].to_numpy(float)
        openp = df["Open"].to_numpy(float)
        vol = df["Volume"].to_numpy(float) if "Volume" in df.columns else np.full(len(close), np.nan)
        sret = pd.Series(close, index=dates).pct_change()
        mret = idx_ret.reindex(dates, method="ffill")
        ar = (sret - mret).to_numpy(float)                 # market-adjusted daily abnormal return
        adv = pd.Series(close * vol, index=dates).rolling(20).mean().to_numpy(float)

        for edate in g["event_date"]:
            d0 = int(np.searchsorted(dates, np.datetime64(edate)))   # first trading day >= event
            if d0 <= 20 or d0 + ENTRY_OFFSET + maxH >= len(dates):
                n_short += 1
                continue
            if not (np.isfinite(adv[d0]) and adv[d0] >= ADV_MIN):
                continue
            car = float(np.nansum(ar[d0:d0 + SURPRISE_END + 1])) * 100.0   # CAR(0,+1), %
            e = d0 + ENTRY_OFFSET
            entry_px = openp[e]
            if not (np.isfinite(entry_px) and entry_px > 0) or not np.isfinite(car):
                continue
            rec = dict(ticker=tkr, event_date=pd.Timestamp(edate), year=pd.Timestamp(edate).year,
                       quarter=pd.Timestamp(edate).to_period("Q"), car01=round(car, 4),
                       adv20=float(adv[d0]),
                       mom63=float(np.nansum(ar[max(d0 - 63, 0):d0]) * 100.0))
            # drift: market-adjusted, open(+2) -> close(+2+H-1). Shares no bar with the ranking window.
            for H in HORIZONS:
                px_end = close[e + H - 1]
                stock = (px_end / entry_px - 1.0) * 100.0
                i0, i1 = idx.reindex(dates, method="ffill").to_numpy(float)[e], \
                    idx.reindex(dates, method="ffill").to_numpy(float)[e + H - 1]
                bench = (i1 / i0 - 1.0) * 100.0 if np.isfinite(i0) and i0 > 0 else np.nan
                rec[f"drift{H}"] = round(stock - bench, 4) if np.isfinite(bench) else np.nan
            rows.append(rec)

    d = pd.DataFrame(rows).dropna(subset=[f"drift{h}" for h in HORIZONS])
    d["decile"] = d.groupby("quarter", observed=True)["car01"].transform(
        lambda s: pd.qcut(s, 10, labels=False, duplicates="drop") + 1 if s.notna().sum() >= 20 else np.nan)
    d = d.dropna(subset=["decile"])
    d["decile"] = d["decile"].astype(int)
    train = d[(d["year"] >= TRAIN[0]) & (d["year"] <= TRAIN[1])]
    oow = d[d["year"] > TRAIN[1]]

    res = {
        "_doc": "0128 PEAD Gate-1 (MEASUREMENT; 0 trials; no ledger row; sealed set not read).",
        "prereg": "diagnostics/research/preregistry/0128-pead-gate1.md",
        "coverage": {
            "events_all_nse": int(n_events_all), "joinable_to_ohlcv": int(n_joinable),
            "and_pit_nifty500_member": int(n_member),
            "usable_after_adv_and_history": int(len(d)),
            "dropped_insufficient_history": int(n_short),
            "per_year": {int(k): int(v) for k, v in d.groupby("year").size().items()},
            "per_quarter_median": int(d.groupby("quarter", observed=True).size().median()),
            "topdecile_per_year": {int(k): int(v) for k, v in
                                   d[d.decile == 10].groupby("year").size().items()},
        },
        "train_window": list(TRAIN), "n_train": int(len(train)), "n_out_of_window": int(len(oow)),
    }

    # ---- drift by decile x horizon (train) ----
    dec_tbl = []
    for dec in range(1, 11):
        s = train[train["decile"] == dec]
        row = {"decile": dec, "N": int(len(s)), "meanCAR01": round(float(s["car01"].mean()), 2)}
        for H in HORIZONS:
            row[f"drift{H}"] = round(float(s[f"drift{H}"].mean()), 3)
        dec_tbl.append(row)
    res["decile_table_train"] = dec_tbl

    # ---- top-minus-bottom spread with CIs ----
    spreads = {}
    for H in HORIZONS:
        top = train.loc[train["decile"] == 10, f"drift{H}"].to_numpy(float)
        bot = train.loc[train["decile"] == 1, f"drift{H}"].to_numpy(float)
        spreads[H] = dict(top_mean=round(float(np.nanmean(top)), 3),
                          top_ci=list(boot_ci(top)),
                          bottom_mean=round(float(np.nanmean(bot)), 3),
                          spread=round(float(np.nanmean(top) - np.nanmean(bot)), 3),
                          spread_ci=list(diff_ci(top, bot)),
                          n_top=int(len(top)), n_bot=int(len(bot)))
    res["spreads_train"] = spreads
    best_H = max(HORIZONS, key=lambda h: spreads[h]["spread"])
    res["best_horizon_train"] = best_H

    # ---- per-year (train + out-of-window, reported separately) ----
    peryear = []
    for y, g in d.groupby("year"):
        top = g.loc[g["decile"] == 10, f"drift{best_H}"].to_numpy(float)
        bot = g.loc[g["decile"] == 1, f"drift{best_H}"].to_numpy(float)
        peryear.append({"year": int(y), "in_train": bool(TRAIN[0] <= y <= TRAIN[1]),
                        "n_top": int(len(top)),
                        "top_drift": round(float(np.nanmean(top)), 3),
                        "spread": round(float(np.nanmean(top) - np.nanmean(bot)), 3)})
    res["per_year_best_horizon"] = peryear
    tr_signs = [p["spread"] for p in peryear if p["in_train"]]
    n_pos = sum(1 for v in tr_signs if v > 0)

    # ---- §4 confounds ----
    conf = {}
    for name, col, qs in (("momentum63", "mom63", 3), ("adv", "adv20", 3)):
        t = train.copy()
        t["strat"] = pd.qcut(t[col], qs, labels=[f"{name}_lo", f"{name}_mid", f"{name}_hi"],
                             duplicates="drop")
        conf[name] = {}
        for s, g in t.groupby("strat", observed=True):
            top = g.loc[g["decile"] == 10, f"drift{best_H}"].to_numpy(float)
            bot = g.loc[g["decile"] == 1, f"drift{best_H}"].to_numpy(float)
            conf[name][str(s)] = dict(n_top=int(len(top)),
                                      spread=round(float(np.nanmean(top) - np.nanmean(bot)), 3),
                                      ci=list(diff_ci(top, bot)))
    res["confounds"] = conf

    # ---- out-of-window (descriptive, NOT the decision basis) ----
    if len(oow):
        top = oow.loc[oow["decile"] == 10, f"drift{best_H}"].to_numpy(float)
        bot = oow.loc[oow["decile"] == 1, f"drift{best_H}"].to_numpy(float)
        res["out_of_window_2023_2026"] = dict(
            n_top=int(len(top)), top_drift=round(float(np.nanmean(top)), 3),
            spread=round(float(np.nanmean(top) - np.nanmean(bot)), 3),
            spread_ci=list(diff_ci(top, bot)),
            note="descriptive only — NOT the Gate-1 decision basis (pre-reg §1)")

    # ---- §3 gate ----
    sp = spreads[best_H]
    top_net = sp["top_mean"] - ROUND_TRIP_COST_PCT
    topdec_yr = list(res["coverage"]["topdecile_per_year"].values())
    gate = {
        "best_horizon": best_H,
        "1_existence_CI_excludes_zero": bool(sp["spread_ci"][0] > 0 or sp["spread_ci"][1] < 0),
        "2_majority_train_year_sign": f"{max(n_pos, len(tr_signs)-n_pos)}/{len(tr_signs)}",
        "2_pass": bool(n_pos * 2 > len(tr_signs)),
        "3_top_decile_net_pct": round(top_net, 3),
        "3_pass": bool(top_net > MIN_NET_PCT),
        "4_min_topdecile_per_yr": int(min(topdec_yr)) if topdec_yr else 0,
        "4_pass": bool(topdec_yr and min(topdec_yr) >= MIN_TOPDEC_PER_YR),
    }
    gate["PASS"] = bool(gate["1_existence_CI_excludes_zero"] and gate["2_pass"]
                        and gate["3_pass"] and gate["4_pass"])
    res["gate"] = gate
    res["VERDICT"] = ("PASS — Phase 2 may be pre-registered at H=%d" % best_H if gate["PASS"]
                      else "FAIL — door closes; SL-002 moves OPEN -> verdict")

    OUT_JSON.write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")

    c = res["coverage"]
    md = [
        "# 0128 — PEAD Gate-1: does post-earnings drift exist on our universe, 2019+?",
        "",
        "**MEASUREMENT — 0 trials, no screen-ledger row, sealed set and judge log untouched.**",
        "**Standing counts: screens 14 · sealed opens 1 · n_trials 138.**",
        "",
        "## Coverage census",
        "",
        f"{c['events_all_nse']} NSE result events → **{c['joinable_to_ohlcv']}** joinable to OHLCV → "
        f"**{c['and_pit_nifty500_member']}** PIT Nifty-500 members → **{c['usable_after_adv_and_history']}** "
        f"usable after ADV ≥ ₹5cr and history ({c['dropped_insufficient_history']} dropped on history).",
        "",
        md_table(pd.DataFrame([{"year": k, "usable_events": v,
                                "top_decile": c["topdecile_per_year"].get(k)}
                               for k, v in c["per_year"].items()])),
        "",
        "## Drift by surprise decile × horizon (train 2019-2022, market-adjusted %)",
        "",
        md_table(pd.DataFrame(res["decile_table_train"])),
        "",
        "## Top-minus-bottom decile spread (train)",
        "", "```", json.dumps(res["spreads_train"], indent=2, default=str), "```",
        "",
        f"## Per-year at the strongest train horizon (H={best_H})",
        "",
        md_table(pd.DataFrame(res["per_year_best_horizon"])),
        "",
        "## §4 confound checks",
        "", "```", json.dumps(res["confounds"], indent=2, default=str), "```",
        "",
        "## Out-of-window 2023-2026 (descriptive, NOT the decision basis)",
        "", "```", json.dumps(res.get("out_of_window_2023_2026", {}), indent=2, default=str), "```",
        "",
        "## Gate (pre-committed §3)",
        "", "```", json.dumps(res["gate"], indent=2, default=str), "```",
        "", f"## VERDICT: {res['VERDICT']}", "",
        "Reproduce: `python scripts/diag_pead_gate1_0128.py`", "",
    ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    enc = sys.stdout.encoding or "utf-8"
    sys.stdout.write("\n".join(md).encode(enc, "replace").decode(enc, "replace") + "\n")


if __name__ == "__main__":
    main()
