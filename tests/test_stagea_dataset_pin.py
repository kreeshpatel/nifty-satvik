"""Stage A — dataset pin: the sha256-identified OHLCV snapshot that makes baseline_v1
byte-reproducible.

yfinance history drifts run-to-run (observed CAGR 14.2/15.6/16.25 on identical commands), so a
headline number is only reproducible against a FIXED snapshot. A pinned run loads that snapshot
(a release asset) and verifies the sha256 of its exact bytes before doing anything. These tests
pin the primitive (``file_sha256``) and the safety gate (a wrong snapshot aborts loud, before any
backtest). Hermetic — no network."""
from __future__ import annotations

import hashlib
import pickle

import pandas as pd

from nq.data.ohlcv import file_sha256
from scripts.run_cpcv import _recorded_pin, main


def _tiny_cache(path):
    """A minimal valid OHLCV cache so load_ohlcv_cache returns a non-empty dict."""
    df = pd.DataFrame(
        {"Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [1.0], "Volume": [1.0]},
        index=pd.to_datetime(["2020-01-01"]),
    )
    with open(path, "wb") as f:
        pickle.dump({"AAA": df}, f)
    return path


def test_file_sha256_matches_hashlib(tmp_path):
    p = _tiny_cache(tmp_path / "ohlcv.pkl")
    assert file_sha256(p) == hashlib.sha256(p.read_bytes()).hexdigest()


def test_file_sha256_missing_is_empty(tmp_path):
    assert file_sha256(tmp_path / "nope.pkl") == ""


def test_pin_mismatch_aborts_before_backtest(tmp_path):
    # A wrong/expired snapshot must fail loud (exit 2), not silently run on the wrong data.
    p = _tiny_cache(tmp_path / "ohlcv.pkl")
    rc = main(["--mode", "current", "--cache", str(p), "--expect-sha256", "deadbeef"])
    assert rc == 2


def test_recorded_pin_carries_sha_slot():
    # baseline_v1.json must expose the pin slot run_cpcv reads (value may still be null pre-mint).
    assert "ohlcv_sha256" in _recorded_pin()
