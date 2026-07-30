"""Corrected-universe anchor harness — September item 1 runs THIS script in full; those numbers are
the memo of record. This session only smoke-tests the plumbing on a truncated window.

Runs BOTH books on pinned (survivor) vs corrected (pinned + backfill + aliases, the committed
`corrected_universe()` path) data via the existing harnesses, and emits the side-by-side anchor table
(Sharpe / CAGR / MaxDD / after-tax approx / per-year) plus the swing trade-level diff (recovered
delisted names). After-tax uses the standing 0114 approximation (annual positive returns haircut at
STCG 20.8%) — the September memo may refine via the full cost model.

    python scripts/run_corrected_anchor.py --smoke          # truncated window (plumbing proof)
    python scripts/run_corrected_anchor.py                  # full window (September's run of record)
    python scripts/run_corrected_anchor.py --bracket        # LH solvency-gate sensitivity bracket:
        # full-window LH base on pinned / corrected AS-IS (lower bound) / corrected with the D/E
        # gate WAIVED for recovered-only names (upper bound — assumes every recovered name would
        # have passed). The waiver is a runtime wrap of nq.engine.panel.solvent_universe_mask
        # (orig_mask | ticker in recovered) applied ONLY inside this diagnostic — no nq/** change,
        # engine untouched. All other filters (membership, ADV, signal) stay intact. Diagnostic for
        # the review-binder §1 flag; NOT the memo of record.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from config import load_frozen_cfg  # noqa: E402
from nq.data.features import compute_all_features  # noqa: E402
from nq.data.fundamentals import load_fund_store  # noqa: E402
from nq.data.membership import load_membership  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from nq.engine.panel import compose_ranked_panel  # noqa: E402
from nq.runner.research import _daily_returns, run_backtest  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_weekly_rank import backtest as swing_backtest  # noqa: E402
from run_bhanushali_weekly_rank import prep_weekly_rank  # noqa: E402

STCG = 0.208


def metrics(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 30:
        return {}
    e = (1 + r).cumprod()
    yrs = len(r) / 252
    per_year = {int(y): round(((1 + g).cumprod().iloc[-1] - 1) * 100, 1)
                for y, g in r.groupby(r.index.year)}
    at = np.prod([1 + (v / 100 if v <= 0 else v / 100 * (1 - STCG)) for v in per_year.values()])
    return {"sharpe": round(float(r.mean() / r.std() * np.sqrt(252)), 3),
            "cagr_%": round(float((e.iloc[-1] ** (1 / yrs) - 1) * 100), 2),
            "maxdd_%": round(float((e / e.cummax() - 1).min() * 100), 1),
            "aftertax_cagr_%": round(float(at ** (1 / yrs) - 1) * 100, 2),
            "per_year_%": per_year}


def resolved_store(base: dict, backfill_path: Path | None, alias_aware: bool) -> dict:
    """Compose the fundamentals store the gate will see. Pure data-side composition through the
    existing ``fund_store`` parameter — NO nq/** change, engine untouched.

    ``alias_aware``: an alias old-symbol with no fundamentals inherits its SUCCESSOR's frame. Same
    company, same balance sheet; the OHLCV layer already resolves this pair via the alias map, the
    fundamentals lookup simply never did. Never overwrites an existing frame.
    """
    store = dict(base)
    if backfill_path and backfill_path.exists():
        with open(backfill_path, "rb") as f:
            store.update(pickle.load(f))
    if alias_aware:
        amap = json.load(open(ROOT / "data" / "delisted_alias_map.json"))["aliases"]
        for old, spec in amap.items():
            src = store.get(spec["to"])
            if src is not None and len(src) and (store.get(old) is None or not len(store.get(old))):
                store[old] = src
    return store


def lh_book(ohlcv, start, end, waive_de_for: set[str] | None = None,
            fund_store: dict | None = None
            ) -> tuple[pd.Series, pd.DataFrame]:
    """LH base run -> (daily returns, trades). ``waive_de_for``: tickers that skip the solvency
    gate (recovered-names bracket arm) via a runtime wrap of the panel-module mask — restored in
    a finally, so nothing leaks into any other run in the same process."""
    import nq.engine.panel as panel_mod
    orig = panel_mod.solvent_universe_mask
    if waive_de_for:
        def waived(df, **kw):
            return orig(df, **kw) | df["ticker"].isin(waive_de_for)
        panel_mod.solvent_universe_mask = waived
    try:
        panel = compose_ranked_panel(compute_all_features(ohlcv), ohlcv,
                                     fund_store=fund_store if fund_store is not None
                                     else load_fund_store(), membership=load_membership())
    finally:
        panel_mod.solvent_universe_mask = orig
    panel["date"] = pd.to_datetime(panel["date"])
    res = run_backtest(panel, load_frozen_cfg(), start=start, end=end)
    return _daily_returns(res["equity_curve"]), pd.DataFrame(res["trades"])


def swing_book(ohlcv, mem, start) -> tuple[pd.Series, pd.DataFrame]:
    led: list = []
    m = swing_backtest(prep_weekly_rank(ohlcv), mem, ledger=led, start=start)
    return m["ret"].dropna(), pd.DataFrame(led)


def bracket(start: str, end: str) -> int:
    """The §1-flag diagnostic: bound the LH exposure hidden by the D/E data-vs-economics
    conflation. Lower bound = corrected AS-IS (0 by construction if the identity holds);
    upper bound = every recovered name passes the gate."""
    print(f"=== LH solvency-gate sensitivity bracket [window {start}..{end}] ===")
    mem = load_membership()
    pinned = load_ohlcv_cache(OHLCV_CACHE)
    corrected = corrected_universe()
    recovered = set(corrected) - set(pinned)
    print(f"universes: pinned {len(pinned)} | corrected {len(corrected)} | recovered {len(recovered)}")

    # Alias-old-symbol screen. NOTE (corrected 2026-07-29 by scripts/diag_alias_census.py): these
    # byte-identical pairs are the 17 MAPPED aliases being materialized on purpose (old symbol ->
    # successor's series), NOT unreconciled duplicates. PIT membership windows are disjoint for
    # 17/17, so one company can never occupy two slots and arm (b) is NOT "contaminated" in the
    # double-counting sense. Arm (c) is retained only as the narrower reading of the bound — the
    # gap between (b) and (c) is renamed-but-alive companies whose fundamentals live under the
    # successor symbol, which --resolved fixes properly via an alias-aware fundamentals join.
    fp: dict[str, list[str]] = {}
    for t, df in corrected.items():
        if df is None or len(df) == 0:
            continue
        h = hashlib.md5(pd.util.hash_pandas_object(df["Close"].round(4), index=True).values).hexdigest()
        fp.setdefault(h, []).append(t)
    dup_groups = {h: v for h, v in fp.items() if len(v) > 1}
    dup_recovered = {t for v in dup_groups.values() for t in v if t in recovered}
    genuine = recovered - dup_recovered
    print(f"duplicate-entity groups: {len(dup_groups)} | recovered tickers that are duplicates of a "
          f"still-listed name: {len(dup_recovered)} | genuinely-recovered: {len(genuine)}")

    arms = {}
    for name, oh, waive in (("pinned", pinned, None),
                            ("corrected AS-IS (a)", corrected, None),
                            ("corrected GATE-WAIVED (b)", corrected, recovered),
                            ("GATE-WAIVED, dedup (c)", corrected, genuine)):
        r, tr = lh_book(oh, start, end, waive_de_for=waive)
        arms[name] = (metrics(r), tr)
        print(f"  LH base / {name}: done ({len(tr)} trades)")

    t = pd.DataFrame([{"arm": k, **m} for k, (m, _) in arms.items()])
    print("\n=== LH BRACKET TABLE ===")
    print(t.drop(columns=["per_year_%"]).to_string(index=False))
    print("\nper-year:")
    for k, (m, _) in arms.items():
        print(f"  {k}: {m.get('per_year_%')}")
    rep = {"window": [start, end], "n_recovered": len(recovered), "n_dup_recovered": len(dup_recovered),
           "dup_groups": [v for v in dup_groups.values()],
           "arms": {k: m for k, (m, _) in arms.items()}}

    ma, mb = arms["corrected AS-IS (a)"][0], arms["corrected GATE-WAIVED (b)"][0]
    mc = arms["GATE-WAIVED, dedup (c)"][0]
    for lbl, m2 in (("(b) contaminated", mb), ("(c) dedup — the honest upper bound", mc)):
        print("\n(a)->{} deltas:  dSharpe {:+.3f} | dCAGR {:+.2f}pp | dMaxDD {:+.1f}pp".format(
            lbl, m2["sharpe"] - ma["sharpe"], m2["cagr_%"] - ma["cagr_%"],
            m2["maxdd_%"] - ma["maxdd_%"]))
    ident = arms["pinned"][0] == ma
    print(f"pinned == corrected-AS-IS identity on this window: {ident}")

    tr_b = arms["corrected GATE-WAIVED (b)"][1]
    rec_tr = tr_b[tr_b["ticker"].isin(recovered)] if len(tr_b) else tr_b
    if len(rec_tr):
        d = rec_tr[rec_tr["ticker"].isin(dup_recovered)]
        print(f"\nof (b)'s recovered-name trades: {len(d)} are duplicate-entity tickers "
              f"({d['days_held'].sum()/5:.0f} name-weeks, pnl {d['pnl'].sum():,.0f}) — contamination")
    print(f"\n=== RECOVERED NAMES IN THE TOP-15 BOOK UNDER (b) ===")
    print(f"trades: {len(rec_tr)} of {len(tr_b)} total | "
          f"name-weeks held (days/5): {rec_tr['days_held'].sum() / 5:.0f}" if len(rec_tr)
          else "trades: 0 — no recovered name ever entered the book under the waiver")
    if len(rec_tr):
        by = rec_tr.groupby("ticker").agg(n=("ticker", "size"), days=("days_held", "sum"),
                                          pnl=("pnl", "sum")).sort_values("days", ascending=False)
        print(by.to_string())

    # swing-side full-window consistency check (smoke showed 1.256->1.031; is the direction stable?)
    print("\n=== SWING FULL-WINDOW CONSISTENCY (vs smoke) ===")
    for uni, oh in (("pinned", pinned), ("corrected", corrected)):
        r, led = swing_book(oh, mem, start)
        r = r[r.index <= end]
        led = led[pd.to_datetime(led["entry_date"]) <= end] if len(led) else led
        m = metrics(r)
        rep.setdefault("swing", {})[uni] = {**m, "n_trades": len(led)}
        print(f"  swing base / {uni}: sharpe {m['sharpe']} cagr {m['cagr_%']} maxdd {m['maxdd_%']} "
              f"({len(led)} trades)")

    rep["recovered_in_book_b"] = {
        "n_trades": int(len(rec_tr)), "n_trades_total": int(len(tr_b)),
        "name_weeks": round(float(rec_tr["days_held"].sum()) / 5, 0) if len(rec_tr) else 0,
        "by_name": (by.to_dict("index") if len(rec_tr) else {})}
    out = ROOT / "diagnostics" / "research" / "lh_solvency_bracket.json"
    out.write_text(json.dumps(rep, indent=2, default=float), encoding="utf-8")
    print(f"\nreport -> {out.relative_to(ROOT)}")
    return 0


def resolved(start: str, end: str, stamp: str) -> int:
    """Phase-4: the bracket resolved to a POINT ESTIMATE. The gate now judges the recovered names
    on their real balance sheets instead of on absence — no waiver anywhere in this function."""
    print(f"=== corrected anchor, fundamentals RESOLVED [window {start}..{end}] ===")
    pinned = load_ohlcv_cache(OHLCV_CACHE)
    corrected = corrected_universe()
    base = load_fund_store()
    bf = ROOT / "data" / f"fundamentals_pit_backfill_{stamp}.pkl"
    s_alias = resolved_store(base, None, alias_aware=True)
    s_full = resolved_store(base, bf, alias_aware=True)
    print(f"fund store: base {len(base)} | +alias-aware {len(s_alias)} | +backfill {len(s_full)} "
          f"(backfill artifact: {bf.name if bf.exists() else 'MISSING'})")

    arms = {}
    for name, oh, st in (("pinned (baseline_v1)", pinned, base),
                         ("corrected AS-IS", corrected, base),
                         ("corrected + alias-aware", corrected, s_alias),
                         ("corrected + alias + backfill", corrected, s_full)):
        r, tr = lh_book(oh, start, end, fund_store=st)
        arms[name] = (metrics(r), tr)
        print(f"  {name}: done ({len(tr)} trades)")

    t = pd.DataFrame([{"arm": k, **m} for k, (m, _) in arms.items()])
    print("\n=== RESOLVED ANCHOR TABLE (no waiver — real gate on real data) ===")
    print(t.drop(columns=["per_year_%"]).to_string(index=False))
    print("\nper-year:")
    for k, (m, _) in arms.items():
        print(f"  {k}: {m.get('per_year_%')}")

    m0 = arms["corrected AS-IS"][0]
    mf = arms["corrected + alias + backfill"][0]
    print(f"\nPOINT ESTIMATE  dSharpe {mf['sharpe']-m0['sharpe']:+.3f} | "
          f"dCAGR {mf['cagr_%']-m0['cagr_%']:+.2f}pp | dMaxDD {mf['maxdd_%']-m0['maxdd_%']:+.1f}pp"
          "   (retired bounds: +0.202 naive / +0.024 dedup)")

    # which recovered names now enter, and how the real gate judged them
    recovered = set(corrected) - set(pinned)
    tr_f = arms["corrected + alias + backfill"][1]
    rec_tr = tr_f[tr_f["ticker"].isin(recovered)] if len(tr_f) else tr_f
    print(f"\nrecovered names entering the book on REAL fundamentals: "
          f"{len(rec_tr)} trades of {len(tr_f)}")
    if len(rec_tr):
        by = rec_tr.groupby("ticker").agg(n=("ticker", "size"), days=("days_held", "sum"),
                                          pnl=("pnl", "sum")).sort_values("days", ascending=False)
        print(by.head(25).to_string())
    admitted = sorted(set(rec_tr["ticker"])) if len(rec_tr) else []
    have_de = {t_ for t_ in recovered
               if s_full.get(t_) is not None and len(s_full[t_])
               and "debt_equity" in s_full[t_].columns and s_full[t_]["debt_equity"].notna().any()}
    print(f"\nrecovered with D/E data after resolution: {len(have_de)} of {len(recovered)}")
    print(f"  of those, PASSED the gate into the book at least once: {len(admitted)}")
    print(f"  had data but the gate REJECTED them (levered/failed): "
          f"{len(have_de) - len(set(admitted) & have_de)}")

    rep = {"window": [start, end], "stamp": stamp,
           "arms": {k: m for k, (m, _) in arms.items()},
           "recovered_with_de": sorted(have_de), "recovered_admitted": admitted}
    out = ROOT / "diagnostics" / "research" / "lh_anchor_resolved.json"
    out.write_text(json.dumps(rep, indent=2, default=float), encoding="utf-8")
    print(f"\nreport -> {out.relative_to(ROOT)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="truncated window: plumbing proof only")
    ap.add_argument("--resolved", action="store_true",
                    help="Phase-4: real gate on backfilled + alias-aware fundamentals")
    ap.add_argument("--stamp", default="20260729", help="backfill artifact stamp")
    ap.add_argument("--bracket", action="store_true",
                    help="LH solvency-gate sensitivity bracket (full window, diagnostic)")
    a = ap.parse_args()
    start, end = ("2019-01-01", "2021-12-31") if a.smoke else ("2017-01-01", "2026-06-30")
    if a.bracket:
        return bracket(start, end)   # --bracket --smoke = cheap print-path exercise, not the answer
    if a.resolved:
        return resolved(start, end, a.stamp)
    tag = "SMOKE (truncated — NOT the record)" if a.smoke else "FULL (September's record)"
    print(f"=== corrected-universe anchor harness [{tag}] window {start}..{end} ===")
    mem = load_membership()
    pinned = load_ohlcv_cache(OHLCV_CACHE)
    corrected = corrected_universe()
    print(f"universes: pinned {len(pinned)} names | corrected {len(corrected)} names "
          f"(+{len(set(corrected) - set(pinned))} recovered)")

    rows = []
    for uni, oh in (("pinned", pinned), ("corrected", corrected)):
        r, _ = lh_book(oh, start, end)
        rows.append({"book": "LH base", "universe": uni, **metrics(r)})
        print(f"  LH base / {uni}: done")
    leds = {}
    for uni, oh in (("pinned", pinned), ("corrected", corrected)):
        r, led = swing_book(oh, mem, start)
        led = led[pd.to_datetime(led["entry_date"]) <= end] if len(led) else led
        r = r[r.index <= end]
        leds[uni] = led
        rows.append({"book": "swing base", "universe": uni, **metrics(r)})
        print(f"  swing base / {uni}: done ({len(led)} trades)")

    t = pd.DataFrame(rows)
    print("\n=== ANCHOR TABLE ===")
    print(t.drop(columns=["per_year_%"]).to_string(index=False))
    print("\nper-year:")
    for _, r0 in t.iterrows():
        print(f"  {r0['book']} / {r0['universe']}: {r0.get('per_year_%')}")

    # trade diff (swing): which trades exist only under the corrected universe (recovered names)
    if all(len(leds[u]) for u in leds):
        def keys(df):
            return set(zip(df["tkr"], pd.to_datetime(df["entry_date"]).dt.strftime("%G-%V")))
        only_corr = keys(leds["corrected"]) - keys(leds["pinned"])
        only_pin = keys(leds["pinned"]) - keys(leds["corrected"])
        rec_names = sorted({t_ for t_, _ in only_corr})
        print(f"\n=== TRADE DIFF (swing) ===")
        print(f"trades only in corrected: {len(only_corr)} | only in pinned: {len(only_pin)}")
        print(f"names driving the corrected-only trades (recovered/delisted + reshuffle): {rec_names[:20]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
