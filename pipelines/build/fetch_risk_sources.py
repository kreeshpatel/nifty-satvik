"""Fetch the surveillance (ASM) circular attachments and the quarterly shareholding-pattern XBRL (pledge), for the
L5 crash-risk feature panel. Data engineering only; raw files are gitignored and never committed.

Politeness comes from ``harvest_results_xbrl.Polite``: at most 1 req/s to www.nseindia.com and 2 req/s to the
archive host, exponential backoff on 403/429/5xx, and a stop after 10 minutes of persistent 403.

  python pipelines/build/fetch_risk_sources.py asm   # circular lists 2019-01.. + ASM attachments (xlsx/csv kept)
  python pipelines/build/fetch_risk_sources.py shp   # shareholding lists 2021-01.. + SHP XBRL for PIT N500 names
"""
from __future__ import annotations

import gzip
import io
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "pipelines" / "build")]
from harvest_results_xbrl import Persistent403, Polite  # noqa: E402

SURV = ROOT / "data" / "surv_raw"   # gitignored (/data/*)
SHP = ROOT / "data" / "shp_raw"
CIRC_URL = "https://www.nseindia.com/api/circulars?fromDate={f}&toDate={t}&dept=SURV"
SHP_URL = "https://www.nseindia.com/api/corporate-share-holdings-master?index=equities&from_date={f}&to_date={t}"
ASM_WORDS = ("ADDITIONAL SURVEILLANCE", "ASM")


def _months(start: str):
    return pd.period_range(start, pd.Timestamp.today().strftime("%Y-%m"), freq="M")


def _rows(r):
    j = r.json()
    return j if isinstance(j, list) else j.get("data", [])


def _list(p: Polite, url: str, d: Path, start: str):
    d.mkdir(parents=True, exist_ok=True)
    for m in _months(start):
        f = d / f"{m}.json"
        if f.exists() and m < pd.Period(pd.Timestamp.today(), "M"):
            continue
        r = p.get(url.format(f=m.start_time.strftime("%d-%m-%Y"), t=m.end_time.strftime("%d-%m-%Y")), timeout=120)
        if r is None:
            print("FAIL list", m, flush=True)
            continue
        f.write_text(json.dumps(_rows(r)), encoding="utf-8")


def asm(p: Polite) -> dict:
    _list(p, CIRC_URL, SURV / "lists", "2019-01")
    circ = [c for f in sorted((SURV / "lists").glob("*.json")) for c in json.loads(f.read_text(encoding="utf-8"))]
    circ = [c for c in circ if any(w in str(c.get("sub", "")).upper() for w in ASM_WORDS)]
    n_ok = n_bad = 0
    for c in circ:
        out = SURV / "asm" / str(c["circNumber"])
        if out.exists():
            continue
        r = p.get(c["circFilelink"], timeout=120)
        out.mkdir(parents=True, exist_ok=True)
        meta = {k: c.get(k) for k in ("cirDate", "circNumber", "sub", "circFilelink")}
        if r is None or r.status_code != 200:
            meta["status"] = getattr(r, "status_code", -1)
            n_bad += 1
        else:
            meta["status"] = 200
            n_ok += 1
            if str(c.get("fileExt", "")).lower() == "zip":
                try:
                    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                        for n in z.namelist():
                            if n.lower().endswith((".xlsx", ".xls", ".csv")):
                                (out / Path(n).name).write_bytes(z.read(n))
                except zipfile.BadZipFile:
                    meta["status"] = "badzip"
            elif str(c.get("fileExt", "")).lower() in ("xlsx", "xls", "csv"):
                (out / Path(c["circFilelink"]).name).write_bytes(r.content)
        (out / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return {"asm_circulars": len(circ), "fetched_now": n_ok, "failed_now": n_bad}


def shp(p: Polite) -> dict:
    from nq.data.membership import load_membership
    members = set((load_membership() or {}).keys())
    _list(p, SHP_URL, SHP / "lists", "2021-01")
    rows = [r for f in sorted((SHP / "lists").glob("*.json")) for r in json.loads(f.read_text(encoding="utf-8"))]
    rows = [r for r in rows if str(r.get("symbol", "")).upper() in members and str(r.get("xbrl", "")).endswith(".xml")]
    n_ok = n_bad = 0
    for r in rows:
        f = SHP / "xml" / f"{r['recordId']}.xml.gz"
        if f.exists():
            continue
        f.parent.mkdir(parents=True, exist_ok=True)
        resp = p.get(r["xbrl"], timeout=90)
        if resp is not None and resp.status_code == 200 and resp.content.lstrip()[:1] == b"<":
            f.write_bytes(gzip.compress(resp.content))
            n_ok += 1
        else:
            n_bad += 1
    return {"shp_rows_members": len(rows), "fetched_now": n_ok, "failed_now": n_bad}


if __name__ == "__main__":
    p = Polite()
    try:
        print(json.dumps({"asm": asm, "shp": shp}[sys.argv[1]](p), indent=1), flush=True)
    except Persistent403 as e:
        print(f"STOP: {e}", flush=True)
        sys.exit(3)
