"""Weekly lifecycle report (ADR-0020, Part D): results/lifecycle_status.json and a one-screen table on the scan run page.

For each tracked strategy: stage, weeks in stage, cumulative return and drawdown on its forward record, where the return
sits in its frozen band at the nearest horizon, GREEN / AMBER / RED, the benchmark over the same dates, and any review
trigger. Rules: skills/strategy-lifecycle/SKILL.md. Reads only; writes its own two files and one append-only status log.

    python pipelines/lifecycle/weekly_status.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "pipelines" / "lifecycle")]
import core as C  # noqa: E402

RECORDS = ROOT / "forward" / "records"
BANDS = ROOT / "forward" / "bands"
STAGES = ROOT / "forward" / "lifecycle" / "stages.json"
STATUS_LOG = ROOT / "forward" / "lifecycle" / "status_log.csv"
OUT = ROOT / "results" / "lifecycle_status.json"
FILLS = ROOT / "results" / "execution_fills_export.json"     # optional export of the app's execution_events table
STRATEGIES = {"live_swing": "Live swing (Grade A)", "xsec_momentum_0001": "Cross-sectional momentum (0001)",
              "blend_70_30_vt15": "70/30 momentum/swing, 15% vol target", "long_horizon": "Long-horizon trend"}


def latest_band(strategy: str) -> dict | None:
    files = sorted(BANDS.glob(f"{strategy}_bands_*.json"))
    return json.loads(files[-1].read_text(encoding="utf-8")) | {"_file": files[-1].name} if files else None


def stage_of(strategy: str) -> dict:
    cur = json.loads(STAGES.read_text(encoding="utf-8")) if STAGES.exists() else []
    mine = [e for e in cur if e["strategy"] == strategy]
    return mine[-1] if mine else {"stage": "RESEARCH", "from": None}


def monthly_reds(strategy: str, status: str, date: str) -> int:
    """Consecutive month-end REDs, counting this week as the current month's latest check."""
    log = pd.read_csv(STATUS_LOG, dtype=str) if STATUS_LOG.exists() else pd.DataFrame(columns=["date", "strategy", "status", "weeks"])
    mine = pd.concat([log[log.strategy == strategy][["date", "status"]], pd.DataFrame([{"date": date, "status": status}])])
    mine = mine.drop_duplicates("date", keep="last").sort_values("date")
    last_of_month = mine.groupby(mine["date"].str[:7]).tail(1)["status"].tolist()
    n = 0
    for s in reversed(last_of_month):
        if s != "RED":
            break
        n += 1
    return n


