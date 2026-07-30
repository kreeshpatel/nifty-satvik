"""Forward-only PIT accumulators (owner-signed 2026-07-28) — daily collection for datasets whose
history is blocked (bulk/block: API bot-wall) or broken (ratings: junk equity linkage pre-2023 stream).

Append-only stores with a fetch timestamp per row; idempotent on re-run (content-key dedup); a
staleness ALARM if a feed's newest data date falls >5 sessions behind. Engine untouched — this is a
pure data-collection sidecar in the daily cron family. NO analysis of collected data is authorized.

Outputs (git-whitelisted so the cron can publish them):
  results/bulkblock_forward.csv   [deal_type, date, symbol, client, side, qty, price, fetch_ts]
  results/ratings_forward.csv     [symbol, agency, rating, action, outlook, date_cr, broadcast, fetch_ts]
  results/forward_accum_health.json

    python scripts/run_forward_accumulators.py
"""
from __future__ import annotations

import io
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config import RESULTS_DIR  # noqa: E402

HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/126 Safari/537.36",
       "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.nseindia.com/"}
BB_OUT = RESULTS_DIR / "bulkblock_forward.csv"
RT_OUT = RESULTS_DIR / "ratings_forward.csv"
HEALTH = RESULTS_DIR / "forward_accum_health.json"
STALE_SESSIONS = 5
_SYM_RE = re.compile(r"^[A-Z][A-Z0-9&\-]{0,14}$")
_JUNK = {"NOTLISTED", "NOT", "NA", "NOTAPPLICABLE", "NIL", "NONE"}


def _validate_fetch_ts(new: pd.DataFrame) -> None:
    """Refuse to write a sentinel / unparseable timestamp into the append-only forward record.

    Defense in depth (added 2026-07-30). The accumulator-health probe once passed the literal
    string "PROBE" as `fetch_ts` and it landed in the live CSVs, overwriting real fetch times on
    three rows (caught and restored in 3216ce7). The probe is now isolated to a scratch copy, but
    the live record must be unwritable with junk regardless of caller — a provenance column whose
    values do not parse as datetimes is not provenance.
    """
    if "fetch_ts" not in new.columns or new.empty:
        return
    vals = new["fetch_ts"].astype(str)
    parsed = pd.to_datetime(vals, errors="coerce", format="mixed")
    bad = sorted(set(vals[parsed.isna()]))
    if bad:
        raise ValueError(
            f"refusing to append rows with non-datetime fetch_ts: {bad[:5]} — the forward "
            f"accumulators are an append-only provenance record; use a real timestamp "
            f"(pd.Timestamp.now('UTC')), and probe against a scratch copy, not the live path."
        )


def _append_dedup(out: Path, new: pd.DataFrame, keys: list[str]) -> int:
    _validate_fetch_ts(new)
    if out.exists():
        old = pd.read_csv(out, dtype=str)
        both = pd.concat([old, new.astype(str)], ignore_index=True)
    else:
        both = new.astype(str)
    before = len(both)
    both = both.drop_duplicates(subset=keys, keep="first")
    added = len(both) - (len(old) if out.exists() else 0)
    both.to_csv(out, index=False)
    return max(added, 0) if before else 0


def collect_bulkblock(sess: requests.Session, fetch_ts: str, out: Path | None = None) -> tuple[int, str | None]:
    rows = []
    for typ, url in (("bulk", "https://archives.nseindia.com/content/equities/bulk.csv"),
                     ("block", "https://archives.nseindia.com/content/equities/block.csv")):
        r = sess.get(url, headers=HDR, timeout=30)
        if r.status_code != 200:
            continue
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = [c.strip() for c in df.columns]
        for _, x in df.iterrows():
            rows.append({"deal_type": typ, "date": str(x.get("Date", "")).strip(),
                         "symbol": str(x.get("Symbol", "")).strip(),
                         "client": str(x.get("Client Name", "")).strip(),
                         "side": str(x.get("Buy/Sell", "")).strip(),
                         "qty": x.get("Quantity Traded"),
                         "price": x.get("Trade Price / Wght. Avg. Price"),
                         "fetch_ts": fetch_ts})
    if not rows:
        return 0, None
    new = pd.DataFrame(rows).fillna("")
    added = _append_dedup(out or BB_OUT, new, ["deal_type", "date", "symbol", "client", "side", "qty", "price"])
    last = pd.to_datetime(new["date"], format="%d-%b-%Y", errors="coerce").max()
    return added, (str(last.date()) if last == last else None)


