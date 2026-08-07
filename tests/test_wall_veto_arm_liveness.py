"""The forward wall must refuse to log a veto arm that cannot veto.

`forward/prereg.md` registers the wall as a three-book comparison — base, veto-0.1, drift — written
one atomic row at a time into a hash-chained, append-only log. The chain makes the rows tamper-
evident: a later reader is meant to be able to trust that what was logged is what was known on the
day it was logged.

`nq.research.residual.residual_ranks` inner-joins each name's returns to the FF-India factor panel.
Past the factors' last date the join produces no rows, so `resid_rank` is NaN for every name on
every session and the veto condition `resid_rank < VETO_Q` is never true. The veto book then steps
the unmodified panel and finishes byte-identical to base — no error, no empty column, nothing to
notice. On 2026-08-08 `data/ff_india_factors.parquet` ended **2026-06-29**, before the wall's own
registered start floor of 2026-07-02, so this was the state the wall would have started in.

The result would not have been a broken arm. It would have been a *perfect agreement* between two
books written into a tamper-evident log, certifying that an independent shadow book concurred with
base when only one book ever ran — and it could not be retracted afterwards without breaking the
chain that gives the log its value.

So the guard refuses to log at all, matching `config.assert_calendar_covers` one layer down: past
the coverage of an input that a real-world commitment depends on, refuse to guess.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from config import load_frozen_cfg
from nq.paper.book import PaperBook
from nq.paper.wall_cron import VetoArmUnavailable, update_wall
from nq.research.residual import residual_ranks

N_SESSIONS = 300
# Cover all but the last 8 sessions. This has to clear REG_WIN (252) + SKIP (21) + 5 or
# `residual_ranks` produces no scores for ANY name and raises "No objects to concatenate" instead —
# a second, louder failure mode that is not the one this file is about. The dangerous case is the
# quiet one: plenty of history, ranks that simply stop before the sessions being logged.
FACTOR_SESSIONS = N_SESSIONS - 8


def _panel_and_factors(factors_path, *, factor_sessions: int | None = None) -> pd.DataFrame:
    """A 300-session synthetic panel (> REG_WIN 252 + SKIP 21, so residual ranks exist) with a
    factor panel that optionally stops early — reproducing the live shape of the defect."""
    rng = np.random.default_rng(7)
    dates = pd.bdate_range("2024-01-01", periods=N_SESSIONS)
    factor_end = dates[factor_sessions - 1] if factor_sessions is not None else None
    tks = [f"T{i:02d}" for i in range(12)]
    close = dict.fromkeys(tks, 100.0)
    rows, fac = [], []
    for d in dates:
        rets = {t: float(rng.normal(0.0006, 0.02)) for t in tks}
        for t in tks:
            close[t] *= 1.0 + rets[t]
            c = close[t]
            rows.append({"date": d, "ticker": t, "open": c * 0.999, "high": c * 1.01,
                         "low": c * 0.99, "close": c, "atr_pct_63": 2.0, "adv_rupees_20d": 1e9})
        if factor_end is None or d <= factor_end:
            fac.append({"date": d, "mkt": float(np.mean(list(rets.values()))),
                        "hml": float(rng.normal(0, 0.005))})
    panel = pd.DataFrame(rows).sort_values(["ticker", "date"])
    panel["trend_rank"] = (panel.groupby("ticker")["close"].pct_change(63)
                           .groupby(panel["date"]).rank(pct=True))
    panel["date"] = pd.to_datetime(panel["date"])
    pd.DataFrame(fac).to_parquet(factors_path, index=False)
    return panel


def test_stale_factors_make_the_arm_inert_at_the_source():
    """The mechanism, isolated. This is what the guard exists to catch, stated as a fact about
    `residual_ranks` rather than about the wall — if this ever stops being true, the guard's
    reasoning needs revisiting even if its assertion still passes."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as td:
        facp = Path(td) / "ff.parquet"
        panel = _panel_and_factors(facp, factor_sessions=FACTOR_SESSIONS)
        factors = pd.read_parquet(facp).set_index("date").sort_index()
        rr = residual_ranks(panel[["date", "ticker", "close"]], factors)

    assert not rr.empty, "fixture is degenerate — no residual ranks at all"
    assert rr["date"].max() < panel["date"].max(), (
        "residual_ranks produced scores past the factor coverage — the inner join no longer "
        "truncates, so re-derive what the veto arm actually does past the factor end"
    )


def test_the_wall_refuses_to_log_an_inert_veto_arm(tmp_path):
    cfg = load_frozen_cfg()
    facp = tmp_path / "ff.parquet"
    panel = _panel_and_factors(facp, factor_sessions=FACTOR_SESSIONS)

    base = PaperBook(cfg)
    base.run_batch(panel)

    with pytest.raises(VetoArmUnavailable) as exc:
        update_wall(base, panel, cfg, state_dir=tmp_path, factors_path=facp, holidays=[])

    msg = str(exc.value)
    assert "byte-identical to base" in msg, "the message must name the failure, not just the symptom"
    assert "ff_india_factors" in msg and "forward/prereg.md" in msg, (
        "an operator hitting this in eight months needs both remedies in the message: extend the "
        "factor panel, or amend the pre-registration to retire the arm"
    )


def test_nothing_is_written_when_the_arm_is_unavailable(tmp_path):
    """The point of raising rather than warning. A partially-written wall is the outcome the chain
    cannot recover from."""
    cfg = load_frozen_cfg()
    facp = tmp_path / "ff.parquet"
    panel = _panel_and_factors(facp, factor_sessions=FACTOR_SESSIONS)
    base = PaperBook(cfg)
    base.run_batch(panel)

    with pytest.raises(VetoArmUnavailable):
        update_wall(base, panel, cfg, state_dir=tmp_path, factors_path=facp, holidays=[])

    assert not (tmp_path / "forward_wall.csv").exists(), (
        "a wall row was appended despite the veto arm being unavailable"
    )


def test_a_live_arm_still_logs_and_actually_differs_from_base(tmp_path):
    """The paired positive, and the assertion the original integration test was missing: it checked
    that a veto row exists, not that the veto book ever diverged. A row whose veto column merely
    *equals* base is exactly the artifact this file is about."""
    cfg = load_frozen_cfg()
    facp = tmp_path / "ff.parquet"
    panel = _panel_and_factors(facp)          # factors cover the whole panel

    base = PaperBook(cfg)
    base.run_batch(panel)
    assert update_wall(base, panel, cfg, state_dir=tmp_path, factors_path=facp, holidays=[]) > 0

    from nq.paper.forward_wall import read_verified
    rows = [r for r in read_verified(tmp_path / "forward_wall.csv") if r["status"] == "ok"]
    assert rows, "no ok rows were written"
    assert any(float(r["veto_equity"]) != float(r["base_equity"]) for r in rows), (
        "the veto book tracked base exactly on every logged session. Either the arm is inert and "
        "the guard missed it, or the fixture cannot distinguish the two books."
    )
