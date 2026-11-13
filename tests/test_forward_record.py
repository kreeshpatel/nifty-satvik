"""ADR-0018: the append-only forward record. Closed history is immutable; the rebuild is an audit.

End-to-end on the hermetic R94 fixture (tests/fixtures, no network): a scan at week A is published the
old way, then a later scan at week B runs the cron's `_forward_record_publish`, which seeds the ledger
from A's published files and merges B's rebuild into it. Every test first proves that the rebuild DID
change the past (so the assertion that the record did not is never vacuous).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import forward_record as FR  # noqa: E402
import run_bhanushali_cron as C  # noqa: E402
import run_bhanushali_weekly_rank as R94  # noqa: E402
from build_r94_golden_fixture import synth_universe  # noqa: E402

START = "2018-01-01"
CUT_A = "2019-06-28"          # the frozen week (a Friday)
CUT_B = "2019-08-30"          # the scan that merges into it


@pytest.fixture(scope="module")
def universe():
    return synth_universe()


def _scan(universe, cut, *, rule=None, mutate=None, drop=()):
    """The cron's book-building steps on the fixture, truncated at `cut`."""
    ohlcv, index = universe
    o = {t: df[df.index <= pd.Timestamp(cut)].copy() for t, df in ohlcv.items() if t not in drop}
    if mutate:
        mutate(o)
    rule = rule if rule is not None else C.LIVE_EXIT
    P = R94.prep_weekly_rank(o, index_provider=lambda _t: index)
    a_set = R94.grade_a_entries(P)
    out_paper = R94.backtest(P, None, ledger=[], start=START, return_state=True, a_grade=a_set,
                             **C.LIVE_DISCIPLINE, **rule)
    led_all: list = []
    tracker_kw = dict(ledger=led_all, start=START, return_state=True, uncapped=True, a_grade=a_set,
                      **C.LIVE_DISCIPLINE, **rule)
    out_all = R94.backtest(P, None, **tracker_kw)
    gen = str(max(pd.Timestamp(s["dates"][-1]) for s in P.values()).date())
    outputs = C.build_envelopes(P, out_all, led_all, out_paper, gen, None)
    return dict(P=P, a_set=a_set, out_paper=out_paper, gen=gen, outputs=outputs, led_all=led_all,
                tracker_kw=tracker_kw)


def _publish_old_way(sd: Path, s: dict) -> None:
    env, hist, an, pf, hdf = s["outputs"]
    FR.write_published(dict(envelope=env, sig_hist=hist, analytics=an, portfolio=pf, hist_df=hdf), sd)


def _publish_forward(sd: Path, s: dict) -> dict:
    """What `forward_record.py cron` does to the tracker's envelope."""
    env, hist, an, pf, hdf = FR.publish_scan(
        sd, s["gen"], s["outputs"], s["led_all"],
        FR.tracker_rebuilder(s["P"], None, s["tracker_kw"], s["out_paper"], s["gen"]))
    merged = dict(envelope=env, sig_hist=hist, analytics=an, portfolio=pf, hist_df=hdf)
    FR.write_published(merged, sd)
    return merged


def _closed(hist):
    return {FR.key_of(r): r for r in hist if r.get("status") != "ACTIVE"}


def _audit(sd: Path) -> dict:
    return json.loads((sd / "forward_record" / "audit.json").read_text(encoding="utf-8"))


# ── migration ────────────────────────────────────────────────────────────────────────────────

def test_first_run_on_unchanged_data_republishes_the_committed_record_byte_for_byte(universe, tmp_path):
    a = _scan(universe, CUT_A)
    _publish_old_way(tmp_path / "old", a)
    _publish_old_way(tmp_path / "fwd", a)
    _publish_forward(tmp_path / "fwd", a)                       # seeds from the files, merges the same scan
    for f in FR._PUBLISHED_FILES:
        assert (tmp_path / "old" / f).read_bytes() == (tmp_path / "fwd" / f).read_bytes(), f
    led = FR.load_ledger(tmp_path / "fwd")
    assert led["state"]["as_of"] == a["gen"] and led["state"]["closed"], "the ledger must hold the record"
    assert _audit(tmp_path / "fwd")["level"] == "green"


