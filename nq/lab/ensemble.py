"""Strategy Lab ensemble: re-run one config under small, decision-irrelevant perturbations -> a noise band.

WHY

`diagnostics/research/engine_assumptions/2026-10-20_batch.md` found PATH CHAOS: adding +50bp of cost RAISED
CAGR by 4.6pp, because a tiny change reshuffles which signals win the scarce seats. A single replay is
therefore one draw from a distribution, and a single-replay delta below ~0.2 Sharpe is not a measurement.
This module measures that distribution so a candidate can be judged against it (paired, same draws).

THE PERTURBATIONS (each is decision-irrelevant: nothing here changes WHAT the strategy is)

(a) COST JITTER. One draw ``delta ~ U(-10bp, +10bp)`` is ADDED to every transaction-cost leg (buy and sell
    alike, so +-10bp per side, +-20bp round trip), floored so a leg never goes negative. Done by rebinding
    ``R94._cost_leg`` in-process for the duration of a run and restoring it in a ``finally``. The engine is
    NOT edited. ``_cost_leg`` is not told which side it is pricing, so the two sides share one draw.
(b) START-DATE JITTER. The engine's ``start`` is drawn from the first 20 trading days of 2019
    (``2019-01-01`` + 0..19 business days). Starting later or earlier changes the capital path and which
    signals are met with free cash. Every path is REPORTED on the common window ``report_from``..CUT as a
    CONTINUOUS SLICE of that path's own NAV (never a fresh-capital re-run from the window start, which
    resets the equity peak and manufactures a pass; CLAUDE.md).
(c) FILL-ORDER TIE JITTER. SKIPPED, by inspection. The engine sorts fill candidates by
    ``key = (-rank, ticker)`` (``scripts/run_bhanushali_weekly_rank.py``, ``sorted(cands, key=_key)``), a
    TOTAL order: equal CRS ranks are already broken deterministically by ticker, and ``rank`` is a
    continuous CRS distance. Perturbing the order of exact ties would be a change to the engine's tie rule,
    not a noise draw, so it is not offered. :data:`TIE_JITTER_SKIPPED` records why; ``perturb=("ties",)``
    raises.

PAIRING. The draws depend only on ``(n, seed, perturb)``, never on the config, so two configs run with the
same arguments see identical perturbations path by path. :func:`compare_ensembles` refuses to difference two
ensembles whose draws differ.

TRAIN ONLY. Prices are cut at :data:`nq.lab.runs.CUT` and the cut is asserted both when the context is built
and again before every ensemble (`CutViolation`). Nothing here reads the sealed judge log.
"""
from __future__ import annotations

import contextlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Mapping, Sequence

import numpy as np
import pandas as pd

from nq.lab import runs as L
from nq.lab.stats import r_sanity_flags

TIE_JITTER_SKIPPED = ("fill-order tie jitter skipped: the engine's candidate key is (-rank, ticker), a total "
                      "order, so ties are already broken deterministically and jittering them would change "
                      "the engine's tie rule rather than sample noise")
PERTURBATIONS = ("cost", "start")
COST_JITTER = 0.0010                    # +-10bp per side
START_JITTER_DAYS = 20                  # first ~20 trading days of the window
REPORT_FROM = "2019-03-01"              # common reporting window start (a slice, never a re-run)
DEFAULT_SEED = 20261102
TRADING_DAYS = 252
METRICS = ("sharpe", "cagr", "maxdd", "trades")


# --------------------------------------------------------------------------- context (built once, shared)
@dataclass
class EnsembleContext:
    """Prepared, CUT-asserted engine inputs shared by every path of every config."""
    P: dict
    mem: Any
    events: dict
    last_bar: pd.Timestamp
    ohlcv_ids: str = ""
    _a_grade: dict = field(default_factory=dict)

    def a_grade(self, mode: str):
        """The Grade-A set. ``default`` = the live set; ``filter_before_rank`` = D6 (membership-aware)."""
        if mode not in self._a_grade:
            R94 = L._engine()[0]
            if mode == "default":
                self._a_grade[mode] = R94.grade_a_entries(self.P)
            elif mode == "filter_before_rank":
                self._a_grade[mode] = R94.grade_a_entries(self.P, mem=self.mem, filter_before_rank=True)
            else:
                raise ValueError(f"grade_mode must be 'default' or 'filter_before_rank', got {mode!r}")
        return self._a_grade[mode]


