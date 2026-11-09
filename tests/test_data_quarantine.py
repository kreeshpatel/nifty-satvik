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


def _run(cache, held=(), refetch=None, universe=None, ref=None):
    ref = _ref(list(cache)) if ref is None else ref
    return quarantine_or_halt(cache, list(held), {}, universe_size=universe or len(cache),
                              refetch=refetch, ref=ref, known={})


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
    assert "adjustment factor fell x4" in q["reason"]
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

    out, rec = _run(cache, refetch=refetch)
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

    def setup(cache, full=None, held=()):
        state.update(cache=cache, full=full or {}, held=list(held))
        _ref(list(cache)).to_parquet(ref_path)

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
    monkeypatch.setattr("nq.data.history_guard.open_tickers", lambda *_a, **_k: set())   # not the real book
    return setup


def test_refresh_quarantines_one_name_and_the_scan_proceeds(wired):
    wired({"AAA": _clean(), "BBB": _split_broken(), "CCC": _clean()}, full={"BBB": _split_broken()})
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
    wired(cache, full={})
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
    n = C._mask_quarantined(P, {"X"}, pd.Timestamp("2026-11-02"))
    assert n == {"signals_cleared": 1, "entry_windows_dropped": 1}
    assert P["X"]["last_signal"] is None and sorted(P["X"]["entry_win"]) == [0, 1]   # history kept
    assert P["Y"]["last_signal"] is not None and P["Y"]["entry_win"] == {2: ("y",)}
