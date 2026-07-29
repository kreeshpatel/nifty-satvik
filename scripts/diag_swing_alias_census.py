"""Phase-2 swing-record alias census — READ-ONLY.

The certified 0094 record (1.132 Sharpe / 255 trades) was produced on the corrected universe, in
which every alias old-symbol is materialized as a pointer to its successor's series. Two questions:

  Q1 CONCURRENCY  Did any of the record's trades hold BOTH symbols of an alias pair at the same
                  time — one company occupying two of the book's slots?

  Q2 RE-CUT COST  Does the record reproduce if the alias old-symbols are dropped (the naive
                  "one series per company" re-cut)? Reports headline delta + trade diff, so the
                  September governance call on the pin can see what a re-cut would destroy.

Writes nothing but a report. Does NOT re-certify, does NOT touch the golden master, does NOT alter
any live artifact — the record of reference stays exactly as certified.

    python scripts/diag_swing_alias_census.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from nq.data.membership import load_membership  # noqa: E402
from run_bhanushali_path1 import corrected_universe  # noqa: E402
from run_bhanushali_weekly_rank import backtest as swing_backtest  # noqa: E402
from run_bhanushali_weekly_rank import prep_weekly_rank  # noqa: E402


def run(oh, mem):
    led: list = []
    m = swing_backtest(prep_weekly_rank(oh), mem, ledger=led)
    return m, pd.DataFrame(led)


def main() -> int:
    print("=== Phase-2 swing alias census (read-only) ===")
    mem = load_membership()
    amap = json.load(open(ROOT / "data" / "delisted_alias_map.json"))["aliases"]
    uni = corrected_universe()

    m_rec, led = run(uni, mem)
    print(f"record run: sharpe {m_rec['sharpe']:.3f} | trades {m_rec['trades']} | "
          f"cagr {m_rec['cagr']*100:.2f}%")

    # ---- Q1 concurrency -------------------------------------------------------------
    led["entry_date"] = pd.to_datetime(led["entry_date"])
    led["exit_date"] = pd.to_datetime(led["exit_date"])
    by_tkr = {t: g for t, g in led.groupby("tkr")}
    print("\n--- Q1 CONCURRENCY: alias pair held in two slots at once? ---")
    clashes = []
    for old, spec in amap.items():
        new = spec["to"]
        ga, gb = by_tkr.get(old), by_tkr.get(new)
        if ga is None or gb is None:
            continue
        for _, ra in ga.iterrows():
            for _, rb in gb.iterrows():
                s = max(ra["entry_date"], rb["entry_date"])
                e = min(ra["exit_date"], rb["exit_date"])
                if e > s:
                    clashes.append({"pair": f"{old}/{new}", "days": int((e - s).days),
                                    "a_entry": str(ra["entry_date"])[:10],
                                    "b_entry": str(rb["entry_date"])[:10]})
    both = [f"{o}/{s['to']}" for o, s in amap.items()
            if o in by_tkr and s["to"] in by_tkr]
    print(f"alias pairs where BOTH symbols traded at all (any time): {len(both)} {both}")
    print(f"CONCURRENT holdings of the same company: {len(clashes)}")
    for c in clashes:
        print(f"  CLASH {c['pair']}: {c['days']}d overlap ({c['a_entry']} vs {c['b_entry']})")
    if not clashes:
        print("  -> none. The record never held one company in two slots.")

    # ---- Q2 re-cut cost --------------------------------------------------------------
    print("\n--- Q2 RE-CUT: drop alias old-symbols (naive one-series-per-company) ---")
    recut = {t: df for t, df in uni.items() if t not in amap}
    print(f"universe {len(uni)} -> {len(recut)} names")
    m_cut, led_cut = run(recut, mem)
    print(f"re-cut run: sharpe {m_cut['sharpe']:.3f} | trades {m_cut['trades']} | "
          f"cagr {m_cut['cagr']*100:.2f}%")
    print(f"DELTA vs record: dSharpe {m_cut['sharpe']-m_rec['sharpe']:+.3f} | "
          f"dCAGR {(m_cut['cagr']-m_rec['cagr'])*100:+.2f}pp | "
          f"dtrades {m_cut['trades']-m_rec['trades']:+d}")

    def keys(df):
        return set(zip(df["tkr"], pd.to_datetime(df["entry_date"]).dt.strftime("%G-%V")))
    lost = keys(led) - keys(led_cut)
    gained = keys(led_cut) - keys(led)
    print(f"trades LOST by the re-cut: {len(lost)} | gained: {len(gained)}")
    lost_alias = sorted({t for t, _ in lost if t in amap})
    print(f"  lost trades that are alias old-symbols (legitimate PIT history under the old name): "
          f"{len([1 for t, _ in lost if t in amap])} across {lost_alias}")

    rep = {"record": {"sharpe": round(float(m_rec["sharpe"]), 4), "trades": int(m_rec["trades"]),
                      "cagr_pct": round(float(m_rec["cagr"]) * 100, 3)},
           "recut": {"sharpe": round(float(m_cut["sharpe"]), 4), "trades": int(m_cut["trades"]),
                     "cagr_pct": round(float(m_cut["cagr"]) * 100, 3), "names": len(recut)},
           "concurrency": {"pairs_both_traded": both, "clashes": clashes},
           "trade_diff": {"lost": len(lost), "gained": len(gained),
                          "lost_alias_symbols": lost_alias}}
    out = ROOT / "diagnostics" / "research" / "swing_alias_census.json"
    out.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    print(f"\nreport -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