def one(strategy: str) -> dict:
    rec = C.read_record(RECORDS / f"{strategy}.csv")
    st = stage_of(strategy)
    out = {"strategy": strategy, "label": STRATEGIES[strategy], "stage": st["stage"], "stage_from": st.get("from")}
    band = latest_band(strategy)
    out["bands_file"] = band["_file"] if band else None
    if len(rec) < 2:
        return out | {"weeks": max(len(rec) - 1, 0), "status": "NEW", "provisional": True,
                      "note": "no forward weeks yet" if len(rec) else "record not started"}
    nav = rec["nav"].astype(float).to_numpy()
    weeks = len(rec) - 1
    r0 = pd.to_numeric(rec["weekly_return"], errors="coerce").iloc[0]
    if r0 == r0:                                     # a linked record's first row already carries a week's return
        nav = np.concatenate([[nav[0] / (1 + float(r0))], nav])
        weeks = len(rec)
    cum = float(nav[-1] / nav[0] - 1) * 100
    depth = float((1 - nav / np.maximum.accumulate(nav)).max()) * 100
    out |= {"weeks": weeks, "record_from": rec["date"].iloc[0], "record_to": rec["date"].iloc[-1],
            "cum_return_pct": round(cum, 2), "drawdown_depth_pct": round(depth, 2),
            "weeks_in_stage": int((rec["date"] > str(st.get("from") or "")).sum()) if st.get("from") else weeks}
    tri = pd.to_numeric(rec["benchmark_tri"], errors="coerce").to_numpy()
    rnav, dates = rec["nav"].astype(float).to_numpy(), rec["date"].tolist()
    ok = np.flatnonzero(~np.isnan(tri))
    if len(ok) >= 2:
        f, l = int(ok[0]), int(ok[-1])
        out["benchmark"] = {"name": C.BENCHMARK, "return_pct": round(float(tri[l] / tri[f] - 1) * 100, 2),
                            "strategy_same_dates_pct": round(float(rnav[l] / rnav[f] - 1) * 100, 2), "from": dates[f], "to": dates[l]}
        w = pd.DataFrame({"s": pd.Series(rnav).pct_change(), "b": pd.Series(tri).pct_change()}).dropna().tail(52)
        if len(w) >= 52 and w.s.std() > 0 and w.b.std() > 0:
            rs, rb = float(w.s.mean() / w.s.std()), float(w.b.mean() / w.b.std())
            out["benchmark"] |= {"risk_adjusted_52w": round(rs * np.sqrt(52), 2), "benchmark_risk_adjusted_52w": round(rb * np.sqrt(52), 2),
                                 "trails_benchmark_52w": bool(rs < rb)}
        else:
            out["benchmark"]["trails_benchmark_52w"] = None      # needs 52 weeks
    if band is None:
        return out | {"status": "NO BANDS", "provisional": True}
    h = C.nearest_horizon(weeks)
    blk = band["horizons"][str(h)]
    cls = C.classify(cum, depth, blk, band["worst_backtest_drawdown_pct"])
    out |= {"horizon_weeks": h, "band_return_pct": blk["cum_return_pct"]["band"], "band_drawdown_p95_pct": blk["drawdown_depth_pct"]["band"]["p95"],
            "drawdown_breaker_pct": abs(band["drawdown_breaker_pct"]), "percentile": C.return_percentile(cum, blk),
            "status": cls["status"], "reasons": cls["reasons"], "provisional": weeks < C.MIN_VERDICT_WEEKS}
    trig = []
    reds = monthly_reds(strategy, cls["status"], rec["date"].iloc[-1])
    if cls["drawdown_breaker"]:
        trig.append("RED on the drawdown breaker: review now; retirement may be considered")
    elif cls["status"] == "RED" and weeks < C.MIN_VERDICT_WEEKS:
        trig.append(f"RED, provisional (week {weeks} of 26): no verdict; check for a data or execution fault only")
    elif cls["status"] == "RED":
        trig.append("RED: open a review (three questions)" + (f"; RED at {reds} consecutive monthly checks, retirement may be considered" if reds >= 2 else ""))
    if out.get("benchmark", {}).get("trails_benchmark_52w"):
        trig.append("trails the benchmark's risk-adjusted return over 52 weeks: flag for the next quarterly review")
    if st["stage"] == "PAPER" and weeks >= 26 and cls["status"] in ("GREEN", "AMBER"):
        trig.append("26 weeks of paper reached at AMBER or better: eligible for a PILOT decision if no RED in the last 8 weeks")
    out["triggers"] = trig
    return out


def fills_from_db() -> list[dict] | None:
    """The app's recorded fills, read-only, when the scan has been given `LIFECYCLE_FILLS_DB_URL`.

    Owner rule (ADR-0020, 2026-11-14): fills are read for TRACKING ERROR ONLY, never for a model decision. Nothing in the
    scan, the engine or the records imports this function. Individual fills are never written to the repository, which
    is public: only the aggregates from `core.tracking_error` are published."""
    url = os.environ.get("LIFECYCLE_FILLS_DB_URL", "").strip()
    if not url:
        return None
    from sqlalchemy import create_engine, text
    eng = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 10} if url.startswith("postgres") else {})
    with eng.connect() as c:
        rows = c.execute(text("SELECT id, signal_id, side, qty, price, corrects_event_id FROM execution_events ORDER BY id")).mappings().all()
    superseded = {r["corrects_event_id"] for r in rows if r["corrects_event_id"]}
    return [{"signal_id": r["signal_id"], "side": r["side"], "qty": r["qty"], "price": r["price"]} for r in rows if r["id"] not in superseded]