# ── 1. a restated past bar does not change a closed trade; 4. the audit reports it ────────────

def test_a_restated_past_bar_does_not_change_a_closed_trade(universe, tmp_path):
    a = _scan(universe, CUT_A)
    _publish_old_way(tmp_path, a)
    frozen = _closed(a["outputs"][1])
    victim = next(k for k, r in frozen.items() if r["close_date"] > "2018-06-01")
    t, entry = victim.split("|")
    close = frozen[victim]["close_date"]

    def restate(o):                       # the vendor re-adjusts the bars inside the trade's holding window
        df = o[t]
        m = (df.index >= pd.Timestamp(entry)) & (df.index <= pd.Timestamp(close))
        df.loc[m, ["Open", "High", "Low", "Close"]] *= 0.93

    b = _scan(universe, CUT_B, mutate=restate)
    rebuilt = _closed(b["outputs"][1])
    assert rebuilt.get(victim) != frozen[victim], "fixture did not restate the trade - test would be vacuous"

    merged = _publish_forward(tmp_path, b)
    rec = _closed(merged["sig_hist"])
    for k, row in frozen.items():
        assert rec[k] == row, f"closed trade {k} changed"
    audit = _audit(tmp_path)
    assert audit["level"] == "red"
    assert any(f["trade"] == victim and f["kind"] in ("restated", "vanished_closed") for f in audit["red"])
    log = (tmp_path / "forward_record" / "drift.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(log[-1])["level"] == "red"


# ── 2. a new universe entrant does not create a past signal ───────────────────────────────────

def test_a_new_universe_entrant_creates_no_past_signal(universe, tmp_path):
    entrant = "ALPHA"
    a = _scan(universe, CUT_A, drop=(entrant,))
    _publish_old_way(tmp_path, a)
    b = _scan(universe, CUT_B)
    retro = [k for k in list(_closed(b["outputs"][1])) + [FR.key_of(r) for r in b["outputs"][1]]
             if k.startswith(entrant + "|") and k.split("|")[1] <= a["gen"]]
    assert retro, "the entrant has no past trade in the rebuild - test would be vacuous"

    merged = _publish_forward(tmp_path, b)
    a_keys = {FR.key_of(r) for r in a["outputs"][1]}
    for r in merged["sig_hist"]:
        k = FR.key_of(r)
        assert k in a_keys or k.split("|")[1] > a["gen"], f"{k} entered in a frozen week"
    assert all(c.get("ticker") != entrant or not c.get("bought_date") or c["bought_date"] > a["gen"]
               for c in merged["envelope"]["signals"])
    for k, row in _closed(a["outputs"][1]).items():
        assert _closed(merged["sig_hist"])[k] == row
    supp = {f["trade"] for f in _audit(tmp_path)["amber"] if f["kind"] == "suppressed_retroactive"}
    assert set(retro) <= supp


# ── 3. an exit-rule change reaches only trades opened after it, with no effective-date gate ────

def test_an_exit_rule_change_applies_only_to_trades_opened_after_it(universe, tmp_path, monkeypatch):
    old_rule, new_rule = C.LIVE_EXIT, C.P2_EXIT
    a = _scan(universe, CUT_A, rule=old_rule)
    _publish_old_way(tmp_path, a)
    _publish_forward(tmp_path, a)              # switched on (seeded) in a week the rule did not change
    open_at_a = {FR.key_of(r) for r in a["outputs"][1] if r["status"] == "ACTIVE"}

    monkeypatch.setattr(C, "LIVE_EXIT", new_rule)              # the owner changes the live exit
    b_new = _scan(universe, CUT_B, rule=new_rule)
    b_old = _scan(universe, CUT_B, rule=old_rule)
    new_rows = {FR.key_of(r): r for r in b_new["outputs"][1]}
    old_rows = {FR.key_of(r): r for r in b_old["outputs"][1]}
    differs = [k for k in open_at_a if new_rows.get(k) != old_rows.get(k)]
    assert differs, "the two rules agree on every held trade - test would be vacuous"

    merged = _publish_forward(tmp_path, b_new)
    rec = {FR.key_of(r): r for r in merged["sig_hist"]}
    for k in open_at_a:                                          # opened before the change: the OLD rule
        assert rec[k] == old_rows[k], k
    after = [k for k in rec if k.split("|")[1] > a["gen"]]
    assert after, "no trade opened after the change - test would be vacuous"
    for k in after:                                              # opened after it: the NEW rule
        assert rec[k] == new_rows[k], k
    led = FR.load_ledger(tmp_path)
    assert FR.exit_rule_fp(old_rule) in led["exit_rules"] and led["current_rule"] == FR.exit_rule_fp(new_rule)
    for k, row in _closed(a["outputs"][1]).items():          # closed before the change: untouched
        assert rec[k] == row
    # No TRADE finding: a rule change alone must not read as a restatement. (The ₹10L capital book is not
    # pinned - it is re-simulated under the new rule and chain-linked - so a NAV-gap amber is expected.)
    audit = _audit(tmp_path)
    assert audit["level"] != "red"
    assert [f["kind"] for f in audit["red"] + audit["amber"]] in ([], ["nav_level_gap"])
    src = (ROOT / "scripts" / "forward_record.py").read_text(encoding="utf-8")
    assert "EFFECTIVE" not in src, "the forward record must not need an effective-date constant"


# ── merge mechanics (unit level) ──────────────────────────────────────────────────────────────

def _pub(closed=(), active=(), nav=(), as_of="2026-01-09"):
    hist = [dict(ticker=t, signal_date=d, status="HIT_STOP", entry=100.0, close_price=95.0, close_date=c,
                 return_pct=-5.0, pnl_pct=-5.0, r_multiple=r, net_pnl=-1.0, days_since=5, hold_days=5,
                 exit_reason="stop") for t, d, c, r in closed]
    hist += [dict(ticker=t, signal_date=d, status="ACTIVE", entry=100.0) for t, d in active]
    cards = [dict(ticker=t, bought_date=d, signal_date=d, status="ACTIVE") for t, d in active]
    env = {"generated_at": as_of, "signals": cards, "n_positions": len(active)}
    hdf = pd.DataFrame({"date": [d for d, _ in nav], "total_value": [v for _, v in nav]})
    return FR.published(env, hist, {}, {"total_value": None}, hdf)


def test_a_rerun_of_the_latest_week_remerges_against_its_parent_and_time_never_runs_backwards():
    rule = C.LIVE_EXIT
    fp = FR.exit_rule_fp(rule)
    led = FR.seed(_pub(active=[("X", "2026-01-05")], as_of="2026-01-09"), "2026-01-09", rule, seeded_from="t")
    w2 = _pub(closed=[("X", "2026-01-05", "2026-01-13", -1.0)], as_of="2026-01-16")
    _, led2, _ = FR.merge(led, "2026-01-16", {fp: w2}, rule)
    # the re-run of 01-16 sees X still open (a corrected rebuild): it replaces the week, not the past
    _, led3, audit = FR.merge(led2, "2026-01-16", {fp: _pub(active=[("X", "2026-01-05")], as_of="2026-01-16")}, rule)
    assert audit["base_as_of"] == "2026-01-09" and "X|2026-01-05" in led3["state"]["open"]
    with pytest.raises(FR.ForwardRecordError):
        FR.merge(led3, "2026-01-02", {fp: w2}, rule)


def test_an_amendment_lets_the_rebuild_win_once_and_nav_is_chain_linked():
    rule = C.LIVE_EXIT
    fp = FR.exit_rule_fp(rule)
    seed = _pub(closed=[("X", "2026-01-05", "2026-01-07", -1.0)], nav=[("2026-01-08", 100.0), ("2026-01-09", 110.0)])
    led = FR.seed(seed, "2026-01-09", rule, seeded_from="t")
    rb = _pub(closed=[("X", "2026-01-05", "2026-01-07", -2.0)],
              nav=[("2026-01-08", 100.0), ("2026-01-09", 100.0), ("2026-01-12", 105.0)], as_of="2026-01-12")
    m, led2, audit = FR.merge(led, "2026-01-12", {fp: rb}, rule)
    assert _closed(m["sig_hist"])["X|2026-01-05"]["r_multiple"] == -1.0          # frozen wins
    assert [f["kind"] for f in audit["red"]] == ["restated"]
    nav = list(zip(m["hist_df"]["date"], m["hist_df"]["total_value"]))
    assert nav == [("2026-01-08", 100.0), ("2026-01-09", 110.0), ("2026-01-12", pytest.approx(115.5))]
    m2, led3, audit2 = FR.merge(led2, "2026-01-13", {fp: rb}, rule,
                                amendments={"X|2026-01-05": "2026-01-13: vendor fix, declared"})
    assert _closed(m2["sig_hist"])["X|2026-01-05"]["r_multiple"] == -2.0          # declared: rebuild wins
    assert audit2["amendments_applied"] and audit2["level"] == "green"
    _, _, audit3 = FR.merge(led3, "2026-01-14", {fp: rb}, rule,
                            amendments={"X|2026-01-05": "2026-01-13: vendor fix, declared"})
    assert not audit3["amendments_applied"], "an amendment applies once"


def test_off_by_default_the_production_cron_does_not_know_the_forward_record_exists():
    """OFF = the scanner workflow runs run_bhanushali_cron.py, which is untouched by ADR-0018."""
    src = (ROOT / "scripts" / "run_bhanushali_cron.py").read_text(encoding="utf-8")
    assert "forward_record" not in src
    wf = (ROOT / ".github" / "workflows" / "cron-bhanushali-scanner.yml").read_text(encoding="utf-8")
    assert "forward_record.py cron" not in wf, "switching on is an owner decision (ADR-0018)"


def test_the_cron_wrapper_routes_only_the_tracker_envelope_and_restores_its_seams(tmp_path, monkeypatch):
    """`cron_main` runs the unmodified main(); a stub main() stands in for it so no data is needed."""
    seen = {}

    def fake_main(argv=None):
        P = {}
        R94.backtest(P, None, ledger=[], start=START, return_state=True, a_grade=set())     # paper book
        led = []
        R94.backtest(P, None, ledger=led, start=START, return_state=True, uncapped=True, a_grade=set())
        seen["record"] = C.build_envelopes(P, {"tracker": True}, led, {}, "2026-01-09", None)
        seen["shadow"] = C.build_envelopes(P, {"shadow": True}, [], {}, "2026-01-09", None)
        return 0

    calls = []
    monkeypatch.setattr(C, "main", fake_main)
    monkeypatch.setattr(R94, "backtest", lambda P, mem, **kw: {})
    monkeypatch.setattr(C, "build_envelopes", lambda *a, **k: ("raw", a[1]))
    monkeypatch.setattr(FR, "publish_scan", lambda sd, gen, outs, led, rb: calls.append((sd, outs)) or "merged")
    orig_bt, orig_be = R94.backtest, C.build_envelopes
    assert FR.cron_main(["--state-dir", str(tmp_path)]) == 0
    assert seen == {"record": "merged", "shadow": ("raw", {"shadow": True})}
    assert calls == [(tmp_path, ("raw", {"tracker": True}))]
    assert R94.backtest is orig_bt and C.build_envelopes is orig_be, "the seams must be restored"


def test_the_seams_the_wrapper_relies_on_still_exist_in_the_cron():
    """`cron_main` assumes main() builds the tracker (the first uncapped grade-A backtest) BEFORE it builds
    the envelopes from that tracker's ledger. If main() is reordered, this goes red, not the wrapper."""
    src = (ROOT / "scripts" / "run_bhanushali_cron.py").read_text(encoding="utf-8")
    body = src[src.index("def main("):]
    tracker = body.index("out_all = R94.backtest(")
    assert "uncapped=True" in body[tracker:tracker + 200] and "a_grade=a_set" in body[tracker:tracker + 300]
    first_uncapped = body.index("uncapped=True")
    assert first_uncapped > tracker, "another uncapped backtest now precedes the tracker"
    env = body.index("build_envelopes(")
    assert tracker < env and "out_all, led_all" in body[env:env + 120]
