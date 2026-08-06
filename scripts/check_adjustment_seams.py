"""Run the adjustment-monotonicity guard over a cache and report every seam.

    python scripts/check_adjustment_seams.py                 # the on-disk cache (data/ohlcv.pkl)
    python scripts/check_adjustment_seams.py --fresh         # a clean single-vintage vendor pull
    python scripts/check_adjustment_seams.py --json out.json

``--fresh`` matters because ``data/ohlcv.pkl`` is two different artifacts depending on where you
stand: on a research machine it is the pinned release ``dataset-pin-20260701``, while on the cron
runner it is an actions-cache instance rebuilt from the vendor on the first run of each month.
``--fresh`` reproduces the latter — one download call, one adjustment vintage — which is the only
way to ask "does the LIVE book carry this seam?" from here.

Exit code is 1 when the guard is RED (a seam not on the register), 0 otherwise, so this is usable
as a CI or cron step.
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


def main(argv: list[str]) -> int:
    from nq.data.adjustment_guard import check_adjustment_monotonicity, load_reference

    if "--fresh" in argv:
        from nq.data.ohlcv import download_ohlcv
        ref = load_reference()
        syms = sorted(set(ref["symbol"]))
        print(f"fresh single-vintage pull of {len(syms)} symbols (this is what a cold live "
              f"rebuild produces) ...", flush=True)
        ohlcv = download_ohlcv(syms, start="2017-01-01")
        label = "fresh vendor pull"
    else:
        ohlcv = pickle.load(open(ROOT / "data" / "ohlcv.pkl", "rb"))
        label = "data/ohlcv.pkl as on disk"

    rep = check_adjustment_monotonicity(ohlcv)
    d = rep.as_dict()
    print(f"\n=== adjustment guard: {label} ===")
    print(f"overall {d['overall']} | symbols checked {d['symbols_checked']} | "
          f"probe dates {d['probe_dates']} | seams {d['n_seams']} "
          f"(new {d['n_new_seams']}) | indeterminate {d['n_indeterminate']}")
    for s in sorted(d["seams"], key=lambda r: (r["window_end"], r["symbol"])):
        flag = "NEW " if not s["known"] else "    "
        print(f" {flag}{s['symbol']:<12}{s['window_start']}..{s['window_end']}  "
              f"x{s['step_factor']:<8.4f} adj {s['adj_before']:.6f} -> {s['adj_after']:.6f}  "
              f"{s.get('provenance', '')}  {s.get('cause', '')}")
    if d["n_indeterminate"]:
        print(f"\n indeterminate ({d['n_indeterminate']}): "
              f"{[r.get('symbol') for r in d['indeterminate'][:8]]}")

    if "--json" in argv:
        out = Path(argv[argv.index("--json") + 1])
        out.write_text(json.dumps({"cache": label, **d}, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {out}")
    return 1 if d["overall"] == "RED" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
