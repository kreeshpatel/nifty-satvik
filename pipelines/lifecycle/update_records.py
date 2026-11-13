"""Weekly forward records (ADR-0020, Part C): forward/records/<strategy>.csv, append-only, one row per week.

Runs in the Saturday scan, after the scan has refreshed its OHLCV cache, on that same cache (the live scan's data feed).
It only ever APPENDS a row for a week that is not yet recorded. It never rewrites a past row (ADR-0018): a new week's
return is taken from a rebuild from the record's start, and chained onto the frozen NAV of the previous row.

  xsec_momentum_0001   paper record. Pre-reg 0001's book (top 30 mid-band by NSE momentum score, monthly), fresh ₹10L at
                       the record's first date.
  blend_70_30_vt15     paper record. 70% of the momentum record's daily returns / 30% of the live swing paper book's, with
                       the 15% volatility target (pipelines/lifecycle/core.py::vol_target_blend).
  live_swing           LINKED from results/portfolio_history_weekly.csv (its existing record; nothing recomputed).
  long_horizon         LINKED from results/forward_wall.csv, base arm (its existing record).

Each row: date, nav, weekly_return, holdings, turnover, benchmark_tri (Nifty Midcap150 Momentum 50 TRI), note.
The first row of a paper record is its start: NAV ₹10,00,000 and no return.

This step cannot block the scan: every strategy is wrapped, failures print a ::warning:: and the exit code is always 0.

    python pipelines/lifecycle/update_records.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "pipelines" / "research"), str(ROOT / "pipelines" / "lifecycle")]
import core as C  # noqa: E402

RECORDS = ROOT / "forward" / "records"
STAGES = ROOT / "forward" / "lifecycle" / "stages.json"
TRI_FILE = ROOT / "diagnostics" / "research" / "benchmarks" / "tri" / "nifty_midcap150_momentum_50_tri.csv"
CAPITAL = 1_000_000.0


def warn(msg: str) -> None:
    sys.stdout.write(f"::warning::lifecycle records: {msg}\n")


# ------------------------------------------------------------------------------------------------ benchmark
def update_tri() -> pd.Series:
    """The committed TRI history, topped up from niftyindices.com when the network allows. Never raises."""
    s = pd.Series(dtype=float)
    if TRI_FILE.exists():
        d = pd.read_csv(TRI_FILE, parse_dates=["date"])
        s = d.set_index("date")["tri"].astype(float)
    try:
        import requests
        last = s.index.max() if len(s) else pd.Timestamp("2016-01-01")
        today = pd.Timestamp.today().normalize()
        if today - last > pd.Timedelta(days=1):
            h = {"User-Agent": "Mozilla/5.0 (research script)", "Accept": "application/json, text/javascript, */*; q=0.01",
                 "Content-Type": "application/json; charset=utf-8", "X-Requested-With": "XMLHttpRequest",
                 "Origin": "https://www.niftyindices.com", "Referer": "https://www.niftyindices.com/reports/historical-data"}
            ses = requests.Session()
            ses.get("https://www.niftyindices.com/reports/historical-data", headers=h, timeout=30)
            name = "NIFTY MIDCAP150 MOMENTUM 50"
            cinfo = "{'name':'%s','startDate':'%s','endDate':'%s','indexName':'%s'}" % (
                name, (last + pd.Timedelta(days=1)).strftime("%d-%b-%Y"), today.strftime("%d-%b-%Y"), name)
            r = ses.post("https://www.niftyindices.com/BackPage/getTotalReturnIndexString", headers=h,
                         data=json.dumps({"cinfo": cinfo}), timeout=60)
            rows = json.loads(r.text)
            if rows:
                new = pd.Series({pd.to_datetime(x["Date"], format="%d %b %Y"): float(x["TotalReturnsIndex"]) for x in rows})
                s = pd.concat([s, new[~new.index.isin(s.index)]]).sort_index()
                TRI_FILE.parent.mkdir(parents=True, exist_ok=True)
                pd.DataFrame({"date": s.index.strftime("%Y-%m-%d"), "tri": s.values}).to_csv(TRI_FILE, index=False)
    except Exception as exc:                                                  # noqa: BLE001 — a benchmark gap must not stop a record
        warn(f"benchmark TRI not refreshed ({type(exc).__name__}: {exc}); rows carry the last known value or blank")
    return s


def tri_on(tri: pd.Series, date: str):
    if not len(tri):
        return None
    s = tri[tri.index <= pd.Timestamp(date)]
    return round(float(s.iloc[-1]), 2) if len(s) and (pd.Timestamp(date) - s.index[-1]).days <= 7 else None


# ------------------------------------------------------------------------------------------------ helpers
def week_ends(nav: pd.Series) -> pd.Series:
    """Last session of each Friday-ending week."""
    return nav.groupby(nav.index.to_period("W-FRI")).tail(1)


def log_stage(strategy: str, stage: str, date: str, note: str, dry: bool) -> None:
    """Append a stage line the first time a strategy gets a record. Existing lines are never changed."""
    cur = json.loads(STAGES.read_text(encoding="utf-8")) if STAGES.exists() else []
    if any(e["strategy"] == strategy for e in cur) or dry:
        return
    STAGES.parent.mkdir(parents=True, exist_ok=True)
    STAGES.write_text(json.dumps(cur + [{"strategy": strategy, "stage": stage, "from": date, "note": note}], indent=1) + "\n",
                      encoding="utf-8")


def chain(path: Path, rebuilt: pd.Series, extra, tri: pd.Series, note: str, dry: bool) -> int:
    """Append every week-end of `rebuilt` (a NAV rebuilt from the record's start) that is after the last recorded week.

    The new row's NAV = previous frozen NAV x (rebuilt now / rebuilt at the previous row's date)."""
    rec = C.read_record(path)
    we = week_ends(rebuilt)
    n = 0
    if not len(rec):
        d0 = we.index[0]
        row = {"date": str(d0.date()), "nav": CAPITAL, "weekly_return": None, "benchmark_tri": tri_on(tri, str(d0.date())),
               "note": f"record start; {note}", **extra(d0, None)}
        if not dry:
            C.append_row(path, row)
        rec = pd.DataFrame([row])
        n += 1
    last_date, last_nav = pd.Timestamp(rec["date"].iloc[-1]), float(rec["nav"].iloc[-1])
    for d, v in we[we.index > last_date].items():
        base = rebuilt[rebuilt.index <= last_date]
        if not len(base) or base.iloc[-1] <= 0:
            warn(f"{path.name}: no rebuilt value at {last_date.date()}, week {d.date()} skipped")
            continue
        ret = float(v / base.iloc[-1] - 1)
        last_nav = round(last_nav * (1 + ret), 2)
        row = {"date": str(d.date()), "nav": last_nav, "weekly_return": round(ret, 6), "benchmark_tri": tri_on(tri, str(d.date())),
               "note": note, **extra(d, last_date)}
        if not dry:
            C.append_row(path, row)
        last_date = d
        n += 1
    return n


# ------------------------------------------------------------------------------------------------ strategies
def momentum_run(start: str):
    """Pre-reg 0001's book on the live scan's OHLCV cache, fresh capital at `start`. Returns (daily NAV, curve, trades)."""
    import run_0001_xsec_momentum as M
    from nq.data.membership import load_membership
    from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache
    from nq.engine.rebalance_book import RebalanceConfig, simulate_rebalance_book
    from nq.universe import build_universe
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    first = min(d.index.min() for d in ohlcv.values())
    last = max(d.index.max() for d in ohlcv.values())
    p = M.add_signals(build_universe(ohlcv, load_membership(), start=str(first.date()), end=str(last.date())))
    b = p[p["ticker"].isin(p.loc[p["size_band"] == M.BAND, "ticker"].unique())].copy()
    b["rank"] = np.where(b["eligible"] & (b["size_band"] == M.BAND) & b["nms"].notna(), b["nms"], np.nan)
    bt = simulate_rebalance_book(b, cfg=RebalanceConfig(**M.BOOK), start=start, end=str(last.date()), initial_capital=CAPITAL)
    cur = pd.DataFrame(bt["equity_curve"])
    cur["date"] = pd.to_datetime(cur["date"])
    return cur.set_index("date")["equity"].astype(float), cur.set_index("date"), pd.DataFrame(bt["trades"])


def do_momentum(tri: pd.Series, dry: bool) -> pd.Series | None:
    path = RECORDS / "xsec_momentum_0001.csv"
    rec = C.read_record(path)
    from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache
    last_bar = max(d.index.max() for d in load_ohlcv_cache(OHLCV_CACHE).values())
    start = str(rec["date"].iloc[0]) if len(rec) else str(last_bar.date())
    nav, cur, tr = momentum_run(start)
    if not len(nav):
        warn("momentum: the engine returned an empty curve (not enough history in the scan cache?)")
        return None

    def extra(d, prev):
        hold = int(cur["n_positions"].get(d, 0)) if "n_positions" in cur else None
        to = None
        if prev is not None and len(tr) and "exit_date" in tr:
            x = pd.to_datetime(tr["exit_date"])
            sold = tr[(x > prev) & (x <= d)]
            to = round(float((sold["exit"] * sold["qty"]).sum() / nav.get(d, np.nan)), 4) if len(sold) else 0.0
        return {"holdings": hold, "turnover": to}
    n = chain(path, nav, extra, tri, "paper; pre-reg 0001 book on the live scan cache", dry)
    log_stage("xsec_momentum_0001", "PAPER", start, "paper record started by pipelines/lifecycle/update_records.py (ADR-0020)", dry)
    sys.stdout.write(f"xsec_momentum_0001: {n} row(s) appended; holdings now {int(cur['n_positions'].iloc[-1]) if 'n_positions' in cur else '?'}\n")
    return nav


def swing_nav() -> pd.Series:
    ph = pd.read_csv(ROOT / "results" / "portfolio_history_weekly.csv", parse_dates=["date"]).set_index("date")["total_value"].astype(float)
    return ph[~ph.index.duplicated(keep="last")].sort_index()


def do_blend(mom_nav: pd.Series | None, tri: pd.Series, dry: bool) -> None:
    if mom_nav is None:
        warn("blend: skipped because the momentum leg did not run")
        return
    path = RECORDS / "blend_70_30_vt15.csv"
    sw = swing_nav()
    start = mom_nav.index[0]
    sw = sw[sw.index >= start]
    if not len(sw):
        warn("blend: the swing paper book has no value on or after the record start")
        return
    r, expo = C.vol_target_blend(mom_nav.pct_change().fillna(0), sw.pct_change().fillna(0))
    nav = CAPITAL * (1 + r).cumprod()
    extra = lambda d, prev: {"holdings": None, "turnover": None}
    n = chain(path, nav, extra, tri, f"paper; 70/30 momentum/swing, 15% vol target; exposure {float(expo.iloc[-1]):.2f}", dry)
    log_stage("blend_70_30_vt15", "PAPER", str(start.date()), "paper record started by pipelines/lifecycle/update_records.py (ADR-0020)", dry)
    sys.stdout.write(f"blend_70_30_vt15: {n} row(s) appended; exposure now {float(expo.iloc[-1]):.2f}\n")


def do_linked(tri: pd.Series, dry: bool) -> None:
    """The live swing and long-horizon keep their own records; these files are the same numbers in the common format."""
    sw = week_ends(swing_nav())
    wall = pd.read_csv(ROOT / "results" / "forward_wall.csv", parse_dates=["date"])
    wall = wall[wall.status == "ok"].set_index("date")
    lh0 = float(wall.base_equity.iloc[0] / (1 + wall.base_ret.iloc[0]))
    lh = week_ends(wall.base_equity.astype(float))
    for name, series, hold, src in (("live_swing", sw, None, "results/portfolio_history_weekly.csv"),
                                    ("long_horizon", lh, wall.base_npos, "results/forward_wall.csv base arm")):
        path = RECORDS / f"{name}.csv"
        rec = C.read_record(path)
        last = pd.Timestamp(rec["date"].iloc[-1]) if len(rec) else None
        prev_nav = float(rec["nav"].iloc[-1]) if len(rec) else (CAPITAL if name == "live_swing" else lh0)
        n = 0
        for d, v in series.items():
            if last is not None and d <= last:
                continue
            row = {"date": str(d.date()), "nav": round(float(v), 2), "weekly_return": round(float(v / prev_nav - 1), 6),
                   "holdings": None if hold is None else int(hold.get(d, np.nan)) if d in hold.index else None, "turnover": None,
                   "benchmark_tri": tri_on(tri, str(d.date())), "note": f"linked from {src}"}
            if not dry:
                C.append_row(path, row)
            prev_nav, n = float(v), n + 1
        sys.stdout.write(f"{name}: {n} row(s) appended (linked)\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", choices=["linked"], help="linked: only mirror the existing swing and long-horizon records")
    a = ap.parse_args()
    tri = update_tri()
    mom = None
    for label, fn in (("linked records", lambda: do_linked(tri, a.dry_run)),):
        try:
            fn()
        except Exception as exc:                                              # noqa: BLE001
            warn(f"{label} failed ({type(exc).__name__}: {exc})")
    if a.only == "linked":
        return 0
    try:
        mom = do_momentum(tri, a.dry_run)
    except Exception as exc:                                                  # noqa: BLE001
        warn(f"momentum record failed ({type(exc).__name__}: {exc})")
    try:
        do_blend(mom, tri, a.dry_run)
    except Exception as exc:                                                  # noqa: BLE001
        warn(f"blend record failed ({type(exc).__name__}: {exc})")
    return 0


if __name__ == "__main__":
    t0 = time.time()
    code = main()
    sys.stdout.write(f"lifecycle records done in {time.time() - t0:.0f}s\n")
    raise SystemExit(code)
