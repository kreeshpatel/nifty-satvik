"""NSE bhavcopy URLs, the 2024-07 schema cutover, and the dual-scheme fallback.

Extracted from harvest_fo_bhavcopy.py on 2026-08-10 so the F&O universe builder could share it. Two
copies of a vendor URL template is two things to fix when NSE moves a path, and the forgotten copy is
the one that breaks a year later — so these pin the templates in one place.

Hermetic: the session is a stub. Nothing here opens a socket.
"""
from __future__ import annotations

import io
import zipfile

import pandas as pd
import pytest

from nq.data.nse_bhavcopy import (UDIFF_FROM, fetch_bhavcopy, fetch_for_date, url_for, url_old,
                                  url_udiff)


class _Resp:
    def __init__(self, status=200, content=b""):
        self.status_code, self.content = status, content


class _Sess:
    """Serves prepared bodies by URL and records call order."""

    def __init__(self, bodies: dict | None = None, raise_on: str | None = None):
        self.bodies, self.raise_on, self.calls = bodies or {}, raise_on, []

    def get(self, url, headers=None, timeout=None):
        self.calls.append(url)
        if self.raise_on and self.raise_on in url:
            raise ConnectionError("boom")
        return _Resp(*self.bodies.get(url, (404, b"")))


def _zipped(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("bhav.csv", df.to_csv(index=False))
    return buf.getvalue()


# --------------------------------------------------------------------------- URL templates
def test_old_url_uses_uppercase_month_and_zero_padded_day():
    u = url_old("2019-06-03")
    assert u == ("https://archives.nseindia.com/content/historical/DERIVATIVES/2019/JUN/"
                 "fo03JUN2019bhav.csv.zip")


def test_udiff_url_is_compact_iso():
    assert url_udiff("2025-01-07").endswith("BhavCopy_NSE_FO_0_0_0_20250107_F_0000.csv.zip")


# NOTE the "//" prefixes. "archives.nseindia.com" is a SUBSTRING of "nsearchives.nseindia.com"
# ("nse" + "archives"), so a bare containment check matches both hosts and silently passes. The
# host boundary is the only safe discriminator here.
OLD_HOST, UDIFF_HOST = "//archives.nseindia.com", "//nsearchives.nseindia.com"


@pytest.mark.parametrize("d,first", [
    ("2024-06-28", OLD_HOST),        # last OLD-era session
    ("2024-07-01", UDIFF_HOST),      # the cutover itself
    ("2024-07-02", UDIFF_HOST),
])
def test_the_cutover_selects_the_era_appropriate_scheme_first(d, first):
    primary, secondary = url_for(d)
    assert first in primary and first not in secondary


def test_the_cutover_constant_is_the_documented_date():
    assert UDIFF_FROM == pd.Timestamp("2024-07-01")


def test_both_schemes_are_always_offered():
    """The fallback is what covers the cutover fuzz and NSE's UDiFF backfill of older dates."""
    for d in ("2017-01-02", "2026-01-02"):
        primary, secondary = url_for(d)
        hosts = {OLD_HOST in primary, OLD_HOST in secondary}
        assert hosts == {True, False}, "exactly one of the pair must be the OLD-scheme host"
        assert {UDIFF_HOST in primary, UDIFF_HOST in secondary} == {True, False}


# --------------------------------------------------------------------------- fetching
def test_fetch_unzips_a_csv():
    df = pd.DataFrame({"INSTRUMENT": ["FUTSTK"], "SYMBOL": ["RELIANCE"]})
    url = url_old("2019-06-03")
    out = fetch_bhavcopy(_Sess({url: (200, _zipped(df))}), url)
    assert out is not None and out["SYMBOL"].tolist() == ["RELIANCE"]


@pytest.mark.parametrize("status,content", [(404, b""), (200, b""), (503, b"x"), (200, b"not-a-zip")])
def test_every_failure_mode_is_none_not_an_exception(status, content):
    """A missing file is the NORMAL case — holidays, and the era a scheme does not cover. The caller
    distinguishes holiday from outage by both schemes missing, not by catching."""
    url = url_old("2019-06-03")
    assert fetch_bhavcopy(_Sess({url: (status, content)}), url) is None


def test_a_transport_exception_is_also_none():
    url = url_old("2019-06-03")
    assert fetch_bhavcopy(_Sess(raise_on="archives"), url) is None


def test_fetch_for_date_falls_back_to_the_other_scheme():
    d = "2024-07-01"                                    # UDiFF era; only the OLD file exists
    primary, secondary = url_for(d)
    df = pd.DataFrame({"INSTRUMENT": ["FUTSTK"], "SYMBOL": ["TCS"]})
    sess = _Sess({secondary: (200, _zipped(df))})
    out = fetch_for_date(sess, d)
    assert out is not None and out["SYMBOL"].tolist() == ["TCS"]
    assert sess.calls == [primary, secondary], "primary must be tried first, exactly once"


def test_fetch_for_date_does_not_call_the_fallback_when_the_primary_succeeds():
    d = "2019-06-03"
    primary, _ = url_for(d)
    sess = _Sess({primary: (200, _zipped(pd.DataFrame({"INSTRUMENT": ["FUTSTK"],
                                                       "SYMBOL": ["INFY"]})))})
    assert fetch_for_date(sess, d) is not None
    assert sess.calls == [primary], "a wasted request per session over 2,400 days is not free"


def test_both_schemes_missing_is_none():
    sess = _Sess({})
    assert fetch_for_date(sess, "2019-06-03") is None
    assert len(sess.calls) == 2


# --------------------------------------------------------------------------- the refactor held
def test_the_oi_harvester_now_shares_this_downloader():
    """Guard against the copy coming back: harvest_fo_bhavcopy must not re-declare the templates."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "pipelines" / "build"
           / "harvest_fo_bhavcopy.py").read_text(encoding="utf-8")
    assert "from nq.data.nse_bhavcopy import fetch_for_date" in src
    assert "def _url_old" not in src and "def _url_udiff" not in src
    assert "def _fetch" not in src
    # The docstring still DESCRIBES both schemes and must keep doing so; it writes the hosts
    # WITHOUT a scheme prefix. So "https://" is the marker that separates documentation from an
    # executable template. The unzip machinery must be gone too.
    assert "https://archives" not in src and "https://nsearchives" not in src
    assert "import zipfile" not in src
