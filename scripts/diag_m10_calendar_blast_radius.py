"""M10 blast radius — what the corrected NSE calendar actually moves, measured with a control.

The 2026 holiday block was wrong in both directions (see ``scripts/build_nse_holidays.py``). The
calendar's only research-path use is the phantom-bar drop in ``clean_ohlcv_for_features``, so the
exposure is asymmetric and can be reasoned about exactly before it is measured:

* **Spurious holidays destroy real data.** 2026-02-17 / 03-20 / 03-30 each carry **710 real,
  positive-volume bars** in the pinned dataset. The cleaner was deleting all 2,130 of them.
* **Missing holidays are already covered.** 2026-01-15 carries 614 bars, and all 614 are
  zero-volume-flat placeholders that the cleaner's *second* filter drops regardless. 2026-03-26
  and 2026-03-31 carry no bars at all. So this direction moves nothing.

That predicts a one-directional effect on the LH momentum book, confined to Feb-Jun 2026, and no
effect at all on the swing book (``corrected_universe()`` never calls the cleaner) or on the
2017-2019 golden master (entirely below ``NSE_HOLIDAYS_COVERED_FROM``).

This script tests the prediction rather than asserting it: it runs the LH base arm **twice in one
process** — once with the old committed calendar monkeypatched back in, once with the corrected
one — so the two numbers differ in the calendar and nothing else.

    python scripts/diag_m10_calendar_blast_radius.py

Writes ``diagnostics/research/foundation_audit_2026Q3/m10_blast_radius.json``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))

import nq.data.features as feat_mod  # noqa: E402
import nq.data.ohlcv as ohlcv_mod  # noqa: E402
from config import NSE_HOLIDAYS  # noqa: E402
from nq.data.ohlcv import OHLCV_CACHE, load_ohlcv_cache  # noqa: E402
from run_corrected_anchor import lh_book, metrics  # noqa: E402

OUT = ROOT / "diagnostics" / "research" / "foundation_audit_2026Q3" / "m10_blast_radius.json"

# The calendar exactly as committed before 2026-08-06, reconstructed from the corrected set so the
# control is the real "before" and not a paraphrase of it.
SPURIOUS = {"2026-02-17", "2026-03-20", "2026-03-30", "2026-08-17",
            "2026-09-04", "2026-10-12", "2026-10-26", "2026-11-16"}
RESTORED = {"2026-01-15", "2026-01-26", "2026-02-15", "2026-03-03", "2026-03-21", "2026-03-26",
            "2026-03-31", "2026-09-14", "2026-10-20", "2026-11-08", "2026-11-10", "2026-11-24"}
OLD_2026_KEPT = {"2026-01-26", "2026-03-03", "2026-04-03", "2026-04-14", "2026-05-01",
                 "2026-05-28", "2026-06-26", "2026-08-15", "2026-10-02", "2026-12-25"}
OLD_CALENDAR = ({d for d in NSE_HOLIDAYS if not d.startswith("2026")} | SPURIOUS | OLD_2026_KEPT)


def _run(ohlcv, calendar: set[str]) -> tuple[pd.Series, pd.DataFrame]:
    """Run the LH base arm with `calendar` in force, restoring the real one afterwards.

    Both modules bind ``NSE_HOLIDAYS`` at import into their own namespace and read it at call
    time, so patching both namespaces is what actually swaps the calendar for a run.
    """
    saved = (ohlcv_mod.NSE_HOLIDAYS, feat_mod.NSE_HOLIDAYS)
    ohlcv_mod.NSE_HOLIDAYS = feat_mod.NSE_HOLIDAYS = set(calendar)
    try:
        return lh_book(ohlcv, start="2017-01-01", end="2026-06-30")
    finally:
        ohlcv_mod.NSE_HOLIDAYS, feat_mod.NSE_HOLIDAYS = saved


def main() -> int:
    ohlcv = load_ohlcv_cache(OHLCV_CACHE)
    print(f"pinned universe: {len(ohlcv)} names\n")

    print("arm 1/2 — OLD calendar (the control)...")
    r_old, t_old = _run(ohlcv, OLD_CALENDAR)
    print("arm 2/2 — CORRECTED calendar...")
    r_new, t_new = _run(ohlcv, set(NSE_HOLIDAYS))

    m_old, m_new = metrics(r_old), metrics(r_new)
    rows = [("sharpe", m_old["sharpe"], m_new["sharpe"]),
            ("cagr_%", m_old["cagr_%"], m_new["cagr_%"]),
            ("maxdd_%", m_old["maxdd_%"], m_new["maxdd_%"]),
            ("n_trades", len(t_old), len(t_new)),
            ("n_return_bars", len(r_old.dropna()), len(r_new.dropna()))]
    print(f"\n{'metric':<16}{'old':>12}{'corrected':>12}{'delta':>12}")
    for k, a, b in rows:
        print(f"{k:<16}{a:>12}{b:>12}{round(b - a, 4):>12}")

    # Where the two curves first part company: the prediction is Feb-2026, not earlier.
    common = r_old.index.intersection(r_new.index)
    diff = (r_new.reindex(common) - r_old.reindex(common)).abs()
    first = diff[diff > 1e-12].index.min() if (diff > 1e-12).any() else None
    print(f"\nfirst divergent session: {first}   "
          f"(divergent sessions: {int((diff > 1e-12).sum())} of {len(common)})")

    payload = {
        "generated": "2026-08-06", "item": "M10", "class": "measurement / verification",
        "control": "same process, same data, calendar swapped in nq.data.ohlcv + nq.data.features",
        "window": "2017-01-01..2026-06-30", "universe": "pinned (data/ohlcv.pkl, f8625a8f)",
        "old_calendar": {"sharpe": m_old["sharpe"], "cagr_pct": m_old["cagr_%"],
                         "maxdd_pct": m_old["maxdd_%"], "n_trades": len(t_old),
                         "per_year_pct": m_old["per_year_%"]},
        "corrected_calendar": {"sharpe": m_new["sharpe"], "cagr_pct": m_new["cagr_%"],
                               "maxdd_pct": m_new["maxdd_%"], "n_trades": len(t_new),
                               "per_year_pct": m_new["per_year_%"]},
        "delta": {"sharpe": round(m_new["sharpe"] - m_old["sharpe"], 4),
                  "cagr_pp": round(m_new["cagr_%"] - m_old["cagr_%"], 4),
                  "maxdd_pp": round(m_new["maxdd_%"] - m_old["maxdd_%"], 4),
                  "n_trades": len(t_new) - len(t_old)},
        "first_divergent_session": (None if first is None else str(pd.Timestamp(first).date())),
        "divergent_sessions": int((diff > 1e-12).sum()), "common_sessions": int(len(common)),
        "unaffected_by_construction": {
            "swing book": "corrected_universe() never calls the cleaner; the 1.132/255 "
                          "determinism guard reproduces byte-identically",
            "stage2 golden master": "runs 2017-01-01..2019-12-31, entirely below "
                                    "NSE_HOLIDAYS_COVERED_FROM (2025-01-01)",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
