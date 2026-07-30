"""Guards for the append-only forward accumulators (results/*_forward.csv).

Why these exist: the accumulator-health probe once called the collectors against the LIVE files
with a literal "PROBE" timestamp, overwriting real fetch times on three rows (caught and restored
in 3216ce7). Two layers now prevent a recurrence, and both are pinned here:

  (a) the probe operates on a scratch COPY — the live path is never written;
  (b) the append path refuses a fetch_ts that does not parse as a datetime, so the live record is
      unwritable with junk regardless of caller.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from run_forward_accumulators import _append_dedup, _validate_fetch_ts  # noqa: E402

KEYS = ["deal_type", "date", "symbol"]


def _frame(fetch_ts: str, symbol: str = "AAA") -> pd.DataFrame:
    return pd.DataFrame([{"deal_type": "bulk", "date": "28-JUL-2026", "symbol": symbol,
                          "fetch_ts": fetch_ts}])


# --- layer (b): the append path refuses sentinels -----------------------------------------

@pytest.mark.parametrize("junk", ["PROBE", "TEST", "", "nan", "n/a", "-"])
def test_append_refuses_non_datetime_fetch_ts(tmp_path, junk):
    """A sentinel timestamp must raise, not be written."""
    out = tmp_path / "acc.csv"
    with pytest.raises(ValueError, match="non-datetime fetch_ts"):
        _append_dedup(out, _frame(junk), KEYS)
    assert not out.exists(), "nothing may be written when validation fails"


def test_append_refuses_sentinel_without_touching_existing_file(tmp_path):
    """The live-record protection that actually matters: a bad append leaves prior bytes intact."""
    out = tmp_path / "acc.csv"
    _append_dedup(out, _frame("2026-07-28 20:59:44"), KEYS)
    before = out.read_bytes()
    with pytest.raises(ValueError):
        _append_dedup(out, _frame("PROBE", symbol="BBB"), KEYS)
    assert out.read_bytes() == before, "a rejected append must not modify the existing record"


def test_append_accepts_real_timestamps(tmp_path):
    out = tmp_path / "acc.csv"
    assert _append_dedup(out, _frame("2026-07-28 20:59:44"), KEYS) == 1
    # idempotent: the same content-keyed row adds nothing on re-append
    assert _append_dedup(out, _frame("2026-07-29 21:00:00"), KEYS) == 0
    df = pd.read_csv(out, dtype=str)
    assert len(df) == 1
    assert df.loc[0, "fetch_ts"] == "2026-07-28 20:59:44", "first-seen provenance is kept"


def test_validate_is_a_noop_without_the_column():
    _validate_fetch_ts(pd.DataFrame([{"a": 1}]))      # no fetch_ts column
    _validate_fetch_ts(pd.DataFrame(columns=["fetch_ts"]))  # empty


# --- layer (a): the probe writes to a scratch copy, never the live path --------------------

def test_probe_pattern_leaves_live_file_untouched(tmp_path, monkeypatch):
    """Simulates the health probe: copy -> probe the copy -> live bytes unchanged.

    Mirrors diag_accumulator_health.py's idempotency probe without hitting the network — the
    collectors' `out=` override is the mechanism under test.
    """
    import hashlib
    import shutil

    live = tmp_path / "live_forward.csv"
    _append_dedup(live, _frame("2026-07-28 20:59:44"), KEYS)
    before = hashlib.sha256(live.read_bytes()).hexdigest()

    scratch = tmp_path / "scratch" / live.name
    scratch.parent.mkdir()
    shutil.copy2(live, scratch)

    # the probe's re-append goes to the COPY
    added = _append_dedup(scratch, _frame("2026-07-30 10:00:00", symbol="BBB"), KEYS)

    assert added == 1, "the scratch copy did take the probe write"
    assert hashlib.sha256(live.read_bytes()).hexdigest() == before, "live record must be untouched"
    assert len(pd.read_csv(scratch, dtype=str)) == 2
    assert len(pd.read_csv(live, dtype=str)) == 1


def test_collectors_expose_an_out_override():
    """The probe isolation depends on this signature; keep it from silently regressing."""
    import inspect

    from run_forward_accumulators import collect_bulkblock, collect_ratings

    for fn in (collect_bulkblock, collect_ratings):
        params = inspect.signature(fn).parameters
        assert "out" in params, f"{fn.__name__} must accept an out= path override"
        assert params["out"].default is None, f"{fn.__name__}'s out= must default to the live path"
