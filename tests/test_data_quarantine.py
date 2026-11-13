"""One bad name must not cost the whole weekly scan (prod-fix 2026-11-08).

The adjustment guard halted the 2026-10-10, 10-31 and 11-07 scans over ONE stock each. Pinned here:

  * a single-name violation is SELF-HEALED if a full re-fetch clears it (a split), else QUARANTINED, and
    the scan proceeds;
  * a quarantined HELD name keeps its position, is never exited on suspect data and keeps its last good
    stop; a quarantined unheld name cannot signal;
  * MORE than max(5, 2% of the universe) bad names, or a bad index series, still HALTS;
  * with the flag off, the old halt-on-first-violation behaviour is untouched.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import run_bhanushali_cron as C  # noqa: E402
import run_bhanushali_weekly_rank as R94  # noqa: E402
from build_r94_golden_fixture import START_FIX, synth_universe  # noqa: E402
from nq.data import adjustment_guard as AG  # noqa: E402
from nq.data.data_quarantine import (  # noqa: E402
    SystemicDataFailure, check_index_series, quarantine_or_halt, systemic_limit,
)
from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT  # noqa: E402

BARS = pd.bdate_range("2025-01-01", periods=420)
PROBES = [BARS[i] for i in (20, 120, 220, 320, 419)]


def _ref(symbols) -> pd.DataFrame:
    return pd.DataFrame([{"symbol": s, "date": d, "close": 100.0} for s in symbols for d in PROBES])


def _clean() -> pd.DataFrame:
    return pd.DataFrame({"Close": 100.0}, index=BARS)


def _split_broken() -> pd.DataFrame:
    """Post-split basis (/4) from probe 3 to probe 4 only: an adjustment factor that FALLS x4 then recovers."""
    c = pd.Series(100.0, index=BARS)
    c[(BARS >= PROBES[2]) & (BARS < PROBES[3])] = 25.0
    return pd.DataFrame({"Close": c})


def _registry(cache) -> dict:
    """A registered (KNOWN) seam for every name whose series carries the x4 step, dated inside the live window."""
    return {(t, str(PROBES[2].date())): {"factor": 4.0, "cause": "test", "provenance": "test"}
            for t, df in cache.items() if (df["Close"] < 50).any()}


def _run(cache, held=(), refetch=None, universe=None, ref=None, register=True):
    """register=True: the bad names are KNOWN (registered) seams; False: UNKNOWN (unregistered) violations."""
    ref = _ref(list(cache)) if ref is None else ref
    return quarantine_or_halt(cache, list(held), {}, universe_size=universe or len(cache),
                              refetch=refetch, ref=ref, known=_registry(cache) if register else {})


# ── thresholds ──────────────────────────────────────────────────────────────────────────────────────
def test_systemic_limit_is_max_of_five_and_two_percent():
    assert systemic_limit(50) == 5 and systemic_limit(250) == 5
    assert systemic_limit(500) == 10 and systemic_limit(551) == 12


# ── one bad name: quarantine, do not halt ──────────────────────────────────────────────────────────
def test_a_single_bad_name_is_quarantined_and_the_rest_is_untouched():
    cache = {"AAA": _clean(), "BBB": _split_broken(), "CCC": _clean()}
    out, rec = _run(cache)                                   # no re-fetch available -> cannot heal
    assert [q["ticker"] for q in rec["quarantined"]] == ["BBB"]
    q = rec["quarantined"][0]
    assert q["held"] is False and q["action"] == "excluded_from_new_signals"
    assert "registered seam" in q["reason"]
    assert out["AAA"] is cache["AAA"] and out["CCC"] is cache["CCC"]


def test_a_held_bad_name_is_flagged_as_kept_and_frozen():
    cache = {"AAA": _clean(), "BBB": _split_broken()}
    _, rec = _run(cache, held=["BBB"])
    q = rec["quarantined"][0]
    assert q["held"] is True and q["action"] == "position_kept_stop_frozen_no_exit"


def test_self_heal_by_full_refetch_clears_a_split():
    cache = {"AAA": _clean(), "BBB": _split_broken()}
    asked: list = []

    def refetch(tickers):
        asked.append(list(tickers))
        return {"BBB": _clean()}                              # the vendor's clean, fully re-adjusted history

    out, rec = _run(cache, refetch=refetch, register=False)
    assert asked == [["BBB"]], "only the offending name is re-fetched"
    assert rec["healed"] == ["BBB"] and rec["quarantined"] == []
    assert out["BBB"]["Close"].eq(100.0).all()                # the healed series replaced the broken one


def test_a_refetch_that_is_still_broken_ends_in_quarantine():
    cache = {"AAA": _clean(), "BBB": _split_broken()}
    _, rec = _run(cache, refetch=lambda t: {"BBB": _split_broken()})   # a seam the VENDOR serves
    assert rec["healed"] == [] and [q["ticker"] for q in rec["quarantined"]] == ["BBB"]
    assert rec["quarantined"][0]["self_heal_attempted"] is True


def test_a_failing_or_empty_refetch_degrades_to_quarantine_not_a_crash():
    cache = {"AAA": _clean(), "BBB": _split_broken()}

    def boom(_t):
        raise RuntimeError("yfinance down")

    for rf in (boom, lambda t: {}, lambda t: {"BBB": pd.DataFrame()}):
        _, rec = _run(cache, refetch=rf)
        assert [q["ticker"] for q in rec["quarantined"]] == ["BBB"]


def test_no_violation_is_an_empty_record():
    _, rec = _run({"AAA": _clean(), "BBB": _clean()})
    assert rec["flagged"] == [] and rec["quarantined"] == [] and rec["healed"] == []


# ── systemic: still halt ───────────────────────────────────────────────────────────────────────────
def test_many_bad_names_halt_the_scan():
    cache = {f"S{i}": _split_broken() for i in range(6)}      # 6 > max(5, 2% of 6)
    with pytest.raises(SystemicDataFailure, match="SYSTEMIC DATA FAILURE"):
        _run(cache)


def test_exactly_the_limit_is_still_quarantine():
    cache = {f"S{i}": _split_broken() for i in range(5)}
    _, rec = _run(cache)
    assert len(rec["quarantined"]) == 5


def test_a_refetch_is_not_spent_on_an_outage():
    cache = {f"S{i}": _split_broken() for i in range(6)}
    calls: list = []
    with pytest.raises(SystemicDataFailure):
        _run(cache, refetch=lambda t: calls.append(t) or {})
    assert calls == []


def test_the_limit_scales_with_the_universe():
    cache = {"AAA": _clean(), **{f"S{i}": _split_broken() for i in range(8)}}
    _, rec = _run(cache, universe=500)                        # limit 10: eight bad names are per-name defects
    assert len(rec["quarantined"]) == 8
    with pytest.raises(SystemicDataFailure):
        _run(cache, universe=100)                             # limit 5


def test_a_bad_index_series_halts(tmp_path):
    def write(closes, start="2020-01-01"):
        f = tmp_path / "n50.csv"
        pd.DataFrame({"date": pd.bdate_range(start, periods=len(closes)), "nifty50_close": closes}).to_csv(f, index=False)
        return f

    good = [10000.0 + i for i in range(300)]
    check_index_series(write(good))                           # clean passes
    with pytest.raises(SystemicDataFailure, match="one-day move"):
        check_index_series(write(good[:150] + [good[150] * 0.5] + good[151:]))
    with pytest.raises(SystemicDataFailure, match="too short"):
        check_index_series(write(good[:50]))
    with pytest.raises(SystemicDataFailure, match="behind the price data"):
        check_index_series(write(good), as_of="2030-01-01")
    with pytest.raises(SystemicDataFailure, match="missing"):
        check_index_series(tmp_path / "absent.csv")


# ── through _refresh_ohlcv: the real wiring ────────────────────────────────────────────────────────
@pytest.fixture()
def wired(tmp_path, monkeypatch):
    """_refresh_ohlcv against a synthetic cache: no network, no real book, own raw-close reference."""
    import nq.data.ohlcv as O
    import run_cpcv

    state = {"cache": {}, "full": {}, "held": []}
    ref_path = tmp_path / "ref.parquet"

    def setup(cache, full=None, held=(), known=False):
        state.update(cache=cache, full=full or {}, held=list(held))
        _ref(list(cache)).to_parquet(ref_path)
        monkeypatch.setattr(AG, "KNOWN_SEAMS", _registry(cache) if known else {})

    def fake_download(tickers, start=None, end=None, min_bars=50, **_):
        if min_bars == 1:                                      # the 25-day top-up: nothing new
            return {}
        return {t: state["full"][t] for t in tickers if t in state["full"]}

    monkeypatch.setattr(C, "load_ohlcv_cache", lambda _p: dict(state["cache"]))
    monkeypatch.setattr(C, "OHLCV_CACHE", tmp_path / "ohlcv.pkl")
    monkeypatch.setattr(O, "download_ohlcv", fake_download)
    monkeypatch.setattr(O, "save_ohlcv_cache", lambda *_a, **_k: None)
    monkeypatch.setattr(run_cpcv, "build_universe", lambda *_a, **_k: list(state["cache"]))
    monkeypatch.setattr(AG, "REFERENCE", ref_path)
    monkeypatch.setattr(AG, "load_book_positions", lambda *_a, **_k: list(state["held"]))
    monkeypatch.setattr(AG, "load_book_entry_dates", lambda *_a, **_k: {})
    monkeypatch.setattr(AG, "KNOWN_SEAMS", {})
    monkeypatch.setattr("nq.data.trading_calendar.filter_ohlcv_non_session", lambda o, **_k: (o, None))  # synthetic bars
    monkeypatch.setattr("nq.data.history_guard.open_tickers", lambda *_a, **_k: set())   # not the real book
    return setup


def test_refresh_quarantines_one_name_and_the_scan_proceeds(wired):
    wired({"AAA": _clean(), "BBB": _split_broken(), "CCC": _clean()}, full={"BBB": _split_broken()}, known=True)
    q: dict = {}
    out = C._refresh_ohlcv("2025-01-01", 520, True, quarantine_out=q)
    assert set(out) == {"AAA", "BBB", "CCC"}
    assert [x["ticker"] for x in q["quarantined"]] == ["BBB"]


def test_refresh_self_heals_a_split_and_quarantines_nothing(wired):
    wired({"AAA": _clean(), "BBB": _split_broken()}, full={"BBB": _clean()})
    q: dict = {}
    out = C._refresh_ohlcv("2025-01-01", 520, True, quarantine_out=q)
    assert q["healed"] == ["BBB"] and q["quarantined"] == []
    assert out["BBB"]["Close"].eq(100.0).all()


def test_refresh_without_the_flag_still_halts_on_one_name(wired):
    wired({"AAA": _clean(), "BBB": _split_broken()}, full={"BBB": _clean()})
    with pytest.raises(ValueError, match="ADJUSTMENT MONOTONICITY VIOLATED"):
        C._refresh_ohlcv("2025-01-01", 520, True)              # quarantine_out=None -> strict legacy halt


def test_refresh_halts_on_a_systemic_failure(wired):
    cache = {f"S{i}": _split_broken() for i in range(6)}
    wired(cache, full={}, known=True)
    with pytest.raises(SystemicDataFailure):
        C._refresh_ohlcv("2025-01-01", 520, True, quarantine_out={})


def test_the_live_flag_is_on_and_the_record_is_contracted():
    assert C.QUARANTINE_NOT_HALT is True
    contracts = (ROOT / "results" / "output_contracts.json").read_text(encoding="utf-8")
    assert "results/data_quarantine.json" in contracts
    assert "!results/data_quarantine.json" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "results/data_quarantine.json" in (
        ROOT / ".github" / "workflows" / "cron-bhanushali-scanner.yml").read_text(encoding="utf-8")


# ── engine: a held quarantined name is kept, frozen, never exited ──────────────────────────────────
@pytest.fixture(scope="module")
def fix():
    ohlcv, index = synth_universe()
    return ohlcv, index


def _bt(ohlcv, index, **kw):
    P = R94.prep_weekly_rank(ohlcv, index_provider=lambda _t: index)
    led: list = []
    out = R94.backtest(P, None, ledger=led, start=START_FIX, return_state=True, uncapped=True,
                       **LIVE_DISCIPLINE, **LIVE_EXIT, **kw)
    return led, out


def _trade(led):
    return next(r for r in led if r["tkr"] == "INDIG" and str(r["entry_date"])[:10] == "2017-12-18")


def test_a_held_quarantined_name_is_kept_with_its_last_good_stop(fix):
    ohlcv, index = fix
    led0, _ = _bt(ohlcv, index)
    t0 = _trade(led0)
    assert t0["reason"] == "sma_break", "precondition: unquarantined, this trade closes"
    last_good = pd.Timestamp(t0["entry_date"]) + pd.Timedelta(days=12)

    led, out = _bt(ohlcv, index, quarantine={"INDIG": last_good})
    assert not any(r["tkr"] == "INDIG" and str(r["entry_date"])[:10] == "2017-12-18" for r in led), \
        "a quarantined position must not be exited on suspect data"
    p = out["open_positions"]["INDIG"]
    assert p["data_quarantine"] == str(last_good.date())

    # its stop is exactly the stop a run that ENDS at the last good date holds: nothing moved afterwards
    cut = {k: v[v.index <= last_good] for k, v in ohlcv.items()}
    _, out_cut = _bt(cut, index[index.index <= last_good] if hasattr(index, "index") else index)
    good = out_cut["open_positions"]["INDIG"]
    assert (p["stop"], p["trail"], p["sh"]) == (good["stop"], good["trail"], good["sh"])


def test_quarantine_off_or_for_another_name_changes_nothing(fix):
    ohlcv, index = fix
    led0, _ = _bt(ohlcv, index)
    assert _bt(ohlcv, index, quarantine=None)[0] == led0
    assert _bt(ohlcv, index, quarantine={})[0] == led0
    assert _bt(ohlcv, index, quarantine={"NOSUCH": pd.Timestamp("2017-01-01")})[0] == led0


def test_sessions_on_or_before_the_last_good_date_run_normally(fix):
    ohlcv, index = fix
    led0, _ = _bt(ohlcv, index)
    end = max(pd.Timestamp(r["exit_date"]) for r in led0)
    led, _ = _bt(ohlcv, index, quarantine={"INDIG": end})      # last good = after every exit: no effect
    assert led == led0


# ── an unheld quarantined name cannot signal ───────────────────────────────────────────────────────
def test_mask_quarantined_clears_the_live_signal_and_only_the_new_windows():
    d = pd.to_datetime(["2026-10-26", "2026-11-02", "2026-11-09"])
    P = {"X": {"dates": list(d), "last_signal": {"rank": 0.1},
               "entry_win": {0: ("w0",), 1: ("w1",), 2: ("w2",)}},
         "Y": {"dates": list(d), "last_signal": {"rank": 0.2}, "entry_win": {2: ("y",)}}}
    n = C._mask_quarantined(P, {"X": pd.Timestamp("2026-11-02")})
    assert n == {"signals_cleared": 1, "entry_windows_dropped": 1}
    assert P["X"]["last_signal"] is None and sorted(P["X"]["entry_win"]) == [0, 1]   # history kept
    assert P["Y"]["last_signal"] is not None and P["Y"]["entry_win"] == {2: ("y",)}


# ── review fixes (2026-11-12) ──────────────────────────────────────────────────────────────────────
def test_a_short_refetch_never_replaces_deep_history():
    cache = {"AAA": _clean(), "BBB": _split_broken()}
    stub = _clean().iloc[-40:]                                # throttled: 40 bars, passes the seam check
    out, rec = _run(cache, refetch=lambda t: {"BBB": stub})
    assert out["BBB"] is cache["BBB"], "the original deep series must be kept"
    assert rec["healed"] == [] and rec["refetch_rejected_too_short"] == ["BBB"]
    assert [q["ticker"] for q in rec["quarantined"]] == ["BBB"]


def test_a_full_depth_refetch_is_still_accepted():
    cache = {"AAA": _clean(), "BBB": _split_broken()}
    out, rec = _run(cache, refetch=lambda t: {"BBB": _clean().iloc[-int(len(BARS) * 0.95):]}, register=False)
    assert rec["healed"] == ["BBB"] and rec["refetch_rejected_too_short"] == []


def test_a_same_week_rerun_keeps_the_recorded_last_good_date():
    as_of = "2026-11-06"                                       # Friday; this week's last bar
    prior = {"quarantined": [{"ticker": "X", "last_good": "2026-10-30"}]}
    # run 1 published this week, so the previous scan IS this week's bar: nothing would be frozen
    got = C._quarantine_last_good(["X", "Y"], prior, "2026-11-06", as_of)
    assert got["X"] == pd.Timestamp("2026-10-30"), "persisted boundary wins"
    assert got["Y"] == pd.Timestamp("2026-10-30"), "a new name is clamped to the previous Friday"


def test_a_new_name_uses_the_last_published_scan_when_it_is_earlier():
    got = C._quarantine_last_good(["X"], None, "2026-10-23", "2026-11-06")
    assert got["X"] == pd.Timestamp("2026-10-23")
    assert C._quarantine_last_good(["X"], None, None, "2026-11-06")["X"] == pd.Timestamp("2026-10-30")


def test_a_rerun_after_publish_still_freezes(fix):
    ohlcv, index = fix
    t0 = _trade(_bt(ohlcv, index)[0])
    good = pd.Timestamp(t0["entry_date"]) + pd.Timedelta(days=12)
    prior = {"quarantined": [{"ticker": "INDIG", "last_good": str(good.date())}]}
    bound = C._quarantine_last_good(["INDIG"], prior, "2018-08-17", "2018-08-17")["INDIG"]
    assert bound == good
    _, out = _bt(ohlcv, index, quarantine={"INDIG": bound})
    assert out["open_positions"]["INDIG"]["data_quarantine"] == str(good.date())


def test_a_frozen_position_is_marked_at_its_last_good_close_not_the_suspect_one(fix):
    ohlcv, index = fix
    t0 = _trade(_bt(ohlcv, index)[0])
    good = pd.Timestamp(t0["entry_date"]) + pd.Timedelta(days=12)
    bad = dict(ohlcv)
    df = ohlcv["INDIG"].copy()
    df.loc[df.index > good, ["Open", "High", "Low", "Close"]] *= 0.5   # an unadjusted 2:1 split
    bad["INDIG"] = df
    last_good_close = float(ohlcv["INDIG"].loc[ohlcv["INDIG"].index <= good, "Close"].iloc[-1])
    entry = float(t0["entry"])

    plog: list = []
    _bt(bad, index, quarantine={"INDIG": good}, position_log=plog)
    frozen = [r for r in plog if r["tkr"] == "INDIG" and abs(r["entry"] - entry) < 0.01 and r["date"] > good]
    assert frozen, "the position must still be logged after the last good date"
    assert all(r["mark_px"] == pytest.approx(last_good_close) for r in frozen), \
        "NAV must carry the frozen position at its last good close"

    plog2: list = []
    _bt(bad, index, position_log=plog2)                                  # unquarantined: marks the suspect close
    assert any(r["tkr"] == "INDIG" and r["date"] > good and r["mark_px"] < 0.6 * last_good_close for r in plog2)


def test_an_exit_already_pending_from_good_data_survives_the_freeze(fix):
    ohlcv, index = fix
    t0 = _trade(_bt(ohlcv, index)[0])
    exit_day = pd.Timestamp(t0["exit_date"])                            # Monday open fill of a Friday decision
    friday = ohlcv["INDIG"].index[ohlcv["INDIG"].index < exit_day][-1]
    led, out = _bt(ohlcv, index, quarantine={"INDIG": friday})
    assert not any(r["tkr"] == "INDIG" and str(r["entry_date"])[:10] == "2017-12-18" for r in led)
    p = out["open_positions"]["INDIG"]
    assert p["data_quarantine"] == str(friday.date())
    assert p["pending"] is not None, "the exit decided from good data must stay queued so the card can say so"


# ── owner decision 2026-11-13: KNOWN problems quarantine, UNKNOWN problems halt ───────────────────────
def test_a_known_seam_is_quarantined_and_its_class_is_recorded():
    cache = {"AAA": _clean(), "BBB": _split_broken()}
    _, rec = _run(cache)
    assert rec["flagged_class"] == {"BBB": "known_seam"}
    assert [(q["ticker"], q["class"]) for q in rec["quarantined"]] == [("BBB", "known_seam")]
    assert "live_seam_escalation" in rec["quarantined"][0]["kinds"]


def test_an_unknown_violation_that_survives_the_refetch_halts_the_scan():
    cache = {"AAA": _clean(), "BBB": _split_broken()}
    with pytest.raises(ValueError, match="ADJUSTMENT MONOTONICITY VIOLATED") as ei:
        _run(cache, refetch=lambda t: {"BBB": _split_broken()}, register=False)
    assert not isinstance(ei.value, SystemicDataFailure), "one unknown name is a diagnosis, not an outage"
    assert "BBB" in str(ei.value)


def test_an_unknown_violation_with_no_refetch_halts_too():
    with pytest.raises(ValueError, match="ADJUSTMENT MONOTONICITY VIOLATED"):
        _run({"AAA": _clean(), "BBB": _split_broken()}, register=False)


def test_a_name_with_both_a_known_and_an_unknown_finding_halts():
    cache = {"AAA": _clean(), "BBB": _split_broken()}
    known = {("BBB", str(PROBES[3].date())): {"factor": 2.0, "cause": "test", "provenance": "test"}}   # other seam
    with pytest.raises(ValueError, match="ADJUSTMENT MONOTONICITY VIOLATED"):
        quarantine_or_halt(cache, [], {}, universe_size=2, refetch=None, ref=_ref(list(cache)), known=known)


def test_a_known_and_an_unknown_name_together_halt_on_the_unknown_one():
    cache = {"AAA": _clean(), "KKK": _split_broken(), "UUU": _split_broken()}
    known = {("KKK", str(PROBES[2].date())): {"factor": 4.0, "cause": "test", "provenance": "test"}}
    with pytest.raises(ValueError, match="UUU"):
        quarantine_or_halt(cache, [], {}, universe_size=3, refetch=None, ref=_ref(list(cache)), known=known)


def test_refresh_halts_on_an_unknown_violation_that_survives_the_refetch(wired):
    wired({"AAA": _clean(), "BBB": _split_broken()}, full={"BBB": _split_broken()}, known=False)
    with pytest.raises(ValueError, match="ADJUSTMENT MONOTONICITY VIOLATED"):
        C._refresh_ohlcv("2025-01-01", 520, True, quarantine_out={})


def test_the_adr_records_the_owner_decision():
    adr = (ROOT / "docs" / "decisions" / "0013-defer-live-seam-repair.md").read_text(encoding="utf-8")
    assert "Amendment 2026-11-13 (owner decision)" in adr and "quarantines the name" in adr


# ── owner decision 2026-11-13: a healed restatement is FLAGGED for approval, never declared ───────────
def _hist(entry=100.0, r=2.0, extra=()):
    rows = [{"ticker": "BBB", "signal_date": "2026-08-31", "status": "CLOSED", "entry": entry,
             "close_price": entry * 1.2, "close_date": "2026-09-30", "r_multiple": r, "exit_reason": "sma_break"},
            {"ticker": "AAA", "signal_date": "2026-08-31", "status": "CLOSED", "entry": 50.0,
             "close_price": 55.0, "close_date": "2026-09-30", "r_multiple": 1.0, "exit_reason": "sma_break"}]
    return rows + list(extra)


def test_a_healed_names_restated_trade_is_flagged_not_declared():
    from nq.data.data_quarantine import pending_restatements
    out = pending_restatements(_hist(), _hist(entry=50.0, r=3.1), {"BBB"}, {})
    assert [r["trade"] for r in out] == ["BBB|2026-08-31"]
    r = out[0]
    assert r["kind"] == "restated" and r["old"]["entry"] == 100.0 and r["new"]["entry"] == 50.0
    assert r["ticker"] == "BBB" and 'history_restatements.json' in r["approve"] and '"BBB|2026-08-31"' in r["approve"]


def test_only_healed_names_are_listed_and_unchanged_history_is_silent():
    from nq.data.data_quarantine import pending_restatements
    assert pending_restatements(_hist(), _hist(), {"BBB"}, {}) == []
    assert pending_restatements(_hist(), _hist(entry=50.0), set(), {}) == []        # not a healed name
    vanished = pending_restatements(_hist(), [h for h in _hist() if h["ticker"] != "BBB"], {"BBB"}, {})
    assert [(r["kind"], r["new"]) for r in vanished] == [("vanished", None)]


def test_a_declared_restatement_stops_being_pending_and_pending_carries_forward():
    from nq.data.data_quarantine import pending_restatements
    carried = pending_restatements(_hist(), _hist(entry=50.0), {"BBB"}, {})
    again = pending_restatements(_hist(), _hist(), set(), {}, carried=carried)       # healed, history now stable
    assert [r["trade"] for r in again] == ["BBB|2026-08-31"], "stays listed until the owner declares it"
    done = pending_restatements(_hist(), _hist(), set(), {"BBB|2026-08-31": "2026-11-13 owner approved"},
                                carried=carried)
    assert done == []


def test_the_declared_file_is_never_written_by_the_scan():
    src = (ROOT / "scripts" / "run_bhanushali_cron.py").read_text(encoding="utf-8")
    assert "RESTATEMENTS_FILE).read_text" in src          # read only: the owner declares, the scan never does
    assert "RESTATEMENTS_FILE).write_text" not in src


def test_the_drift_check_names_the_key_and_how_to_approve(tmp_path, capsys):
    import json as _j
    import check_history_drift as D
    log = tmp_path / "drift.jsonl"
    log.write_text(_j.dumps({"as_of": "2026-11-13", "restated": [{"trade": "BBB|2026-08-31",
                    "changed": {"entry": [100.0, 50.0]}}], "vanished": [], "vanished_open": []}) + "\n")
    q = tmp_path / "q.json"
    q.write_text(_j.dumps({"pending_restatements": [{"ticker": "BBB", "trade": "BBB|2026-08-31"}]}))
    rc = D.main(["--log", str(log), "--declared", str(tmp_path / "none.json"), "--quarantine", str(q)])
    out = capsys.readouterr().out
    assert rc == 1 and "PENDING OWNER APPROVAL" in out and '"BBB|2026-08-31"' in out and "history_restatements.json" in out


def test_scan_health_shows_quarantine_and_pending_restatement(tmp_path):
    import json as _j
    import scan_health as H
    rec = tmp_path / "q.json"
    rec.write_text(_j.dumps({
        "quarantined": [{"ticker": "HHH", "held": True, "class": "known_seam", "reason": "r"},
                        {"ticker": "UUU", "held": False, "class": "known_seam", "reason": "r"}],
        "pending_restatements": [{"ticker": "BBB", "trade": "BBB|2026-08-31", "kind": "restated",
                                  "approve": 'To approve, add "BBB|2026-08-31" to results/history_restatements.json.'}]}))
    r = H.check_data_quarantine(path=rec)
    sev = {f.key: f.severity for f in r.findings}
    assert sev == {"data-quarantine:held:HHH": "RED", "data-quarantine:excluded:UUU": "AMBER",
                   "data-quarantine:pending-restatement:BBB|2026-08-31": "AMBER"}
    assert r.status == "RED" and "check at your broker" in r.findings[0].message
    assert any("OWNER APPROVAL" in f.message and "history_restatements.json" in f.message for f in r.findings)
    assert H.check_data_quarantine(path=tmp_path / "absent.json").status == "GREEN"