def _assert_context_cut(ctx: EnsembleContext) -> None:
    if pd.Timestamp(ctx.last_bar) > pd.Timestamp(L.CUT):
        raise L.CutViolation(f"sealed data reached the ensemble: last bar {pd.Timestamp(ctx.last_bar).date()} > CUT {L.CUT}")
    last = max((pd.Timestamp(s["dates"][-1]) for s in ctx.P.values() if len(s["dates"])), default=None)
    if last is not None and last > pd.Timestamp(L.CUT):
        raise L.CutViolation(f"sealed data reached the prepared panel: last bar {last.date()} > CUT {L.CUT}")


def prepare_context(ohlcv: Mapping[str, pd.DataFrame] | None = None, *, mem: Any = "pit",
                    demerger_rows: Sequence | None = None) -> EnsembleContext:
    """Cut -> assert -> `prep_weekly_rank` -> demerger events -> membership, exactly as `runs.replay` does.

    ``mem="pit"`` loads `load_membership()` (the live gate); pass a dict (tests) or None to override.
    ``ohlcv`` defaults to the corrected universe; ``demerger_rows`` to the registered demergers."""
    R94, live, load_demerger_rows, corrected_universe = L._engine()
    cut = L.cut_universe(ohlcv if ohlcv is not None else corrected_universe())
    last = L.assert_within_cut(cut)
    P = R94.prep_weekly_rank(cut, **live["LIVE_PREP"])
    as_of = max((pd.Timestamp(s["dates"][-1]) for s in P.values()), default=None)
    rows = load_demerger_rows() if demerger_rows is None else demerger_rows
    events = R94.build_demerger_events(cut, rows, **{**live["LIVE_PREP"], "as_of": as_of})
    if isinstance(mem, str) and mem == "pit":
        from nq.data.membership import load_membership
        mem = load_membership()
    ctx = EnsembleContext(P=P, mem=mem, events=events, last_bar=last)
    _assert_context_cut(ctx)
    return ctx


# --------------------------------------------------------------------------- draws (config-independent)
def draw_perturbations(n: int, seed: int, perturb: Sequence[str] = PERTURBATIONS, *,
                       start_base: str = L.MIN_START, jitter: float = COST_JITTER,
                       start_days: int = START_JITTER_DAYS) -> pd.DataFrame:
    """The n perturbation draws: columns ``path``, ``cost_delta`` (fraction), ``start`` (ISO date).

    Depends ONLY on ``(n, seed, perturb, start_base, jitter, start_days)`` so any two configs share it.
    Unselected perturbations are held at their neutral value (delta 0, start = ``start_base``)."""
    bad = [p for p in perturb if p not in PERTURBATIONS]
    if "ties" in bad:
        raise ValueError(TIE_JITTER_SKIPPED)
    if bad:
        raise ValueError(f"unknown perturbation(s) {bad}; choose from {PERTURBATIONS}")
    rng = np.random.default_rng(int(seed))
    cost = rng.uniform(-jitter, jitter, size=int(n))             # always drawn: stream position is fixed
    k = rng.integers(0, int(start_days), size=int(n))
    days = pd.bdate_range(start_base, periods=int(start_days))
    return pd.DataFrame({
        "path": np.arange(int(n)),
        "cost_delta": cost if "cost" in perturb else np.zeros(int(n)),
        "start": [str(days[int(j)].date()) if "start" in perturb else str(days[0].date()) for j in k],
    })


@contextlib.contextmanager
def cost_jitter(delta: float) -> Iterator[None]:
    """Rebind ``R94._cost_leg`` so every leg costs ``max(0, original + delta)``; always restores it."""
    R94 = L._engine()[0]
    orig = R94._cost_leg
    if delta:
        def jittered(adv, notional, cost_off=False, _o=orig, _d=float(delta)):
            return 0.0 if cost_off else max(0.0, _o(adv, notional, cost_off) + _d)
        R94._cost_leg = jittered
    try:
        yield
    finally:
        R94._cost_leg = orig


