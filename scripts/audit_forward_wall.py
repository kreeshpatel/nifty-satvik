"""Forward-wall audit — September runs this against the LIVE logs for the Oct-1 review.
THIS session it is built and tested on synthetic fixtures ONLY (no-peeking holds): every path is a
required explicit argument; there are NO defaults pointing at the live wall.

Checks (per the governance brief):
  1. hash-chain verification (nq.paper.forward_wall.verify_chain) with first-bad-row reporting;
  2. per-book closed-trade counts vs the >=30-trade paper gate (forward/prereg.md);
  3. mechanical-halt event listing (status == 'halt' rows + any book equity <= 50% of its running peak);
  4. watched-sleeve log completeness (expected trading days vs logged points, gap listing);
  5. config-drift check: every frozen key=value the caller supplies must appear verbatim in the
     pre-registration document.

    python scripts/audit_forward_wall.py --chain-log X --trades-json Y --sleeve-json Z --prereg P
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from nq.paper.forward_wall import BOOKS, verify_chain  # noqa: E402

PAPER_GATE_TRADES = 30
HALT_DD = 0.50


def audit_chain(path: Path) -> dict:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ok, bad = verify_chain(rows)
    out = {"rows": len(rows), "chain_ok": ok, "first_bad_row": bad,
           "gap_rows": sum(1 for r in rows if r.get("status") == "gap"),
           "date_span": [rows[0]["date"], rows[-1]["date"]] if rows else None}
    # halt events: explicit status, plus mechanical 50% breach per book
    halts = [{"date": r["date"], "kind": "status"} for r in rows if r.get("status") == "halt"]
    for b in BOOKS:
        peak = 0.0
        for r in rows:
            try:
                eq = float(r.get(f"{b}_equity") or 0)
            except ValueError:
                continue
            peak = max(peak, eq)
            if peak > 0 and eq <= peak * (1 - HALT_DD):
                halts.append({"date": r["date"], "kind": f"{b} equity -50% breach"})
                break
    out["halt_events"] = halts
    return out


def audit_trades(path: Path) -> dict:
    t = json.loads(Path(path).read_text())
    out = {}
    for book, trades in t.items():
        n = len(trades)
        out[book] = {"closed_trades": n, "paper_gate_30": "PASS" if n >= PAPER_GATE_TRADES
                     else f"NOT MET ({n}/{PAPER_GATE_TRADES})"}
    return out


def audit_sleeve(path: Path) -> dict:
    s = json.loads(Path(path).read_text())
    pts = s.get("points", [])
    dates = pd.to_datetime(pd.Series([p["date"] for p in pts])) if pts else pd.Series(dtype="datetime64[ns]")
    out = {"model": s.get("model"), "inception": s.get("inception"), "n_points": len(pts)}
    if len(dates):
        expected = pd.bdate_range(dates.min(), dates.max())
        missing = sorted(set(expected) - set(dates))
        out["expected_sessions"] = len(expected)
        out["missing_sessions"] = [str(d.date()) for d in missing]
        out["complete"] = not missing
    else:
        out["complete"] = False
        out["note"] = "no logged points (valid pre-inception; incomplete otherwise)"
    return out


def audit_config_drift(prereg: Path, frozen: dict[str, str]) -> dict:
    text = Path(prereg).read_text(encoding="utf-8")
    missing = {k: v for k, v in frozen.items() if v not in text}
    return {"frozen_keys_checked": len(frozen), "missing_or_drifted": missing,
            "ok": not missing}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chain-log", required=True)
    ap.add_argument("--trades-json", required=True)
    ap.add_argument("--sleeve-json", required=True)
    ap.add_argument("--prereg", required=True)
    ap.add_argument("--frozen-json", required=False,
                    help="JSON dict of frozen key->verbatim-string checks for the drift audit")
    a = ap.parse_args()
    frozen = json.loads(Path(a.frozen_json).read_text()) if a.frozen_json else {}
    rep = {"chain": audit_chain(Path(a.chain_log)),
           "paper_gate": audit_trades(Path(a.trades_json)),
           "sleeve": audit_sleeve(Path(a.sleeve_json)),
           "config_drift": audit_config_drift(Path(a.prereg), frozen)}
    print(json.dumps(rep, indent=2, default=str))
    ok = (rep["chain"]["chain_ok"] and rep["config_drift"]["ok"])
    print(f"\nAUDIT {'CLEAN' if ok else 'FINDINGS PRESENT'} (gates/sleeve statuses above are "
          f"review inputs, not pass/fail here)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
