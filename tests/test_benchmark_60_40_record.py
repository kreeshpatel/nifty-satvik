"""The 60/40 forward record is append-only and deterministic (no network: synthetic NAVs)."""
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bm_record", ROOT / "forward/benchmark_60_40/record.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def _navs(days=60):
    idx = pd.bdate_range("2026-11-02", periods=days)
    return {R.T.IDX: pd.Series([18 * 1.004 ** i for i in range(days)], index=idx),
            R.T.ARB: pd.Series([43.7 * 1.0002 ** i for i in range(days)], index=idx)}


def _write_weeks(path, n):
    navs = _navs()
    for k in range(n):
        f = pd.Timestamp("2026-11-27") + pd.Timedelta(weeks=k)
        R.append(R.build_row(R.verify(path), f, navs), path)


def test_history_never_rewritten(tmp_path):
    p = tmp_path / "ledger.jsonl"
    _write_weeks(p, 2)
    before = p.read_bytes()
    _write_weeks_more = R.build_row(R.verify(p), pd.Timestamp("2026-12-11"), _navs())
    R.append(_write_weeks_more, p)
    assert p.read_bytes().startswith(before)              # earlier bytes untouched
    with pytest.raises(ValueError):                       # no re-recording an old or same week
        R.append(R.build_row(R.verify(p)[:1], pd.Timestamp("2026-12-04"), _navs()), p)


def test_tampering_detected(tmp_path):
    p = tmp_path / "ledger.jsonl"
    _write_weeks(p, 3)
    rows = [json.loads(x) for x in p.read_text().splitlines()]
    rows[0]["pre_tax_nav"] += 1
    p.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    with pytest.raises(R.LedgerTampered):
        R.verify(p)
    assert "TAMPERED" in R.health_line(p)


def test_replay_is_deterministic_and_drift_rule(tmp_path):
    p = tmp_path / "ledger.jsonl"
    _write_weeks(p, 4)
    rows = R.verify(p)
    tp1, f1 = R.replay(rows)
    tp2, f2 = R.replay(rows)
    assert f1 == f2 and f1[0] is True and tp1.value({R.T.IDX: 1, R.T.ARB: 1}) == tp2.value({R.T.IDX: 1, R.T.ARB: 1})
    assert all(r["after_tax_nav"] <= r["pre_tax_nav"] for r in rows)
    assert R.health_line(p).startswith("60/40 forward record: week 4,")