# --------------------------------------------------------------------------- one path
def slice_metrics(nav: pd.Series, ledger: pd.DataFrame, report_from: str, end: str = L.CUT) -> dict[str, float]:
    """Sharpe / CAGR / MaxDD / trades of a CONTINUOUS SLICE ``report_from..end`` of one run's NAV."""
    nav = nav[(nav.index >= pd.Timestamp(report_from)) & (nav.index <= pd.Timestamp(end))].astype(float)
    nan = float("nan")
    out = {"sharpe": nan, "cagr": nan, "maxdd": nan, "trades": 0, "mean_R": nan, "mean_R_ex_degen": nan,
           "n_degenerate": 0}
    if len(nav) > 2:
        r = nav.pct_change().dropna()
        if r.std() > 0:
            out["sharpe"] = float(r.mean() / r.std() * np.sqrt(TRADING_DAYS))
        years = (nav.index[-1] - nav.index[0]).days / 365.25
        if years > 0 and nav.iloc[0] > 0 and nav.iloc[-1] > 0:
            out["cagr"] = float((nav.iloc[-1] / nav.iloc[0]) ** (1 / years) - 1)
        out["maxdd"] = float((nav / nav.cummax() - 1).min())
    if len(ledger):
        ed = pd.to_datetime(ledger["entry_date"]).dt.normalize()
        led = ledger[(ed >= pd.Timestamp(report_from)) & (ed <= pd.Timestamp(end))]
        out["trades"] = int(len(led))
        if len(led):
            fl = r_sanity_flags(led)
            ok = ~fl["degenerate_stop"].to_numpy()
            out["n_degenerate"] = int((~ok).sum())
            out["mean_R"] = float(led["R"].astype(float).mean())
            if ok.any():
                out["mean_R_ex_degen"] = float(led.loc[ok, "R"].astype(float).mean())
    return out


def run_path(config: Mapping[str, Any], ctx: EnsembleContext, *, cost_delta: float = 0.0,
             start: str | None = None, grade_mode: str = "default", report_from: str = REPORT_FROM,
             keep_ledger: bool = False) -> dict[str, Any]:
    """One engine run under one perturbation draw. Returns metrics (+ the ledger if asked)."""
    R94 = L._engine()[0]
    cfg = L.normalize_config(config)
    if start is not None:
        cfg = {**cfg, "start": str(pd.Timestamp(start).date())}
    kw = L.engine_kwargs(cfg)
    ledger: list = []
    a_grade = ctx.a_grade(grade_mode) if cfg["grade_gate"] else None
    with cost_jitter(cost_delta):
        out = R94.backtest(ctx.P, ctx.mem, ledger=ledger, a_grade=a_grade, **kw, demerger_events=ctx.events)
    nav = pd.Series(out["curve"], dtype=float)
    nav.index = pd.DatetimeIndex(nav.index).normalize()
    nav = nav[~nav.index.duplicated(keep="last")].sort_index()
    led = pd.DataFrame(ledger)
    res = slice_metrics(nav, led, report_from)
    if keep_ledger:
        res["ledger"] = led
    return res


# --------------------------------------------------------------------------- ensemble + summary
def _summ(x: pd.Series) -> dict[str, float]:
    v = pd.to_numeric(x, errors="coerce").dropna().to_numpy(float)
    if not len(v):
        return {"median": float("nan"), "p5": float("nan"), "p95": float("nan"), "mean": float("nan"), "n": 0}
    return {"median": float(np.median(v)), "p5": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95)),
            "mean": float(v.mean()), "n": int(len(v))}


