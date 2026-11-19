"""Harvest NSE financial-results listings and their XBRL instance files (data engineering only).

Goal link: the point-in-time quarterly EPS / line-item input for the January multi-signal model.
No signal, no returns, no trial. Raw NSE data never enters git (NSE terms restrict redistribution):
listings live in .cache/data_audit_v2/ and XBRL XML in data/xbrl_raw/ (both ignored); only
data/xbrl_raw/manifest.csv (url, symbol, timestamps, status, sha256) is committed.

Two NSE listing endpoints, because SEBI's Integrated Filing regime moved results:
  * legacy      api/corporates-financial-results?period={Quarterly|Half-Yearly|Annual}
                (filter = broadcast date; carries results until ~2025-03, near-empty after)
  * integrated  api/integrated-filing-results  (type "Integrated Filing- Financials";
                Financials filings from ~2025-04; paginated, `size` honoured)
  The integrated endpoint is a scope addition made after the first look (the legacy one returned
  0-31 rows/month after 2025-03); see the quality report.

Politeness: <=1 request/s to www.nseindia.com, <=2/s to the archive host, exponential backoff on
403/429/5xx, abort when 403s persist for 10 minutes.

Usage:
  python pipelines/build/harvest_results_xbrl.py listings
  python pipelines/build/harvest_results_xbrl.py time50
  python pipelines/build/harvest_results_xbrl.py fetch --years 2019 2020 [--limit N]
  python pipelines/build/harvest_results_xbrl.py status
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / ".cache" / "data_audit_v2"
RAW = ROOT / "data" / "xbrl_raw"
MANIFEST = RAW / "manifest.csv"
MANIFEST_COLS = ["url", "symbol", "broadcast_ts", "listing", "http_status", "sha256", "bytes", "fetched_at"]

LEGACY = {"fin_results": "Quarterly", "fin_results_half": "Half-Yearly", "fin_results_annual": "Annual"}
LEGACY_URL = ("https://www.nseindia.com/api/corporates-financial-results?index=equities"
              "&from_date={f}&to_date={t}&period={p}")
INTEGRATED_DIR = "fin_results_integrated"
INTEGRATED_URL = ("https://www.nseindia.com/api/integrated-filing-results?index=equities"
                  "&from_date={f}&to_date={t}&type=Integrated%20Filing-%20Financials&size={n}")
MONTHS = pd.period_range("2019-01", "2026-11", freq="M")
INTEGRATED_MONTHS = pd.period_range("2024-10", "2026-11", freq="M")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
      "Accept": "application/json,text/plain,*/*", "Referer": "https://www.nseindia.com/"}
MIN_INTERVAL = {"www.nseindia.com": 1.0, "nsearchives.nseindia.in": 0.5, "archives.nseindia.com": 0.5}
PERSISTENT_403_S = 600


class Persistent403(RuntimeError):
    pass


class Polite:
    """One session, per-host minimum spacing, exponential backoff, 10-minute 403 abort."""

    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update(UA)
        self.last: dict[str, float] = {}
        self.first_403: float | None = None

    def get(self, url: str, timeout: int = 60, max_tries: int = 8) -> requests.Response | None:
        host = urlparse(url).netloc
        gap = MIN_INTERVAL.get(host, 1.0)
        delay = 2.0
        for _ in range(max_tries):
            wait = self.last.get(host, 0.0) + gap - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self.last[host] = time.monotonic()
            try:
                r = self.s.get(url, timeout=timeout)
            except requests.RequestException:
                time.sleep(delay)
                delay = min(delay * 2, 120)
                continue
            if r.status_code in (403, 429) or r.status_code >= 500:
                if r.status_code == 403:
                    self.first_403 = self.first_403 or time.monotonic()
                    if time.monotonic() - self.first_403 > PERSISTENT_403_S:
                        raise Persistent403(f"403s persisted >10 min (last url {url})")
                time.sleep(delay)
                delay = min(delay * 2, 120)
                continue
            self.first_403 = None
            return r
        return None


# ── listings ────────────────────────────────────────────────────────────────────────────────
def _rows(j) -> list:
    return j if isinstance(j, list) else (j.get("data", []) if isinstance(j, dict) else [])


def pull_listings(p: Polite) -> dict:
    report = {}
    for name, period in LEGACY.items():
        d = CACHE / name
        d.mkdir(parents=True, exist_ok=True)
        for m in MONTHS:
            f = d / f"{m}.json"
            if f.exists():
                continue
            r = p.get(LEGACY_URL.format(f=m.start_time.strftime("%d-%m-%Y"), t=m.end_time.strftime("%d-%m-%Y"), p=period))
            if r is None:
                print(f"FAIL {name} {m}", flush=True)
                continue
            try:
                j = r.json()
            except ValueError:
                print(f"NONJSON {name} {m} {r.status_code}", flush=True)
                continue
            f.write_text(json.dumps(j), encoding="utf-8")
            print(f"{name} {m} {len(_rows(j))}", flush=True)
        report[name] = _count(d)
    d = CACHE / INTEGRATED_DIR
    d.mkdir(parents=True, exist_ok=True)
    for m in INTEGRATED_MONTHS:
        f = d / f"{m}.json"
        if f.exists():
            continue
        a, b = m.start_time.strftime("%d-%m-%Y"), m.end_time.strftime("%d-%m-%Y")
        r = p.get(INTEGRATED_URL.format(f=a, t=b, n=10000), timeout=180)
        if r is None:
            print(f"FAIL integrated {m}", flush=True)
            continue
        j = r.json()
        if j.get("totalCount", 0) > len(_rows(j)):
            print(f"WARN integrated {m}: totalCount {j.get('totalCount')} > rows {len(_rows(j))}", flush=True)
            continue  # do not cache a truncated month
        f.write_text(json.dumps(j), encoding="utf-8")
        print(f"integrated {m} {len(_rows(j))}", flush=True)
    report[INTEGRATED_DIR] = _count(d)
    return report


def _count(d: Path) -> dict:
    by_year: dict[str, int] = {}
    for f in sorted(d.glob("*.json")):
        n = len(_rows(json.loads(f.read_text(encoding="utf-8"))))
        by_year[f.stem[:4]] = by_year.get(f.stem[:4], 0) + n
    return {"months": len(list(d.glob("*.json"))), "rows": sum(by_year.values()), "by_year": by_year}


def load_listing_frame() -> pd.DataFrame:
    """Every filing across all listings, normalised to one schema (one row per listing row).

    broadcast_ts rule: legacy -> broadCastDate. Integrated -> broadcast_Date; when it is null
    (NSE leaves it null on revisions) -> max(creation_Date, revised_Date), the later of the two
    times the filing could have become public (conservative)."""
    out = []
    for name in LEGACY:
        for f in sorted((CACHE / name).glob("*.json")):
            for r in _rows(json.loads(f.read_text(encoding="utf-8"))):
                out.append({
                    "listing": name, "symbol": r.get("symbol"), "isin": r.get("isin"),
                    "company": r.get("companyName"),
                    "xbrl_url": r.get("xbrl"), "broadcast_raw": r.get("broadCastDate"),
                    "from_date": r.get("fromDate"), "to_date": r.get("toDate"),
                    "consolidated_listing": r.get("consolidated"), "audited": r.get("audited"),
                    "cumulative": r.get("cumulative"), "re_ind": r.get("reInd"),
                    "seq": str(r.get("seqNumber")), "listing_period": r.get("period"),
                    "type_sub": None, "revision_remark": None, "bank": r.get("bank"),
                })
    for f in sorted((CACHE / INTEGRATED_DIR).glob("*.json")):
        for r in _rows(json.loads(f.read_text(encoding="utf-8"))):
            if not str(r.get("type", "")).endswith("Financials"):
                continue
            bc = r.get("broadcast_Date")
            if not bc:
                cands = [pd.to_datetime(x, format="mixed", dayfirst=True, errors="coerce")
                         for x in (r.get("creation_Date"), r.get("revised_Date")) if x]
                cands = [c for c in cands if pd.notna(c)]
                bc = max(cands).strftime("%d-%b-%Y %H:%M:%S") if cands else None
            out.append({
                "listing": INTEGRATED_DIR, "symbol": r.get("symbol"), "isin": None, "company": r.get("cmName"),
                "xbrl_url": r.get("xbrl"), "broadcast_raw": bc,
                "from_date": None, "to_date": r.get("qe_Date"),
                "consolidated_listing": r.get("consolidated"), "audited": r.get("audited"),
                "cumulative": None, "re_ind": None, "seq": str(r.get("seq_Id")), "listing_period": None,
                "type_sub": r.get("type_Sub"), "revision_remark": r.get("revision_Remark"), "bank": None,
            })
    df = pd.DataFrame(out)
    if not len(df):
        return df
    df["broadcast_ts"] = pd.to_datetime(df["broadcast_raw"], format="%d-%b-%Y %H:%M:%S", errors="coerce")
    df = df[df["xbrl_url"].astype(str).str.startswith("http") & df["xbrl_url"].astype(str).str.endswith(".xml")]
    # the same XBRL can appear in two listings (transition months): keep the earliest broadcast
    return (df.sort_values(["xbrl_url", "broadcast_ts"]).drop_duplicates("xbrl_url", keep="first")
              .reset_index(drop=True))


# ── XBRL fetch ──────────────────────────────────────────────────────────────────────────────
def _raw_path(url: str, year: int) -> Path:
    return RAW / str(year) / (Path(urlparse(url).path).name + ".gz")


def read_manifest() -> dict[str, dict]:
    if not MANIFEST.exists():
        return {}
    with MANIFEST.open(newline="", encoding="utf-8") as fh:
        return {r["url"]: r for r in csv.DictReader(fh)}


def _append_manifest(row: dict) -> None:
    new = not MANIFEST.exists()
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=MANIFEST_COLS)
        if new:
            w.writeheader()
        w.writerow(row)


def stratified_sample(n_per: int = 4, seed: int = 20261119) -> pd.DataFrame:
    """n_per filings per (XBRL taxonomy prefix, broadcast year): exercises every format before the bulk run."""
    lf = load_listing_frame()
    lf = lf[lf["broadcast_ts"].notna()].copy()
    lf["taxonomy"] = lf["xbrl_url"].str.extract(r"xbrl/([A-Z_]+?)_\d")[0]
    lf["year"] = lf["broadcast_ts"].dt.year
    return lf.groupby(["taxonomy", "year"]).sample(frac=1, random_state=seed).groupby(["taxonomy", "year"]).head(n_per)


def fetch(p: Polite, years: list[int] | None, limit: int | None = None, only: pd.DataFrame | None = None) -> dict:
    lf = load_listing_frame() if only is None else only
    lf = lf[lf["broadcast_ts"].notna()]
    if years:
        lf = lf[lf["broadcast_ts"].dt.year.isin(years)]
    lf = lf.sort_values("broadcast_ts")
    done = {u for u, r in read_manifest().items() if r["http_status"] == "200"}
    todo = lf[~lf["xbrl_url"].isin(done)]
    if limit:
        todo = todo.head(limit)
    t0, n_ok, n_bad = time.monotonic(), 0, 0
    for i, r in enumerate(todo.itertuples(index=False), 1):
        resp = p.get(r.xbrl_url, timeout=90)
        status = resp.status_code if resp is not None else -1
        sha, nbytes = "", 0
        if resp is not None and status == 200 and resp.content.lstrip()[:1] == b"<":
            body = resp.content
            sha, nbytes = hashlib.sha256(body).hexdigest(), len(body)
            path = _raw_path(r.xbrl_url, r.broadcast_ts.year)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(gzip.compress(body, compresslevel=6))
            n_ok += 1
        else:
            status = status if status != 200 else -2  # 200 but not XML
            n_bad += 1
        _append_manifest({"url": r.xbrl_url, "symbol": r.symbol,
                          "broadcast_ts": r.broadcast_ts.strftime("%Y-%m-%d %H:%M:%S"), "listing": r.listing,
                          "http_status": status, "sha256": sha, "bytes": nbytes,
                          "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
        if i % 200 == 0:
            el = time.monotonic() - t0
            print(f"{i}/{len(todo)} ok={n_ok} bad={n_bad} {el/i:.2f}s/file", flush=True)
    el = time.monotonic() - t0
    return {"attempted": len(todo), "ok": n_ok, "bad": n_bad, "seconds": round(el, 1),
            "s_per_file": round(el / max(len(todo), 1), 3)}


def status() -> dict:
    lf = load_listing_frame()
    man = read_manifest()
    ok = {u for u, r in man.items() if r["http_status"] == "200"}
    by = lf.assign(y=lf["broadcast_ts"].dt.year, got=lf["xbrl_url"].isin(ok)).groupby("y")["got"].agg(["size", "sum"])
    return {"listing_xbrl_urls": int(len(lf)), "fetched_ok": len(ok),
            "manifest_rows": len(man), "by_year": {int(k): [int(a), int(b)] for k, (a, b) in by.iterrows()}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["listings", "time50", "fetch", "status"])
    ap.add_argument("--years", type=int, nargs="*")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    p = Polite()
    try:
        if a.cmd == "listings":
            print(json.dumps(pull_listings(p), indent=1))
        elif a.cmd == "time50":
            res = fetch(p, [2019], limit=50)
            total = len(load_listing_frame())
            res["projected_hours_all"] = round(res["s_per_file"] * total / 3600, 2)
            res["listing_xbrl_urls"] = total
            print(json.dumps(res, indent=1))
        elif a.cmd == "fetch":
            print(json.dumps(fetch(p, a.years, a.limit), indent=1))
        else:
            print(json.dumps(status(), indent=1))
    except Persistent403 as e:
        print(f"STOP: {e}", flush=True)
        sys.exit(3)


if __name__ == "__main__":
    main()
