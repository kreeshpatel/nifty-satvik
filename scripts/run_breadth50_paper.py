"""Forward paper logger for the breadth-50 watched book — EW / SW / SW-accum (proposal §4, the
2026-08-16 3-arm amendment). OBSERVATIONAL, and held to the book's stricter discipline: **zero
in-sample fitting**. It logs realized weekly NAVs for the three arms from a fixed inception FORWARD
only, appends them to results/breadth50_forward.json, and reports NO spread and NO arm comparison —
the EW-vs-SW / EW-vs-SW-accum verdict is the wall/review's to read later, never this logger's, never
in-sample. Like the swing paper book it is EMPTY until fresh post-inception bars accrue (research
OHLCV lags; the real cron downloads).

Construction is frozen: top-50 by weekly CRS (W-FRI), EW 2%/name; SW tilted by dlv_med21 (0118); SW-
accum tilted by the 0139 accumulation composite — all via nq.research.breadth50.build_books, all
PIT-lagged (features <= the signal-week Friday; entry the following Monday). It evaluates nothing about
which arm is better.

    python scripts/run_breadth50_paper.py --start 2026-10-01          # forward log (owner inception)
    python scripts/run_breadth50_paper.py --validate --start 2026-01-01  # STRUCTURAL check on scratch
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipelines" / "diagnostics"))

from config import RESULTS_DIR  # noqa: E402
from nq.data.delivery import DELIVERY_RAW_PATH, apply_alias_map, derive_delivery_features  # noqa: E402
from nq.data.earnings import EARNINGS_RAW_PATH, build_event_table  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.research.breadth50 import EVENT_WINDOW_CD, build_books, weekly_crs_dist  # noqa: E402

OUT = RESULTS_DIR / "breadth50_forward.json"
INCEPTION = "2026-10-01"   # placeholder — the OWNER sets the real inception at the §4 amendment slot


def _load():
    oh = load_ohlcv_cache(OHLCV_CACHE)
    closes = pd.DataFrame({t: g["Close"] for t, g in oh.items()})
    closes.index = pd.to_datetime(closes.index)
    oi = pd.read_parquet(ROOT / "data" / "options_oi_pit.parquet")
    idx = oi["spot"]; idx.index = pd.to_datetime(oi.index)
    # weekly A composite (0139), definition frozen from the committed diagnostic
    from diag_delivery_accumulation import build_weekly_A  # noqa: E402
    W = build_weekly_A()
    A = W.pivot_table(index="wk", columns="symbol", values="A")
    A.index = pd.to_datetime(A.index)
    # delivery dlv_med21 (0118), daily -> reduce per week in the loop
    dfeat = derive_delivery_features(apply_alias_map(pd.read_parquet(DELIVERY_RAW_PATH)))
    dfeat["date"] = pd.to_datetime(dfeat["date"])
    events = build_event_table(apply_alias_map(pd.read_parquet(EARNINGS_RAW_PATH)))
    return closes, idx, A, dfeat, events


def _week_features(asof, closes, idx, A, dfeat, events):
    crs = weekly_crs_dist(closes, idx, asof)
    d = dfeat[(dfeat["date"] <= asof) & (dfeat["date"] >= asof - pd.Timedelta(days=10))]
    dlv = d.sort_values("date").groupby("symbol")["dlv_med21"].last()
    wk = A.index[A.index <= asof]
    accum = A.loc[wk[-1]] if len(wk) else pd.Series(dtype=float)
    monday = asof + pd.Timedelta(days=3)
    known = events[events["ann_ts"] <= asof]
    hit = known[(known["event_date"] >= monday) &
                (known["event_date"] <= monday + pd.Timedelta(days=EVENT_WINDOW_CD))]
    flag = pd.Series(True, index=hit["symbol"].unique())
    return crs, dlv, accum, flag


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=INCEPTION)
    ap.add_argument("--validate", action="store_true",
                    help="structural check on a scratch path (weights/NAV integrity); reports NO performance")
    args = ap.parse_args(argv)
    start = pd.Timestamp(args.start)

    closes, idx, A, dfeat, events = _load()
    wret = closes.resample("W-FRI").last().pct_change()          # per-name weekly return
    weeks = [w for w in wret.index if w >= start and w < wret.index[-1]]

    arms = {"ew": "w_ew", "sw": "w_sw", "sw_accum": "w_sw_accum"}
    rows = {k: [] for k in arms}                                 # (week, arm_return)
    integrity_ok = True
    for w in weeks:
        crs, dlv, accum, flag = _week_features(w, closes, idx, A, dfeat, events)
        if crs.dropna().shape[0] < 50:
            continue
        books = build_books(crs, dlv, flag, accum=accum)
        nxt = wret.index[wret.index.get_loc(w) + 1]
        r = wret.loc[nxt].reindex(books.index)                  # next-week realized return per name
        for k, wc in arms.items():
            if not np.isclose(books[wc].sum(), 1.0):
                integrity_ok = False
            rows[k].append((str(nxt.date()), float((books[wc] * r.fillna(0.0)).sum())))

    npts = len(rows["ew"])
    state = {"model": "breadth-50 watched book (EW / SW / SW-accum), proposal §4",
             "inception": str(start.date()), "observational": True, "arms": list(arms),
             "n_points": npts, "construction": "frozen; zero in-sample fitting; logger reports no spread"}
    if npts >= 1:
        # store realized weekly returns ONLY (NAVs are derivable; the review computes any comparison,
        # not this logger). No spread, no 'winner', nothing evaluative is emitted here.
        state["weekly_returns"] = {k: rows[k] for k in arms}
        state["asof"] = rows["ew"][-1][0]
    else:
        state["note"] = ("no post-inception weeks with data yet (research OHLCV lags the inception; the "
                         "real cron downloads) — empty is valid, not an error")

    if args.validate:
        # STRUCTURAL check only: confirm the loop ran, weights summed to 1 every week, returns finite.
        # Deliberately prints NO arm performance / NO spread — that would peek at the forward experiment.
        finite = all(np.isfinite(v) for k in arms for _, v in rows[k])
        print(f"breadth-50 logger VALIDATE: weeks processed {npts} | weight-integrity {integrity_ok} | "
              f"returns-finite {finite} | 3 arms present {set(arms) == set(rows)}")
        print("  (structural only — no performance, no spread reported, forward seal intact)")
        return 0 if (integrity_ok and finite) else 1

    OUT.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"breadth-50 forward logger (observational): {npts} post-inception week(s) -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