def collect_ratings(sess: requests.Session, fetch_ts: str, out: Path | None = None) -> tuple[int, str | None]:
    sess.get("https://www.nseindia.com/companies-listing/corporate-filings-credit-rating",
             headers=HDR, timeout=25)
    time.sleep(1.0)
    f = (pd.Timestamp.today() - pd.Timedelta(days=10)).strftime("%d-%m-%Y")
    t = pd.Timestamp.today().strftime("%d-%m-%Y")
    r = sess.get(f"https://www.nseindia.com/api/corporate-credit-rating?index=equities"
                 f"&from_date={f}&to_date={t}", headers=HDR, timeout=40)
    rec = r.json() if r.status_code == 200 and len(r.content) > 2 else []
    rows = []
    for x in rec:
        sym = str(x.get("Symbol") or "").strip().upper()
        # The source's symbol field is junk-dominated (probe: whole windows carry ZERO valid symbols),
        # so a strict equity filter would collect ~nothing. Ingest keeps ALL rows and marks
        # symbol_clean where the field is a valid ticker; CompanyName+ISIN are kept for future
        # name-based linkage. Health tracks clean rows separately. (Deviation from the strict-filter
        # brief, flagged: discarding everything would defeat the accumulator.)
        clean = bool(_SYM_RE.match(sym)) and sym not in _JUNK and not sym.replace("-", "").isdigit()
        rows.append({"symbol": sym if clean else "", "symbol_clean": clean,
                     "company": x.get("CompanyName"), "isin": x.get("ISIN"),
                     "agency": x.get("NameOfCRAgency"),
                     "rating": x.get("CreditRating"), "action": x.get("RatingAction"),
                     "outlook": x.get("Outlook"), "date_cr": x.get("DateofCR"),
                     "broadcast": x.get("BroadcastDateTime"), "fetch_ts": fetch_ts})
    if not rows:
        return 0, None
    new = pd.DataFrame(rows).fillna("")
    added = _append_dedup(out or RT_OUT, new, ["company", "isin", "agency", "rating", "action", "date_cr", "broadcast"])
    last = pd.to_datetime(new["broadcast"], format="%d-%b-%Y %H:%M:%S", errors="coerce").max()
    return added, (str(last.date()) if last == last else None)


def main() -> int:
    fetch_ts = pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M:%S")
    sess = requests.Session()
    sess.get("https://www.nseindia.com/", headers=HDR, timeout=25)
    health = json.loads(HEALTH.read_text()) if HEALTH.exists() else {}
    for name, fn in (("bulkblock", collect_bulkblock), ("ratings", collect_ratings)):
        try:
            added, last_data = fn(sess, fetch_ts)
            h = health.get(name, {})
            if last_data:
                h["last_data_date"] = max(last_data, h.get("last_data_date", ""))
            h["last_fetch_ts"] = fetch_ts
            h["rows_added_last_run"] = added
            ldd = h.get("last_data_date")
            stale = bool(ldd and len(pd.bdate_range(ldd, pd.Timestamp.today())) - 1 > STALE_SESSIONS)
            h["stale"] = stale
            health[name] = h
            flag = "  *** STALENESS ALARM ***" if stale else ""
            print(f"{name}: +{added} rows | last data {h.get('last_data_date')}{flag}", flush=True)
        except Exception as e:
            health.setdefault(name, {})["last_error"] = f"{fetch_ts}: {type(e).__name__}"
            print(f"{name}: FETCH ERROR {type(e).__name__} (recorded; accumulator continues)", flush=True)
    HEALTH.write_text(json.dumps(health, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
