"""Forward-wall daily-writer integration test (nq.paper.wall_cron.update_wall).

Verifies the operational glue: stepping the base book + a residual-veto book off one panel produces a
chain-verified 3-book row whose base NAV reconciles to the paper book by construction, and that a
re-run is idempotent (the chain refuses a double-run). Primitive-level gap/double-run/drift are already
covered by test_forward_wall_job.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import load_frozen_cfg
from nq.paper.book import PaperBook
from nq.paper.forward_wall import read_verified
from nq.paper.wall_cron import update_wall


def _synthetic(tmp_factors) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    dates = pd.bdate_range("2024-01-01", periods=300)          # > 252 + 21 so residual ranks exist
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
        fac.append({"date": d, "mkt": float(np.mean(list(rets.values()))), "hml": float(rng.normal(0, 0.005))})
    panel = pd.DataFrame(rows).sort_values(["ticker", "date"])
    panel["trend_rank"] = panel.groupby("ticker")["close"].pct_change(63).groupby(panel["date"]).rank(pct=True)
    panel["date"] = pd.to_datetime(panel["date"])
    pd.DataFrame(fac).to_parquet(tmp_factors, index=False)
    return panel


def test_update_wall_reconciles_verifies_and_is_idempotent(tmp_path):
    cfg = load_frozen_cfg()
    facp = tmp_path / "ff.parquet"
    panel = _synthetic(facp)

    base = PaperBook(cfg)
    base.run_batch(panel)                                       # step the operational base book
    n = update_wall(base, panel, cfg, state_dir=tmp_path, factors_path=facp, holidays=[])
    assert n > 0

    rows = read_verified(tmp_path / "forward_wall.csv")         # chain intact (raises otherwise)
    assert rows[-1]["status"] == "ok"
    for f in ("base_equity", "veto_equity", "drift_equity", "drift_mult"):
        assert rows[-1][f] != ""                                # one atomic row, all three books + drift state
    # reconciliation: the wall's base NAV == the paper book NAV, to the cent (one source, not a recompute)
    assert abs(float(rows[-1]["base_equity"]) - base.equity_curve[-1]["equity"]) < 0.01
    # idempotent: a second call appends nothing (the chain's date guard refuses a double-run)
    assert update_wall(base, panel, cfg, state_dir=tmp_path, factors_path=facp, holidays=[]) == 0


def test_a_stall_is_logged_as_gaps_and_only_the_latest_session_is_a_row(tmp_path):
    """forward/prereg.md §3 rule 4: "a missed day is a gap, never reconstructed."

    The 2026-08-24..28 stall would otherwise have entered the chain as five `ok` rows — recomputed
    history that a later reader cannot tell from rows written on the day. This asserts the shape of
    the log after a catch-up, which is the thing the chain itself cannot check.
    """
    cfg = load_frozen_cfg()
    facp = tmp_path / "ff.parquet"
    panel = _synthetic(facp)
    dates = sorted(panel["date"].unique())

    # Log up to a first session, then let the wall fall four sessions behind.
    early = panel[panel["date"] <= dates[-5]]
    b1 = PaperBook(cfg)
    b1.run_batch(early)
    update_wall(b1, early, cfg, state_dir=tmp_path, factors_path=facp, holidays=[])
    logged_through = read_verified(tmp_path / "forward_wall.csv")[-1]["date"]

    b2 = PaperBook(cfg)
    b2.run_batch(panel)
    n = update_wall(b2, panel, cfg, state_dir=tmp_path, factors_path=facp, holidays=[])

    rows = read_verified(tmp_path / "forward_wall.csv")          # chain still intact
    new = [r for r in rows if r["date"] > logged_through]
    assert n == 1, "only the most recent session may be logged as an observation"
    assert new[-1]["status"] == "ok", "the current session must still be logged"
    assert [r["status"] for r in new[:-1]] == ["gap"] * (len(new) - 1)
    assert len(new) > 1, "the fixture did not actually produce a stall to catch up from"
    for r in new[:-1]:
        assert r["base_equity"] == "", "a gap carries no book fields — it is not an observation"


def test_the_owner_override_restores_the_reconstruction(tmp_path):
    """`backfill=True` is a deliberate override of §3 rule 4, so it must actually do something."""
    cfg = load_frozen_cfg()
    facp = tmp_path / "ff.parquet"
    panel = _synthetic(facp)
    dates = sorted(panel["date"].unique())

    early = panel[panel["date"] <= dates[-5]]
    b1 = PaperBook(cfg)
    b1.run_batch(early)
    update_wall(b1, early, cfg, state_dir=tmp_path, factors_path=facp, holidays=[])

    b2 = PaperBook(cfg)
    b2.run_batch(panel)
    n = update_wall(b2, panel, cfg, state_dir=tmp_path, factors_path=facp, holidays=[],
                    backfill=True)
    assert n > 1, "the override must log every missed session, not just the latest"
    assert all(r["status"] == "ok" for r in read_verified(tmp_path / "forward_wall.csv")[-n:])
