"""Build data/results_xbrl.parquet from the fetched XBRL files (data engineering only, no signal).

Joins every manifest row with http_status 200 to its listing row (broadcast_ts, listing, ISIN),
parses the gzipped XBRL with nq.data.results_xbrl.parse_xbrl, assigns filing_seq (original = 0,
later filings of the same period = revisions) and writes the gitignored parquet plus a parse log.

  python pipelines/build/build_results_xbrl.py [--years 2019 2020]
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "pipelines" / "build")]

from harvest_results_xbrl import _raw_path, load_listing_frame, read_manifest  # noqa: E402
from nq.data.results_xbrl import RESULTS_XBRL_PATH, SCHEMA, assign_filing_seq, parse_xbrl  # noqa: E402

LOG = ROOT / ".cache" / "data_audit_v2" / "results_xbrl_build_log.json"


def build(years: list[int] | None = None) -> dict:
    lf = load_listing_frame().set_index("xbrl_url")
    man = {u: r for u, r in read_manifest().items() if r["http_status"] == "200"}
    rows, fails = [], {}
    for url in man:
        if url not in lf.index:
            fails[url] = "not_in_listing"
            continue
        L = lf.loc[url]
        if years and L.broadcast_ts.year not in years:
            continue
        try:
            recs = parse_xbrl(gzip.decompress(_raw_path(url, L.broadcast_ts.year).read_bytes()))
        except Exception as e:  # noqa: BLE001 - recorded, never silently dropped
            fails[url] = f"exception:{type(e).__name__}"
            continue
        if not recs:
            fails[url] = "no_reporting_period"
            continue
        for r in recs:
            r.update(broadcast_ts=L.broadcast_ts, xbrl_url=url, listing=L["listing"])
            r["isin"] = r["isin"] or L["isin"]
            r["symbol"] = r["symbol"] or L["symbol"]
            if r["consolidated"] is None and isinstance(L.consolidated_listing, str):
                r["consolidated"] = L.consolidated_listing.lower().startswith("consol")
            rows.append(r)
    df = pd.DataFrame(rows)
    if len(df):
        for c in ("period_start", "period_end"):
            df[c] = pd.to_datetime(df[c])
        df = assign_filing_seq(df)[SCHEMA]
        RESULTS_XBRL_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(RESULTS_XBRL_PATH, index=False)
    out = {"files_ok_in_manifest": len(man), "rows": int(len(df)),
           "filings_parsed": int(df["xbrl_url"].nunique()) if len(df) else 0,
           "file_failures": len(fails), "failure_reasons": pd.Series(fails).value_counts().to_dict() if fails else {}}
    LOG.write_text(json.dumps({"summary": out, "failures": fails}, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, nargs="*")
    print(json.dumps(build(ap.parse_args().years), indent=1))
