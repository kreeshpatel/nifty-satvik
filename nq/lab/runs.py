"""Strategy Lab engine replay + multiplicity meter.

WHY A METER

The lab makes trying a config free, and a free search is the exact thing that manufactures a Sharpe. So
every DISTINCT config that is run is written to ``lab_runs.jsonl`` and the app deflates each Sharpe by
``n_configs_tried()``. Re-running a config already seen (cache hit) does not add a row: the meter counts
ideas, not clicks. It does not replace the program's own n_trials ledger — it is a lower bound on the
search the lab itself has done.

TRAIN ONLY

Every price series is cut at :data:`CUT` before the engine sees it and the cut is *asserted*, so the
sealed 2024H2+ slice can never reach a replay. Reported stats start no earlier than :data:`MIN_START`;
earlier bars are warm-up only. Nothing here edits a production path: the engine is imported read-only
and driven exactly as `pipelines/diagnostics/diag_giveback_ratchet_0148.py` drives it.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from nq.validation.dsr import deflated_sharpe_ratio, expected_max_sharpe

ROOT = Path(__file__).resolve().parents[2]
CUT = "2024-06-30"
MIN_START = "2019-01-01"
CACHE_DIR = ROOT / "lab_cache"
RUNS_PATH = ROOT / "lab_runs.jsonl"
TRADING_DAYS, WINDOW = 252, 63

# The live book, spelled as the lab's override keys. ``grade_gate`` True = trade Grade-A only (the live
# a_grade set); ``exit`` "live" = config P scaled exit, "base" = the engine's own default exit;
# ``pit_membership`` see replay().
DEFAULT_CONFIG: dict[str, Any] = {
    "ext_cap": 0.20, "grade_gate": True, "uncapped": False,
    "max_notional_pct": 0.20, "max_risk_pct": 0.10, "exit": "live", "start": MIN_START,
    "pit_membership": True,
}


class CutViolation(AssertionError):
    """A price series reached past :data:`CUT` — the sealed slice must never reach the engine."""


# --------------------------------------------------------------------------- the CUT
def assert_within_cut(ohlcv: Mapping[str, pd.DataFrame], cut: str = CUT) -> pd.Timestamp | None:
    """Raise :class:`CutViolation` if any series has a bar after ``cut``; return the last bar seen."""
    last = max((pd.DatetimeIndex(df.index).max() for df in ohlcv.values() if len(df)), default=None)
    if last is not None and last > pd.Timestamp(cut):
        raise CutViolation(f"sealed data reached the lab: last bar {last.date()} > CUT {cut}")
    return last


def cut_universe(ohlcv: Mapping[str, pd.DataFrame], cut: str = CUT, min_bars: int = 60) -> dict[str, pd.DataFrame]:
    """Truncate every series at ``cut``, drop stubs, and assert the result is clean."""
    out = {t: df[pd.DatetimeIndex(df.index) <= pd.Timestamp(cut)] for t, df in ohlcv.items()}
    out = {t: df for t, df in out.items() if len(df) > min_bars}
    assert_within_cut(out, cut)
    return out


# --------------------------------------------------------------------------- config & cache key
def normalize_config(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Defaults + overrides, validated, with canonical types so equal configs hash equal."""
    c = {**DEFAULT_CONFIG, **(dict(config) if config else {})}
    unknown = set(c) - set(DEFAULT_CONFIG)
    if unknown:
        raise ValueError(f"unknown lab config keys: {sorted(unknown)}")
    if c["exit"] not in ("live", "base"):
        raise ValueError(f"exit must be 'live' or 'base', got {c['exit']!r}")
    c["start"] = str(pd.Timestamp(c["start"]).date())
    if not MIN_START <= c["start"] < CUT:
        raise ValueError(f"start must be in [{MIN_START}, {CUT}): earlier bars are warm-up only")
    for k in ("ext_cap", "max_notional_pct", "max_risk_pct"):
        c[k] = None if c[k] is None else float(c[k])
    for k in ("grade_gate", "uncapped", "pit_membership"):
        c[k] = bool(c[k])
    return c


