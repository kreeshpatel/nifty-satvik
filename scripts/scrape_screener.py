"""Scrape Screener.in annual fundamentals → PIT D/E for delisted/historical names (Stage A).

The carried ``data/fundamentals_pit_screener.pkl`` covers only ~469 current names, so the ~213
delisted/historical index members are dropped by the solvency gate (0 D/E coverage) and the
survivorship correction is a no-op. This one-time, polite, cached scrape fills their D/E from
Screener company pages (which carry ~10-12 fiscal years), then MERGES into the store (never
clobbers the existing names). Owner-authorized deep-history augment (pre-reg 0017 lineage).

Polite by construction: real User-Agent, 2.5s + jitter spacing, bounded backoff, HTML cached per
ticker (re-runs/resume never re-hit the site). NOT a cron. Pure HTML→PIT-frame parsing is in
``nq.data.fundamentals.build_pit_frame_from_screener`` (hermetically tested). Usage:

    python scripts/scrape_screener.py --mode delisted --limit 5        # smoke
    python scripts/scrape_screener.py --mode delisted --out data/fundamentals_pit_screener.pkl
"""
from __future__ import annotations

import argparse
import collections
import io
import pickle
import random
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DATA_DIR  # noqa: E402
from nq.data.fundamentals import FUND_STORE_PATH, build_pit_frame_from_screener  # noqa: E402

BASE = "https://www.screener.in/company/{symbol}/{variant}"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
}
DEFAULT_CACHE = DATA_DIR / "_screener_cache"   # gitignored (/data/* ignore)


def _section_table(html: str, section_id: str, required_label: str):
    """Parse the table inside <section id="section_id"> containing a row labelled
    ``required_label``. Returns a DataFrame or None."""
    import pandas as pd
    start = html.find(f'id="{section_id}"')
    if start < 0:
        return None
    nxt = html.find("<section", start + 10)
    chunk = html[start: nxt if nxt > 0 else start + 60000]
    try:
        tables = pd.read_html(io.StringIO(chunk))
    except ValueError:
        return None
    want = required_label.replace("\xa0", "").replace("+", "").strip().lower()
    for t in tables:
        if t.shape[1] < 2:
            continue
        labels = {str(x).replace("\xa0", "").replace("+", "").strip().lower()
                  for x in t.iloc[:, 0].astype(str)}
        if want in labels:
            return t
    return None


def frame_from_html(html: str):
    """Annual P&L + Balance Sheet sections of a Screener page → PIT frame."""
    import pandas as pd
    pl = _section_table(html, "profit-loss", "EPS in Rs")
    if pl is None:                       # some pages label it 'Net Profit' only
        pl = _section_table(html, "profit-loss", "Net Profit")
    bs = _section_table(html, "balance-sheet", "Equity Capital")
    if pl is None and bs is None:
        return pd.DataFrame()
    return build_pit_frame_from_screener(pl, bs)


def _cache_path(cache_dir: Path, symbol: str, variant: str) -> Path:
    return cache_dir / f"{symbol}__{variant.strip('/').replace('/', '_') or 'standalone'}.html"


def fetch_html(symbol: str, *, cache_dir: Path, sleep: float, use_cache: bool = True,
               retries: int = 3) -> tuple[str | None, str]:
    """Fetch one company's Screener HTML (consolidated, fallback standalone), cached + polite.
    Returns (html_or_None, source ∈ {cache, consolidated, standalone, fail})."""
    import requests
    cache_dir.mkdir(parents=True, exist_ok=True)
    for variant_name, variant in (("consolidated", "consolidated/"), ("standalone", "")):
        cpath = _cache_path(cache_dir, symbol, variant)
        if use_cache and cpath.exists():
            html = cpath.read_text(encoding="utf-8", errors="replace")
            if "profit-loss" in html:
                return html, "cache"
        url = BASE.format(symbol=symbol, variant=variant)
        for attempt in range(retries):
            try:
                resp = requests.get(url, headers=HEADERS, timeout=30)
            except requests.RequestException:
                time.sleep((attempt + 1) * 2.0)
                continue
            if resp.status_code == 200 and "profit-loss" in resp.text:
                cpath.write_text(resp.text, encoding="utf-8")
                time.sleep(sleep + random.uniform(0.0, 1.0))
                return resp.text, variant_name
            if resp.status_code in (429, 403, 503):
                time.sleep((attempt + 1) * 5.0)
                continue
            break
        time.sleep(sleep + random.uniform(0.0, 1.0))
    return None, "fail"


def _targets(mode: str) -> list[str]:
    from config import NIFTY_500
    from scripts.run_cpcv import _recoverable_delisted
    if mode == "current":
        return list(NIFTY_500)
    if mode == "delisted":
        return sorted(_recoverable_delisted())
    if mode == "all":
        return sorted(set(NIFTY_500) | _recoverable_delisted())
    raise ValueError(f"unknown mode {mode!r} (current/delisted/all)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scrape_screener")
    ap.add_argument("--mode", choices=["delisted", "current", "all"], default="delisted")
    ap.add_argument("--out", default=str(FUND_STORE_PATH), help="merged store pickle")
    ap.add_argument("--cache-dir", default=str(DEFAULT_CACHE))
    ap.add_argument("--sleep", type=float, default=2.5)
    ap.add_argument("--limit", type=int, default=0, help="cap tickers (0=all; smoke)")
    ap.add_argument("--no-merge", action="store_true", help="write only newly-scraped (don't merge existing)")
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args(argv)

    targets = _targets(args.mode)
    if args.limit:
        targets = targets[: args.limit]
    cache_dir = Path(args.cache_dir)
    print(f"Scraping Screener for {len(targets)} {args.mode} names (cache={cache_dir}, sleep={args.sleep}s)...",
          flush=True)

    scraped: dict[str, Any] = {}
    sources: collections.Counter[str] = collections.Counter()
    for i, t in enumerate(targets):
        html, src = fetch_html(t, cache_dir=cache_dir, sleep=args.sleep, use_cache=not args.no_cache)
        sources[src] += 1
        if html is not None:
            try:
                frame = frame_from_html(html)
            except Exception as e:  # noqa: BLE001 — one bad page must not abort the build
                print(f"  parse error {t}: {e!r}", flush=True)
                frame = None
            if frame is not None and not frame.empty:
                scraped[t] = frame
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(targets)}; {len(scraped)} with data; sources={dict(sources)}", flush=True)

    out = Path(args.out)
    store: dict[str, Any] = {}
    if not args.no_merge and out.exists():
        with open(out, "rb") as f:
            store = pickle.load(f)
        print(f"merging into existing store: {len(store)} names", flush=True)
    before = len(store)
    store.update(scraped)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as f:
        pickle.dump(store, f)
    print(f"\nScraped {len(scraped)}/{len(targets)} {args.mode} names with data; "
          f"store {before} -> {len(store)}. Sources: {dict(sources)}\nWrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
