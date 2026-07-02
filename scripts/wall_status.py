"""Read-only forward-wall status — verify the hash chain and print the three books' NAV/drawdown.

    python scripts/wall_status.py [--state-dir results]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import RESULTS_DIR  # noqa: E402
from nq.paper.forward_wall import IntegrityError, read_verified  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify + summarize the forward-wall log")
    ap.add_argument("--state-dir", default=str(RESULTS_DIR))
    args = ap.parse_args(argv)
    path = Path(args.state_dir) / "forward_wall.csv"
    if not path.exists():
        print(f"no wall log at {path} (not started yet)")
        return 0
    try:
        rows = read_verified(path)                     # re-hashes the whole chain; raises on tamper
    except IntegrityError as e:
        print(f"CHAIN BROKEN — {e}")
        return 1
    ok = [r for r in rows if r["status"] == "ok"]
    print(f"wall VERIFIED: {len(rows)} rows ({len(ok)} ok / {len(rows) - len(ok)} gap), "
          f"{rows[0]['date']} .. {rows[-1]['date']}")
    for b in ("base", "veto", "drift"):
        eqs = [float(r[f"{b}_equity"]) for r in ok if r[f"{b}_equity"] != ""]
        if not eqs:
            continue
        peak, dd = eqs[0], 0.0
        for e in eqs:
            peak = max(peak, e)
            dd = min(dd, e / peak - 1.0)
        extra = f"  drift_mult {ok[-1]['drift_mult']}" if b == "drift" else ""
        print(f"  {b:<6} NAV {eqs[-1]:>13,.0f}  since-start {eqs[-1] / eqs[0] - 1:+.1%}  maxDD {dd * 100:.1f}%{extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
