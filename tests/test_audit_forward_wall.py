"""Fixture-only tests for scripts/audit_forward_wall.py — the September wall audit's machinery.
Built and proven on SYNTHETIC logs (extending the forward_wall fixture pattern); the live wall is
never read here (the no-peeking rule holds until the review session runs the script)."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from nq.paper.forward_wall import append_row  # noqa: E402
from audit_forward_wall import (audit_chain, audit_config_drift, audit_sleeve,  # noqa: E402
                                audit_trades)


def _row(date: str, eq: float = 1_000_000.0, status: str = "ok") -> dict:
    r: dict = {"date": date, "status": status, "drift_mult": 1.0}
    for b in ("base", "veto", "drift"):
        r[f"{b}_ret"] = 0.001
        r[f"{b}_equity"] = eq
        r[f"{b}_npos"] = 15
    return r


def test_chain_ok_and_halt_detection(tmp_path):
    log = tmp_path / "wall.csv"
    append_row(_row("2026-07-01", 1_000_000), log)
    append_row(_row("2026-07-02", 1_010_000), log)
    append_row(_row("2026-07-03", 450_000), log)          # -55% from peak -> mechanical halt breach
    rep = audit_chain(log)
    assert rep["chain_ok"] and rep["rows"] == 3
    kinds = {h["kind"] for h in rep["halt_events"]}
    assert any("equity -50% breach" in k for k in kinds)


def test_tampered_chain_reported(tmp_path):
    log = tmp_path / "wall.csv"
    append_row(_row("2026-07-01"), log)
    append_row(_row("2026-07-02"), log)
    rows = list(csv.DictReader(open(log, newline="", encoding="utf-8")))
    rows[0]["base_equity"] = "999999.0"                    # tamper history
    with open(log, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    rep = audit_chain(log)
    assert not rep["chain_ok"] and rep["first_bad_row"] == 0


def test_paper_gate_counts(tmp_path):
    p = tmp_path / "trades.json"
    p.write_text(json.dumps({"A-only": [{"R": 1}] * 31, "base-swing": [{"R": 1}] * 12}))
    rep = audit_trades(p)
    assert rep["A-only"]["paper_gate_30"] == "PASS"
    assert rep["base-swing"]["paper_gate_30"].startswith("NOT MET")


def test_sleeve_completeness(tmp_path):
    p = tmp_path / "sleeve.json"
    pts = [{"date": d} for d in ("2026-07-01", "2026-07-02", "2026-07-06")]   # missing Fri 07-03
    p.write_text(json.dumps({"model": "blend", "inception": "2026-07-01", "points": pts}))
    rep = audit_sleeve(p)
    assert rep["missing_sessions"] == ["2026-07-03"] and not rep["complete"]


def test_config_drift(tmp_path):
    doc = tmp_path / "prereg.md"
    doc.write_text("frozen: vol_target_annual = 0.15, window 42, floor 0.40")
    ok = audit_config_drift(doc, {"vt": "vol_target_annual = 0.15", "win": "window 42"})
    assert ok["ok"]
    bad = audit_config_drift(doc, {"vt": "vol_target_annual = 0.20"})
    assert not bad["ok"] and "vt" in bad["missing_or_drifted"]
