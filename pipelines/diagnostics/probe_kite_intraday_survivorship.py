"""PROBE (no trial, no data stored): can Kite serve intraday history for DELISTED names?

This one question decides whether the intraday store is worth building. Kite's instrument dump lists
**currently tradable** instruments. If a name that delisted in 2019 has no retrievable endpoint, then
an intraday store assembled from Kite is **survivor-only by construction** — and worse than the daily
pin, which at least admitted a bhavcopy backfill (103/813 members recovered). Every number built on a
survivor-only store flatters in exactly the direction this programme has already been burned by:
finding 0025 measured the bias and found it scales with holding period, and study 0001 caught a leak
only because a -19.56% drawdown contradicted the published band.

So: probe before building. Minutes of work; decides whether the project is an hour or dead on arrival.

WHAT IT DOES NOT DO. It stores no market data, writes no cache, and never prints or persists a
credential. It reports availability only.

CREDENTIALS come from the environment, matching the repo's existing convention
(`dashboard/backend/routers/kite.py:50`, `refresh_kite_session.py:76`)::

    KITE_API_KEY        your app's API key
    KITE_ACCESS_TOKEN   a live access token (refresh_kite_session.py mints one)

Run it in an interactive session where those are set. Nothing here should ever be committed with a
credential in it, and nothing here reads one from a file.

    python pipelines/diagnostics/probe_kite_intraday_survivorship.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "diagnostics" / "research" / "kite_intraday_probe.json"

# Names known to have left the index during 2017-2026, with a date they were demonstrably trading.
# Sourced from the delisted backfill the daily store already needed
# (research/findings/0025, data/delisted_alias_map.json).
DELISTED = {
    "DHFL": "2019-06-03",          # Piramal resolution completed 2021-06-11
    "JETAIRWAYS": "2018-09-03",    # grounded April 2019
    "ALBK": "2019-03-01",          # PSU amalgamation 2020-03-19
    "LAKSHVILAS": "2020-03-02",    # DBS takeover 2020-11-25
    "INFRATEL": "2019-06-03",      # merged into INDUSTOWER
}
CONTROL = {"RELIANCE": "2019-06-03"}   # still listed — proves the credential path works
INTERVAL = "15minute"
WINDOW_DAYS = 5


def probe(kite, instruments: dict, symbol: str, when: str) -> dict:
    """Availability only — bar count and span, never the bars themselves."""
    token = instruments.get(symbol)
    if token is None:
        return {"symbol": symbol, "instrument_token": None, "verdict": "NOT IN INSTRUMENT DUMP",
                "detail": "Kite lists currently tradable instruments; a delisted name may be absent."}
    start = dt.date.fromisoformat(when)
    try:
        bars = kite.historical_data(token, start, start + dt.timedelta(days=WINDOW_DAYS), INTERVAL)
    except Exception as exc:                                    # noqa: BLE001 — report, never raise
        return {"symbol": symbol, "instrument_token": token, "verdict": "REQUEST FAILED",
                "detail": f"{type(exc).__name__}: {str(exc)[:160]}"}
    if not bars:
        return {"symbol": symbol, "instrument_token": token, "verdict": "EMPTY",
                "detail": f"token resolved but no {INTERVAL} bars around {when}"}
    return {"symbol": symbol, "instrument_token": token, "verdict": "AVAILABLE",
            "n_bars": len(bars),
            "first": str(bars[0]["date"])[:19], "last": str(bars[-1]["date"])[:19]}


def main() -> int:
    api_key = os.getenv("KITE_API_KEY", "").strip().strip("<>").strip()
    access_token = os.getenv("KITE_ACCESS_TOKEN", "").strip().strip("<>").strip()
    if not api_key or not access_token:
        print("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in the environment.")
        print("This probe never reads a credential from a file and never prints one.")
        return 2

    from kiteconnect import KiteConnect                          # noqa: PLC0415 — optional dep

    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)

    print("fetching the NSE instrument dump ...", flush=True)
    dump = kite.instruments("NSE")
    instruments = {row["tradingsymbol"]: row["instrument_token"] for row in dump}
    print(f"  {len(instruments):,} currently listed NSE instruments\n", flush=True)

    results = {"control": [probe(kite, instruments, s, d) for s, d in CONTROL.items()],
               "delisted": [probe(kite, instruments, s, d) for s, d in DELISTED.items()]}

    for group, rows in results.items():
        print(f"{group.upper()}")
        for r in rows:
            extra = (f"{r.get('n_bars')} bars {r.get('first')} .. {r.get('last')}"
                     if r["verdict"] == "AVAILABLE" else r.get("detail", ""))
            print(f"  {r['symbol']:<12s} {r['verdict']:<22s} {extra}")
        print()

    ctrl_ok = all(r["verdict"] == "AVAILABLE" for r in results["control"])
    n_ok = sum(1 for r in results["delisted"] if r["verdict"] == "AVAILABLE")
    n = len(results["delisted"])

    if not ctrl_ok:
        verdict = ("INCONCLUSIVE — the control name failed, so this measures the credential path, "
                   "not Kite's coverage. Fix the token and re-run.")
    elif n_ok == 0:
        verdict = ("DEAD ON ARRIVAL — Kite serves no delisted name. An intraday store from this "
                   "source is survivor-only BY CONSTRUCTION, which is worse than the daily pin. "
                   "Either find a source that carries delisted intraday (TickData is the candidate) "
                   "or abandon the intraday direction.")
    elif n_ok < n:
        verdict = (f"PARTIAL — {n_ok} of {n} delisted names available. Quantify the gap against the "
                   f"PIT membership list before building; a partial delisted tail is still a "
                   f"measurable bias, not an unknown one.")
    else:
        verdict = (f"CLEAR — all {n} delisted names served. Survivorship is not a structural blocker; "
                   f"proceed to scope the universe and build, with the coverage/PIT audit first.")

    payload = {"_doc": "PROBE. No trial, no data stored, no credential persisted.",
               "reproduce": "python pipelines/diagnostics/probe_kite_intraday_survivorship.py",
               "interval": INTERVAL, "window_days": WINDOW_DAYS,
               "n_listed_instruments": len(instruments),
               "results": results, "verdict": verdict}
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"VERDICT: {verdict}\n\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