def execution() -> dict:
    """Tracking error of real fills against the model. Aggregates only."""
    fills, source = None, None
    try:
        fills = fills_from_db()
        source = "app database (read-only)" if fills is not None else None
    except Exception as exc:                                                  # noqa: BLE001 — never block the report
        return {"n_fills_matched": 0, "fills_source": None, "note": f"fills could not be read ({type(exc).__name__})"}
    if fills is None and FILLS.exists():
        fills, source = json.loads(FILLS.read_text(encoding="utf-8")), FILLS.name
    if fills is None:
        return {"n_fills_matched": 0, "fills_source": None,
                "note": "the scan has no read access to the app's fills yet (repository secret LIFECYCLE_FILLS_DB_URL not set)"}
    hist = json.loads((ROOT / "results" / "signals_history_weekly.json").read_text(encoding="utf-8"))
    hist = hist if isinstance(hist, list) else hist.get("signals", [])
    stops = {}
    arch = ROOT / "results" / "cards_archive.jsonl"
    if arch.exists():
        for ln in arch.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                c = json.loads(ln)
                if c.get("stop"):
                    stops.setdefault(f"{c['ticker']}__{c['signal_date']}", c["stop"])
    model = {f"{h['ticker']}__{h['signal_date']}": {"entry": h.get("entry"), "stop": stops.get(f"{h['ticker']}__{h['signal_date']}"),
                                                     "exit": h.get("close_price") if h.get("status") != "ACTIVE" else None} for h in hist}
    return C.tracking_error(fills, model) | {"fills_source": source, "n_fills_read": len(fills)}


def table(rows: list[dict]) -> str:
    t = ["## Strategy lifecycle — weekly status (ADR-0020)", "",
         "| strategy | stage | weeks | return | drawdown | vs band (horizon) | status | benchmark, same dates | trigger |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        b = r.get("benchmark") or {}
        stat = r.get("status", "—") + (" (provisional)" if r.get("provisional") and r.get("status") in ("GREEN", "AMBER", "RED") else "")
        t.append(f"| {r['label']} | {r['stage']} | {r.get('weeks', 0)} | "
                 + (f"{r['cum_return_pct']:+.1f}%" if "cum_return_pct" in r else "—") + " | "
                 + (f"−{r['drawdown_depth_pct']:.1f}%" if "drawdown_depth_pct" in r else "—") + " | "
                 + (f"{r['percentile']} ({r['horizon_weeks']}w)" if "percentile" in r else "—") + f" | {stat} | "
                 + (f"{b['return_pct']:+.1f}% vs {b['strategy_same_dates_pct']:+.1f}%" if b else "—") + " | "
                 + ("; ".join(r.get("triggers") or []) or r.get("note") or "—") + " |")
    t += ["", "No verdict comes from fewer than 26 weeks of forward data, except the drawdown breaker. RED means a review, not a kill."]
    return "\n".join(t) + "\n"


def main() -> int:
    rows = [one(s) for s in STRATEGIES]
    asof = max((r.get("record_to") or "" for r in rows), default="")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ex = execution()
    OUT.write_text(json.dumps({"as_of": asof, "rules": "skills/strategy-lifecycle/SKILL.md", "benchmark": C.BENCHMARK, "strategies": rows,
                               "execution_tracking_error": ex}, indent=2) + "\n", encoding="utf-8")
    # append-only status log: one line per strategy per record week
    seen = set()
    if STATUS_LOG.exists():
        seen = {(a, b) for a, b in pd.read_csv(STATUS_LOG, dtype=str)[["date", "strategy"]].itertuples(index=False)}
    else:
        STATUS_LOG.parent.mkdir(parents=True, exist_ok=True)
        STATUS_LOG.write_text("date,strategy,status,weeks\n", encoding="utf-8")
    with STATUS_LOG.open("a", encoding="utf-8", newline="") as fh:
        for r in rows:
            if r.get("record_to") and (r["record_to"], r["strategy"]) not in seen and r.get("status") in ("GREEN", "AMBER", "RED"):
                fh.write(f"{r['record_to']},{r['strategy']},{r['status']},{r['weeks']}\n")
    text = table(rows) + "\n**Execution tracking error (real fills vs model):** " + (
        f"{ex['n_fills_matched']} fills matched, mean slippage {ex['mean_slippage_bps']} bps / {ex['mean_slippage_R']}R"
        if ex.get("n_fills_matched") else ex.get("note", "not measurable")) + "\n"
    sys.stdout.buffer.write(text.encode("utf-8"))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
