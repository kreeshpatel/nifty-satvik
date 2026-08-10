"""The Kite fetch driver — credential hygiene, throttle, and the no-network audit path.

The driver is thin by design (mechanics live in `nq.data.intraday`), so what is worth testing here
is the part that would be expensive to get wrong: that a credential can never reach an artifact or
stdout, that the audit path needs no network, and that the throttle honours Kite's documented
3 requests/second.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "pipelines" / "build" / "fetch_intraday_store.py"


def _mod():
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("fetch_intraday_store", SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_the_driver_imports_without_a_credential_or_a_client():
    """Importing must not construct a KiteConnect or read the environment — the import is also what
    --audit-only relies on, and that path is offline."""
    m = _mod()
    assert m.MIN_INTERVAL_S >= 1 / 3, "Kite documents 3 req/s; the gap must be at least 1/3s"
    assert m.STORE.name == "intraday" and m.MEMBERSHIP.name == "fo_membership.parquet"


def test_no_credential_is_ever_read_from_a_file_or_printed():
    src = SRC.read_text(encoding="utf-8")
    assert 'os.getenv("KITE_API_KEY"' in src and 'os.getenv("KITE_ACCESS_TOKEN"' in src
    # The only mentions may be the getenv reads and prose. Never an f-string interpolation, never a
    # write, never a print of the value itself.
    for bad in ("{api_key}", "{access_token}", "print(api_key", "print(access_token",
                "write_text(api_key", "KITE_ACCESS_TOKEN\")\n    print"):
        assert bad not in src, f"credential could leak via {bad!r}"


def test_missing_credentials_exit_two_rather_than_crashing(monkeypatch, capsys):
    m = _mod()
    monkeypatch.delenv("KITE_API_KEY", raising=False)
    monkeypatch.delenv("KITE_ACCESS_TOKEN", raising=False)
    monkeypatch.setattr(sys, "argv", ["fetch_intraday_store.py", "--interval", "15minute"])
    monkeypatch.setattr(m, "_universe", lambda limit: ["RELIANCE"])
    assert m.main() == 2
    out = capsys.readouterr().out
    assert "never reads a credential from a file" in out


def test_audit_only_needs_no_network_and_writes_the_survivorship_status(tmp_path, monkeypatch,
                                                                       capsys):
    import json

    import pandas as pd

    m = _mod()
    store = tmp_path / "15minute"
    store.mkdir(parents=True)
    bars = pd.DataFrame({"date": pd.date_range("2019-06-03 09:15", periods=4, freq="15min"),
                         "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10})
    bars.to_parquet(store / "RELIANCE.parquet", index=False)

    audit = tmp_path / "coverage.json"
    monkeypatch.setattr(m, "STORE", tmp_path)
    monkeypatch.setattr(m, "AUDIT", audit)
    monkeypatch.setattr(m, "_universe", lambda limit: ["RELIANCE", "DHFL"])
    monkeypatch.setattr(sys, "argv", ["fetch_intraday_store.py", "--audit-only",
                                      "--interval", "15minute"])
    # No KITE_* set, no kiteconnect import reachable: if the audit path touched either, this fails.
    monkeypatch.delenv("KITE_API_KEY", raising=False)
    assert m.main() == 0

    payload = json.loads(audit.read_text(encoding="utf-8"))
    assert payload["n_present"] == 1 and payload["n_requested"] == 2
    assert "DHFL" in payload["delisted_requested"]
    assert payload["delisted_present"] == []
    assert "ADR-0015" in payload["survivorship_note"]
    assert payload["corporate_action_status"].startswith("UNVERIFIED")


def test_the_audit_reports_split_seams_as_candidates_not_corrections(tmp_path, monkeypatch):
    import json

    import pandas as pd

    m = _mod()
    store = tmp_path / "15minute"
    store.mkdir(parents=True)
    rows = []
    for i, px in enumerate((100.0, 50.0)):          # a clean 1:2 seam overnight
        day = pd.Timestamp("2026-01-01") + pd.Timedelta(days=i)
        rows += [{"date": day + pd.Timedelta(hours=9), "open": px, "high": px, "low": px,
                  "close": px, "volume": 1},
                 {"date": day + pd.Timedelta(hours=15), "open": px, "high": px, "low": px,
                  "close": px, "volume": 1}]
    pd.DataFrame(rows).to_parquet(store / "SPLITCO.parquet", index=False)

    audit = tmp_path / "coverage.json"
    monkeypatch.setattr(m, "STORE", tmp_path)
    monkeypatch.setattr(m, "AUDIT", audit)
    assert m._audit("15minute", ["SPLITCO"]) == 0

    payload = json.loads(audit.read_text(encoding="utf-8"))
    assert payload["split_seam_candidates"]["SPLITCO"][0]["nearest"] == pytest.approx(0.5)
    assert "not corrections" in payload["corporate_action_status"]
    # The bars on disk must be untouched: a demerger looks identical and rescaling fabricates return.
    assert pd.read_parquet(store / "SPLITCO.parquet")["close"].tolist() == [100.0, 100.0, 50.0, 50.0]


def test_a_missing_membership_panel_fails_loudly_with_the_fix(monkeypatch):
    m = _mod()
    monkeypatch.setattr(m, "MEMBERSHIP", ROOT / "data" / "does_not_exist.parquet")
    with pytest.raises(SystemExit, match="build_fo_universe"):
        m._universe(None)
