"""ADR-0018 shadow mode: run the forward record after the live scan, never touching the published results,
and classify every difference from the live commit as expected (frozen past vs rebuilt past) or not.

The wrapped cron's `main()` is replaced by a stand-in that drives the SAME seams the real one does (the
tracker's uncapped grade-A backtest, then `build_envelopes` on its ledger, then the writes into
`--state-dir`), with outputs from the hermetic R94 fixture. So the merge, the audit, the parity check and
the classifier all run for real; only the data download is stood in for.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import forward_record as FR  # noqa: E402
import forward_record_shadow as S  # noqa: E402
import run_bhanushali_cron as C  # noqa: E402
import run_bhanushali_weekly_rank as R94  # noqa: E402
import test_forward_record as TF  # noqa: E402  (the fixture scan helpers)


@pytest.fixture(scope="module")
def universe():
    from build_r94_golden_fixture import synth_universe
    return synth_universe()


def _results_fingerprint() -> dict:
    out = {}
    for p in sorted((ROOT / "results").rglob("*")):
        if p.is_file():
            out[p.relative_to(ROOT).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _stage(tmp_path, universe, mutate=None):
    """Week A archived, week B published live (the old way), and a cron stand-in that reproduces B."""
    a = TF._scan(universe, TF.CUT_A)
    b = TF._scan(universe, TF.CUT_B, mutate=mutate)
    live = tmp_path / "live"
    TF._publish_old_way(live, b)
    TF._publish_old_way(live / "archive" / a["gen"], a)
    TF._publish_old_way(live / "archive" / b["gen"], b)       # the live scan archives its own week too
    return a, b, live


def _stand_in(b):
    def fake_main(argv):
        sd = Path(argv[argv.index("--state-dir") + 1])
        led: list = []
        R94.backtest(None, None, ledger=led, uncapped=True, a_grade=set())     # the tracker seam
        outs = C.build_envelopes(None, None, led, None, b["gen"], None)        # the envelope seam
        env, hist, an, pf, hdf = outs
        FR.write_published(dict(envelope=env, sig_hist=hist, analytics=an, portfolio=pf, hist_df=hdf), sd)
        return 0

    def fake_backtest(P, mem, **kw):
        if kw.get("ledger") is not None and kw.get("uncapped"):
            kw["ledger"].extend(b["led_all"])
        return {}
    return fake_main, fake_backtest


def _run(tmp_path, monkeypatch, b, live):
    fake_main, fake_bt = _stand_in(b)
    monkeypatch.setattr(C, "main", fake_main)
    monkeypatch.setattr(R94, "backtest", fake_bt)
    monkeypatch.setattr(C, "build_envelopes", lambda *a, **k: b["outputs"])
    return S.run_shadow(tmp_path / "out", ["--start", TF.START], live_dir=live)


# ── the output-dir override: nothing reaches results/ ─────────────────────────────────────────

def test_a_shadow_run_writes_only_into_its_out_dir(tmp_path, monkeypatch, universe):
    a, b, live = _stage(tmp_path, universe)
    before = _results_fingerprint()
    live_before = {p.name: p.read_bytes() for p in live.glob("*.json*")}
    r = _run(tmp_path, monkeypatch, b, live)
    assert _results_fingerprint() == before, "a shadow run wrote into the repo's results/"
    assert {p.name: p.read_bytes() for p in live.glob("*.json*")} == live_before, "it touched the live record"
    out = tmp_path / "out"
    assert (out / "forward_record" / "ledger.json").exists() and (out / S.REPORT_NAME).exists()
    assert (out / "raw" / "signals_history_weekly.json").exists()
    assert r["base_as_of"] == a["gen"] and r["live_as_of"] == b["gen"]


def test_the_out_dir_can_never_be_the_published_results(tmp_path):
    with pytest.raises(S.ShadowError):
        S.run_shadow(ROOT / "results" / "fr_shadow_tmp", [], live_dir=ROOT / "results")
    with pytest.raises(S.ShadowError):
        S.run_shadow(tmp_path / "live" / "x", [], live_dir=tmp_path / "live")
    with pytest.raises(S.ShadowError):
        S.run_shadow(tmp_path / "out", ["--state-dir", "results"], live_dir=tmp_path / "live")


def test_the_previous_record_is_the_latest_archived_week_before_the_live_one(tmp_path):
    for name in ("2026-10-23", "2026-10-30", "2026-10-30__rerun-20261101T000000Z", "2026-11-06"):
        d = tmp_path / name
        d.mkdir()
        for f in (S.ENV, S.HIST):
            (d / f).write_text("{}", encoding="utf-8")
    assert S.previous_record(tmp_path, "2026-11-06").name == "2026-10-30__rerun-20261101T000000Z"


# ── the classifier ────────────────────────────────────────────────────────────────────────────

def test_a_restated_week_is_clean_with_every_difference_expected(tmp_path, monkeypatch, universe):
    def restate(o):                       # rewrite the bars of every trade closed by A
        for t in o:
            m = o[t].index <= pd.Timestamp("2018-12-31")
            o[t].loc[m, ["Open", "High", "Low", "Close"]] *= 0.95
    a, b, live = _stage(tmp_path, universe, mutate=restate)
    r = _run(tmp_path, monkeypatch, b, live)
    assert r["parity"] == "IDENTICAL"
    assert r["n_expected"] > 0, "the restatement produced no difference - test would be vacuous"
    assert r["verdict"] == "CLEAN", [x for x in r["differences"] if x["class"] == "unexpected"]
    assert any("frozen past" in x["why"] for x in r["differences"] if x["file"] == S.HIST)


def test_a_difference_no_audit_finding_explains_is_unexpected(tmp_path, monkeypatch, universe):
    a, b, live = _stage(tmp_path, universe)
    env = json.loads((live / S.ENV).read_text(encoding="utf-8"))
    env["cash"] = env["cash"] + 1.0                            # the live commit says something else
    (live / S.ENV).write_text(json.dumps(env, indent=2), encoding="utf-8")
    r = _run(tmp_path, monkeypatch, b, live)
    assert r["verdict"] == "NOT CLEAN"
    un = [x for x in r["differences"] if x["class"] == "unexpected"]
    assert any(x["item"] == "whole file (parity)" for x in un), "parity must catch a different vintage"
    assert any(x["file"] == S.ENV and x["item"] == "cash" for x in un)


def test_classifier_rules_on_hand_made_records():
    row = dict(ticker="X", signal_date="2026-01-05", status="HIT_STOP", r_multiple=-1.0)
    live = {"env": {"generated_at": "d", "signals": []}, "hist": [dict(row, r_multiple=-2.0),
            dict(ticker="Z", signal_date="2026-01-06", status="ACTIVE")], "an": {}, "pf": {}, "nav": []}
    rec = {"env": {"generated_at": "d", "signals": []}, "hist": [row], "an": {}, "pf": {}, "nav": []}
    explained = {"base_as_of": "2026-01-09", "nav_chain_link_scale": 1.0,
                 "red": [{"kind": "restated", "trade": "X|2026-01-05"}],
                 "amber": [{"kind": "suppressed_retroactive", "trade": "Z|2026-01-06"}], "info": []}
    out = S.classify(live, rec, explained, set(), set())
    assert {x["class"] for x in out} == {"expected"}
    silent = dict(explained, red=[], amber=[])
    out = S.classify(live, rec, silent, set(), set())
    assert {x["class"] for x in out} == {"unexpected"}, "a difference the audit does not name is unexpected"
    # a post-frozen NAV row that is not a clean chain-link is unexpected; a frozen-past row is expected
    live_n = dict(live, hist=rec["hist"], nav=[["2026-01-08", 100.0], ["2026-01-12", 105.0]])
    rec_n = dict(rec, nav=[["2026-01-08", 101.0], ["2026-01-12", 106.0]])
    out = S.classify(live_n, rec_n, silent, set(), set())
    assert [x["class"] for x in out if x["file"] == S.NAV] == ["expected", "unexpected"]


def test_the_shadow_workflow_cannot_publish():
    wf = (ROOT / ".github" / "workflows" / "cron-forward-record-shadow.yml").read_text(encoding="utf-8")
    assert "contents: read" in wf and "contents: write" not in wf
    assert "git push" not in wf and "git commit" not in wf and "git add" not in wf
    assert "actions/cache/restore@" in wf and "actions/cache@" not in wf, "restore only: never save the cache"
    assert '--out-dir "$RUNNER_TEMP/fr_shadow"' in wf
    assert "workflows: [\"cron-bhanushali-scanner\"]" in wf and "workflow_dispatch" in wf
