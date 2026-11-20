"""Forward paper record of the 60/40 benchmark. No capital, no trading. It is the benchmark the company engine
must beat after tax (pre-registration 0153 d/f).

BOOK
- 60% index fund: Tata Nifty Midcap 150 Momentum 50 Index Fund, Direct Growth, AMFI 150738.
- 40% arbitrage fund: Kotak Arbitrage Fund, Direct Growth, AMFI 119771 (one of the two arbitrage funds PR #214
  used).
- Notional Rs 20,00,000, bought at the first record's NAVs.
- Rebalance to 60/40 only when the index-fund weight drifts more than 5pp from 60% at a weekly record.

NAVS
- Source: api.mfapi.in/mf/<code>, a mirror of AMFI's daily NAV history.
- Each record uses each fund's last NAV dated on or before the record Friday.
- Status STALE if either NAV is more than 3 calendar days old; otherwise OK.

TAX
- Engine: PR #212's lot engine (forward/benchmark_60_40/taxlots.py, verbatim), for an individual at the 30% slab,
  with no harvesting.
- Both funds are equity-oriented. A financial year's realised gains are settled at its end (31 March), and tax is
  paid from the book's cash.
- After-tax NAV = what the book would hold after selling everything at this week's NAVs and paying the tax due.
- Pre-tax NAV = mark-to-market value, after trading costs and taxes already paid.

RECORD
- forward/benchmark_60_40/ledger.jsonl is append-only. Each row stores its inputs (NAVs and dates), its outputs, an
  as-of timestamp and `prev_sha`, the SHA-256 of every byte of the ledger before the row.
- The book is rebuilt each week by replaying the stored NAVs, so the record is deterministic.
- A history that has been altered fails `verify()`, and nothing is appended to it.

    python forward/benchmark_60_40/record.py [--asof YYYY-MM-DD] [--dry-run]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import taxlots as T  # noqa: E402

LEDGER = HERE / "ledger.jsonl"
CODES = {T.IDX: 150738, T.ARB: 119771}
TARGET = {T.IDX: 0.60, T.ARB: 0.40}
CAPITAL = 2_000_000.0
DRIFT_PP = 0.05
STALE_DAYS = 3
FIRST_FRIDAY = "2026-11-27"   # the first Friday after the Phase 0 merges (#217 and #218, 2026-11-21)
SLAB = 0.30


class LedgerTampered(RuntimeError):
    pass


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def read(path: Path = LEDGER) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def verify(path: Path = LEDGER) -> list[dict]:
    """Raise LedgerTampered unless every row's prev_sha matches the bytes before it."""
    if not path.exists():
        return []
    raw = path.read_bytes()
    rows, pos = [], 0
    for line in raw.splitlines(keepends=True):
        if not line.strip():
            pos += len(line)
            continue
        r = json.loads(line)
        if r.get("prev_sha") != _sha(raw[:pos]):
            raise LedgerTampered(f"row week {r.get('week')} ({r.get('friday')}): history before it was changed")
        rows.append(r)
        pos += len(line)
    return rows


def replay(rows: list[dict]) -> tuple[T.Taxpayer | None, list[bool]]:
    """Rebuild the book from stored NAVs. Returns the taxpayer state after the last row and the per-row rebalance flags."""
    if not rows:
        return None, []
    cfg = T.load_cfg()
    tp = T.Taxpayer(cfg, kind="individual", slab=SLAB, harvest=False)
    tp.cash = CAPITAL
    flags, prev = [], None
    for r in rows:
        d = pd.Timestamp(r["friday"])
        px = {T.IDX: r["nav_index"], T.ARB: r["nav_arbitrage"]}
        if prev is not None and T.fy_of(d) != T.fy_of(prev):
            tp.settle(pd.Timestamp(f"{T.fy_of(prev)}-03-31"))
        if prev is None:
            tp.retarget({k: CAPITAL * w for k, w in TARGET.items()}, px, d)
            flags.append(True)
        else:
            v = tp.value(px)
            w_idx = tp.units[T.IDX] * px[T.IDX] / v if v > 0 else 0.0
            reb = abs(w_idx - TARGET[T.IDX]) > DRIFT_PP
            if reb:
                tp.retarget({k: v * w for k, w in TARGET.items()}, px, d)
            flags.append(reb)
        prev = d
    return tp, flags