def config_hash(config: Mapping[str, Any] | None = None) -> str:
    """sha256 of the canonical (normalised, sorted-key, compact) config JSON."""
    blob = json.dumps(normalize_config(config), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- multiplicity meter
def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def record_run(config: Mapping[str, Any], sharpe: float, path: Path | None = None) -> bool:
    """Append {config_hash, config, ran_at, sharpe} unless this config is already on the ledger.

    Returns True when a row was written (a NEW distinct config)."""
    p = Path(path) if path else RUNS_PATH
    cfg = normalize_config(config)
    h = config_hash(cfg)
    if any(r["config_hash"] == h for r in _rows(p)):
        return False
    ok = sharpe is not None and np.isfinite(sharpe)
    row = {"config_hash": h, "config": cfg, "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "sharpe": float(sharpe) if ok else None}
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return True


def n_configs_tried(path: Path | None = None) -> int:
    """Number of DISTINCT configs ever run in the lab (the DSR's n_trials)."""
    return len({r["config_hash"] for r in _rows(Path(path) if path else RUNS_PATH)})


def deflated_sharpe(sharpe: float, n_returns: int, n_trials: int, *, skew: float = 0.0,
                    kurt: float = 3.0) -> dict[str, float]:
    """Deflate an annual Sharpe by the lab's search size, via `nq.validation.dsr`.

    The repo's convention (`nq.runner.research`) is the PER-WINDOW basis: a book that holds ~63 days has
    ~``n_returns/63`` effectively independent observations, not ``n_returns``. So the annual Sharpe is
    converted to per-window units (``/ sqrt(252/63)``) and ``n_obs = n_returns // 63``.

    The cross-trial Sharpe variance that sets the expected-max benchmark is the sampling variance of a
    Sharpe over that many windows, ``1 / n_obs`` (a documented proxy; the lab has no cross-trial spread
    until it has many runs). Returns ``dsr`` (probability the Sharpe beats the N-trial max, 0-1),
    ``sr0_annual`` (that expected-max Sharpe, annualised) and ``deflated_sharpe = sharpe - sr0_annual``.
    """
    n_obs = int(n_returns) // WINDOW
    nan = float("nan")
    if n_obs <= 1 or not np.isfinite(sharpe):
        return {"dsr": nan, "sr0_annual": nan, "deflated_sharpe": nan, "n_trials": int(n_trials), "n_obs": n_obs}
    scale = float(np.sqrt(TRADING_DAYS / WINDOW))
    var_w = 1.0 / n_obs
    k = max(1, int(n_trials))
    dsr = deflated_sharpe_ratio(sharpe / scale, n_obs, skewness=skew, kurtosis=kurt,
                                n_trials=k, sharpe_variance=var_w)
    sr0 = expected_max_sharpe(k, var_w) * scale
    return {"dsr": dsr, "sr0_annual": sr0, "deflated_sharpe": float(sharpe) - sr0,
            "n_trials": int(n_trials), "n_obs": n_obs}


# --------------------------------------------------------------------------- engine replay
def _engine():
    """Lazy, read-only import of the production engine (scripts/ is not a package)."""
    for p in (ROOT, ROOT / "scripts"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import run_bhanushali_weekly_rank as R94
    from run_bhanushali_cron import (LIVE_DISCIPLINE, LIVE_EXIT, LIVE_PREP, LIVE_STALENESS,
                                     load_demerger_rows)
    from run_bhanushali_path1 import corrected_universe
    live = dict(LIVE_DISCIPLINE=LIVE_DISCIPLINE, LIVE_EXIT=LIVE_EXIT, LIVE_PREP=LIVE_PREP,
                LIVE_STALENESS=LIVE_STALENESS)
    return R94, live, load_demerger_rows, corrected_universe


def load_nifty(cut: str = CUT) -> pd.Series:
    """Nifty-50 closes from the committed benchmark CSV (as `scripts/diag_portfolio_risk.py`), cut at CUT."""
    _engine()                                        # puts scripts/ on sys.path
    import run_bhanushali_weekly_crs as CRS
    n50 = pd.read_csv(CRS.NIFTY50_CSV, parse_dates=["date"]).set_index("date")["nifty50_close"].sort_index()
    n50.index = pd.DatetimeIndex(n50.index).normalize()
    n50 = n50[~n50.index.duplicated(keep="last")].sort_index()
    n50 = n50[n50.index <= pd.Timestamp(cut)]
    if len(n50) and n50.index.max() > pd.Timestamp(cut):
        raise CutViolation("index series past CUT")
    return n50


def load_cut_universe() -> dict[str, pd.DataFrame]:
    """The corrected universe, cut at CUT and asserted (for the app's trade-quality / holdings panels)."""
    return cut_universe(_engine()[3]())


def replay(config: Mapping[str, Any] | None = None, *, use_cache: bool = True,
           cache_dir: Path | None = None, runs_path: Path | None = None,
           ohlcv: Mapping[str, pd.DataFrame] | None = None) -> dict[str, Any]:
    """Run the engine under ``config`` (train window only) and return nav / ledger / logs.

    Mirrors `diag_giveback_ratchet_0148.py`: cut -> `prep_weekly_rank` -> demerger events -> `backtest`
    with the LIVE_* blocks, overriding only the lab's keys. ``pit_membership`` True (DEFAULT) applies
    `load_membership()` exactly as the live cron does: a name is buyable only while it is a Nifty-500
    member (measured 20.5% CAGR / 1.025 Sharpe / -40.1% MaxDD, 2019-01-01..2024-06-28). False passes
    ``mem=None``, which is what several older diagnostics did (0148, diag_stop_width,
    diag_portfolio_risk): that book can buy names outside the index and reads 39.4% / 1.666. It is
    NOT the live book, so it is available only as an explicit, labelled comparison. The
    corporate-action HOLD stays OFF (a 5.5-year reconstruction has no owner to resolve a freeze;
    `diag_portfolio_risk` SPEC A1).

    Returns ``{"config", "config_hash", "nav", "ledger", "position_log", "event_log", "sharpe", "maxdd",
    "cagr", "n_trades", "last_bar", "seconds", "cached"}``. The result is pickled under ``lab_cache/``
    keyed by the config hash, and the run is added to the multiplicity ledger once.
    """
    cfg = normalize_config(config)
    h = config_hash(cfg)
    cdir = Path(cache_dir) if cache_dir else CACHE_DIR
    f = cdir / f"{h}.pkl"
    if use_cache and f.exists():
        res = pd.read_pickle(f)
        res["cached"] = True
        record_run(cfg, res["sharpe"], runs_path)       # no-op if already on the ledger
        return res

    t0 = time.time()
    R94, live, load_demerger_rows, corrected_universe = _engine()
    from nq.data.membership import load_membership
    cut = cut_universe(ohlcv if ohlcv is not None else corrected_universe())
    last = assert_within_cut(cut)
    P = R94.prep_weekly_rank(cut, **live["LIVE_PREP"])
    events = R94.build_demerger_events(cut, load_demerger_rows(), **live["LIVE_PREP"])
    mem = load_membership() if cfg["pit_membership"] else None

    discipline = {**live["LIVE_DISCIPLINE"], "ext_cap": cfg["ext_cap"],
                  "max_notional_pct": cfg["max_notional_pct"], "max_risk_pct": cfg["max_risk_pct"]}
    exit_cfg = live["LIVE_EXIT"] if cfg["exit"] == "live" else {}
    ledger: list = []
    plog: list = []
    elog: list = []
    out = R94.backtest(P, mem, ledger=ledger, start=cfg["start"], uncapped=cfg["uncapped"],
                       a_grade=R94.grade_a_entries(P) if cfg["grade_gate"] else None,
                       **discipline, **exit_cfg, **live["LIVE_STALENESS"],
                       demerger_events=events, position_log=plog, event_log=elog)
    nav = pd.Series(out["curve"], dtype=float)
    nav.index = pd.DatetimeIndex(nav.index).normalize()
    nav = nav[~nav.index.duplicated(keep="last")].sort_index()
    nav = nav[nav.index >= pd.Timestamp(cfg["start"])]
    r = nav.pct_change().dropna()
    sharpe = float(r.mean() / r.std() * np.sqrt(TRADING_DAYS)) if len(r) > 2 and r.std() > 0 else float("nan")
    res = {"config": cfg, "config_hash": h, "nav": nav, "ledger": pd.DataFrame(ledger),
           "position_log": pd.DataFrame(plog), "event_log": pd.DataFrame(elog),
           "sharpe": sharpe, "maxdd": float((nav / nav.cummax() - 1).min()), "cagr": float(out["cagr"]),
           "n_trades": int(len(ledger)), "last_bar": str(last.date()),
           "seconds": round(time.time() - t0, 1), "cached": False}
    cdir.mkdir(parents=True, exist_ok=True)
    pd.to_pickle(res, f)
    record_run(cfg, sharpe, runs_path)
    return res