def replay_ensemble(config: Mapping[str, Any] | None = None, *, n: int = 30, seed: int = DEFAULT_SEED,
                    perturb: Sequence[str] = PERTURBATIONS, context: EnsembleContext | None = None,
                    grade_mode: str = "default", report_from: str = REPORT_FROM,
                    start_base: str = L.MIN_START, keep_ledger: bool = False,
                    progress: Callable[[int, int], None] | None = None) -> dict[str, Any]:
    """Run the lab config ``n`` times under the seeded perturbations and summarise the noise band.

    ``context`` shares the prepared panel across configs (build once with :func:`prepare_context`).
    ``grade_mode`` ``filter_before_rank`` = D6 (not a lab config key; it is labelled in the manifest).
    Returns ``{config, config_hash, grade_mode, manifest, n, seed, perturb, skipped, draws, paths, summary,
    report_from, seconds}``; ``paths`` is a DataFrame (one row per path) with sharpe/cagr/maxdd/trades and
    per-trade mean R raw and ex degenerate stops; ``summary`` is {metric: {median, p5, p95, mean, n}}."""
    cfg = L.normalize_config(config)
    ctx = context if context is not None else prepare_context()
    _assert_context_cut(ctx)
    draws = draw_perturbations(n, seed, perturb, start_base=start_base)
    t0 = time.time()
    rows, ledgers = [], {}
    for k, d in draws.iterrows():
        m = run_path(cfg, ctx, cost_delta=float(d["cost_delta"]), start=str(d["start"]),
                     grade_mode=grade_mode, report_from=report_from, keep_ledger=keep_ledger)
        if keep_ledger:
            ledgers[int(d["path"])] = m.pop("ledger")
        rows.append({"path": int(d["path"]), "cost_delta": float(d["cost_delta"]), "start": str(d["start"]), **m})
        if progress:
            progress(int(k) + 1, int(n))
    paths = pd.DataFrame(rows)
    ekw = {**L.engine_kwargs(cfg), "grade_gate": cfg["grade_gate"]}
    if grade_mode != "default":
        ekw["a_grade"] = grade_mode                       # not an engine kwarg: only here so the label names it
    from nq.runner.manifest import build_manifest
    manifest = build_manifest(ekw, membership="pit" if cfg["pit_membership"] else "none",
                              data_vintage=str(pd.Timestamp(ctx.last_bar).date()), window=(report_from, L.CUT))
    res = {"config": cfg, "config_hash": L.config_hash(cfg), "grade_mode": grade_mode, "manifest": manifest,
           "n": int(n), "seed": int(seed), "perturb": list(perturb), "skipped": [TIE_JITTER_SKIPPED],
           "draws": draws, "paths": paths, "report_from": report_from,
           "summary": {m: _summ(paths[m]) for m in (*METRICS, "mean_R", "mean_R_ex_degen")},
           "seconds": round(time.time() - t0, 1)}
    if keep_ledger:
        res["ledgers"] = ledgers
    return res


# --------------------------------------------------------------------------- paired comparison
def compare_ensembles(a: Mapping[str, Any], b: Mapping[str, Any]) -> dict[str, Any]:
    """Paired differences ``b - a`` over the SAME perturbation draws.

    Raises ValueError if the two ensembles were not drawn identically (different n/seed/perturb).
    ``paths`` holds the per-path differences; ``summary`` the median and 5-95% band of each; ``share_better``
    the fraction of paths on which b's Sharpe beats a's. ``robust`` is the reading rule's test: the 5th
    percentile of the paired dSharpe is above zero (otherwise the difference is inside path noise)."""
    da, db = a["draws"].reset_index(drop=True), b["draws"].reset_index(drop=True)
    if not da.equals(db):
        raise ValueError("ensembles were not drawn identically (n/seed/perturb differ); paired comparison refused")
    pa, pb = a["paths"].set_index("path"), b["paths"].set_index("path")
    d = pd.DataFrame({"path": pa.index})
    d = d.set_index("path")
    for m in METRICS:
        d["d_" + m] = pb[m].astype(float) - pa[m].astype(float)
    for m in ("mean_R", "mean_R_ex_degen"):
        d["d_" + m] = pb[m].astype(float) - pa[m].astype(float)
    summ = {c[2:]: _summ(d[c]) for c in d.columns}
    ds = d["d_sharpe"].dropna()
    share = float((ds > 0).mean()) if len(ds) else float("nan")
    p5 = summ["sharpe"]["p5"]
    return {"paths": d.reset_index(), "summary": summ, "share_better": share, "n_paired": int(len(ds)),
            "robust": bool(np.isfinite(p5) and p5 > 0),
            "a_hash": a.get("config_hash"), "b_hash": b.get("config_hash")}


def ensemble_to_json(res: Mapping[str, Any]) -> dict[str, Any]:
    """A JSON-safe view of an ensemble result (no frames)."""
    return {"config": res["config"], "config_hash": res["config_hash"], "grade_mode": res["grade_mode"],
            "manifest_label": res["manifest"]["label"], "differs_on": res["manifest"]["differs_on"],
            "n": res["n"], "seed": res["seed"], "perturb": res["perturb"], "skipped": res["skipped"],
            "report_from": res["report_from"], "summary": res["summary"],
            "paths": json.loads(res["paths"].to_json(orient="records"))}
