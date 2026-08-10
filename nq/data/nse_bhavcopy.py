"""NSE F&O bhavcopy retrieval — URLs, the schema cutover, and the dual-format fallback.

Extracted from ``pipelines/build/harvest_fo_bhavcopy.py`` on 2026-08-10 so a second consumer (the
F&O universe builder) could reuse it instead of copying the URL templates. Two copies of a vendor URL
format is two things to fix when NSE moves a path, and the second copy is the one nobody remembers.

NSE serves the F&O bhavcopy under two schemes:
  * OLD  (2017-01 .. 2024-06): ``archives.nseindia.com/content/historical/DERIVATIVES/...``
  * UDiFF (2024-07 ..)       : ``nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_...``

``fetch_for_date`` tries the scheme the date implies and falls back to the other, which covers the
exact cutover fuzz and NSE's UDiFF backfill of older dates. HEAD is unreliable on
archives.nseindia.com (it 503s on files that GET fine), so this always GETs.

Nothing here parses content: callers hand the raw frame to ``options_oi.parse_fo_bhavcopy`` or
``fo_universe.parse_fo_members``. That separation is what lets both consumers share one downloader.
"""
from __future__ import annotations

import io
import zipfile

import pandas as pd

__all__ = ["UDIFF_FROM", "HDR", "url_old", "url_udiff", "url_for", "fetch_bhavcopy", "fetch_for_date"]

HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
       "Referer": "https://www.nseindia.com/"}

UDIFF_FROM = pd.Timestamp("2024-07-01")


def url_old(d) -> str:
    """Pre-2024-07 archive path. Month is upper-case three-letter; day is zero-padded."""
    d = pd.Timestamp(d)
    mon = d.strftime("%b").upper()
    return (f"https://archives.nseindia.com/content/historical/DERIVATIVES/{d.year}/{mon}/"
            f"fo{d.strftime('%d')}{mon}{d.year}bhav.csv.zip")


def url_udiff(d) -> str:
    """2024-07 onward UDiFF path."""
    d = pd.Timestamp(d)
    return ("https://nsearchives.nseindia.com/content/fo/"
            f"BhavCopy_NSE_FO_0_0_0_{d.strftime('%Y%m%d')}_F_0000.csv.zip")


def url_for(d) -> tuple[str, str]:
    """``(primary, secondary)`` for a date — the scheme its era implies, then the other one."""
    d = pd.Timestamp(d)
    return ((url_udiff(d), url_old(d)) if d >= UDIFF_FROM
            else (url_old(d), url_udiff(d)))


def fetch_bhavcopy(sess, url: str) -> pd.DataFrame | None:
    """GET one zipped bhavcopy -> DataFrame, or None.

    Returns None rather than raising on every failure mode — a missing file is the NORMAL case here
    (holidays, and the era that a given scheme does not cover), so the caller distinguishes
    "holiday" from "outage" by whether BOTH schemes missed, not by an exception.
    """
    try:
        r = sess.get(url, headers=HDR, timeout=40)
        if r.status_code != 200 or not r.content:
            return None
        z = zipfile.ZipFile(io.BytesIO(r.content))
        return pd.read_csv(z.open(z.namelist()[0]))
    except Exception:                                   # noqa: BLE001 — absence is not an error here
        return None


def fetch_for_date(sess, d) -> pd.DataFrame | None:
    """Try the era-appropriate scheme, then the other. None when both miss (holiday or gap)."""
    primary, secondary = url_for(d)
    df = fetch_bhavcopy(sess, primary)
    return df if df is not None else fetch_bhavcopy(sess, secondary)
