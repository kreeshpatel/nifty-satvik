"""Golden-master FIXTURE BUILDER for the live weekly-swing engine (R94) — constitution M1.

The momentum engine has a byte-identical golden gate (tests/test_stage2_golden.py); the live
swing engine (scripts/run_bhanushali_weekly_rank.py) had none — its "default OFF => byte-identical"
claims were enforced by comments alone (constitution row C7 / menu M1). This builder creates the
harness:

  * a DETERMINISTIC synthetic OHLCV universe (formulaic price paths — no RNG, no market data,
    no network) written to  tests/fixtures/r94_golden_ohlcv.csv, plus a synthetic index series
    for the CRS denominator (ticker __INDEX__ in the same CSV). Using synthetic data keeps the
    fixture hermetic: the live benchmark CSVs and data/ohlcv.pkl mutate weekly, so pinning to
    them would make the golden rot.
  * the EXPECTED outputs of two cells, written to tests/fixtures/r94_golden_expected.json:
      - cell "frozen_defaults": backtest() with every lever at its default — the frozen 0094
        research configuration. This cell may NEVER change; a diff here means the frozen engine
        drifted.
      - cell "live_config": the live grade-A / LIVE_DISCIPLINE / LIVE_EXIT configuration with the
        B-1 staleness gate OFF. This is the PRE-FIX baseline of record, retained permanently so
        the B-1 fix's diff stays visible and auditable.
      - cell "live_config_b1_fixed": what scripts/run_bhanushali_cron.py ACTUALLY runs today —
        the same configuration plus LIVE_STALENESS (capped paper book + uncapped ledger +
        dashboard envelope). Its diff_vs_live_config block is the fix's receipt. This cell
        changes ONLY with a documented owner config change — regenerate in the same commit and
        state the diff (the constitution's fix-with-receipts rule).

The fixture deliberately includes a SUSPENSION case (ticker SUSPX stops printing bars
2021-06-30 while positions are typically still open) so the golden CAPTURES the B-1
absent-bar behaviour of record. When B-1 is fixed behind a cfg gate, the fix's exact effect
shows up as a documented diff of this cell run with the gate on — nothing else may move.

Deterministic by construction: prices are closed-form functions of the bar index (exp trend x
sinusoidal pullback x small sin wiggle); no Date.now, no RNG. Reproducing the expected JSON
requires only this repo's code.

    python scripts/build_r94_golden_fixture.py            # (re)write fixture + expected JSON
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

FIXDIR = ROOT / "tests" / "fixtures"
OHLCV_CSV = FIXDIR / "r94_golden_ohlcv.csv"
EXPECTED_JSON = FIXDIR / "r94_golden_expected.json"

DATES = ("2015-01-01", "2021-12-31")     # ends on a Friday -> last week complete -> cards exist
SUSPEND_AFTER = "2020-09-30"             # SUSPX prints no bars after this (the B-1 case)
START_FIX = "2016-06-01"                 # backtest window start (after the 44w-SMA warm-up)

# ticker -> (p0, growth/yr, pullback_amp, pullback_period_days, phase)
# Growth + DEEP periodic pullbacks: the amplitude is large enough that price cycles from well
# above the 44w SMA down through it, so the golden exercises every exit branch (target tranche,
# blow-off pattern, sma_break, stop) — not just the time cap. Periods/phases are staggered so
# signal weeks differ across names (exercises the CRS-rank fill ordering under the cash cap).
_SPECS = {
    "ALPHA": (120.0, 0.45, 0.20, 190, 0.0),
    "BRAVO": (85.0, 0.32, 0.24, 240, 1.3),
    "CHARL": (240.0, 0.28, 0.22, 165, 2.1),
    "DELTA": (60.0, 0.55, 0.18, 260, 0.7),
    "ECHOX": (150.0, 0.22, 0.26, 210, 2.9),
    "FOXTR": (95.0, 0.40, 0.21, 145, 4.0),
    "GOLFX": (310.0, 0.18, 0.19, 285, 5.1),
    "SUSPX": (70.0, 0.48, 0.23, 175, 0.4),   # truncated after SUSPEND_AFTER
    # KILOX/LIMAX are phase-tuned (offline search, values hard-coded so the fixture stays
    # closed-form) so their LAST COMPLETED week fires a signal. Without them the fixture produced
    # zero FRESH buy cards and the card-construction path — where constitution D5 lives — was
    # entirely unpinned. Their entry window is the week after the data ends, so they never fill:
    # they exist to exercise card arithmetic, not the book.
    "KILOX": (100.0, 0.40, 0.22, 180, 5.0),
    "LIMAX": (340.0, 0.36, 0.26, 195, 3.7),
    # MIKEX also fires on the last completed week, but with a WIDE weekly candle (see _RANGE_MULT)
    # so its signal-week low sits further than max_risk_pct below the entry. That is the case where
    # the discipline stop-lift actually binds — i.e. where constitution D5 (card printed the raw
    # low, book used the lifted stop) produced a real divergence. Without it the D5 fix would be
    # exercised only in its no-op branch.
    "MIKEX": (260.0, 0.38, 0.24, 180, 5.0),
}
# per-ticker multiplier on the intrabar high/low excursion (1.0 = the standard narrow candle)
_RANGE_MULT = {"MIKEX": 18.0}
# Names that TREND UP into a signal then break down hard — these are what fire the stop and
# runner-sma_break branches, so the golden pins every exit path, not just the time cap.
# ticker -> (p0, growth/yr, amp, period, phase, crash_start_bar, crash_rate/yr)
_CRASH_SPECS = {
    # HOTEL/INDIG break down gradually -> the runner's sma_break branch.
    "HOTEL": (200.0, 0.40, 0.16, 200, 0.9, 1180, -0.85),
    "INDIG": (140.0, 0.36, 0.18, 230, 3.4, 1320, -0.70),
    # JULIE collapses VERTICALLY right after its signal -> the weekly close undercuts the stop
    # before the 44w SMA is even reached, pinning the stop branch (and its next-open fill).
    "JULIE": (110.0, 0.44, 0.17, 215, 1.8, 1400, -3.20),
}
_INDEX_SPEC = (10_000.0, 0.08, 0.030, 300, 0.0)   # slow index => stocks' RS trends up


def _path(n: int, p0: float, g: float, amp: float, period: float, phase: float,
          crash_start: int | None = None, crash_rate: float = 0.0) -> np.ndarray:
    t = np.arange(n, dtype=float)
    trend = p0 * np.exp(g * t / 252.0)
    wave = 1.0 + amp * np.sin(2.0 * np.pi * t / period + phase)
    wig = 1.0 + 0.010 * np.sin(0.90 * t) + 0.006 * np.sin(2.30 * t + 1.0)
    path = trend * wave * wig
    if crash_start is not None and crash_start < n:
        k = np.clip(t - crash_start, 0.0, None)
        path = path * np.exp(crash_rate * k / 252.0)
    return path


def synth_universe() -> tuple[dict[str, pd.DataFrame], pd.Series]:
    """The deterministic fixture universe + index series (closed-form, no RNG)."""
    idx = pd.bdate_range(*DATES)
    n = len(idx)
    t = np.arange(n, dtype=float)
    out: dict[str, pd.DataFrame] = {}
    specs = {**{k: (*v, None, 0.0) for k, v in _SPECS.items()}, **_CRASH_SPECS}
    for name, (p0, g, amp, period, phase, cstart, crate) in specs.items():
        close = _path(n, p0, g, amp, period, phase, cstart, crate)
        rm = _RANGE_MULT.get(name, 1.0)
        open_ = np.r_[close[0], close[:-1]] * (1.0 + 0.002 * np.sin(1.7 * t))
        high = np.maximum(open_, close) * (1.0 + rm * (0.004 + 0.003 * np.abs(np.sin(0.7 * t))))
        low = np.minimum(open_, close) * (1.0 - rm * (0.004 + 0.003 * np.abs(np.sin(1.1 * t))))
        volume = 2.0e6 + 1.0e6 * np.sin(0.3 * t) ** 2
        df = pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close,
                           "Volume": volume}, index=idx)
        if name == "SUSPX":
            df = df[df.index <= pd.Timestamp(SUSPEND_AFTER)]
        out[name] = df
    p0, g, amp, period, phase = _INDEX_SPEC
    index = pd.Series(_path(n, p0, g, amp, period, phase), index=idx, name="index")
    return out, index


def _sha16(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _ledger_key(led: list[dict]) -> list:
    return [(r["tkr"], str(r["entry_date"])[:10], str(r.get("exit_date"))[:10],
             str(r.get("reason")), round(float(r.get("R", 0.0)), 3),
             round(float(r["entry"]), 2), round(float(r.get("exit_px", 0.0)), 2)) for r in led]


def _curve_key(curve: pd.Series) -> list:
    return [(str(d.date()), round(float(v), 4)) for d, v in curve.items()]


def _fresh_card_probe(envelope: dict) -> list[dict]:
    """Per FRESH buy card: the record-parity arithmetic now printed, alongside the pre-fix values
    (stop = raw signal-week low, target = +2R off that wider stop). ``delta`` fields are the D5
    divergence this fix closed — zero only when the raw low was already inside the risk cap."""
    from run_bhanushali_cron import TARGET_R
    out = []
    for s in envelope.get("signals", []):
        if s.get("bought_date") or "stop_week_low" not in s:
            continue
        entry, stop, low = float(s["entry"]), float(s["stop"]), float(s["stop_week_low"])
        pre_target = round(entry + TARGET_R * (entry - low), 2)
        out.append({
            "ticker": s["ticker"], "entry": entry,
            "stop_record": stop, "stop_prefix_raw_low": round(low, 2),
            "target_record": float(s["target"]), "target_prefix": pre_target,
            "risk_pct_record": round((entry - stop) / entry * 100, 2),
            "risk_pct_prefix": round((entry - low) / entry * 100, 2),
            "stop_delta": round(stop - low, 2),
            "target_delta": round(float(s["target"]) - pre_target, 2),
            "ext_pct_over_sma44": s.get("ext_pct_over_sma44"),
            "record_would_skip_as_extended": s.get("record_would_skip_as_extended"),
            # lists (not tuples) so the JSON round-trip compares equal to the in-memory run
            "tranche_levels": [[t["type"], t.get("level"), t.get("arm")]
                               for t in (s.get("exit_plan") or {}).get("tranches", [])],
        })
    return sorted(out, key=lambda r: r["ticker"])


def run_cells(ohlcv: dict, index: pd.Series):
    import run_bhanushali_weekly_rank as R94
    from run_bhanushali_cron import LIVE_DISCIPLINE, LIVE_EXIT, build_envelopes

    P = R94.prep_weekly_rank(ohlcv, index_provider=lambda _t: index)

    # ── cell A: the frozen 0094 defaults — may NEVER change ──
    led_a: list = []
    a = R94.backtest(P, None, ledger=led_a, start=START_FIX)
    cell_a = {
        "trades": int(a["trades"]),
        "win_rate": round(float(a["wr"]), 6),
        "expR": round(float(a["expR"]), 6),
        "cagr": round(float(a["cagr"]), 6),
        "sharpe": round(float(a["sharpe"]), 6),
        "max_dd": round(float(a["dd"]), 6),
        "exit_reasons": {k: int(v) for k, v in sorted(a["reasons"].items())},
        "ledger_hash": _sha16(_ledger_key(led_a)),
        "n_ledger": len(led_a),
        "final_equity": round(float(a["curve"].iloc[-1]), 2),
        "curve_hash": _sha16(_curve_key(a["curve"])),
    }

    # ── cell B: the live cron configuration (grade-A, discipline, config-P scaled exit) ──
    a_set = R94.grade_a_entries(P)
    led_paper: list = []
    out_paper = R94.backtest(P, None, ledger=led_paper, start=START_FIX, return_state=True,
                             a_grade=a_set, **LIVE_DISCIPLINE, **LIVE_EXIT)
    led_all: list = []
    out_all = R94.backtest(P, None, ledger=led_all, start=START_FIX, return_state=True,
                           uncapped=True, a_grade=a_set, **LIVE_DISCIPLINE, **LIVE_EXIT)
    last = max(pd.Timestamp(s["dates"][-1]) for s in P.values())
    generated_at = str(last.date())
    envelope, sig_hist, analytics, portfolio, hist_df = build_envelopes(
        P, out_all, led_all, out_paper, generated_at, mem=None)
    # B-1 PROBE (constitution bug B-1): a name whose bars STOP mid-hold is currently unmanageable
    # (exit logic skips on a missing bar) and is marked at ENTRY price in the NAV sum. Pin that
    # behaviour explicitly so the cfg-gated staleness fix shows up as a precise, isolated diff.
    b1 = {}
    for t_, p_ in out_paper["open_positions"].items():
        last_bar = str(pd.Timestamp(P[t_]["dates"][-1]).date())
        if last_bar < generated_at:
            b1[t_] = {"last_bar": last_bar,
                      "entry": round(float(p_["en"]), 2),
                      "entry_date": str(p_["rec"]["entry_date"])[:10] if "rec" in p_ else None,
                      "last_close": round(float(P[t_]["c"][-1]), 2),
                      "shares": round(float(p_["sh"]), 6),
                      "marked_at_entry_not_last_close": True}

    cell_b = {
        "generated_at": generated_at,
        "n_grade_a_windows": len(a_set),
        "paper_exit_reasons": {k: int(v) for k, v in
                               sorted(pd.Series([r.get("reason") for r in led_paper])
                                      .value_counts().to_dict().items())} if led_paper else {},
        "b1_absent_bar_positions": b1,
        "paper_ledger_hash": _sha16(_ledger_key(led_paper)),
        "paper_n_ledger": len(led_paper),
        "paper_final_equity": round(float(out_paper["equity"]), 2),
        "paper_cash": round(float(out_paper["cash"]), 2),
        "paper_open_positions": sorted(out_paper["open_positions"]),
        "paper_curve_hash": _sha16(_curve_key(out_paper["curve"])),
        "uncapped_ledger_hash": _sha16(_ledger_key(led_all)),
        "uncapped_n_ledger": len(led_all),
        "uncapped_open_positions": sorted(out_all["open_positions"]),
        # the UNCAPPED ledger funds every Grade-A signal, so its exit mix is the full lifecycle —
        # the capped book's mix depends on who won the cash race and is not a coverage guarantee.
        "uncapped_exit_reasons": {k: int(v) for k, v in
                                  sorted(pd.Series([r.get("reason") for r in led_all])
                                         .value_counts().to_dict().items())} if led_all else {},
        "envelope_hash": _sha16(envelope),
        "n_signals": len(envelope["signals"]),
        "sig_hist_hash": _sha16(sig_hist),
        "analytics": analytics,
        "portfolio_hash": _sha16(portfolio),
        "hist_rows": len(hist_df),
    }

    # ── cell C: the live configuration WITH the B-1 staleness gate ON ──
    # Same call as cell B plus stale_absent_days = the momentum engine's STALE_ABSENT_DAYS. This
    # cell exists so the B-1 fix's effect is a COMMITTED, inspectable diff rather than a claim:
    # everything that is not the suspended holding must be identical to cell B.
    from run_bhanushali_cron import LIVE_STALENESS
    led_fix: list = []
    out_fix = R94.backtest(P, None, ledger=led_fix, start=START_FIX, return_state=True,
                           a_grade=a_set, **LIVE_DISCIPLINE, **LIVE_EXIT, **LIVE_STALENESS)
    led_fix_all: list = []
    out_fix_all = R94.backtest(P, None, ledger=led_fix_all, start=START_FIX, return_state=True,
                               uncapped=True, a_grade=a_set, **LIVE_DISCIPLINE, **LIVE_EXIT,
                               **LIVE_STALENESS)
    env_fix, sig_hist_fix, analytics_fix, portfolio_fix, hist_df_fix = build_envelopes(
        P, out_fix_all, led_fix_all, out_fix, generated_at, mem=None)
    stale_rows = [r for r in led_fix if r.get("reason") == "stale"]
    cell_c = {
        "stale_absent_days": int(LIVE_STALENESS["stale_absent_days"]),
        "uncapped_ledger_hash": _sha16(_ledger_key(led_fix_all)),
        "uncapped_n_ledger": len(led_fix_all),
        "uncapped_open_positions": sorted(out_fix_all["open_positions"]),
        "uncapped_exit_reasons": {k: int(v) for k, v in
                                  sorted(pd.Series([r.get("reason") for r in led_fix_all])
                                         .value_counts().to_dict().items())} if led_fix_all else {},
        "envelope_hash": _sha16(env_fix),
        "n_signals": len(env_fix["signals"]),
        "sig_hist_hash": _sha16(sig_hist_fix),
        "analytics": analytics_fix,
        "portfolio_hash": _sha16(portfolio_fix),
        "hist_rows": len(hist_df_fix),
        # ── constitution D5 receipt: the card arithmetic, and what it WOULD have printed before
        # the parity fix (stop = the raw signal-week low). Kept permanently so the divergence the
        # fix closed stays inspectable without digging through git history.
        "fresh_cards": _fresh_card_probe(env_fix),
        "paper_ledger_hash": _sha16(_ledger_key(led_fix)),
        "paper_n_ledger": len(led_fix),
        "paper_final_equity": round(float(out_fix["equity"]), 2),
        "paper_cash": round(float(out_fix["cash"]), 2),
        "paper_open_positions": sorted(out_fix["open_positions"]),
        "paper_curve_hash": _sha16(_curve_key(out_fix["curve"])),
        "paper_exit_reasons": {k: int(v) for k, v in
                               sorted(pd.Series([r.get("reason") for r in led_fix])
                                      .value_counts().to_dict().items())} if led_fix else {},
        "stale_exits": [{"tkr": r["tkr"], "entry_date": str(r["entry_date"])[:10],
                         "exit_date": str(r["exit_date"])[:10], "entry": r["entry"],
                         "exit_px": r["exit_px"], "R": r["R"],
                         "stale_absent_sessions": r.get("stale_absent_sessions")}
                        for r in stale_rows],
        # the diff vs cell B, precomputed so the commit message and the test agree
        "diff_vs_live_config": {
            "closed_trades_delta": len(led_fix) - len(led_paper),
            "final_equity_delta": round(float(out_fix["equity"]) - float(out_paper["equity"]), 2),
            "positions_released": sorted(set(out_paper["open_positions"])
                                         - set(out_fix["open_positions"])),
            "positions_added": sorted(set(out_fix["open_positions"])
                                      - set(out_paper["open_positions"])),
        },
    }
    return cell_a, cell_b, cell_c


def main() -> int:
    FIXDIR.mkdir(parents=True, exist_ok=True)
    ohlcv, index = synth_universe()

    rows = []
    for t, df in ohlcv.items():
        d = df.reset_index().rename(columns={"index": "date"})
        d.insert(0, "ticker", t)
        rows.append(d)
    d = index.rename("Close").to_frame().reset_index().rename(columns={"index": "date"})
    d["Open"] = d["High"] = d["Low"] = d["Close"]
    d["Volume"] = 0.0
    d.insert(0, "ticker", "__INDEX__")
    rows.append(d[["ticker", "date", "Open", "High", "Low", "Close", "Volume"]])
    pd.concat(rows, ignore_index=True).to_csv(OHLCV_CSV, index=False)

    cell_a, cell_b, cell_c = run_cells(ohlcv, index)
    expected = {
        "_note": ("R94 golden master (constitution M1). cell frozen_defaults may NEVER change; "
                  "cell live_config changes only with a documented owner config change — "
                  "regenerate via scripts/build_r94_golden_fixture.py in the SAME commit and "
                  "state the diff. cell live_config_b1_fixed is the same live config with the "
                  "B-1 staleness gate ON; its diff_vs_live_config block IS the fix's receipt."),
        "fixture_csv_sha16": hashlib.sha256(OHLCV_CSV.read_bytes()).hexdigest()[:16],
        "frozen_defaults": cell_a,
        "live_config": cell_b,
        "live_config_b1_fixed": cell_c,
    }
    EXPECTED_JSON.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    print(f"fixture  -> {OHLCV_CSV}")
    print(f"expected -> {EXPECTED_JSON}")
    print(json.dumps({"frozen_defaults": {k: cell_a[k] for k in ('trades', 'sharpe', 'exit_reasons')},
                      "live_config": {k: cell_b[k] for k in ('paper_n_ledger', 'paper_exit_reasons',
                                                             'n_signals', 'paper_open_positions',
                                                             'b1_absent_bar_positions')},
                      "live_config_b1_fixed": {k: cell_c[k] for k in
                                               ('paper_n_ledger', 'paper_exit_reasons',
                                                'stale_exits', 'diff_vs_live_config')}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