def navs_from_rows(tp: T.Taxpayer, row: dict) -> tuple[float, float, float]:
    px = {T.IDX: row["nav_index"], T.ARB: row["nav_arbitrage"]}
    pre = tp.value(px)
    liq = copy.deepcopy(tp)
    for i in sorted(TARGET):
        liq.sell(i, liq.units[i] * px[i], px[i], pd.Timestamp(row["friday"]))
    liq.settle(pd.Timestamp(row["friday"]))
    w_idx = tp.units[T.IDX] * px[T.IDX] / pre if pre > 0 else float("nan")
    return round(pre, 2), round(liq.cash, 2), round(w_idx, 6)


def fetch_nav(code: int):
    import requests
    j = requests.get(f"https://api.mfapi.in/mf/{code}", timeout=60).json()
    s = pd.DataFrame(j["data"])
    s["date"] = pd.to_datetime(s["date"], format="%d-%m-%Y")
    return s.assign(nav=s["nav"].astype(float)).set_index("date")["nav"].sort_index()


def build_row(rows: list[dict], friday: pd.Timestamp, navs: dict) -> dict:
    """navs: {T.IDX: Series, T.ARB: Series} indexed by NAV date."""
    got = {}
    for k, s in navs.items():
        s = s[s.index <= friday]
        got[k] = (float(s.iloc[-1]), s.index[-1])
    stale = any((friday - dt).days > STALE_DAYS for _, dt in got.values())
    row = {"week": len(rows) + 1, "friday": str(friday.date()),
           "nav_index": got[T.IDX][0], "nav_index_date": str(got[T.IDX][1].date()),
           "nav_arbitrage": got[T.ARB][0], "nav_arbitrage_date": str(got[T.ARB][1].date()),
           "scheme_codes": {"index": CODES[T.IDX], "arbitrage": CODES[T.ARB]}}
    tp, flags = replay(rows + [row])
    pre, after, w = navs_from_rows(tp, row)
    row.update(pre_tax_nav=pre, after_tax_nav=after, index_weight=w, rebalanced=flags[-1],
               status="STALE" if stale else "OK",
               recorded_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    return row


def append(row: dict, path: Path = LEDGER) -> dict:
    rows = verify(path)
    if rows and pd.Timestamp(row["friday"]) <= pd.Timestamp(rows[-1]["friday"]):
        raise ValueError(f"append-only: {row['friday']} is not after the last record {rows[-1]['friday']}")
    raw = path.read_bytes() if path.exists() else b""
    row = dict(row, prev_sha=_sha(raw))
    with path.open("ab") as fh:
        fh.write((json.dumps(row, sort_keys=True) + "\n").encode("utf-8"))
    return row


def health_line(path: Path = LEDGER) -> str:
    try:
        rows = verify(path)
    except LedgerTampered as e:
        return f"60/40 forward record: LEDGER TAMPERED ({e})"
    if not rows:
        return f"60/40 forward record: not started (first record {FIRST_FRIDAY})"
    r = rows[-1]
    return (f"60/40 forward record: week {r['week']}, pre-tax NAV Rs {r['pre_tax_nav']:,.0f}, "
            f"after-tax NAV Rs {r['after_tax_nav']:,.0f}, status {r['status']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    today = pd.Timestamp(a.asof) if a.asof else pd.Timestamp.today().normalize()
    friday = today - pd.Timedelta(days=(today.weekday() - 4) % 7)
    if not a.dry_run and friday < pd.Timestamp(FIRST_FRIDAY):
        print(f"not started: first record is {FIRST_FRIDAY}")
        return 0
    rows = verify()
    navs = {k: fetch_nav(c) for k, c in CODES.items()}
    row = build_row(rows if not a.dry_run else [], friday, navs)
    if a.dry_run:
        print(json.dumps(row, indent=1))
        return 0
    if rows and rows[-1]["friday"] == row["friday"]:
        print(f"already recorded {row['friday']}")
        return 0
    print(json.dumps(append(row), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
